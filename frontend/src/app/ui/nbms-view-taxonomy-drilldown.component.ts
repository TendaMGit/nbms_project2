import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault, TitleCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { ReplaySubject, catchError, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import type { IndicatorDetailResponse, IndicatorDimension, IndicatorVisualProfile } from '../models/api.models';
import type { IndicatorCubeRow, IndicatorViewRoutePatch, IndicatorViewRouteState, IndicatorViewSummary } from '../models/indicator-visual.models';
import { IndicatorAnalyticsService } from '../services/indicator-analytics.service';
import { buildStandardBarOptions } from '../utils/chart-options.utils';
import { readCssVar, withAlpha } from '../utils/theme.utils';
import { NbmsDataTableComponent } from './nbms-data-table.component';
import {
  buildGovernanceCallouts,
  formatWholeNumber,
  groupIndicatorDimensions,
  nextTaxonomyLevel,
  pickTaxonomyLevel,
  previousTaxonomyLevel,
} from './indicator-view.helpers';

type TaxonomyRow = {
  label: string;
  code: string;
  value: string;
  count: string;
  level: string;
};

type TaxonomySegment = {
  level: string;
  code: string;
};

type TaxonomyVm = {
  loading: boolean;
  error: string | null;
  summary: IndicatorViewSummary;
  rows: TaxonomyRow[];
  chart: ChartData<'bar'> | null;
  levels: Array<{ id: string; label: string }>;
  activeLevel: string;
  breadcrumbs: TaxonomySegment[];
  available: boolean;
};

@Component({
  selector: 'nbms-view-taxonomy-drilldown',
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
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    NbmsDataTableComponent,
  ],
  template: `
    <section class="view-shell" *ngIf="vm$ | async as vm">
      <ng-container *ngIf="!vm.loading; else loadingState">
        <div *ngIf="vm.available; else unavailableState" class="view-shell">
          <div class="toolbar">
            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Group by level</mat-label>
              <mat-select [value]="vm.activeLevel" (valueChange)="changeLevel($event)">
                <mat-option *ngFor="let level of vm.levels; trackBy: trackByValue" [value]="level.id">
                  {{ level.label }}
                </mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Top N</mat-label>
              <mat-select [value]="state?.top_n || 20" (valueChange)="stateChange.emit({ top_n: $event })">
                <mat-option [value]="20">20</mat-option>
                <mat-option [value]="50">50</mat-option>
                <mat-option [value]="100">100</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Search within results</mat-label>
              <input matInput [formControl]="searchControl" />
            </mat-form-field>
          </div>

          <div class="breadcrumb-row" *ngIf="vm.breadcrumbs.length">
            <button mat-stroked-button type="button" (click)="stepBack(vm)">Back to higher level</button>
            <span *ngFor="let crumb of vm.breadcrumbs; let last = last; trackBy: trackByBreadcrumb">
              {{ crumb.code }}
              <span *ngIf="!last"> / </span>
            </span>
          </div>

          <article class="panel nbms-card-surface" *ngIf="!vm.error; else errorState">
            <header class="panel-head">
              <div>
                <p class="eyebrow">Taxonomy</p>
                <h3>{{ vm.activeLevel | titlecase }} drilldown</h3>
              </div>
              <span>{{ vm.rows.length }} rows</span>
            </header>
            <div class="chart-wrap" *ngIf="vm.chart; else noChart">
              <canvas baseChart [type]="'bar'" [data]="vm.chart" [options]="barOptions" (chartClick)="onChartClick($event, vm)"></canvas>
            </div>
          </article>

          <nbms-data-table
            title="Taxonomy slice"
            [rows]="vm.rows"
            [columns]="tableColumns"
            [cellTemplate]="tableCell"
          >
            <span table-actions>{{ vm.rows.length }} rows</span>
          </nbms-data-table>
        </div>
      </ng-container>

      <ng-template #loadingState>
        <div class="skeleton-block"></div>
      </ng-template>

      <ng-template #unavailableState>
        <div class="empty-state">Taxonomy drilldown is not available for this indicator.</div>
      </ng-template>

      <ng-template #errorState>
        <div class="empty-state">{{ vm.error }}</div>
      </ng-template>

      <ng-template #noChart><div class="empty-state">No taxonomy cube rows are available for the current slice.</div></ng-template>

      <ng-template #tableCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'label'">
            <button type="button" class="table-link" (click)="selectRow(vm, row)">{{ row.label }}</button>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .view-shell,
      .toolbar,
      .panel {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .toolbar {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .panel {
        padding: var(--nbms-space-4);
      }

      .panel-head,
      .breadcrumb-row {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: center;
        flex-wrap: wrap;
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

      @media (max-width: 900px) {
        .toolbar {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NbmsViewTaxonomyDrilldownComponent {
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

  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly tableColumns = [
    { key: 'label', label: 'Taxon' },
    { key: 'level', label: 'Level' },
    { key: 'value', label: 'Value' },
    { key: 'count', label: 'Rows' },
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
      const taxonomyLevels = groupIndicatorDimensions(input.dimensions).taxonomy;
      if (!taxonomyLevels.length) {
        const summary = {
          kpis: [],
          callouts: buildGovernanceCallouts(input.indicatorDetail, input.state),
        };
        this.summaryChange.emit(summary);
        return of({ ...this.loadingVm(), loading: false, available: false, summary });
      }
      const activeLevel = pickTaxonomyLevel(input.dimensions, input.state.tax_level);
      return this.analytics
        .getCube(input.indicatorUuid, {
          state: input.state,
          groupBy: [`taxonomy_${activeLevel}`],
          measure: 'value',
          topN: input.state.top_n,
        })
        .pipe(
          map((payload) =>
            buildTaxonomyVm(
              input.indicatorDetail as IndicatorDetailResponse,
              input.dimensions,
              input.state as IndicatorViewRouteState,
              payload.rows,
              activeLevel,
              this.searchControl.value,
            ),
          ),
          catchError((error) =>
            of({
              ...this.loadingVm(),
              loading: false,
              available: true,
              error: readError(error),
              levels: taxonomyLevels.map((row) => ({ id: row.id.replace('taxonomy_', ''), label: row.label })),
              activeLevel,
              breadcrumbs: parseTaxonomySegments(input.state?.tax_code || ''),
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

  constructor() {
    this.searchControl.valueChanges.subscribe(() => this.patchInput({}));
  }

  get state(): IndicatorViewRouteState | null {
    return this.currentInput.state;
  }

  trackByValue(_: number, row: { id: string }): string {
    return row.id;
  }

  trackByBreadcrumb(_: number, row: TaxonomySegment): string {
    return `${row.level}:${row.code}`;
  }

  changeLevel(level: string): void {
    this.stateChange.emit({ tax_level: level, tax_code: '' });
  }

  stepBack(vm: TaxonomyVm): void {
    const breadcrumbs = [...vm.breadcrumbs];
    const removed = breadcrumbs.pop();
    this.stateChange.emit({
      tax_code: encodeTaxonomySegments(breadcrumbs),
      tax_level: removed?.level || previousTaxonomyLevel(this.currentInput.dimensions, vm.activeLevel),
    });
  }

  selectRow(vm: TaxonomyVm, row: TaxonomyRow): void {
    const breadcrumbs = [...vm.breadcrumbs, { level: vm.activeLevel, code: row.code }];
    const nextLevel = nextTaxonomyLevel(this.currentInput.dimensions, vm.activeLevel);
    this.stateChange.emit({
      tax_code: encodeTaxonomySegments(breadcrumbs),
      tax_level: nextLevel,
    });
  }

  onChartClick(event: { active?: Array<{ index?: number }> }, vm: TaxonomyVm): void {
    const index = event.active?.[0]?.index;
    if (typeof index !== 'number') {
      return;
    }
    const row = vm.rows[index];
    if (row) {
      this.selectRow(vm, row);
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

  private loadingVm(): TaxonomyVm {
    return {
      loading: true,
      error: null,
      summary: { kpis: [], callouts: [] },
      rows: [],
      chart: null,
      levels: [],
      activeLevel: '',
      breadcrumbs: [],
      available: true,
    };
  }
}

function buildTaxonomyVm(
  detail: IndicatorDetailResponse,
  dimensions: IndicatorDimension[],
  state: IndicatorViewRouteState,
  rows: IndicatorCubeRow[],
  activeLevel: string,
  search: string,
): TaxonomyVm {
  const normalizedSearch = search.trim().toLowerCase();
  const taxonomyRows = rows
    .map((row) => {
      const code = String(row[`taxonomy_${activeLevel}`] || '');
      const label = String(row[`taxonomy_${activeLevel}_label`] || code || 'Unknown');
      return {
        label,
        code,
        valueNumber: typeof row.value === 'number' ? row.value : 0,
        countNumber: typeof row.count === 'number' ? row.count : 0,
      };
    })
    .filter((row) => row.code)
    .filter((row) => !normalizedSearch || `${row.label} ${row.code}`.toLowerCase().includes(normalizedSearch))
    .sort((a, b) => b.valueNumber - a.valueNumber || a.label.localeCompare(b.label));
  const tableRows: TaxonomyRow[] = taxonomyRows.map((row) => ({
    label: row.label,
    code: row.code,
    value: formatWholeNumber(row.valueNumber),
    count: formatWholeNumber(row.countNumber),
    level: activeLevel,
  }));
  const chart = tableRows.length
    ? {
        labels: tableRows.map((row) => row.label),
        datasets: [
          {
            data: taxonomyRows.map((row) => row.valueNumber),
            backgroundColor: taxonomyRows.map(() => withAlpha(readCssVar('--nbms-color-primary-500'), 0.7)),
            borderRadius: 10,
            maxBarThickness: 28,
          },
        ],
      }
    : null;
  const breadcrumbs = parseTaxonomySegments(state.tax_code);
  const levels = groupIndicatorDimensions(dimensions).taxonomy.map((row) => ({
    id: row.id.replace('taxonomy_', ''),
    label: row.label,
  }));
  return {
    loading: false,
    error: null,
    summary: {
      kpis: [
        {
          title: 'Focus depth',
          value: String(breadcrumbs.length),
          hint: breadcrumbs.length ? 'Taxonomy path applied from the breadcrumb.' : 'No parent taxonomy filter applied.',
          icon: 'account_tree',
          accent: true,
        },
        {
          title: 'Groups',
          value: formatWholeNumber(tableRows.length),
          hint: `Visible ${activeLevel} groups in the current slice.`,
          icon: 'category',
          tone: 'info',
        },
        {
          title: 'Rows',
          value: formatWholeNumber(taxonomyRows.reduce((sum, row) => sum + row.countNumber, 0)),
          hint: 'Underlying records in the grouped slice.',
          icon: 'table_rows',
        },
        {
          title: 'QA',
          value: detail.indicator.qa_status || 'n/a',
          hint: 'Indicator governance remains visible during drilldown.',
          icon: 'verified',
        },
      ],
      callouts: buildGovernanceCallouts(detail, state),
    },
    rows: tableRows,
    chart,
    levels,
    activeLevel,
    breadcrumbs,
    available: true,
  };
}

function parseTaxonomySegments(value: string): TaxonomySegment[] {
  return String(value || '')
    .split('>')
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => {
      const [level, code] = segment.split(':', 2);
      return {
        level: (code ? level : 'taxonomy').replace('taxonomy_', ''),
        code: code || level,
      };
    });
}

function encodeTaxonomySegments(segments: TaxonomySegment[]): string {
  return segments.map((segment) => `${segment.level}:${segment.code}`).join('>');
}

function readError(error: unknown): string {
  if (typeof error === 'object' && error && 'error' in error) {
    const payload = (error as { error?: { detail?: string } }).error;
    if (payload?.detail) {
      return payload.detail;
    }
  }
  return 'The cube endpoint did not return taxonomy drilldown rows for this slice.';
}
