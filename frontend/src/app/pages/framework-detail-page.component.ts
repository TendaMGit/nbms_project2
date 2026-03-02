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
  type FrameworkDetailData,
  type FrameworkIndicatorRow,
  type FrameworkSummaryRow,
  type FrameworkTargetRow
} from '../services/framework-analytics.service';
import { NbmsCalloutComponent } from '../ui/nbms-callout.component';
import { NbmsChartCardComponent } from '../ui/nbms-chart-card.component';
import { NbmsContextBarComponent } from '../ui/nbms-context-bar.component';
import { NbmsDataTableComponent } from '../ui/nbms-data-table.component';
import { NbmsEntityListTableComponent } from '../ui/nbms-entity-list-table.component';
import { NbmsKpiCardComponent } from '../ui/nbms-kpi-card.component';
import { NbmsMapCardComponent } from '../ui/nbms-map-card.component';
import { NbmsNarrativePanelComponent } from '../ui/nbms-narrative-panel.component';
import { NbmsPageHeaderComponent } from '../ui/nbms-page-header.component';
import { NbmsReadinessBadgeComponent } from '../ui/nbms-readiness-badge.component';
import { NbmsStatStripComponent } from '../ui/nbms-stat-strip.component';
import { NbmsTabStripComponent } from '../ui/nbms-tab-strip.component';
import { buildStandardBarOptions } from '../utils/chart-options.utils';
import { readCssVar } from '../utils/theme.utils';

type FrameworkDetailTab = 'overview' | 'targets' | 'coverage' | 'gaps' | 'narrative';

type FrameworkDetailVm = {
  context: ReturnType<ContextStateService['parseQueryParams']> & { tab: FrameworkDetailTab };
  framework: FrameworkSummaryRow;
  targets: FrameworkTargetRow[];
  indicators: FrameworkIndicatorRow[];
  gapIndicators: FrameworkIndicatorRow[];
  stats: Array<{ title: string; value: string; hint: string; icon: string; tone?: 'neutral' | 'positive' | 'negative' | 'info' }>;
  targetVolumeChart: ChartData<'bar'>;
  readinessChart: ChartData<'bar'>;
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
  selector: 'app-framework-detail-page',
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
    NbmsEntityListTableComponent,
    NbmsKpiCardComponent,
    NbmsMapCardComponent,
    NbmsNarrativePanelComponent,
    NbmsPageHeaderComponent,
    NbmsReadinessBadgeComponent,
    NbmsStatStripComponent,
    NbmsTabStripComponent
  ],
  template: `
    <section class="framework-page" *ngIf="vm$ | async as vm">
      <nbms-page-header
        [title]="vm.framework.title"
        subtitle="Framework workspace with target coverage, readiness, and indicator drilldowns."
        [breadcrumbs]="[
          { label: 'Dashboard', route: ['/dashboard'] },
          { label: 'Frameworks', route: ['/frameworks'] },
          { label: vm.framework.id, route: ['/frameworks', vm.framework.id] }
        ]"
        [badges]="[
          { label: vm.context.report_cycle || 'Current cycle', tone: 'info' },
          { label: vm.framework.id, tone: 'neutral' }
        ]"
        [actions]="[
          { id: 'frameworks', label: 'All frameworks', route: ['/frameworks'], variant: 'stroked' },
          { id: 'indicators', label: 'Indicators', route: ['/indicators'], icon: 'insights', variant: 'flat' }
        ]"
      ></nbms-page-header>

      <nbms-tab-strip
        [tabs]="[
          { id: 'overview', label: 'Overview', count: vm.indicators.length },
          { id: 'targets', label: 'Targets', count: vm.targets.length },
          { id: 'coverage', label: 'Coverage', count: vm.targets.length },
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
        helperText="Framework, target, and indicator pages restore the same context state from the URL."
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

      <section class="content-grid" [ngSwitch]="vm.context.tab">
        <ng-container *ngSwitchCase="'overview'">
          <div class="main-column">
            <nbms-chart-card title="Target coverage" eyebrow="Overview" subtitle="Published indicator volume per framework target">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.targetVolumeChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>

            <nbms-chart-card title="Average readiness by target" eyebrow="Overview" subtitle="Targets with the strongest and weakest readiness posture">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.readinessChart" [type]="'bar'" [options]="barOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-narrative-panel
              eyebrow="Overview"
              title="Framework narrative"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'targets'">
          <div class="main-column">
            <nbms-chart-card title="Target coverage" eyebrow="Targets" subtitle="Target ranking in the current context">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.targetVolumeChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Target drilldown"
              tone="info"
              message="Use the target rows below to move into target detail, evidence, gap tracking, and indicator drilldowns."
            ></nbms-callout>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'coverage'">
          <div class="main-column">
            <nbms-map-card
              title="Framework coverage map"
              eyebrow="Coverage"
              subtitle="Spatial roll-up across the framework"
              helperText="A framework aggregate map is not yet available from the backend. Use target or indicator pages for map-backed drilldowns."
            ></nbms-map-card>
          </div>

          <div class="side-column">
            <nbms-chart-card title="Target readiness" eyebrow="Coverage" subtitle="Readiness split by target">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.readinessChart" [type]="'bar'" [options]="barOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'gaps'">
          <div class="main-column">
            <nbms-chart-card title="Targets needing intervention" eyebrow="Gaps" subtitle="Targets with low readiness or blocked indicators">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.readinessChart" [type]="'bar'" [options]="barOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Gap posture"
              tone="warning"
              [message]="vm.gapIndicators.length ? vm.gapIndicators.length + ' indicators remain in warning or blocked states for this framework.' : 'No blocked indicators are visible in the current slice.'"
            ></nbms-callout>
            <nbms-narrative-panel
              eyebrow="Gaps"
              title="What is missing"
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
              title="Framework narrative blocks"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>
      </section>

      <nbms-entity-list-table
        title="Framework targets"
        [rows]="vm.targets"
        [columns]="targetColumns"
        [cellTemplate]="targetCell"
      ></nbms-entity-list-table>

      <nbms-data-table
        title="Indicator contribution table"
        [rows]="vm.context.tab === 'gaps' ? vm.gapIndicators : vm.indicators"
        [columns]="indicatorColumns"
        [cellTemplate]="indicatorCell"
      ></nbms-data-table>

      <ng-template #targetCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'target'">
            <a [routerLink]="['/frameworks', vm.framework.id, 'targets', row.id]">{{ row.label }}</a>
          </ng-container>
          <ng-container *ngSwitchCase="'readiness'">
            <nbms-readiness-badge [score]="round(row.readinessScore)" [status]="toReadinessStatus(row.readinessScore)"></nbms-readiness-badge>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>

      <ng-template #indicatorCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'indicator'">
            <a [routerLink]="['/indicators', row.uuid]">{{ row.code }}</a>
            <span class="sub-copy">{{ row.title }}</span>
          </ng-container>
          <ng-container *ngSwitchCase="'targetCode'">
            <a [routerLink]="['/frameworks', vm.framework.id, 'targets', row.targetCode]">{{ row.targetCode }}</a>
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
      .framework-page,
      .content-grid,
      .main-column,
      .side-column,
      .full-width {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .content-grid {
        grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
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
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FrameworkDetailPageComponent {
  @ViewChild('targetCell', { static: true })
  targetCellTemplate!: TemplateRef<{ $implicit: FrameworkTargetRow; key: string }>;

  @ViewChild('indicatorCell', { static: true })
  indicatorCellTemplate!: TemplateRef<{ $implicit: FrameworkIndicatorRow; key: string }>;

  private readonly route = inject(ActivatedRoute);
  private readonly contextState = inject(ContextStateService);
  private readonly frameworks = inject(FrameworkAnalyticsService);

  readonly targetColumns = [
    { key: 'target', label: 'Target' },
    { key: 'indicatorCount', label: 'Indicators' },
    { key: 'readiness', label: 'Readiness' },
    { key: 'blockedCount', label: 'Blocked' }
  ];

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
    this.route.paramMap.pipe(map((params) => params.get('frameworkId') || 'GBF')),
    this.context$
  ]).pipe(
    switchMap(([frameworkId, context]) =>
      this.frameworks.frameworkDetail(frameworkId, context).pipe(map((detail) => this.buildVm(frameworkId, detail, context)))
    )
  );

  readonly barOptions = buildStandardBarOptions();
  readonly horizontalBarOptions = buildStandardBarOptions(true);

  patchContext(patch: Record<string, unknown>): void {
    this.contextState.update(this.route, patch as any);
  }

  copyNarrative(sections: Array<{ title: string; body: string }>): void {
    const text = sections.map((section) => `${section.title}\n${section.body}`).join('\n\n');
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
  }

  trackByStat(_: number, stat: FrameworkDetailVm['stats'][number]): string {
    return stat.title;
  }

  round(value: number): number {
    return Math.round(value);
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
    detail: FrameworkDetailData,
    context: ReturnType<ContextStateService['parseQueryParams']>
  ): FrameworkDetailVm {
    const framework = detail.framework ?? {
      id: frameworkId,
      title: frameworkId,
      targetCount: detail.targets.length,
      indicatorCount: detail.indicators.length,
      narrative: `${frameworkId} does not yet have a dedicated narrative payload.`
    };

    const targets = detail.targets
      .filter((row) => matchesQuery(`${row.label} ${framework.title}`, context.q))
      .sort((a, b) => b.indicatorCount - a.indicatorCount || a.label.localeCompare(b.label));

    const indicators = detail.indicators
      .filter((row) => matchesQuery(`${row.code} ${row.title} ${row.targetCode}`, context.q))
      .filter((row) => (context.published_only ? row.status.toLowerCase() !== 'draft' : true))
      .sort((a, b) => b.readinessScore - a.readinessScore || a.code.localeCompare(b.code));

    const gapIndicators = indicators.filter((row) => this.toReadinessStatus(row.readinessScore, row.readinessStatus) !== 'ready');
    const yearOptions = buildYearOptions(indicators);

    const targetVolumeChart = {
      labels: targets.slice(0, 8).map((row) => row.label),
      datasets: [
        {
          label: 'Indicators',
          data: targets.slice(0, 8).map((row) => row.indicatorCount),
          backgroundColor: targets.slice(0, 8).map(() => readCssVar('--nbms-color-primary-500')),
          borderRadius: 10,
          maxBarThickness: 28
        }
      ]
    } satisfies ChartData<'bar'>;

    const readinessChart = {
      labels: targets.slice(0, 8).map((row) => row.label),
      datasets: [
        {
          label: 'Avg readiness',
          data: targets.slice(0, 8).map((row) => Math.round(row.readinessScore)),
          backgroundColor: targets.slice(0, 8).map((row) =>
            this.toReadinessStatus(row.readinessScore) === 'ready'
              ? readCssVar('--nbms-color-success')
              : this.toReadinessStatus(row.readinessScore) === 'warning'
                ? readCssVar('--nbms-color-accent-500')
                : readCssVar('--nbms-color-error')
          ),
          borderRadius: 10,
          maxBarThickness: 28
        }
      ]
    } satisfies ChartData<'bar'>;

    const avgReadiness = indicators.length
      ? Math.round(indicators.reduce((sum, row) => sum + row.readinessScore, 0) / indicators.length)
      : 0;

    return {
      context: { ...context, tab: toFrameworkDetailTab(context.tab) },
      framework,
      targets,
      indicators,
      gapIndicators,
      stats: [
        { title: 'Targets', value: String(targets.length), hint: 'Targets in the current slice', icon: 'flag' },
        { title: 'Indicators', value: String(indicators.length), hint: 'Indicators linked to this framework', icon: 'insights' },
        {
          title: 'Avg readiness',
          value: `${avgReadiness}`,
          hint: 'Average readiness score for linked indicators',
          icon: 'analytics',
          tone: this.toReadinessStatus(avgReadiness) === 'ready' ? 'positive' : this.toReadinessStatus(avgReadiness) === 'warning' ? 'info' : 'negative'
        },
        {
          title: 'Spatial outputs',
          value: String(indicators.filter((row) => row.hasSpatial).length),
          hint: 'Indicators with spatially explicit outputs',
          icon: 'map'
        }
      ],
      targetVolumeChart,
      readinessChart,
      narrativeSections: [
        {
          id: 'summary',
          title: 'Framework summary',
          body: framework.narrative
        },
        {
          id: 'gaps',
          title: 'Gap focus',
          body: gapIndicators.length
            ? `${gapIndicators.length} indicators remain in warning or blocked states within this framework.`
            : 'No blocked indicators are visible in the current framework slice.'
        },
        {
          id: 'coverage',
          title: 'Coverage posture',
          body: `${targets.length} targets and ${indicators.length} indicators are currently restorable from the URL-backed context.`
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

function toFrameworkDetailTab(value: string): FrameworkDetailTab {
  return value === 'targets' || value === 'coverage' || value === 'gaps' || value === 'narrative' ? value : 'overview';
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
