import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';
import { ChangeDetectionStrategy, Component, TemplateRef, ViewChild, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { combineLatest, map, switchMap } from 'rxjs';

import { DEFAULT_NBMS_CONTEXT, type NbmsContextOption } from '../models/context.models';
import { ContextStateService } from '../services/context-state.service';
import {
  FrameworkAnalyticsService,
  type FrameworkIndicatorRow,
  type TargetDetailData
} from '../services/framework-analytics.service';
import { NbmsCalloutComponent } from '../ui/nbms-callout.component';
import { NbmsChartCardComponent } from '../ui/nbms-chart-card.component';
import { NbmsContextBarComponent } from '../ui/nbms-context-bar.component';
import { NbmsDataTableComponent } from '../ui/nbms-data-table.component';
import { NbmsEvidenceListComponent } from '../ui/nbms-evidence-list.component';
import { NbmsKpiCardComponent } from '../ui/nbms-kpi-card.component';
import { NbmsMapCardComponent } from '../ui/nbms-map-card.component';
import { NbmsNarrativePanelComponent } from '../ui/nbms-narrative-panel.component';
import { NbmsPageHeaderComponent } from '../ui/nbms-page-header.component';
import { NbmsReadinessBadgeComponent } from '../ui/nbms-readiness-badge.component';
import { NbmsStatStripComponent } from '../ui/nbms-stat-strip.component';
import { NbmsTabStripComponent } from '../ui/nbms-tab-strip.component';
import { buildStandardBarOptions, buildStandardDoughnutOptions } from '../utils/chart-options.utils';
import { readCssVar } from '../utils/theme.utils';

type TargetDetailTab = 'overview' | 'indicators' | 'map' | 'evidence' | 'gaps' | 'narrative';

type TargetDetailVm = {
  context: ReturnType<ContextStateService['parseQueryParams']> & { tab: TargetDetailTab };
  frameworkId: string;
  targetId: string;
  targetLabel: string;
  indicators: FrameworkIndicatorRow[];
  gapIndicators: FrameworkIndicatorRow[];
  evidenceRows: TargetDetailData['evidence'];
  stats: Array<{ title: string; value: string; hint: string; icon: string; tone?: 'neutral' | 'positive' | 'negative' | 'info' }>;
  contributionChart: ChartData<'bar'>;
  readinessChart: ChartData<'doughnut'>;
  narrativeSections: Array<{ id: string; title: string; body: string; helperText?: string }>;
  reportCycleOptions: NbmsContextOption[];
  releaseOptions: NbmsContextOption[];
  methodOptions: NbmsContextOption[];
  geoTypeOptions: NbmsContextOption[];
  yearOptions: number[];
};

const REPORT_CYCLE_OPTIONS: NbmsContextOption[] = [
  { value: 'NR7-2024', label: 'NR7 2024' },
  { value: 'NR7-2022', label: 'NR7 2022' }
];

const RELEASE_OPTIONS: NbmsContextOption[] = [
  { value: 'latest_approved', label: 'Latest approved release' },
  { value: 'draft', label: 'Draft release', disabled: true }
];

const METHOD_OPTIONS: NbmsContextOption[] = [
  { value: 'current', label: 'Current approved method' },
  { value: 'baseline', label: 'Baseline method', disabled: true }
];

const GEO_TYPE_OPTIONS: NbmsContextOption[] = [
  { value: 'national', label: 'National' },
  { value: 'province', label: 'Province' },
  { value: 'biome', label: 'Biome' }
];

@Component({
  selector: 'app-target-detail-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    NgSwitchDefault,
    RouterLink,
    BaseChartDirective,
    NbmsCalloutComponent,
    NbmsChartCardComponent,
    NbmsContextBarComponent,
    NbmsDataTableComponent,
    NbmsEvidenceListComponent,
    NbmsKpiCardComponent,
    NbmsMapCardComponent,
    NbmsNarrativePanelComponent,
    NbmsPageHeaderComponent,
    NbmsReadinessBadgeComponent,
    NbmsStatStripComponent,
    NbmsTabStripComponent
  ],
  template: `
    <section class="target-page" *ngIf="vm$ | async as vm">
      <nbms-page-header
        [title]="vm.targetLabel"
        subtitle="Target analytics workspace with indicator contribution, evidence, gaps, and narrative."
        [breadcrumbs]="[
          { label: 'Dashboard', route: ['/dashboard'] },
          { label: 'Frameworks', route: ['/frameworks'] },
          { label: vm.frameworkId, route: ['/frameworks', vm.frameworkId] },
          { label: vm.targetLabel, route: ['/frameworks', vm.frameworkId, 'targets', vm.targetId] }
        ]"
        [badges]="[
          { label: vm.context.report_cycle || 'Current cycle', tone: 'info' },
          { label: vm.frameworkId, tone: 'neutral' }
        ]"
        [actions]="[
          { id: 'framework', label: 'Framework', route: ['/frameworks', vm.frameworkId], variant: 'stroked' },
          { id: 'indicators', label: 'Indicators', route: ['/indicators'], icon: 'insights', variant: 'flat' }
        ]"
      ></nbms-page-header>

      <nbms-tab-strip
        [tabs]="[
          { id: 'overview', label: 'Overview', count: vm.indicators.length },
          { id: 'indicators', label: 'Indicators', count: vm.indicators.length },
          { id: 'map', label: 'Map', count: vm.indicators.length },
          { id: 'evidence', label: 'Evidence', count: vm.evidenceRows.length },
          { id: 'gaps', label: 'Gaps', count: vm.gapIndicators.length },
          { id: 'narrative', label: 'Narrative' }
        ]"
        [activeTab]="vm.context.tab"
        (tabChange)="patchContext({ tab: $any($event) })"
      ></nbms-tab-strip>

      <nbms-context-bar
        [state]="vm.context"
        [reportCycleOptions]="vm.reportCycleOptions"
        [releaseOptions]="vm.releaseOptions"
        [methodOptions]="vm.methodOptions"
        [geoTypeOptions]="vm.geoTypeOptions"
        [yearOptions]="vm.yearOptions"
        helperText="Target detail keeps the same context state as framework and indicator drilldowns."
        (stateChange)="patchContext($event)"
      ></nbms-context-bar>

      <nbms-stat-strip>
        <nbms-kpi-card
          *ngFor="let stat of vm.stats; trackBy: trackByStat"
          [title]="stat.title"
          [value]="stat.value"
          [hint]="stat.hint"
          [icon]="stat.icon"
          [tone]="stat.tone || 'neutral'"
        ></nbms-kpi-card>
      </nbms-stat-strip>

      <section class="indicator-summary-grid">
        <a
          class="indicator-summary nbms-card-surface"
          *ngFor="let row of vm.indicators.slice(0, 4); trackBy: trackByIndicatorRow"
          [routerLink]="['/indicators', row.uuid]"
        >
          <div class="indicator-summary-head">
            <p class="indicator-kicker">Indicator</p>
            <nbms-readiness-badge [score]="row.readinessScore" [status]="toReadinessStatus(row.readinessScore, row.readinessStatus)"></nbms-readiness-badge>
          </div>
          <h2>{{ row.code }}</h2>
          <p>{{ row.title }}</p>
          <div class="indicator-summary-meta">
            <span>{{ row.status }}</span>
            <span>{{ row.hasSpatial ? 'Spatial output' : 'Tabular only' }}</span>
          </div>
        </a>
      </section>

      <section class="content-grid" [ngSwitch]="vm.context.tab">
        <ng-container *ngSwitchCase="'overview'">
          <div class="main-column">
            <nbms-chart-card title="Indicator contribution" eyebrow="Overview" subtitle="Indicators mapped to this target">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.contributionChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>

            <nbms-chart-card title="Readiness mix" eyebrow="Overview" subtitle="Readiness posture for the current target slice">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.readinessChart" [type]="'doughnut'" [options]="doughnutOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-narrative-panel
              eyebrow="Overview"
              title="Target narrative"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'indicators'">
          <div class="main-column">
            <nbms-chart-card title="Indicator contribution" eyebrow="Indicators" subtitle="Ranked by readiness score">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.contributionChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Indicator drilldown"
              tone="info"
              message="Indicator codes in the contribution table link directly to the indicator analytics workspace with the same context."
            ></nbms-callout>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'map'">
          <div class="main-column">
            <nbms-map-card
              title="Target coverage map"
              eyebrow="Map"
              subtitle="Map-backed target coverage"
              helperText="Target-level aggregate map layers are not yet exposed by the backend. Use the indicator rows below for spatial drilldowns."
            ></nbms-map-card>
          </div>

          <div class="side-column">
            <nbms-chart-card title="Spatial indicator volume" eyebrow="Map" subtitle="Indicators with spatial outputs in this target">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.contributionChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'evidence'">
          <div class="full-width">
            <nbms-evidence-list [rows]="vm.evidenceRows"></nbms-evidence-list>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'gaps'">
          <div class="main-column">
            <nbms-chart-card title="Gap worklist" eyebrow="Gaps" subtitle="Indicators that still need readiness work">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.contributionChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Gap scope"
              tone="warning"
              [message]="vm.gapIndicators.length ? vm.gapIndicators.length + ' indicators in this target remain warning or blocked.' : 'No gap indicators are visible in the current target slice.'"
            ></nbms-callout>
            <nbms-narrative-panel
              eyebrow="Gaps"
              title="Gap narrative"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>

        <ng-container *ngSwitchDefault>
          <div class="full-width">
            <nbms-narrative-panel
              eyebrow="Narrative"
              title="Narrative blocks"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>
      </section>

      <nbms-data-table
        title="Indicator contribution table"
        [rows]="vm.context.tab === 'gaps' ? vm.gapIndicators : vm.indicators"
        [columns]="indicatorColumns"
        [cellTemplate]="indicatorCell"
      ></nbms-data-table>

      <ng-template #indicatorCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'indicator'">
            <a [routerLink]="['/indicators', row.uuid]">{{ row.code }}</a>
            <span class="sub-copy">{{ row.title }}</span>
          </ng-container>
          <ng-container *ngSwitchCase="'readiness'">
            <nbms-readiness-badge [score]="row.readinessScore" [status]="toReadinessStatus(row.readinessScore, row.readinessStatus)"></nbms-readiness-badge>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .target-page,
      .content-grid,
      .main-column,
      .side-column,
      .full-width {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .indicator-summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: var(--nbms-space-3);
      }

      .indicator-summary {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4);
        color: inherit;
        text-decoration: none;
      }

      .indicator-summary-head,
      .indicator-summary-meta {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-2);
        align-items: center;
        flex-wrap: wrap;
      }

      .indicator-kicker,
      .indicator-summary-meta span {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }

      .indicator-summary h2,
      .indicator-summary p {
        margin: 0;
      }

      .indicator-summary p {
        color: var(--nbms-text-secondary);
        line-height: 1.6;
      }

      .content-grid {
        grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
      }

      .side-column {
        align-self: start;
        position: sticky;
        top: 5.4rem;
      }

      .full-width {
        grid-column: 1 / -1;
      }

      .chart-wrap {
        min-height: 320px;
      }

      .sub-copy {
        display: block;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      @media (max-width: 1080px) {
        .content-grid {
          grid-template-columns: 1fr;
        }

        .side-column {
          position: static;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TargetDetailPageComponent {
  @ViewChild('indicatorCell', { static: true })
  indicatorCellTemplate!: TemplateRef<{ $implicit: FrameworkIndicatorRow; key: string }>;

  private readonly route = inject(ActivatedRoute);
  private readonly contextState = inject(ContextStateService);
  private readonly frameworks = inject(FrameworkAnalyticsService);

  readonly indicatorColumns = [
    { key: 'indicator', label: 'Indicator' },
    { key: 'targetCode', label: 'Target' },
    { key: 'readiness', label: 'Readiness' },
    { key: 'status', label: 'Status' },
    { key: 'updatedAt', label: 'Updated' }
  ];

  readonly context$ = this.contextState.connect(this.route, {
    defaults: {
      ...DEFAULT_NBMS_CONTEXT,
      tab: 'overview',
      report_cycle: 'NR7-2024',
      metric: 'coverage',
      agg: 'national'
    }
  });

  readonly vm$ = combineLatest([
    this.route.paramMap.pipe(
      map((params) => ({
        frameworkId: params.get('frameworkId') || 'GBF',
        targetId: params.get('targetId') || 'UNMAPPED'
      }))
    ),
    this.context$
  ]).pipe(
    switchMap(([params, context]) =>
      this.frameworks.targetDetail(params.frameworkId, params.targetId, context).pipe(
        map((detail) => this.buildVm(params.frameworkId, params.targetId, detail, context))
      )
    )
  );

  readonly horizontalBarOptions = buildStandardBarOptions(true);
  readonly doughnutOptions = buildStandardDoughnutOptions();

  patchContext(patch: Record<string, unknown>): void {
    this.contextState.update(this.route, patch as any);
  }

  copyNarrative(sections: Array<{ title: string; body: string }>): void {
    const text = sections.map((section) => `${section.title}\n${section.body}`).join('\n\n');
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
  }

  trackByStat(_: number, stat: TargetDetailVm['stats'][number]): string {
    return stat.title;
  }

  trackByIndicatorRow(_: number, row: FrameworkIndicatorRow): string {
    return row.uuid;
  }

  toReadinessStatus(score: number, explicit?: string): 'ready' | 'warning' | 'blocked' {
    const normalized = (explicit || '').toLowerCase();
    if (normalized === 'ready' || score >= 80) {
      return 'ready';
    }
    if (normalized === 'warning' || score >= 50) {
      return 'warning';
    }
    return 'blocked';
  }

  private buildVm(
    frameworkId: string,
    targetId: string,
    detail: TargetDetailData,
    context: ReturnType<ContextStateService['parseQueryParams']>
  ): TargetDetailVm {
    const indicators = detail.indicators
      .filter((row) => matchesQuery(`${row.code} ${row.title} ${row.targetCode}`, context.q))
      .filter((row) => (context.published_only ? row.status.toLowerCase() !== 'draft' : true))
      .sort((a, b) => b.readinessScore - a.readinessScore || a.code.localeCompare(b.code));

    const gapIndicators = indicators.filter((row) => this.toReadinessStatus(row.readinessScore, row.readinessStatus) !== 'ready');
    const evidenceRows = detail.evidence.filter((row) => matchesQuery(`${row.title} ${row.subtitle} ${row.type}`, context.q));
    const yearOptions = buildYearOptions(indicators);
    const chartRows = (context.tab === 'gaps' ? gapIndicators : indicators).slice(0, 8);

    const contributionChart = {
      labels: chartRows.map((row) => row.code),
      datasets: [
        {
          label: 'Readiness score',
          data: chartRows.map((row) => Math.round(row.readinessScore)),
          backgroundColor: chartRows.map((row) =>
            this.toReadinessStatus(row.readinessScore, row.readinessStatus) === 'ready'
              ? readCssVar('--nbms-color-success')
              : this.toReadinessStatus(row.readinessScore, row.readinessStatus) === 'warning'
                ? readCssVar('--nbms-color-accent-500')
                : readCssVar('--nbms-color-error')
          ),
          borderRadius: 10,
          maxBarThickness: 28
        }
      ]
    } satisfies ChartData<'bar'>;

    const readinessChart = {
      labels: ['Ready', 'Warning', 'Blocked'],
      datasets: [
        {
          data: [
            indicators.filter((row) => this.toReadinessStatus(row.readinessScore, row.readinessStatus) === 'ready').length,
            indicators.filter((row) => this.toReadinessStatus(row.readinessScore, row.readinessStatus) === 'warning').length,
            indicators.filter((row) => this.toReadinessStatus(row.readinessScore, row.readinessStatus) === 'blocked').length
          ],
          backgroundColor: [
            readCssVar('--nbms-color-success'),
            readCssVar('--nbms-color-accent-500'),
            readCssVar('--nbms-color-error')
          ],
          borderWidth: 0
        }
      ]
    } satisfies ChartData<'doughnut'>;

    const avgReadiness = indicators.length
      ? Math.round(indicators.reduce((sum, row) => sum + row.readinessScore, 0) / indicators.length)
      : 0;

    return {
      context: { ...context, tab: toTargetDetailTab(context.tab) },
      frameworkId,
      targetId,
      targetLabel: detail.target?.label || targetId,
      indicators,
      gapIndicators,
      evidenceRows,
      stats: [
        { title: 'Indicators', value: String(indicators.length), hint: 'Indicators mapped to this target', icon: 'insights' },
        {
          title: 'Avg readiness',
          value: `${avgReadiness}`,
          hint: 'Average readiness score for the target slice',
          icon: 'analytics',
          tone: this.toReadinessStatus(avgReadiness) === 'ready' ? 'positive' : this.toReadinessStatus(avgReadiness) === 'warning' ? 'info' : 'negative'
        },
        {
          title: 'Spatial outputs',
          value: String(indicators.filter((row) => row.hasSpatial).length),
          hint: 'Indicators with spatial outputs',
          icon: 'map'
        },
        {
          title: 'Evidence items',
          value: String(evidenceRows.length),
          hint: 'Evidence rows restored for this target',
          icon: 'folder'
        }
      ],
      contributionChart,
      readinessChart,
      narrativeSections: [
        {
          id: 'scope',
          title: 'Target scope',
          body: detail.filterScopeLabel
        },
        {
          id: 'coverage',
          title: 'Coverage summary',
          body: `${indicators.length} indicators and ${evidenceRows.length} evidence rows are available for this target context.`
        },
        {
          id: 'gaps',
          title: 'Gap summary',
          body: gapIndicators.length
            ? `${gapIndicators.length} indicators still require QA, release, or readiness work before publication.`
            : 'No blocked indicators are visible in the current target slice.'
        }
      ],
      reportCycleOptions: REPORT_CYCLE_OPTIONS,
      releaseOptions: RELEASE_OPTIONS,
      methodOptions: METHOD_OPTIONS,
      geoTypeOptions: GEO_TYPE_OPTIONS,
      yearOptions
    };
  }
}

function toTargetDetailTab(value: string): TargetDetailTab {
  return value === 'indicators' || value === 'map' || value === 'evidence' || value === 'gaps' || value === 'narrative'
    ? value
    : 'overview';
}

function buildYearOptions(indicators: FrameworkIndicatorRow[]): number[] {
  const years = indicators.flatMap((row) => {
    const date = row.updatedAt ? new Date(row.updatedAt) : null;
    return date && Number.isFinite(date.getTime()) ? [date.getFullYear()] : [];
  });
  return Array.from(new Set(years)).sort((a, b) => a - b);
}

function matchesQuery(text: string, query: string): boolean {
  return !query.trim() || text.toLowerCase().includes(query.trim().toLowerCase());
}
