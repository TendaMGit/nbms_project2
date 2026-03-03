import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { ReplaySubject, catchError, map, of, shareReplay, startWith, switchMap } from 'rxjs';

import type { IndicatorDetailResponse, IndicatorDimension } from '../models/api.models';
import type { IndicatorCubeRow, IndicatorViewRoutePatch, IndicatorViewRouteState, IndicatorViewSummary } from '../models/indicator-visual.models';
import { IndicatorAnalyticsService } from '../services/indicator-analytics.service';
import { buildGovernanceCallouts, formatWholeNumber, groupIndicatorDimensions, percentOf } from './indicator-view.helpers';

type MatrixVm = {
  loading: boolean;
  error: string | null;
  summary: IndicatorViewSummary;
  dimX: string;
  dimY: string;
  xLabels: string[];
  yLabels: string[];
  cells: Map<string, { value: number; count: number }>;
};

@Component({
  selector: 'nbms-view-matrix',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf],
  template: `
    <section class="view-shell" *ngIf="vm$ | async as vm">
      <ng-container *ngIf="!vm.loading; else loadingState">
        <div class="empty-state" *ngIf="vm.error">{{ vm.error }}</div>
        <article class="panel nbms-card-surface" *ngIf="!vm.error">
          <header class="panel-head">
            <div>
              <p class="eyebrow">Matrix</p>
              <h3>Threat by protection</h3>
            </div>
          </header>

          <div class="matrix" *ngIf="vm.xLabels.length && vm.yLabels.length; else noMatrix">
            <div class="corner"></div>
            <strong *ngFor="let x of vm.xLabels">{{ x }}</strong>
            <ng-container *ngFor="let y of vm.yLabels">
              <strong>{{ y }}</strong>
              <button
                *ngFor="let x of vm.xLabels"
                type="button"
                class="cell"
                [style.opacity]="cellOpacity(vm, x, y)"
                (click)="selectCell(x, y)"
              >
                {{ formatWholeNumber(vm.cells.get(key(x, y))?.value || 0) }}
              </button>
            </ng-container>
          </div>
        </article>
      </ng-container>

      <ng-template #loadingState><div class="skeleton-block"></div></ng-template>
      <ng-template #noMatrix><div class="empty-state">Matrix view is not available for the current indicator slice.</div></ng-template>
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

      .matrix {
        display: grid;
        grid-template-columns: repeat(1, minmax(120px, 160px)) repeat(auto-fit, minmax(90px, 1fr));
        gap: var(--nbms-space-2);
        align-items: stretch;
      }

      .matrix strong,
      .cell {
        display: grid;
        place-items: center;
        min-height: 3.25rem;
        border-radius: var(--nbms-radius-md);
      }

      .cell {
        border: 1px solid var(--nbms-border);
        background: var(--nbms-surface-2);
        color: var(--nbms-text-primary);
        cursor: pointer;
        font: inherit;
        font-weight: 700;
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
export class NbmsViewMatrixComponent {
  @Input() set indicatorUuid(value: string) {
    this.patchInput({ indicatorUuid: value });
  }

  @Input() set indicatorDetail(value: IndicatorDetailResponse | null) {
    this.patchInput({ indicatorDetail: value });
  }

  @Input() set dimensions(value: IndicatorDimension[]) {
    this.patchInput({ dimensions: value });
  }

  @Input() set state(value: IndicatorViewRouteState | null) {
    this.patchInput({ state: value });
  }

  @Output() readonly stateChange = new EventEmitter<IndicatorViewRoutePatch>();
  @Output() readonly summaryChange = new EventEmitter<IndicatorViewSummary>();

  private readonly analytics = inject(IndicatorAnalyticsService);
  private readonly inputs$ = new ReplaySubject<{
    indicatorUuid: string;
    indicatorDetail: IndicatorDetailResponse | null;
    dimensions: IndicatorDimension[];
    state: IndicatorViewRouteState | null;
  }>(1);

  private currentInput = {
    indicatorUuid: '',
    indicatorDetail: null as IndicatorDetailResponse | null,
    dimensions: [] as IndicatorDimension[],
    state: null as IndicatorViewRouteState | null,
  };

  readonly vm$ = this.inputs$.pipe(
    switchMap((input) => {
      if (!input.indicatorUuid || !input.indicatorDetail || !input.state) {
        return of(this.loadingVm());
      }
      const categorical = groupIndicatorDimensions(input.dimensions).categorical;
      const dimX = categorical.find((row) => row.id === 'threat_category')?.id || categorical[0]?.id || '';
      const dimY = categorical.find((row) => row.id === 'protection_category')?.id || categorical[1]?.id || '';
      if (!dimX || !dimY) {
        const summary = { kpis: [], callouts: buildGovernanceCallouts(input.indicatorDetail, input.state) };
        this.summaryChange.emit(summary);
        return of({
          ...this.loadingVm(),
          loading: false,
          error: 'Matrix view is not available because two category dimensions were not found.',
          summary,
        });
      }
      return this.analytics
        .getCube(input.indicatorUuid, {
          state: input.state,
          groupBy: [dimX, dimY],
          measure: 'value',
        })
        .pipe(
          map((payload) => buildMatrixVm(input.indicatorDetail as IndicatorDetailResponse, input.state as IndicatorViewRouteState, payload.rows, dimX, dimY)),
          catchError((error) =>
            of({
              ...this.loadingVm(),
              loading: false,
              error: readError(error),
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

  key(x: string, y: string): string {
    return `${x}::${y}`;
  }

  cellOpacity(vm: MatrixVm, x: string, y: string): number {
    const values = Array.from(vm.cells.values()).map((cell) => cell.value);
    const max = Math.max(...values, 0);
    return 0.35 + percentOf(vm.cells.get(this.key(x, y))?.value || 0, max) / 100;
  }

  selectCell(x: string, y: string): void {
    this.stateChange.emit({ left: x, right: y });
  }

  private patchInput(
    patch: Partial<{
      indicatorUuid: string;
      indicatorDetail: IndicatorDetailResponse | null;
      dimensions: IndicatorDimension[];
      state: IndicatorViewRouteState | null;
    }>,
  ): void {
    this.currentInput = { ...this.currentInput, ...patch };
    this.inputs$.next(this.currentInput);
  }

  private loadingVm(): MatrixVm {
    return {
      loading: true,
      error: null,
      summary: { kpis: [], callouts: [] },
      dimX: '',
      dimY: '',
      xLabels: [],
      yLabels: [],
      cells: new Map(),
    };
  }
}

function buildMatrixVm(
  detail: IndicatorDetailResponse,
  state: IndicatorViewRouteState,
  rows: IndicatorCubeRow[],
  dimX: string,
  dimY: string,
): MatrixVm {
  const xLabels = Array.from(new Set(rows.map((row) => String(row[`${dimX}_label`] || row[dimX] || '')).filter(Boolean)));
  const yLabels = Array.from(new Set(rows.map((row) => String(row[`${dimY}_label`] || row[dimY] || '')).filter(Boolean)));
  const cells = new Map<string, { value: number; count: number }>();
  for (const row of rows) {
    const x = String(row[`${dimX}_label`] || row[dimX] || '');
    const y = String(row[`${dimY}_label`] || row[dimY] || '');
    if (!x || !y) {
      continue;
    }
    cells.set(`${x}::${y}`, {
      value: typeof row.value === 'number' ? row.value : 0,
      count: typeof row.count === 'number' ? row.count : 0,
    });
  }
  return {
    loading: false,
    error: null,
    summary: {
      kpis: [
        { title: 'Matrix rows', value: formatWholeNumber(yLabels.length), hint: 'Y-axis categories', icon: 'table_rows', accent: true },
        { title: 'Matrix cols', value: formatWholeNumber(xLabels.length), hint: 'X-axis categories', icon: 'grid_view', tone: 'info' },
      ],
      callouts: buildGovernanceCallouts(detail, state),
    },
    dimX,
    dimY,
    xLabels,
    yLabels,
    cells,
  };
}

function readError(error: unknown): string {
  if (typeof error === 'object' && error && 'error' in error) {
    const payload = (error as { error?: { detail?: string } }).error;
    if (payload?.detail) {
      return payload.detail;
    }
  }
  return 'The cube endpoint did not return matrix rows for this slice.';
}
