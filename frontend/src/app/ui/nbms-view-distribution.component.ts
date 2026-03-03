import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { ReplaySubject, catchError, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import type { IndicatorDetailResponse, IndicatorDimension, IndicatorVisualProfile } from '../models/api.models';
import type { IndicatorCubeRow, IndicatorViewRoutePatch, IndicatorViewRouteState, IndicatorViewSummary } from '../models/indicator-visual.models';
import { IndicatorAnalyticsService } from '../services/indicator-analytics.service';
import { buildStandardBarOptions } from '../utils/chart-options.utils';
import { readCssVar, withAlpha } from '../utils/theme.utils';
import { NbmsDataTableComponent } from './nbms-data-table.component';
import {
  buildGovernanceCallouts,
  formatMetric,
  formatWholeNumber,
  groupIndicatorDimensions,
  percentOf,
  pickDistributionDimension,
} from './indicator-view.helpers';

type DistributionRow = {
  category: string;
  categoryCode: string;
  value: string;
  share: string;
  count: string;
  release: string;
  method: string;
};

type DistributionVm = {
  loading: boolean;
  error: string | null;
  summary: IndicatorViewSummary;
  dimensionOptions: IndicatorDimension[];
  chart: ChartData<'bar'> | null;
  rows: DistributionRow[];
  activeDimension: string;
  totalValue: number;
};

@Component({
  selector: 'nbms-view-distribution',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    NgSwitchDefault,
    BaseChartDirective,
    MatFormFieldModule,
    MatSelectModule,
    NbmsDataTableComponent,
  ],
  template: `
    <section class="view-shell" *ngIf="vm$ | async as vm">
      <ng-container *ngIf="!vm.loading; else loadingState">
        <mat-form-field appearance="outline" subscriptSizing="dynamic" *ngIf="vm.dimensionOptions.length">
          <mat-label>Category dimension</mat-label>
          <mat-select [value]="vm.activeDimension" (valueChange)="selectDimension($event)">
            <mat-option *ngFor="let option of vm.dimensionOptions; trackBy: trackByDimension" [value]="option.id">
              {{ option.label }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <article class="panel nbms-card-surface" *ngIf="!vm.error; else errorState">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Distribution</p>
              <h3>{{ activeLabel(vm) }}</h3>
            </div>
            <span>Total {{ formatWholeNumber(vm.totalValue) }}</span>
          </header>
          <div class="chart-wrap" *ngIf="vm.chart; else noChart">
            <canvas baseChart [type]="'bar'" [data]="vm.chart" [options]="barOptions" (chartClick)="onChartClick($event, vm)"></canvas>
          </div>
        </article>

        <nbms-data-table
          title="Category slice"
          [rows]="vm.rows"
          [columns]="tableColumns"
          [cellTemplate]="tableCell"
        >
          <span table-actions>{{ vm.rows.length }} rows</span>
        </nbms-data-table>
      </ng-container>

      <ng-template #loadingState>
        <div class="skeleton-block"></div>
      </ng-template>

      <ng-template #errorState>
        <div class="empty-state">{{ vm.error }}</div>
      </ng-template>

      <ng-template #noChart><div class="empty-state">No distribution values are available for this indicator.</div></ng-template>

      <ng-template #tableCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'category'">
            <button type="button" class="table-link" (click)="toggleCategory(row.categoryCode, vm.activeDimension)">{{ row.category }}</button>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .view-shell,
      .panel {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .panel {
        padding: var(--nbms-space-4);
      }

      .panel-head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
      }

      .eyebrow {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      h3 {
        margin: var(--nbms-space-1) 0 0;
      }

      .chart-wrap {
        min-height: 320px;
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

      .empty-state,
      .skeleton-block {
        border-radius: var(--nbms-radius-lg);
        padding: var(--nbms-space-4);
      }

      .empty-state {
        border: 1px dashed var(--nbms-border);
        color: var(--nbms-text-muted);
        text-align: center;
      }

      .skeleton-block {
        min-height: 240px;
        background: linear-gradient(
          90deg,
          color-mix(in srgb, var(--nbms-surface-2) 88%, var(--nbms-surface)) 0%,
          color-mix(in srgb, var(--nbms-surface-muted) 70%, var(--nbms-surface)) 50%,
          color-mix(in srgb, var(--nbms-surface-2) 88%, var(--nbms-surface)) 100%
        );
        background-size: 200% 100%;
        animation: shimmer 1.3s linear infinite;
      }

      @keyframes shimmer {
        from { background-position: 200% 0; }
        to { background-position: -200% 0; }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NbmsViewDistributionComponent {
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
    { key: 'category', label: 'Category' },
    { key: 'value', label: 'Value' },
    { key: 'share', label: 'Share' },
    { key: 'count', label: 'Rows' },
    { key: 'release', label: 'Release' },
    { key: 'method', label: 'Method' },
  ];

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
      if (!input.indicatorUuid || !input.indicatorDetail || !input.state) {
        return of(this.loadingVm());
      }
      const activeDimension = pickDistributionDimension(input.dimensions, input.state.dim);
      if (!activeDimension) {
        const summary = {
          kpis: [],
          callouts: buildGovernanceCallouts(input.indicatorDetail, input.state),
        };
        this.summaryChange.emit(summary);
        return of({
          ...this.loadingVm(),
          loading: false,
          summary,
          error: 'Distribution view is not available because the indicator has no categorical dimensions.',
        });
      }

      const chartState =
        input.state.dim === activeDimension && input.state.dim_value
          ? { ...input.state, dim_value: '' }
          : input.state;
      return this.analytics
        .getCube(input.indicatorUuid, {
          state: chartState,
          groupBy: [activeDimension],
          measure: 'value',
          overrides: { top_n: input.state.top_n },
        })
        .pipe(
          map((payload) =>
            buildDistributionVm(
              input.indicatorDetail as IndicatorDetailResponse,
              input.dimensions,
              input.state as IndicatorViewRouteState,
              payload,
              activeDimension,
            ),
          ),
          catchError((error) =>
            of({
              ...this.loadingVm(),
              loading: false,
              error: readError(error),
              activeDimension,
              dimensionOptions: groupIndicatorDimensions(input.dimensions).categorical,
              summary: {
                kpis: [],
                callouts: buildGovernanceCallouts(input.indicatorDetail as IndicatorDetailResponse, input.state as IndicatorViewRouteState),
              },
            }),
          ),
          startWith(this.loadingVm()),
        );
    }),
    map((vm) => {
      this.summaryChange.emit(vm.summary);
      return vm;
    }),
    shareReplay(1),
  );

  formatWholeNumber(value: number): string {
    return formatWholeNumber(value);
  }

  activeLabel(vm: DistributionVm): string {
    return vm.dimensionOptions.find((row) => row.id === vm.activeDimension)?.label || 'Category distribution';
  }

  trackByDimension(_: number, dimension: IndicatorDimension): string {
    return dimension.id;
  }

  selectDimension(value: string): void {
    this.stateChange.emit({ dim: value, dim_value: '' });
  }

  toggleCategory(code: string, dimension: string): void {
    const current = this.currentInput.state;
    this.stateChange.emit({
      dim: dimension,
      dim_value: current?.dim === dimension && current.dim_value === code ? '' : code,
    });
  }

  onChartClick(event: { active?: Array<{ index?: number }> }, vm: DistributionVm): void {
    const index = event.active?.[0]?.index;
    if (typeof index !== 'number') {
      return;
    }
    const row = vm.rows[index];
    if (row) {
      this.toggleCategory(row.categoryCode, vm.activeDimension);
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

  private loadingVm(): DistributionVm {
    return {
      loading: true,
      error: null,
      summary: { kpis: [], callouts: [] },
      dimensionOptions: [],
      chart: null,
      rows: [],
      activeDimension: '',
      totalValue: 0,
    };
  }
}

function buildDistributionVm(
  detail: IndicatorDetailResponse,
  dimensions: IndicatorDimension[],
  state: IndicatorViewRouteState,
  payload: {
    rows: IndicatorCubeRow[];
    meta: {
      dimensions: Array<{ id: string; label: string }>;
      measure: string;
      applied_filters: { dimension_filters?: Record<string, string> };
    } & Record<string, unknown>;
  },
  activeDimension: string,
): DistributionVm {
  const rows = payload.rows
    .map((row) => {
      const value = typeof row.value === 'number' ? row.value : 0;
      const count = typeof row.count === 'number' ? row.count : 0;
      const categoryCode = String(row[activeDimension] || '');
      const categoryLabel = String(row[`${activeDimension}_label`] || categoryCode || 'Unknown');
      return {
        category: categoryLabel,
        categoryCode,
        numericValue: value,
        count,
      };
    })
    .filter((row) => row.categoryCode)
    .sort((a, b) => b.numericValue - a.numericValue || a.category.localeCompare(b.category));
  const totalValue = rows.reduce((sum, row) => sum + row.numericValue, 0);
  const metaRecord = payload.meta as Record<string, any>;
  const releaseLabel = String(metaRecord['release_used']?.version || 'Latest approved');
  const methodLabel = String(metaRecord['method_used']?.version || 'Current');
  const selectedValue = state.dim === activeDimension ? state.dim_value : '';
  const tableRows: DistributionRow[] = rows
    .filter((row) => !selectedValue || row.categoryCode === selectedValue)
    .map((row) => ({
      category: row.category,
      categoryCode: row.categoryCode,
      value: formatMetric(row.numericValue),
      share: `${percentOf(row.numericValue, totalValue)}%`,
      count: formatWholeNumber(row.count),
      release: releaseLabel,
      method: methodLabel,
    }));
  const chart = rows.length
    ? {
        labels: rows.map((row) => row.category),
        datasets: [
          {
            data: rows.map((row) => percentOf(row.numericValue, totalValue)),
            backgroundColor: rows.map((row) =>
              row.categoryCode === selectedValue
                ? readCssVar('--nbms-color-primary-500')
                : withAlpha(readCssVar('--nbms-color-primary-500'), 0.62),
            ),
            borderRadius: 10,
            maxBarThickness: 28,
          },
        ],
      }
    : null;
  const summary: IndicatorViewSummary = {
    kpis: [
      {
        title: 'Dominant category',
        value: rows[0]?.category || 'n/a',
        hint: rows[0] ? `${percentOf(rows[0].numericValue, totalValue)}% of the current slice` : 'No dominant category.',
        icon: 'category',
        accent: true,
      },
      {
        title: 'Categories',
        value: formatWholeNumber(rows.length),
        hint: 'Available categorical buckets in the current slice.',
        icon: 'table_rows',
        tone: 'info',
      },
      {
        title: 'Rows',
        value: formatWholeNumber(rows.reduce((sum, row) => sum + row.count, 0)),
        hint: 'Underlying records represented in the distribution.',
        icon: 'analytics',
      },
      {
        title: 'Provenance',
        value: `${releaseLabel} / ${methodLabel}`,
        hint: 'Release and methodology applied server-side.',
        icon: 'verified',
      },
    ],
    callouts: buildGovernanceCallouts(detail, state),
  };
  return {
    loading: false,
    error: null,
    summary,
    dimensionOptions: groupIndicatorDimensions(dimensions).categorical,
    chart,
    rows: tableRows,
    activeDimension,
    totalValue,
  };
}

function readError(error: unknown): string {
  if (typeof error === 'object' && error && 'error' in error) {
    const payload = (error as { error?: { detail?: string } }).error;
    if (payload?.detail) {
      return payload.detail;
    }
  }
  return 'The cube endpoint did not return a distribution payload for this slice.';
}
