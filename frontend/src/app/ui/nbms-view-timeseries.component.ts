import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault, TitleCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { Observable, ReplaySubject, catchError, combineLatest, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import type { IndicatorDetailResponse, IndicatorDimension, IndicatorMapResponse, IndicatorSeriesResponse, IndicatorVisualProfile } from '../models/api.models';
import type { IndicatorViewRoutePatch, IndicatorViewRouteState, IndicatorViewSummary } from '../models/indicator-visual.models';
import { IndicatorAnalyticsService } from '../services/indicator-analytics.service';
import { buildStandardBarOptions, buildStandardLineOptions } from '../utils/chart-options.utils';
import { readCssVar, withAlpha } from '../utils/theme.utils';
import { IndicatorMapPanelComponent } from '../components/indicator-map-panel.component';
import { NbmsDataTableComponent } from './nbms-data-table.component';
import { NbmsDistributionCardGridComponent } from './nbms-distribution-card-grid.component';
import {
  buildGovernanceCallouts,
  buildSliceKpis,
  formatMetric,
  formatWholeNumber,
  groupIndicatorDimensions,
  percentOf,
} from './indicator-view.helpers';

type TimeseriesCard = {
  id: string;
  label: string;
  value: string;
  helperText: string;
  progress: number;
  active: boolean;
};

type TimeseriesRow = {
  slice: string;
  sliceCode: string;
  year: number;
  value: string;
  release: string;
  method: string;
  qa: string;
  evidence: string;
};

type TimeseriesVm = {
  loading: boolean;
  error: string | null;
  summary: IndicatorViewSummary;
  aggOptions: Array<{ value: string; label: string }>;
  metricOptions: string[];
  trendChart: ChartData<'line'> | null;
  breakdownChart: ChartData<'bar'> | null;
  comparisonCards: TimeseriesCard[];
  tableRows: TimeseriesRow[];
  mapPayload: IndicatorMapResponse | null;
  tableLabel: string;
  selectedYear: number | null;
};

@Component({
  selector: 'nbms-view-timeseries',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    NgSwitchDefault,
    TitleCasePipe,
    BaseChartDirective,
    MatFormFieldModule,
    MatSelectModule,
    IndicatorMapPanelComponent,
    NbmsDataTableComponent,
    NbmsDistributionCardGridComponent,
  ],
  template: `
    <section class="view-shell" *ngIf="vm$ | async as vm">
      <ng-container *ngIf="!vm.loading; else loadingState">
        <div class="view-toolbar">
          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>Breakdown level</mat-label>
            <mat-select [value]="state?.agg || aggValue(vm)" (valueChange)="setAgg($event)">
              <mat-option *ngFor="let option of vm.aggOptions; trackBy: trackByValue" [value]="option.value">
                {{ option.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" subscriptSizing="dynamic" *ngIf="vm.metricOptions.length">
            <mat-label>Map metric</mat-label>
            <mat-select [value]="state?.metric || 'value'" (valueChange)="stateChange.emit({ metric: $event })">
              <mat-option *ngFor="let metric of vm.metricOptions; trackBy: trackByValue" [value]="metric">
                {{ metric | titlecase }}
              </mat-option>
            </mat-select>
          </mat-form-field>
        </div>

        <div class="chart-grid" *ngIf="!vm.error; else errorState">
          <article class="panel nbms-card-surface">
            <header class="panel-head">
              <div>
                <p class="eyebrow">Trend</p>
                <h3>Time series</h3>
              </div>
              <span>{{ vm.selectedYear ? 'Latest year ' + vm.selectedYear : 'No year selected' }}</span>
            </header>
            <div class="chart-wrap" *ngIf="vm.trendChart; else noTrend">
              <canvas baseChart [type]="'line'" [data]="vm.trendChart" [options]="lineOptions"></canvas>
            </div>
          </article>

          <article class="panel nbms-card-surface">
            <header class="panel-head">
              <div>
                <p class="eyebrow">Breakdown</p>
                <h3>Current slice by {{ (state?.agg || aggValue(vm)) | titlecase }}</h3>
              </div>
              <span>{{ vm.comparisonCards.length }} rows</span>
            </header>
            <div class="chart-wrap" *ngIf="vm.breakdownChart; else noBreakdown">
              <canvas baseChart [type]="'bar'" [data]="vm.breakdownChart" [options]="barOptions" (chartClick)="onChartClick($event, vm)"></canvas>
            </div>
          </article>
        </div>

        <nbms-distribution-card-grid
          [cards]="vm.comparisonCards"
          (select)="selectSlice($event)"
        ></nbms-distribution-card-grid>

        <article class="panel nbms-card-surface">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Map</p>
              <h3>Spatial drilldown</h3>
            </div>
            <span *ngIf="vm.mapPayload?.meta?.legend as legend">
              {{ legend.metric | titlecase }} {{ legend.min ?? 'n/a' }} to {{ legend.max ?? 'n/a' }}
            </span>
          </header>
          <app-indicator-map-panel [featureCollection]="vm.mapPayload"></app-indicator-map-panel>
        </article>

        <nbms-data-table
          title="Auditable slice"
          [rows]="vm.tableRows"
          [columns]="tableColumns"
          [cellTemplate]="tableCell"
          [itemSize]="50"
        >
          <span table-actions>{{ vm.tableLabel }}</span>
        </nbms-data-table>
      </ng-container>

      <ng-template #loadingState>
        <div class="skeleton-grid">
          <div class="skeleton-block"></div>
          <div class="skeleton-block"></div>
          <div class="skeleton-block skeleton-block--wide"></div>
        </div>
      </ng-template>

      <ng-template #errorState>
        <div class="empty-state">{{ vm.error }}</div>
      </ng-template>

      <ng-template #noTrend><div class="empty-state">No time-series values are available for the current slice.</div></ng-template>
      <ng-template #noBreakdown><div class="empty-state">No comparison slice is available for the selected breakdown level.</div></ng-template>

      <ng-template #tableCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'slice'">
            <button type="button" class="table-link" (click)="selectSlice(row.sliceCode)">{{ row.slice }}</button>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .view-shell,
      .chart-grid,
      .view-toolbar,
      .skeleton-grid {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .view-toolbar {
        grid-template-columns: repeat(2, minmax(0, 240px));
      }

      .chart-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .panel {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4);
      }

      .panel-head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
      }

      .panel-head h3,
      .panel-head p,
      .table-link {
        margin: 0;
      }

      .eyebrow {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      .chart-wrap {
        min-height: 300px;
      }

      .table-link {
        border: 0;
        background: transparent;
        color: var(--nbms-text-primary);
        cursor: pointer;
        font: inherit;
        font-weight: 700;
        padding: 0;
        text-align: left;
      }

      .table-link:hover,
      .table-link:focus-visible {
        color: var(--nbms-accent-600);
        outline: none;
      }

      .empty-state {
        border: 1px dashed var(--nbms-border);
        border-radius: var(--nbms-radius-lg);
        color: var(--nbms-text-muted);
        padding: var(--nbms-space-4);
        text-align: center;
      }

      .skeleton-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .skeleton-block {
        min-height: 220px;
        border-radius: var(--nbms-radius-lg);
        background: linear-gradient(
          90deg,
          color-mix(in srgb, var(--nbms-surface-2) 88%, var(--nbms-surface)) 0%,
          color-mix(in srgb, var(--nbms-surface-muted) 70%, var(--nbms-surface)) 50%,
          color-mix(in srgb, var(--nbms-surface-2) 88%, var(--nbms-surface)) 100%
        );
        background-size: 200% 100%;
        animation: shimmer 1.3s linear infinite;
      }

      .skeleton-block--wide {
        grid-column: 1 / -1;
      }

      @keyframes shimmer {
        from { background-position: 200% 0; }
        to { background-position: -200% 0; }
      }

      @media (max-width: 900px) {
        .view-toolbar,
        .chart-grid,
        .skeleton-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NbmsViewTimeseriesComponent {
  @Input() set indicatorUuid(value: string) {
    this.patchInput({ indicatorUuid: value });
  }

  @Input() set indicatorDetail(value: IndicatorDetailResponse | null) {
    this.patchInput({ indicatorDetail: value });
  }

  @Input() set visualProfile(value: IndicatorVisualProfile | null) {
    this.patchInput({ visualProfile: value });
  }

  @Input() set dimensions(value: IndicatorDimension[]) {
    this.patchInput({ dimensions: value });
  }

  @Input() set state(value: IndicatorViewRouteState | null) {
    this.patchInput({ state: value });
  }

  @Output() readonly stateChange = new EventEmitter<IndicatorViewRoutePatch>();
  @Output() readonly summaryChange = new EventEmitter<IndicatorViewSummary>();

  readonly tableColumns = [
    { key: 'slice', label: 'Slice' },
    { key: 'year', label: 'Year' },
    { key: 'value', label: 'Value' },
    { key: 'release', label: 'Release' },
    { key: 'method', label: 'Method' },
    { key: 'qa', label: 'QA' },
    { key: 'evidence', label: 'Evidence' },
  ];

  readonly lineOptions = buildStandardLineOptions();
  readonly barOptions = buildStandardBarOptions(true);

  private readonly analytics = inject(IndicatorAnalyticsService);
  private readonly inputs$ = new ReplaySubject<{
    indicatorUuid: string;
    indicatorDetail: IndicatorDetailResponse | null;
    visualProfile: IndicatorVisualProfile | null;
    dimensions: IndicatorDimension[];
    state: IndicatorViewRouteState | null;
  }>(1);

  private currentInput = {
    indicatorUuid: '',
    indicatorDetail: null as IndicatorDetailResponse | null,
    visualProfile: null as IndicatorVisualProfile | null,
    dimensions: [] as IndicatorDimension[],
    state: null as IndicatorViewRouteState | null,
  };

  readonly vm$ = this.inputs$.pipe(
    switchMap((input) => {
      if (!input.indicatorUuid || !input.indicatorDetail || !input.visualProfile || !input.state) {
        return of(this.loadingVm());
      }
      const geoDimensions = groupIndicatorDimensions(input.dimensions).geographic;
      const aggValue = geoDimensions.some((row) => row.id === input.state?.agg)
        ? input.state.agg
        : geoDimensions[0]?.id || 'province';
      const trend$ = this.analytics.getSeries(input.indicatorUuid, {
        state: input.state,
        agg: 'year',
      });
      const breakdown$ = this.analytics.getSeries(input.indicatorUuid, {
        state: input.state,
        agg: aggValue,
        overrides: { geo_code: undefined },
      });
      const mapResponse$: Observable<IndicatorMapResponse | null> = input.visualProfile.mapLayers.length
        ? this.analytics.getMap(input.indicatorUuid, {
            state: input.state,
            layer: input.visualProfile.mapLayers[0].layerCode,
          })
        : of(null);

      return combineLatest([
        trend$.pipe(catchError((error) => of({ error: readError(error), payload: null }))),
        breakdown$.pipe(catchError((error) => of({ error: readError(error), payload: null }))),
        mapResponse$.pipe(catchError((error) => of({ error: readError(error), payload: null }))),
      ]).pipe(
        map(([trendResult, breakdownResult, mapResult]) => {
          const trendPayload = unwrapSeries(trendResult);
          const breakdownPayload = unwrapSeries(breakdownResult);
          const mapPayload = unwrapMap(mapResult);
          const error = readPayloadError(trendResult) || readPayloadError(breakdownResult) || null;
          const vm = buildTimeseriesVm({
            detail: input.indicatorDetail as IndicatorDetailResponse,
            state: input.state as IndicatorViewRouteState,
            dimensions: input.dimensions,
            trendPayload,
            breakdownPayload,
            mapPayload,
            aggValue,
          });
          const summary = {
            ...vm.summary,
            callouts: [
              ...vm.summary.callouts,
              ...buildGovernanceCallouts(input.indicatorDetail as IndicatorDetailResponse, input.state as IndicatorViewRouteState, mapPayload),
            ],
          };
          this.summaryChange.emit(summary);
          return { ...vm, error, summary };
        }),
        startWith(this.loadingVm()),
      );
    }),
    shareReplay(1),
  );

  get state(): IndicatorViewRouteState | null {
    return this.currentInput.state;
  }

  trackByValue(_: number, value: string | { value: string }): string {
    return typeof value === 'string' ? value : value.value;
  }

  aggValue(vm: TimeseriesVm): string {
    return vm.aggOptions[0]?.value || 'province';
  }

  setAgg(value: string): void {
    this.stateChange.emit({ agg: value, geo_type: 'national', geo_code: '' });
  }

  selectSlice(code: string): void {
    const current = this.currentInput.state;
    const agg = current?.agg || 'province';
    if (!code) {
      this.stateChange.emit({ geo_code: '' });
      return;
    }
    this.stateChange.emit({
      agg,
      geo_type: agg as IndicatorViewRouteState['geo_type'],
      geo_code: current?.geo_code === code ? '' : code,
    });
  }

  onChartClick(event: { active?: Array<{ index?: number }> }, vm: TimeseriesVm): void {
    const index = event.active?.[0]?.index;
    if (typeof index !== 'number') {
      return;
    }
    const card = vm.comparisonCards[index];
    if (card) {
      this.selectSlice(card.id);
    }
  }

  private patchInput(
    patch: Partial<{
      indicatorUuid: string;
      indicatorDetail: IndicatorDetailResponse | null;
      visualProfile: IndicatorVisualProfile | null;
      dimensions: IndicatorDimension[];
      state: IndicatorViewRouteState | null;
    }>,
  ): void {
    this.currentInput = { ...this.currentInput, ...patch };
    this.inputs$.next(this.currentInput);
  }

  private loadingVm(): TimeseriesVm {
    return {
      loading: true,
      error: null,
      summary: { kpis: [], callouts: [] },
      aggOptions: [],
      metricOptions: [],
      trendChart: null,
      breakdownChart: null,
      comparisonCards: [],
      tableRows: [],
      mapPayload: null,
      tableLabel: 'Loading slice...',
      selectedYear: null,
    };
  }
}

function unwrapSeries(
  value: IndicatorSeriesResponse | { payload: IndicatorSeriesResponse | null; error: string | null } | null,
): IndicatorSeriesResponse | null {
  if (!value) {
    return null;
  }
  return 'payload' in value ? value.payload : value;
}

function unwrapMap(
  value: IndicatorMapResponse | { payload: IndicatorMapResponse | null; error: string | null } | null,
): IndicatorMapResponse | null {
  if (!value) {
    return null;
  }
  return 'payload' in value ? value.payload : value;
}

function readPayloadError(value: unknown): string | null {
  if (!value || typeof value !== 'object' || !('error' in value)) {
    return null;
  }
  const error = (value as { error?: string | null }).error;
  return error || null;
}

function buildTimeseriesVm(options: {
  detail: IndicatorDetailResponse;
  state: IndicatorViewRouteState;
  dimensions: IndicatorDimension[];
  trendPayload: IndicatorSeriesResponse | null;
  breakdownPayload: IndicatorSeriesResponse | null;
  mapPayload: IndicatorMapResponse | null;
  aggValue: string;
}): TimeseriesVm {
  const trendRows = (options.trendPayload?.results || [])
    .map((row) => ({
      year: Number(row.bucket),
      value: typeof row.numeric_mean === 'number' ? row.numeric_mean : null,
    }))
    .filter((row) => Number.isFinite(row.year) && typeof row.value === 'number')
    .sort((a, b) => a.year - b.year);
  const unit = options.trendPayload?.meta?.units?.[0] || options.detail.series[0]?.unit || '';
  const selectedYear =
    options.trendPayload?.meta?.time_range?.selected_year ||
    options.state.end_year ||
    trendRows[trendRows.length - 1]?.year ||
    null;
  const breakdownRows = buildBreakdownRows(options.breakdownPayload, selectedYear, unit, options.state.geo_code);
  const comparisonCards = breakdownRows.map((row) => ({
    id: row.sliceCode,
    label: row.slice,
    value: row.value,
    helperText: row.release,
    progress: row.progress,
    active: row.sliceCode === options.state.geo_code,
  }));
  const trendChart = trendRows.length
    ? {
        labels: trendRows.map((row) => String(row.year)),
        datasets: [
          {
            data: trendRows.map((row) => row.value as number),
            borderColor: readCssVar('--nbms-color-secondary-500'),
            backgroundColor: withAlpha(readCssVar('--nbms-color-secondary-500'), 0.18),
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 5,
          },
        ],
      }
    : null;
  const breakdownChart = comparisonCards.length
    ? {
        labels: comparisonCards.map((row) => row.label),
        datasets: [
          {
            data: breakdownRows.map((row) => row.numericValue),
            backgroundColor: comparisonCards.map((row) =>
              row.active ? readCssVar('--nbms-color-primary-500') : withAlpha(readCssVar('--nbms-color-primary-500'), 0.58),
            ),
            borderRadius: 10,
            maxBarThickness: 28,
          },
        ],
      }
    : null;
  const latestValue = trendRows[trendRows.length - 1]?.value ?? null;
  const baselineValue = trendRows[0]?.value ?? null;
  const releaseLabel = String(options.trendPayload?.meta?.release_used?.['version'] || 'Latest approved');
  const methodLabel = String(options.trendPayload?.meta?.method_used?.['version'] || 'Current');
  const summary: IndicatorViewSummary = {
    kpis: buildSliceKpis({
      latestValue,
      comparisonValue: baselineValue,
      rowCount: breakdownRows.length || trendRows.length,
      unit,
      primaryLabel: 'Latest value',
      helper: selectedYear ? `Latest published reading in ${selectedYear}` : 'Latest published reading in the current slice.',
      provenanceLabel: `${releaseLabel} / ${methodLabel}`,
    }),
    callouts: [],
  };
  return {
    loading: false,
    error: null,
    summary,
    aggOptions: groupIndicatorDimensions(options.dimensions).geographic.map((row) => ({
      value: row.id,
      label: row.label,
    })),
    metricOptions:
      options.mapPayload?.meta?.available_metrics ||
      (options.detail.indicator.tags?.includes('spatial') ? ['value', 'change', 'coverage', 'uncertainty'] : []),
    trendChart,
    breakdownChart,
    comparisonCards,
    tableRows: buildTableRows({
      detail: options.detail,
      state: options.state,
      trendRows,
      breakdownRows,
      releaseLabel,
      methodLabel,
      selectedYear,
    }),
    mapPayload: options.mapPayload,
    tableLabel: `${formatWholeNumber(breakdownRows.length || trendRows.length)} rows, ${options.aggValue} slice`,
    selectedYear,
  };
}

function buildBreakdownRows(
  payload: IndicatorSeriesResponse | null,
  selectedYear: number | null,
  unit: string,
  activeCode: string,
): Array<TimeseriesRow & { numericValue: number; progress: number }> {
  const rows = (payload?.results || [])
    .map((bucket) => {
      const values = bucket.values || [];
      const preferred =
        values.find((value) => value.year === selectedYear && typeof value.value_numeric === 'number') ||
        [...values].reverse().find((value) => typeof value.value_numeric === 'number');
      if (!preferred || typeof preferred.value_numeric !== 'number') {
        return null;
      }
      return {
        slice: bucket.label || String(bucket.bucket),
        sliceCode: String(bucket.bucket),
        year: preferred.year,
        value: formatMetric(preferred.value_numeric, unit),
        numericValue: preferred.value_numeric,
        release: preferred.dataset_release?.version || 'Latest approved',
        method: String(payload?.meta?.method_used?.['version'] || 'Current'),
        qa: activeCode && activeCode === String(bucket.bucket) ? 'Focused slice' : 'In current slice',
        evidence: preferred.uncertainty ? '1+' : '0',
      };
    })
    .filter((row): row is TimeseriesRow & { numericValue: number; progress: number } => row !== null)
    .sort((a, b) => b.numericValue - a.numericValue || a.slice.localeCompare(b.slice));
  const max = Math.max(...rows.map((row) => row.numericValue), 0);
  return rows.map((row) => ({
    ...row,
    progress: percentOf(row.numericValue, max),
  }));
}

function buildTableRows(options: {
  detail: IndicatorDetailResponse;
  state: IndicatorViewRouteState;
  trendRows: Array<{ year: number; value: number | null }>;
  breakdownRows: Array<TimeseriesRow & { numericValue: number; progress: number }>;
  releaseLabel: string;
  methodLabel: string;
  selectedYear: number | null;
}): TimeseriesRow[] {
  if (options.state.geo_code) {
    return options.trendRows.map((row) => ({
      slice: options.state.geo_code || 'Selected slice',
      sliceCode: options.state.geo_code,
      year: row.year,
      value: formatMetric(row.value, options.detail.series[0]?.unit || ''),
      release: options.releaseLabel,
      method: options.methodLabel,
      qa: options.detail.indicator.qa_status || 'n/a',
      evidence: String(options.detail.evidence.length),
    }));
  }
  return options.breakdownRows.map((row) => ({
    ...row,
    year: options.selectedYear || row.year,
    qa: options.detail.indicator.qa_status || 'n/a',
    evidence: String(options.detail.evidence.length),
  }));
}

function readError(error: unknown): string {
  if (typeof error === 'object' && error && 'error' in error) {
    const payload = (error as { error?: { detail?: string } }).error;
    if (payload?.detail) {
      return payload.detail;
    }
  }
  return 'The analytics endpoint did not return a timeseries payload for this slice.';
}
