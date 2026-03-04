import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, TemplateRef, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, combineLatest, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { indicatorDetailPageStyles } from './indicator-detail-page.styles';
import { indicatorDetailPageTemplate } from './indicator-detail-page.template';
import {
  type DetailTableRow,
  type DetailVm,
  type IndicatorDetailContext,
  type IndicatorTab,
  DEFAULT_REPORT_CYCLE,
  buildIndicatorDetailVm,
  emptyDatasets,
  emptyMethods,
  emptySeries,
  toTab,
} from './indicator-detail-page.helpers';
import { type NbmsContextOption, DEFAULT_NBMS_CONTEXT } from '../models/context.models';
import type { IndicatorDimension } from '../models/api.models';
import type { IndicatorViewRoutePatch, IndicatorViewRouteState } from '../models/indicator-visual.models';
import { DownloadRecordService } from '../services/download-record.service';
import { IndicatorPackRegistryService } from '../services/indicator-pack-registry.service';
import { IndicatorService } from '../services/indicator.service';
import { IndicatorViewStateService } from '../services/indicator-view-state.service';
import { NbmsCalloutComponent } from '../ui/nbms-callout.component';
import { NbmsContextBarComponent } from '../ui/nbms-context-bar.component';
import { NbmsIndicatorViewHostComponent } from '../ui/nbms-indicator-view-host.component';
import { NbmsInterpretationEditorComponent } from '../ui/nbms-interpretation-editor.component';
import { NbmsShareMenuComponent } from '../ui/nbms-share-menu.component';
import { NbmsReadinessBadgeComponent } from '../ui/nbms-readiness-badge.component';
import { NbmsStatusPillComponent } from '../ui/nbms-status-pill.component';
import { NbmsToastService } from '../ui/nbms-toast.service';

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
    MatButtonModule,
    MatIconModule,
    NbmsCalloutComponent,
    NbmsContextBarComponent,
    NbmsIndicatorViewHostComponent,
    NbmsInterpretationEditorComponent,
    NbmsReadinessBadgeComponent,
    NbmsShareMenuComponent,
    NbmsStatusPillComponent,
  ],
  template: indicatorDetailPageTemplate,
  styles: [indicatorDetailPageStyles],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IndicatorDetailPageComponent {
  @ViewChild('detailTableCell', { static: true })
  detailTableCellTemplate!: TemplateRef<{ $implicit: DetailTableRow; key: string }>;

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly indicators = inject(IndicatorService);
  private readonly downloads = inject(DownloadRecordService);
  private readonly toast = inject(NbmsToastService);
  private readonly viewState = inject(IndicatorViewStateService);
  private readonly packs = inject(IndicatorPackRegistryService);

  readonly tableColumns: Array<{ key: keyof DetailTableRow | 'value' | 'status'; label: string }> = [
    { key: 'year', label: 'Year' },
    { key: 'region', label: 'Region' },
    { key: 'geographyType', label: 'Geography type' },
    { key: 'value', label: 'Value' },
    { key: 'status', label: 'Status' },
    { key: 'notes', label: 'Notes' },
  ];

  private readonly indicatorUuid$ = this.route.paramMap.pipe(
    map((params) => params.get('uuid') ?? ''),
    shareReplay(1),
  );

  readonly state$ = this.viewState.connect(this.route, {
    defaults: this.viewState.defaultState({
      ...DEFAULT_NBMS_CONTEXT,
      tab: 'indicator',
      report_cycle: 'NR7-2024',
      release: 'latest_approved',
      method: 'current',
      agg: 'province',
      metric: 'value',
      top_n: 20,
    }),
  });

  readonly detail$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicators.detail(uuid)),
    shareReplay(1),
  );

  readonly datasets$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicators.datasets(uuid).pipe(catchError(() => of(emptyDatasets(uuid))))),
    shareReplay(1),
  );

  readonly methods$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicators.methods(uuid).pipe(catchError(() => of(emptyMethods(uuid))))),
    shareReplay(1),
  );

  readonly pack$ = this.indicatorUuid$.pipe(
    switchMap((uuid) =>
      this.packs.getPack(uuid).pipe(catchError(() => of(null))),
    ),
    shareReplay(1),
  );

  readonly visualProfile$ = this.pack$.pipe(
    map((pack) => pack?.profile || null),
    shareReplay(1),
  );

  readonly dimensions$ = this.pack$.pipe(
    map((pack) => pack?.dimensions || ([] as IndicatorDimension[])),
    shareReplay(1),
  );

  readonly yearSeries$ = combineLatest([this.indicatorUuid$, this.state$]).pipe(
    switchMap(([uuid, state]) =>
      this.indicators
        .series(uuid, {
          agg: 'year',
          report_cycle: state.report_cycle,
          release: state.release,
          method: state.method,
          geo_type: state.geo_type,
          geo_code: state.geo_code || undefined,
          start_year: state.start_year ?? undefined,
          end_year: state.end_year ?? undefined,
          metric: state.metric,
        })
        .pipe(catchError(() => of(emptySeries(uuid, 'year')))),
    ),
    shareReplay(1),
  );

  readonly provinceHistory$ = combineLatest([this.indicatorUuid$, this.state$]).pipe(
    switchMap(([uuid, state]) =>
      this.indicators
        .series(uuid, {
          agg: 'province',
          report_cycle: state.report_cycle,
          release: state.release,
          method: state.method,
          start_year: state.start_year ?? undefined,
          end_year: state.end_year ?? undefined,
          metric: state.metric,
        })
        .pipe(catchError(() => of(emptySeries(uuid, 'province')))),
    ),
    shareReplay(1),
  );

  readonly yearOptions$ = combineLatest([this.yearSeries$, this.visualProfile$]).pipe(
    map(([series, profile]) => {
      const fromSeries = series.results
        .map((row) => Number(row.bucket))
        .filter((year) => Number.isFinite(year))
        .sort((a, b) => a - b);
      if (fromSeries.length) {
        return fromSeries;
      }
      return profile?.meta?.time_range?.available_years || [];
    }),
    shareReplay(1),
  );

  readonly provinceSnapshot$ = combineLatest([this.indicatorUuid$, this.state$]).pipe(
    switchMap(([uuid, state]) =>
      this.indicators
        .series(uuid, {
          agg: 'province',
          report_cycle: state.report_cycle,
          release: state.release,
          method: state.method,
          start_year: state.end_year ?? state.start_year ?? undefined,
          end_year: state.end_year ?? state.start_year ?? undefined,
          metric: state.metric,
        })
        .pipe(catchError(() => of(emptySeries(uuid, 'province')))),
    ),
    shareReplay(1),
  );

  readonly detailContext$ = this.state$.pipe(
    map((state) => toDetailContext(state)),
    shareReplay(1),
  );

  readonly vm$ = combineLatest([
    this.detail$,
    this.datasets$,
    this.methods$,
    this.yearSeries$,
    this.provinceHistory$,
    this.provinceSnapshot$,
    this.yearOptions$,
    this.detailContext$,
  ]).pipe(
    map(([detail, datasets, methods, yearSeries, provinceHistory, provinceSnapshot, yearOptions, context]) =>
      buildIndicatorDetailVm(detail, datasets, methods, yearSeries, provinceHistory, provinceSnapshot, yearOptions, context, null),
    ),
    shareReplay(1),
  );

  readonly audit$ = this.indicatorUuid$.pipe(
    switchMap((uuid) =>
      this.indicators.audit(uuid).pipe(
        catchError(() =>
          of({
            indicator_uuid: uuid,
            events: [],
          }),
        ),
      ),
    ),
    shareReplay(1),
  );

  readonly indicatorSurface$ = combineLatest([this.state$, this.visualProfile$, this.dimensions$, this.yearOptions$]).pipe(
    map(([state, visualProfile, dimensions, years]) => ({
      state,
      visualProfile,
      dimensions,
      reportCycleOptions: buildReportCycleOptions(),
      releaseOptions: [{ value: 'latest_approved', label: 'Latest approved release' }] satisfies NbmsContextOption[],
      methodOptions: [{ value: 'current', label: 'Current method' }] satisfies NbmsContextOption[],
      geoTypeOptions: buildGeoTypeOptions(dimensions),
      yearOptions: years,
    })),
    shareReplay(1),
  );

  constructor() {
    this.visualProfile$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((profile) => {
        const current = this.viewState.parseQueryParams(this.route.snapshot.queryParamMap);
        if (profile && !current.view) {
          this.patchViewState({ view: profile.defaultView || 'timeseries' });
        }
      });
  }

  setTab(tab: IndicatorTab): void {
    this.patchViewState({ tab });
  }

  patchViewState(patch: IndicatorViewRoutePatch): void {
    this.viewState.update(this.route, patch);
  }

  resetIndicatorContext(): void {
    this.patchViewState({
      report_cycle: 'NR7-2024',
      release: 'latest_approved',
      method: 'current',
      geo_type: 'national',
      geo_code: '',
      start_year: null,
      end_year: null,
      agg: 'province',
      metric: 'value',
      dim: '',
      dim_value: '',
      compare: '',
      left: '',
      right: '',
      tax_level: '',
      tax_code: '',
      top_n: 20,
    });
  }

  requestApproval(): void {
    this.toast.warn('Request approval is not yet wired. Backend support is still needed for the release workflow action.');
  }

  createSeriesDownload(): void {
    const indicatorUuid = this.route.snapshot.paramMap.get('uuid');
    if (!indicatorUuid) {
      this.toast.warn('Indicator identifier is missing.');
      return;
    }
    this.downloads
      .create({
        record_type: 'indicator_series',
        object_type: 'indicator',
        object_uuid: indicatorUuid,
        query_snapshot: this.viewState.serialize(this.viewState.parseQueryParams(this.route.snapshot.queryParamMap)),
      })
      .subscribe({
        next: (payload) => {
          this.toast.success('Series download record created.');
          void this.router.navigate(['/downloads', payload.uuid]);
        },
        error: () => this.toast.error('Could not queue the series download record.'),
      });
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

  trackByAuditEvent(_: number, row: { event_id: number }): number {
    return row.event_id;
  }

  narrativeSeed(vm: DetailVm): Array<{ id: string; title: string; body: string }> {
    return [
      { id: 'interpretation', title: 'Interpretation', body: vm.interpretation },
      { id: 'key-messages', title: 'Key messages', body: vm.leadSummary },
      {
        id: 'data-limitations',
        title: 'Data limitations',
        body: vm.dataQualityNotes.map((note) => `${note.title}: ${note.body}`).join('\n\n') || 'No limitations have been published.',
      },
      {
        id: 'what-changed',
        title: 'What changed',
        body: vm.pipelineRows.map((row) => `${row.label}: ${row.value}`).join('\n'),
      },
    ];
  }
}

function toDetailContext(state: IndicatorViewRouteState): IndicatorDetailContext {
  return {
    tab: toTab(state.tab),
    report_cycle: state.report_cycle || DEFAULT_REPORT_CYCLE,
    method: state.method || 'current',
    dataset_release: state.release || 'latest_approved',
    geography: state.geo_type === 'province' || state.geo_type === 'biome' ? state.geo_type : 'national',
    start_year: state.start_year,
    end_year: state.end_year,
  };
}

function buildReportCycleOptions(): NbmsContextOption[] {
  return [
    { value: 'NR7-2024', label: 'NR7 2024' },
    { value: 'NR7-2022', label: 'NR7 2022' },
    { value: DEFAULT_REPORT_CYCLE, label: 'NR7 current' },
  ];
}

function buildGeoTypeOptions(dimensions: IndicatorDimension[]): NbmsContextOption[] {
  const geoOptions = dimensions
    .filter((row) => row.type === 'geo')
    .map((row) => ({ value: row.id, label: row.label }));
  return [{ value: 'national', label: 'National' }, ...geoOptions];
}
