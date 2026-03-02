import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, TemplateRef, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import {
  BehaviorSubject,
  catchError,
  combineLatest,
  distinctUntilChanged,
  map,
  of,
  shareReplay,
  startWith,
  switchMap,
  tap
} from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';

import { indicatorDetailPageStyles } from './indicator-detail-page.styles';
import { indicatorDetailPageTemplate } from './indicator-detail-page.template';
import {
  type DetailTableRow,
  type DetailVm,
  type IndicatorDetailContext,
  type IndicatorTab,
  type GeographyFocus,
  DEFAULT_REPORT_CYCLE,
  buildBarOptions,
  buildIndicatorDetailVm,
  buildLineOptions,
  emptySeries,
  emptyDatasets,
  emptyMethods,
  normalizeContext,
  toGeography,
  toNullableNumber,
  toTab
} from './indicator-detail-page.helpers';
import { DownloadRecordService } from '../services/download-record.service';
import { IndicatorService } from '../services/indicator.service';
import { NbmsCalloutComponent } from '../ui/nbms-callout.component';
import { NbmsDataTableComponent } from '../ui/nbms-data-table.component';
import { NbmsKpiCardComponent } from '../ui/nbms-kpi-card.component';
import { NbmsMapCardComponent } from '../ui/nbms-map-card.component';
import { NbmsReadinessBadgeComponent } from '../ui/nbms-readiness-badge.component';
import { NbmsStatusPillComponent } from '../ui/nbms-status-pill.component';
import { NbmsToastService } from '../ui/nbms-toast.service';

// TODO(nbms-backend): Support report_cycle, method, and dataset_release filters on
// GET /api/indicators/:uuid/series and GET /api/indicators/:uuid/map, and add
// GET /api/indicators/:uuid/series?agg=biome for biome analytics and distribution cards.

@Component({
  selector: 'app-indicator-detail-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    NgSwitchDefault,
    RouterLink,
    ReactiveFormsModule,
    BaseChartDirective,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule,
    NbmsCalloutComponent,
    NbmsDataTableComponent,
    NbmsKpiCardComponent,
    NbmsMapCardComponent,
    NbmsReadinessBadgeComponent,
    NbmsStatusPillComponent
  ],
  template: indicatorDetailPageTemplate,
  styles: [indicatorDetailPageStyles],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IndicatorDetailPageComponent {
  @ViewChild('detailTableCell', { static: true })
  detailTableCellTemplate!: TemplateRef<{ $implicit: DetailTableRow; key: string }>;

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly indicatorService = inject(IndicatorService);
  private readonly downloadRecords = inject(DownloadRecordService);
  private readonly toast = inject(NbmsToastService);

  readonly contextForm = new FormGroup({
    tab: new FormControl<IndicatorTab>('indicator', { nonNullable: true }),
    report_cycle: new FormControl<string>(DEFAULT_REPORT_CYCLE, { nonNullable: true }),
    method: new FormControl<string>('', { nonNullable: true }),
    dataset_release: new FormControl<string>('', { nonNullable: true }),
    geography: new FormControl<GeographyFocus>('national', { nonNullable: true }),
    start_year: new FormControl<number | null>(null),
    end_year: new FormControl<number | null>(null)
  });

  readonly tableColumns: Array<{ key: keyof DetailTableRow | 'value' | 'status'; label: string }> = [
    { key: 'year', label: 'Year' },
    { key: 'region', label: 'Region' },
    { key: 'geographyType', label: 'Geography type' },
    { key: 'value', label: 'Value' },
    { key: 'status', label: 'Status' },
    { key: 'notes', label: 'Notes' }
  ];

  private readonly activeRegionSubject = new BehaviorSubject<string | null>(null);

  private readonly indicatorUuid$ = this.route.paramMap.pipe(
    map((params) => params.get('uuid') ?? ''),
    shareReplay(1)
  );

  readonly detail$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.detail(uuid)),
    shareReplay(1)
  );

  readonly datasets$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.datasets(uuid).pipe(catchError(() => of(emptyDatasets(uuid))))),
    shareReplay(1)
  );

  readonly methods$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.methods(uuid).pipe(catchError(() => of(emptyMethods(uuid))))),
    shareReplay(1)
  );

  readonly yearSeries$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.series(uuid, { agg: 'year' }).pipe(catchError(() => of(emptySeries(uuid, 'year'))))),
    shareReplay(1)
  );

  readonly provinceHistory$ = this.indicatorUuid$.pipe(
    switchMap((uuid) =>
      this.indicatorService.series(uuid, { agg: 'province' }).pipe(catchError(() => of(emptySeries(uuid, 'province'))))
    ),
    shareReplay(1)
  );

  readonly yearOptions$ = this.yearSeries$.pipe(
    map((series) =>
      series.results
        .map((row) => Number(row.bucket))
        .filter((year) => Number.isFinite(year))
        .sort((a, b) => a - b)
    ),
    shareReplay(1)
  );

  readonly context$ = combineLatest([
    this.contextForm.valueChanges.pipe(startWith(this.contextForm.getRawValue())),
    this.yearOptions$
  ]).pipe(
    map(([value, years]) => normalizeContext(value, years)),
    distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
    tap((context) => {
      this.patchContext(context);
      this.syncUrl(context);
    }),
    shareReplay(1)
  );

  private readonly selectedYear$ = this.context$.pipe(
    map((context) => context.end_year),
    distinctUntilChanged(),
    shareReplay(1)
  );

  readonly provinceSnapshot$ = combineLatest([this.indicatorUuid$, this.selectedYear$]).pipe(
    switchMap(([uuid, year]) =>
      this.indicatorService
        .series(uuid, { agg: 'province', year: year ?? undefined })
        .pipe(catchError(() => of(emptySeries(uuid, 'province'))))
    ),
    shareReplay(1)
  );

  readonly vm$ = combineLatest([
    this.detail$,
    this.datasets$,
    this.methods$,
    this.yearSeries$,
    this.provinceHistory$,
    this.provinceSnapshot$,
    this.yearOptions$,
    this.context$,
    this.activeRegionSubject.asObservable()
  ]).pipe(
    map(([detail, datasets, methods, yearSeries, provinceHistory, provinceSnapshot, yearOptions, context, activeRegion]) =>
      buildIndicatorDetailVm(detail, datasets, methods, yearSeries, provinceHistory, provinceSnapshot, yearOptions, context, activeRegion)
    ),
    shareReplay(1)
  );

  readonly lineOptions = buildLineOptions();
  readonly barOptions = buildBarOptions();

  constructor() {
    const params = this.route.snapshot.queryParamMap;
    this.contextForm.patchValue(
      {
        tab: toTab(params.get('tab')),
        report_cycle: params.get('report_cycle') ?? DEFAULT_REPORT_CYCLE,
        method: params.get('method') ?? '',
        dataset_release: params.get('dataset_release') ?? params.get('release') ?? '',
        geography: toGeography(params.get('geography') ?? params.get('geo_type')),
        start_year: toNullableNumber(params.get('start_year')),
        end_year: toNullableNumber(params.get('end_year'))
      },
      { emitEvent: false }
    );

    this.contextForm.controls.geography.valueChanges
      .pipe(startWith(this.contextForm.controls.geography.value), takeUntilDestroyed(this.destroyRef))
      .subscribe((geography) => {
        if (geography !== 'province') {
          this.activeRegionSubject.next(null);
        }
      });
  }

  setTab(tab: IndicatorTab): void {
    this.contextForm.controls.tab.setValue(tab);
  }

  toggleRegionFocus(region: string): void {
    if (this.contextForm.controls.geography.value !== 'province') {
      this.contextForm.controls.geography.setValue('province');
    }
    this.activeRegionSubject.next(this.activeRegionSubject.value === region ? null : region);
  }

  clearRegionFocus(): void {
    this.activeRegionSubject.next(null);
  }

  onBreakdownChartClick(event: { active?: Array<{ index?: number }> }, vm: DetailVm): void {
    const index = event.active?.[0]?.index;
    if (typeof index !== 'number' || index < 0 || index >= vm.breakdownRows.length) {
      return;
    }
    this.toggleRegionFocus(vm.breakdownRows[index].region);
  }

  resetAnalyticsFilters(vm: DetailVm): void {
    this.activeRegionSubject.next(null);
    this.contextForm.patchValue({
      report_cycle: DEFAULT_REPORT_CYCLE,
      method: '',
      dataset_release: '',
      geography: 'national',
      start_year: vm.defaultStartYear,
      end_year: vm.defaultEndYear
    });
  }

  async copyPageLink(): Promise<void> {
    const href = globalThis.location?.href;
    if (!href || !globalThis.navigator?.clipboard) {
      this.toast.warn('Clipboard access is not available.');
      return;
    }
    try {
      await globalThis.navigator.clipboard.writeText(href);
      this.toast.success('Indicator link copied.');
    } catch {
      this.toast.error('Could not copy the indicator link.');
    }
  }

  requestApproval(): void {
    // TODO(nbms-backend): Expose the selected series UUID so the detail page can call
    // POST /api/indicator-series/:seriesUuid/workflow for a request-approval action.
    this.toast.warn('Request approval is not yet wired. Backend support is needed for the release workflow action.');
  }

  createSeriesDownload(): void {
    const indicatorUuid = this.route.snapshot.paramMap.get('uuid');
    if (!indicatorUuid) {
      this.toast.warn('Indicator identifier is missing.');
      return;
    }
    this.downloadRecords
      .create({
        record_type: 'indicator_series',
        object_type: 'indicator',
        object_uuid: indicatorUuid,
        query_snapshot: { aggregation: 'year' }
      })
      .subscribe({
        next: (payload) => {
          this.toast.success('Series download record created.');
          void this.router.navigate(['/downloads', payload.uuid]);
        },
        error: () => this.toast.error('Could not queue the series download record.')
      });
  }

  trackByLabel(_: number, row: { label: string }): string {
    return row.label;
  }

  trackByValue(_: number, row: { value: string }): string {
    return row.value;
  }

  trackByText(_: number, row: { label?: string; title?: string; region?: string; key?: string } | string): string {
    if (typeof row === 'string') {
      return row;
    }
    return row.label ?? row.title ?? row.region ?? row.key ?? '';
  }

  trackByYear(_: number, year: number): number {
    return year;
  }

  trackByKey(_: number, row: { key: string }): string {
    return row.key;
  }

  private patchContext(context: IndicatorDetailContext): void {
    const current = this.contextForm.getRawValue();
    if (JSON.stringify(current) === JSON.stringify(context)) {
      return;
    }
    this.contextForm.patchValue(context, { emitEvent: false });
  }

  private syncUrl(context: IndicatorDetailContext): void {
    const queryParams: Record<string, string | null> = {
      tab: context.tab,
      report_cycle: context.report_cycle || null,
      method: context.method || null,
      release: context.dataset_release || null,
      dataset_release: context.dataset_release || null,
      geo_type: context.geography || null,
      geography: context.geography || null,
      start_year: context.start_year ? String(context.start_year) : null,
      end_year: context.end_year ? String(context.end_year) : null
    };
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams,
      queryParamsHandling: '',
      replaceUrl: true
    });
  }
}
