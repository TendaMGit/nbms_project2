import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';
import { ChangeDetectionStrategy, Component, TemplateRef, ViewChild, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { combineLatest, map } from 'rxjs';
import { ChartData } from 'chart.js';

import { DashboardSummary } from '../models/api.models';
import { DEFAULT_NBMS_CONTEXT, type NbmsContextOption } from '../models/context.models';
import { ContextStateService } from '../services/context-state.service';
import { DashboardService } from '../services/dashboard.service';
import { NbmsCalloutComponent } from '../ui/nbms-callout.component';
import { NbmsChartCardComponent } from '../ui/nbms-chart-card.component';
import { NbmsContextBarComponent } from '../ui/nbms-context-bar.component';
import { NbmsDataTableComponent } from '../ui/nbms-data-table.component';
import { NbmsKpiCardComponent } from '../ui/nbms-kpi-card.component';
import { NbmsMapCardComponent } from '../ui/nbms-map-card.component';
import { NbmsNarrativePanelComponent } from '../ui/nbms-narrative-panel.component';
import { NbmsPageHeaderComponent } from '../ui/nbms-page-header.component';
import { NbmsStatStripComponent } from '../ui/nbms-stat-strip.component';
import { NbmsTabStripComponent } from '../ui/nbms-tab-strip.component';
import { buildStandardBarOptions, buildStandardDoughnutOptions, buildStandardLineOptions } from '../utils/chart-options.utils';
import { readCssVar, withAlpha } from '../utils/theme.utils';

type DashboardTab = 'overview' | 'readiness' | 'coverage' | 'changes';

type DashboardStat = {
  title: string;
  value: string;
  hint: string;
  icon: string;
  tone: 'neutral' | 'positive' | 'negative' | 'info';
};

type DashboardRow = {
  uuid: string;
  code: string;
  title: string;
  updatedAt: string | null;
  readinessScore: number;
  readinessStatus: string;
  frameworkCode: string;
  targetCode: string;
  trend: string;
  issues: string[];
  hasSpatial: boolean;
  accessLevel: string;
};

type FrameworkTargetRow = {
  frameworkCode: string;
  targetCode: string;
  total: number;
};

type DashboardBlockerRow = {
  label: string;
  count: number;
};

type DashboardQualityRow = {
  uuid: string;
  code: string;
  targetCode: string;
  issues: string;
};

type DashboardSpotlightRow = {
  frameworkCode: string;
  targetCode: string;
  total: number;
  subtitle: string;
};

type DashboardVm = {
  context: ReturnType<ContextStateService['parseQueryParams']>;
  tabCounts: Record<DashboardTab, number>;
  stats: DashboardStat[];
  recentRows: DashboardRow[];
  readinessRows: DashboardRow[];
  changeRows: DashboardRow[];
  frameworkTargetRows: FrameworkTargetRow[];
  blockerRows: DashboardBlockerRow[];
  qualityRows: DashboardQualityRow[];
  spotlightRows: DashboardSpotlightRow[];
  readinessChart: ChartData<'doughnut'>;
  targetChart: ChartData<'bar'>;
  changesChart: ChartData<'line'>;
  coverageChart: ChartData<'bar'>;
  narrativeSections: Array<{ id: string; title: string; body: string; helperText?: string }>;
  reportCycleOptions: NbmsContextOption[];
  methodOptions: NbmsContextOption[];
  releaseOptions: NbmsContextOption[];
  geoTypeOptions: NbmsContextOption[];
  yearOptions: number[];
};

@Component({
  selector: 'app-dashboard-page',
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
    NbmsKpiCardComponent,
    NbmsMapCardComponent,
    NbmsNarrativePanelComponent,
    NbmsPageHeaderComponent,
    NbmsStatStripComponent,
    NbmsTabStripComponent
  ],
  template: `
    <section class="dashboard-page" *ngIf="vm$ | async as vm">
      <nbms-page-header
        title="NBMS Home Dashboard"
        subtitle="A shared entry point for readiness, coverage, change tracking, and drilldown into frameworks and indicators."
        [breadcrumbs]="[{ label: 'Dashboard', route: ['/dashboard'] }]"
        [badges]="[
          { label: vm.context.report_cycle || 'Current cycle', tone: 'info' },
          { label: vm.context.geo_type, tone: 'neutral' }
        ]"
        [actions]="[
          { id: 'frameworks', label: 'Frameworks', icon: 'account_tree', route: ['/frameworks'], variant: 'stroked' },
          { id: 'indicators', label: 'Indicators', icon: 'insights', route: ['/indicators'], variant: 'flat' }
        ]"
      ></nbms-page-header>

      <nbms-tab-strip
        [tabs]="[
          { id: 'overview', label: 'Overview', count: vm.tabCounts.overview },
          { id: 'readiness', label: 'Readiness', count: vm.tabCounts.readiness },
          { id: 'coverage', label: 'Coverage', count: vm.tabCounts.coverage },
          { id: 'changes', label: 'Changes', count: vm.tabCounts.changes }
        ]"
        [activeTab]="vm.context.tab"
        (tabChange)="patchContext({ tab: $any($event) })"
      ></nbms-tab-strip>

      <nbms-context-bar
        [state]="vm.context"
        [reportCycleOptions]="vm.reportCycleOptions"
        [methodOptions]="vm.methodOptions"
        [releaseOptions]="vm.releaseOptions"
        [geoTypeOptions]="vm.geoTypeOptions"
        [yearOptions]="vm.yearOptions"
        helperText="Dashboard tabs share the same deep-linkable context model as the framework and indicator analytics pages."
        (stateChange)="patchContext($event)"
      ></nbms-context-bar>

      <nbms-stat-strip>
        <nbms-kpi-card
          *ngFor="let stat of vm.stats; trackBy: trackByStat"
          [title]="stat.title"
          [value]="stat.value"
          [hint]="stat.hint"
          [icon]="stat.icon"
          [tone]="stat.tone"
        ></nbms-kpi-card>
      </nbms-stat-strip>

      <section [ngSwitch]="vm.context.tab">
        <section class="content-grid" *ngSwitchCase="'overview'">
          <div class="main-column">
            <section class="split-grid">
              <nbms-chart-card title="Readiness distribution" eyebrow="Overview" subtitle="Current readiness split for published indicators">
                <div class="chart-wrap">
                  <canvas baseChart [data]="vm.readinessChart" [type]="'doughnut'" [options]="doughnutOptions"></canvas>
                </div>
              </nbms-chart-card>

              <article class="summary-panel nbms-card-surface">
                <div class="summary-panel-head">
                  <div>
                    <p class="eyebrow">Blockers</p>
                    <h2>Top blockers</h2>
                  </div>
                  <span class="sub-copy">{{ vm.blockerRows.length }} blocker patterns</span>
                </div>

                <div class="blocker-list" *ngIf="vm.blockerRows.length; else noBlockers">
                  <article class="blocker-row" *ngFor="let blocker of vm.blockerRows; trackBy: trackByBlocker">
                    <span>{{ blocker.label }}</span>
                    <strong>{{ blocker.count }}</strong>
                  </article>
                </div>
              </article>
            </section>

            <nbms-map-card
              title="Coverage map"
              eyebrow="Overview"
              subtitle="National coverage surface"
              helperText="A dashboard-level choropleth endpoint is not yet exposed. Use framework, target, or indicator drilldowns for spatially explicit map layers."
            ></nbms-map-card>

            <section class="split-grid">
              <nbms-chart-card title="Progress toward targets" eyebrow="Overview" subtitle="Highest-volume framework target slices">
                <div class="chart-wrap">
                  <canvas baseChart [data]="vm.targetChart" [type]="'bar'" [options]="barOptions"></canvas>
                </div>
              </nbms-chart-card>

              <article class="summary-panel nbms-card-surface">
                <div class="summary-panel-head">
                  <div>
                    <p class="eyebrow">Target scorecards</p>
                    <h2>Top target drilldowns</h2>
                  </div>
                </div>
                <div class="spotlight-list">
                  <a
                    class="spotlight-row"
                    *ngFor="let row of vm.spotlightRows; trackBy: trackBySpotlight"
                    [routerLink]="['/frameworks', row.frameworkCode, 'targets', row.targetCode]"
                  >
                    <strong>{{ row.frameworkCode }} / {{ row.targetCode }}</strong>
                    <span>{{ row.subtitle }}</span>
                  </a>
                </div>
              </article>
            </section>

            <section class="split-grid">
              <nbms-chart-card title="What changed since last cycle" eyebrow="Changes" subtitle="Recent update activity across the current slice">
                <div class="chart-wrap">
                  <canvas baseChart [data]="vm.changesChart" [type]="'line'" [options]="lineOptions"></canvas>
                </div>
              </nbms-chart-card>

              <nbms-data-table
                title="Data quality issues"
                [rows]="vm.qualityRows"
                [columns]="qualityColumns"
                [cellTemplate]="qualityCell"
              ></nbms-data-table>
            </section>

            <nbms-data-table
              title="Recently updated indicators"
              [rows]="vm.recentRows"
              [columns]="dashboardColumns"
              [cellTemplate]="dashboardCell"
            ></nbms-data-table>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Pending approvals"
              tone="warning"
              [message]="(vm.stats[1]?.value || '0') + ' items are still awaiting workflow review in the current dashboard context.'"
            ></nbms-callout>
            <nbms-narrative-panel
              eyebrow="Overview"
              title="Key messages"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </section>

        <section class="content-grid" *ngSwitchCase="'readiness'">
          <div class="main-column">
            <nbms-chart-card title="Readiness focus" eyebrow="Readiness" subtitle="Blocked and warning indicators in the current slice">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.readinessChart" [type]="'doughnut'" [options]="doughnutOptions"></canvas>
              </div>
            </nbms-chart-card>

            <nbms-data-table
              title="Readiness worklist"
              [rows]="vm.readinessRows"
              [columns]="dashboardColumns"
              [cellTemplate]="dashboardCell"
            ></nbms-data-table>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Pending approvals"
              [message]="'The dashboard summary currently reports pending approvals at a portfolio level. Use framework and indicator drilldowns to resolve the slice.'"
              tone="warning"
            ></nbms-callout>
            <nbms-narrative-panel
              eyebrow="Readiness"
              title="Readiness narrative"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </section>

        <section class="content-grid" *ngSwitchCase="'coverage'">
          <div class="main-column">
            <nbms-map-card
              title="Coverage map"
              eyebrow="Coverage"
              subtitle="Map-first coverage surface"
              helperText="An aggregated dashboard coverage map is not yet exposed by the backend. Drill into frameworks or indicators for spatially explicit layers."
            ></nbms-map-card>

            <nbms-chart-card title="Coverage by framework target" eyebrow="Coverage" subtitle="Target slices in the current dashboard context">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.coverageChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-data-table
              title="Coverage drilldowns"
              [rows]="vm.frameworkTargetRows"
              [columns]="frameworkColumns"
              [cellTemplate]="frameworkCell"
            ></nbms-data-table>
          </div>
        </section>

        <section class="content-grid" *ngSwitchCase="'changes'">
          <div class="main-column">
            <nbms-chart-card title="Release delta timeline" eyebrow="Changes" subtitle="Recent update activity across the current slice">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.changesChart" [type]="'line'" [options]="lineOptions"></canvas>
              </div>
            </nbms-chart-card>

            <nbms-data-table
              title="Changed indicators"
              [rows]="vm.changeRows"
              [columns]="dashboardColumns"
              [cellTemplate]="dashboardCell"
            ></nbms-data-table>
          </div>

          <div class="side-column">
            <nbms-narrative-panel
              eyebrow="Changes"
              title="What changed"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </section>
      </section>

      <ng-template #dashboardCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'indicator'">
            <a [routerLink]="['/indicators', row.uuid]">{{ row.code }}</a>
            <span class="sub-copy">{{ row.title }}</span>
          </ng-container>
          <ng-container *ngSwitchCase="'frameworkTarget'">
            <a [routerLink]="['/frameworks', row.frameworkCode, 'targets', row.targetCode]">{{ row.frameworkCode }} / {{ row.targetCode }}</a>
          </ng-container>
          <ng-container *ngSwitchCase="'updatedAt'">{{ row.updatedAt || 'n/a' }}</ng-container>
          <ng-container *ngSwitchCase="'readiness'">{{ row.readinessStatus }} ({{ row.readinessScore }})</ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>

      <ng-template #frameworkCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'framework'">
            <a [routerLink]="['/frameworks', row.frameworkCode]">{{ row.frameworkCode }}</a>
          </ng-container>
          <ng-container *ngSwitchCase="'target'">
            <a [routerLink]="['/frameworks', row.frameworkCode, 'targets', row.targetCode]">{{ row.targetCode }}</a>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>

      <ng-template #qualityCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'indicator'">
            <a [routerLink]="['/indicators', row.uuid]">{{ row.code }}</a>
          </ng-container>
          <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
        </ng-container>
      </ng-template>

      <ng-template #noBlockers>
        <div class="nbms-empty-state">No blocker patterns were found in the current dashboard slice.</div>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .dashboard-page,
      .content-grid,
      .main-column,
      .side-column {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .split-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: var(--nbms-space-4);
      }

      .content-grid {
        grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.9fr);
      }

      .side-column {
        align-self: start;
        position: sticky;
        top: 5.4rem;
      }

      .chart-wrap {
        min-height: 280px;
      }

      .summary-panel,
      .spotlight-list,
      .blocker-list {
        display: grid;
        gap: var(--nbms-space-3);
      }

      .summary-panel {
        padding: var(--nbms-space-4) var(--nbms-space-5);
      }

      .summary-panel-head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
      }

      .summary-panel-head h2 {
        margin: var(--nbms-space-1) 0 0;
      }

      .blocker-row {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-2);
        align-items: center;
        border-top: 1px solid var(--nbms-divider);
        padding-top: var(--nbms-space-3);
      }

      .blocker-row span {
        color: var(--nbms-text-secondary);
      }

      .spotlight-row {
        display: grid;
        gap: var(--nbms-space-1);
        border-top: 1px solid var(--nbms-divider);
        color: inherit;
        padding-top: var(--nbms-space-3);
        text-decoration: none;
      }

      .spotlight-row span {
        color: var(--nbms-text-secondary);
      }

      .sub-copy {
        display: block;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      @media (max-width: 1080px) {
        .split-grid,
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
export class DashboardPageComponent {
  @ViewChild('dashboardCell', { static: true }) dashboardCellTemplate!: TemplateRef<{ $implicit: DashboardRow; key: string }>;
  @ViewChild('frameworkCell', { static: true }) frameworkCellTemplate!: TemplateRef<{ $implicit: FrameworkTargetRow; key: string }>;

  private readonly route = inject(ActivatedRoute);
  private readonly dashboard = inject(DashboardService);
  private readonly contextState = inject(ContextStateService);

  readonly dashboardColumns = [
    { key: 'indicator', label: 'Indicator' },
    { key: 'frameworkTarget', label: 'Framework / target' },
    { key: 'readiness', label: 'Readiness' },
    { key: 'trend', label: 'Trend' },
    { key: 'updatedAt', label: 'Updated' }
  ];

  readonly frameworkColumns = [
    { key: 'framework', label: 'Framework' },
    { key: 'target', label: 'Target' },
    { key: 'total', label: 'Links' }
  ];

  readonly qualityColumns = [
    { key: 'indicator', label: 'Indicator' },
    { key: 'targetCode', label: 'Target' },
    { key: 'issues', label: 'Issues' }
  ];

  readonly context$ = this.contextState.connect(this.route, {
    defaults: {
      ...DEFAULT_NBMS_CONTEXT,
      tab: 'overview',
      report_cycle: 'NR7-2024',
      metric: 'readiness',
      agg: 'national'
    }
  });

  readonly vm$ = combineLatest([this.dashboard.getSummary(), this.context$]).pipe(
    map(([summary, context]) => this.buildVm(summary, context))
  );

  readonly doughnutOptions = buildStandardDoughnutOptions();
  readonly barOptions = buildStandardBarOptions();
  readonly horizontalBarOptions = buildStandardBarOptions(true);
  readonly lineOptions = buildStandardLineOptions();

  patchContext(patch: Record<string, unknown>): void {
    this.contextState.update(this.route, patch as any);
  }

  copyNarrative(sections: Array<{ title: string; body: string }>): void {
    const text = sections.map((section) => `${section.title}\n${section.body}`).join('\n\n');
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
  }

  trackByStat(_: number, stat: DashboardStat): string {
    return stat.title;
  }

  trackByBlocker(_: number, row: DashboardBlockerRow): string {
    return row.label;
  }

  trackBySpotlight(_: number, row: DashboardSpotlightRow): string {
    return `${row.frameworkCode}-${row.targetCode}`;
  }

  private buildVm(summary: DashboardSummary, context: ReturnType<ContextStateService['parseQueryParams']>): DashboardVm {
    const rows = buildDashboardRows(summary, context.q);
    const recentRows = rows.slice(0, 10);
    const readinessRows = rows.filter((row) => row.readinessStatus !== 'ready');
    const changeRows = rows.filter((row) => row.updatedAt).slice(0, 12);
    const frameworkTargetRows = summary.published_by_framework_target
      .map((row) => ({
        frameworkCode: row.framework_indicator__framework_target__framework__code,
        targetCode: row.framework_indicator__framework_target__code,
        total: row.total
      }))
      .filter((row) => matchesQuery(`${row.frameworkCode} ${row.targetCode}`, context.q))
      .sort((a, b) => b.total - a.total || a.targetCode.localeCompare(b.targetCode))
      .slice(0, 10);
    const blockerRows = summarizeBlockers(rows).slice(0, 6);
    const qualityRows = rows
      .filter((row) => row.issues.length)
      .map((row) => ({
        uuid: row.uuid,
        code: row.code,
        targetCode: row.targetCode,
        issues: row.issues.join(', ')
      }))
      .slice(0, 12);
    const spotlightRows = frameworkTargetRows.slice(0, 6).map((row) => ({
      frameworkCode: row.frameworkCode,
      targetCode: row.targetCode,
      total: row.total,
      subtitle: `${row.total} linked indicators`
    }));

    const readinessTotals = summary.indicator_readiness.totals;
    const readinessChart = {
      labels: ['Ready', 'Warning', 'Blocked'],
      datasets: [
        {
          data: [readinessTotals.ready, readinessTotals.warning, readinessTotals.blocked],
          backgroundColor: [
            readCssVar('--nbms-color-success'),
            readCssVar('--nbms-color-accent-500'),
            readCssVar('--nbms-color-error')
          ],
          borderWidth: 0
        }
      ]
    } satisfies ChartData<'doughnut'>;

    const targetChart = {
      labels: frameworkTargetRows.slice(0, 6).map((row) => `${row.frameworkCode} ${row.targetCode}`),
      datasets: [
        {
          data: frameworkTargetRows.slice(0, 6).map((row) => row.total),
          backgroundColor: frameworkTargetRows.slice(0, 6).map(() => readCssVar('--nbms-color-secondary-500')),
          borderRadius: 10,
          maxBarThickness: 36
        }
      ]
    } satisfies ChartData<'bar'>;

    const coverageChart = {
      labels: frameworkTargetRows.slice(0, 8).map((row) => row.targetCode),
      datasets: [
        {
          data: frameworkTargetRows.slice(0, 8).map((row) => row.total),
          backgroundColor: frameworkTargetRows.slice(0, 8).map(() => withAlpha(readCssVar('--nbms-color-primary-500'), 0.8)),
          borderRadius: 10,
          maxBarThickness: 28
        }
      ]
    } satisfies ChartData<'bar'>;

    const approvalSeries = summary.approvals_over_time.slice(-10);
    const changesChart = {
      labels: approvalSeries.map((row) => row.day),
      datasets: [
        {
          data: approvalSeries.map((row) => row.total),
          borderColor: readCssVar('--nbms-color-secondary-500'),
          backgroundColor: withAlpha(readCssVar('--nbms-color-secondary-500'), 0.18),
          fill: true,
          tension: 0.3
        }
      ]
    } satisfies ChartData<'line'>;

    const freshnessDays = medianDaysSince(rows.map((row) => row.updatedAt));
    const spatialCount = rows.filter((row) => row.hasSpatial).length;
    const accessControlledCount = rows.filter((row) => row.accessLevel.toLowerCase() !== 'public').length;
    const publishablePercent = rows.length ? Math.round((readinessTotals.ready / rows.length) * 100) : 0;
    const spatialPercent = rows.length ? Math.round((spatialCount / rows.length) * 100) : 0;

    const stats: DashboardStat[] = [
      { title: 'Indicators', value: String(rows.length), hint: 'Indicators in the current dashboard slice', icon: 'insights', tone: 'neutral' },
      { title: 'Pending approvals', value: String(summary.approvals_queue), hint: 'Workflow items awaiting review', icon: 'approval', tone: summary.approvals_queue > 0 ? 'info' : 'neutral' },
      { title: 'Framework targets', value: String(frameworkTargetRows.length), hint: 'Framework → target links visible in this context', icon: 'account_tree', tone: 'neutral' },
      { title: 'Blocked indicators', value: String(readinessRows.filter((row) => row.readinessStatus === 'blocked').length), hint: 'Indicators still blocked for publication', icon: 'warning', tone: readinessRows.some((row) => row.readinessStatus === 'blocked') ? 'negative' : 'neutral' },
      { title: 'Publishable', value: `${readinessTotals.ready} / ${rows.length}`, hint: `${publishablePercent}% ready for publication`, icon: 'verified', tone: readinessTotals.ready ? 'positive' : 'neutral' },
      { title: 'Freshness', value: freshnessDays !== null ? `${freshnessDays}d` : 'n/a', hint: 'Median days since last update', icon: 'schedule', tone: freshnessDays !== null && freshnessDays > 120 ? 'negative' : 'neutral' },
      { title: 'Ready', value: String(readinessTotals.ready), hint: 'Ready indicators in the current slice', icon: 'task_alt', tone: 'positive' },
      { title: 'Spatial coverage', value: `${spatialPercent}%`, hint: `${spatialCount} indicators have spatial outputs`, icon: 'map', tone: 'neutral' },
      { title: 'Access controlled', value: String(accessControlledCount), hint: 'Indicators not marked public in this slice', icon: 'shield', tone: accessControlledCount ? 'info' : 'neutral' }
    ];

    return {
      context: { ...context, tab: toDashboardTab(context.tab) },
      tabCounts: {
        overview: rows.length,
        readiness: readinessRows.length,
        coverage: frameworkTargetRows.length,
        changes: changeRows.length
      },
      stats,
      recentRows,
      readinessRows,
      changeRows,
      frameworkTargetRows,
      blockerRows,
      qualityRows,
      spotlightRows,
      readinessChart,
      targetChart,
      changesChart,
      coverageChart,
      narrativeSections: [
        {
          id: 'summary',
          title: 'Portfolio summary',
          body: `The dashboard currently surfaces ${rows.length} indicators and ${frameworkTargetRows.length} framework target slices in the selected context.`
        },
        {
          id: 'readiness',
          title: 'Readiness pressure',
          body: `${readinessRows.length} indicators remain in warning or blocked states and should be drilled into from the readiness tab.`
        },
        {
          id: 'changes',
          title: 'Recent changes',
          body: `${changeRows.length} indicators show recent update timestamps in the current dashboard slice.`
        }
      ],
      reportCycleOptions: [
        { value: 'NR7-2024', label: 'NR7 2024' },
        { value: 'NR7-2022', label: 'NR7 2022' }
      ],
      methodOptions: [
        { value: 'current', label: 'Current approved method' },
        { value: 'baseline', label: 'Baseline method' }
      ],
      releaseOptions: [
        { value: 'latest_approved', label: 'Latest approved release' },
        { value: 'draft', label: 'Draft release', disabled: true }
      ],
      geoTypeOptions: [
        { value: 'national', label: 'National' },
        { value: 'province', label: 'Province' },
        { value: 'biome', label: 'Biome' }
      ],
      yearOptions: summary.approvals_over_time
        .map((row) => Number(row.day.slice(0, 4)))
        .filter((year) => Number.isFinite(year))
        .filter((year, index, items) => items.indexOf(year) === index)
    };
  }
}

function buildDashboardRows(summary: DashboardSummary, query: string): DashboardRow[] {
  const trendByCode = new Map(summary.trend_signals.map((row) => [row.indicator_code, row.trend]));
  const issueByCode = new Map(summary.data_quality_alerts.map((row) => [row.indicator_code, row.issues]));
  return summary.latest_published_updates
    .map((row) => ({
      uuid: row.uuid,
      code: row.code,
      title: row.title,
      updatedAt: row.last_updated_on || row.updated_at || null,
      readinessScore: row.readiness_score,
      readinessStatus: row.readiness_status,
      frameworkCode: firstFrameworkFromTags(row.tags),
      targetCode: row.national_target.code || 'UNMAPPED',
      trend: trendByCode.get(row.code) || 'unknown',
      issues: issueByCode.get(row.code) || [],
      hasSpatial: row.tags.includes('spatial') || row.coverage.geography.toLowerCase() !== 'national',
      accessLevel: row.sensitivity || 'public'
    }))
    .filter((row) => matchesQuery(`${row.code} ${row.title} ${row.targetCode}`, query))
    .sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || '') || a.code.localeCompare(b.code));
}

function summarizeBlockers(rows: DashboardRow[]): DashboardBlockerRow[] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    for (const issue of row.issues) {
      counts.set(issue, (counts.get(issue) || 0) + 1);
    }
  }
  return Array.from(counts.entries())
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

function medianDaysSince(values: Array<string | null>): number | null {
  const days = values
    .map((value) => {
      if (!value) {
        return null;
      }
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) {
        return null;
      }
      const elapsed = Date.now() - parsed.getTime();
      return Math.max(0, Math.round(elapsed / (1000 * 60 * 60 * 24)));
    })
    .filter((value): value is number => value !== null)
    .sort((a, b) => a - b);

  if (!days.length) {
    return null;
  }

  const middle = Math.floor(days.length / 2);
  return days.length % 2 ? days[middle] : Math.round((days[middle - 1] + days[middle]) / 2);
}

function firstFrameworkFromTags(tags: string[]): string {
  const frameworkTag = tags.find((tag) => ['GBF', 'SDG', 'RAMSAR', 'CMS', 'CITES', 'NBSAP'].some((prefix) => tag.includes(prefix)));
  return frameworkTag?.split(':')[0] || 'GBF';
}

function matchesQuery(text: string, query: string): boolean {
  return !query.trim() || text.toLowerCase().includes(query.trim().toLowerCase());
}

function toDashboardTab(value: string): DashboardTab {
  return value === 'readiness' || value === 'coverage' || value === 'changes' ? value : 'overview';
}

export { DashboardPageComponent as HomeDashboardPageComponent };
