import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';
import { ChangeDetectionStrategy, Component, TemplateRef, ViewChild, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { combineLatest, map } from 'rxjs';

import { DEFAULT_NBMS_CONTEXT, type NbmsContextOption } from '../models/context.models';
import { ContextStateService } from '../services/context-state.service';
import { FrameworkAnalyticsService, type FrameworkSummaryRow } from '../services/framework-analytics.service';
import { NbmsCalloutComponent } from '../ui/nbms-callout.component';
import { NbmsChartCardComponent } from '../ui/nbms-chart-card.component';
import { NbmsContextBarComponent } from '../ui/nbms-context-bar.component';
import { NbmsEntityListTableComponent } from '../ui/nbms-entity-list-table.component';
import { NbmsKpiCardComponent } from '../ui/nbms-kpi-card.component';
import { NbmsMapCardComponent } from '../ui/nbms-map-card.component';
import { NbmsNarrativePanelComponent } from '../ui/nbms-narrative-panel.component';
import { NbmsPageHeaderComponent } from '../ui/nbms-page-header.component';
import { NbmsStatStripComponent } from '../ui/nbms-stat-strip.component';
import { NbmsTabStripComponent } from '../ui/nbms-tab-strip.component';
import { buildStandardBarOptions } from '../utils/chart-options.utils';
import { readCssVar, withAlpha } from '../utils/theme.utils';

type FrameworkExplorerTab = 'list' | 'matrix' | 'map';

type FrameworkStat = {
  title: string;
  value: string;
  hint: string;
  icon: string;
};

type FrameworkExplorerVm = {
  context: ReturnType<ContextStateService['parseQueryParams']> & { tab: FrameworkExplorerTab };
  rows: FrameworkSummaryRow[];
  stats: FrameworkStat[];
  volumeChart: ChartData<'bar'>;
  matrixChart: ChartData<'bar'>;
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
  selector: 'app-framework-explorer-page',
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
    NbmsEntityListTableComponent,
    NbmsKpiCardComponent,
    NbmsMapCardComponent,
    NbmsNarrativePanelComponent,
    NbmsPageHeaderComponent,
    NbmsStatStripComponent,
    NbmsTabStripComponent
  ],
  template: `
    <section class="framework-page" *ngIf="vm$ | async as vm">
      <nbms-page-header
        title="Framework Explorer"
        subtitle="NBMS framework coverage and drilldown entry point for targets, indicators, and reporting narratives."
        [breadcrumbs]="[{ label: 'Dashboard', route: ['/dashboard'] }, { label: 'Frameworks', route: ['/frameworks'] }]"
        [badges]="[
          { label: vm.context.report_cycle || 'Current cycle', tone: 'info' },
          { label: vm.context.geo_type, tone: 'neutral' }
        ]"
        [actions]="[
          { id: 'indicators', label: 'Open indicators', icon: 'insights', route: ['/indicators'], variant: 'stroked' }
        ]"
      ></nbms-page-header>

      <nbms-tab-strip
        [tabs]="[
          { id: 'list', label: 'List', count: vm.rows.length },
          { id: 'matrix', label: 'Matrix', count: vm.rows.length },
          { id: 'map', label: 'Map', count: vm.rows.length }
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
        helperText="Framework analytics use the shared NBMS query model so drilldowns into targets and indicators restore the same context."
        (stateChange)="patchContext($event)"
      ></nbms-context-bar>

      <nbms-stat-strip>
        <nbms-kpi-card
          *ngFor="let stat of vm.stats; trackBy: trackByStat"
          [title]="stat.title"
          [value]="stat.value"
          [hint]="stat.hint"
          [icon]="stat.icon"
        ></nbms-kpi-card>
      </nbms-stat-strip>

      <section class="content-grid" [ngSwitch]="vm.context.tab">
        <ng-container *ngSwitchCase="'list'">
          <div class="main-column">
            <nbms-chart-card title="Framework volume" eyebrow="Explorer" subtitle="Frameworks ranked by linked indicator count">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.volumeChart" [type]="'bar'" [options]="barOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-narrative-panel
              eyebrow="Explorer"
              title="Coverage narrative"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'matrix'">
          <div class="main-column">
            <nbms-chart-card title="Coverage matrix view" eyebrow="Matrix" subtitle="Targets and indicator volume side by side">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.matrixChart" [type]="'bar'" [options]="stackedBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>

          <div class="side-column">
            <nbms-callout
              title="Matrix scope"
              tone="info"
              message="Framework-level matrix coverage is derived from the dashboard summary until a dedicated framework explorer endpoint is exposed."
            ></nbms-callout>
            <nbms-narrative-panel
              eyebrow="Matrix"
              title="What this slice shows"
              [sections]="vm.narrativeSections"
              [showInsertAction]="false"
              (copyRequested)="copyNarrative(vm.narrativeSections)"
            ></nbms-narrative-panel>
          </div>
        </ng-container>

        <ng-container *ngSwitchCase="'map'">
          <div class="main-column">
            <nbms-map-card
              title="Framework coverage map"
              eyebrow="Map"
              subtitle="Spatial framework roll-up"
              helperText="A framework-level aggregate map endpoint is not yet available. Use the target or indicator drilldowns for spatially explicit layers."
            ></nbms-map-card>
          </div>

          <div class="side-column">
            <nbms-chart-card title="Framework volume" eyebrow="Map" subtitle="Current framework slice by linked indicator count">
              <div class="chart-wrap">
                <canvas baseChart [data]="vm.volumeChart" [type]="'bar'" [options]="horizontalBarOptions"></canvas>
              </div>
            </nbms-chart-card>
          </div>
        </ng-container>
      </section>

      <nbms-entity-list-table
        title="Framework index"
        [rows]="vm.rows"
        [columns]="frameworkColumns"
        [cellTemplate]="frameworkCell"
      ></nbms-entity-list-table>

      <ng-template #frameworkCell let-row let-key="key">
        <ng-container [ngSwitch]="key">
          <ng-container *ngSwitchCase="'framework'">
            <a [routerLink]="['/frameworks', row.id]">{{ row.id }}</a>
            <span class="sub-copy">{{ row.title }}</span>
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
      .side-column {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .content-grid {
        grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
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
export class FrameworkExplorerPageComponent {
  @ViewChild('frameworkCell', { static: true })
  frameworkCellTemplate!: TemplateRef<{ $implicit: FrameworkSummaryRow; key: string }>;

  private readonly route = inject(ActivatedRoute);
  private readonly contextState = inject(ContextStateService);
  private readonly frameworks = inject(FrameworkAnalyticsService);

  readonly frameworkColumns = [
    { key: 'framework', label: 'Framework' },
    { key: 'targetCount', label: 'Targets' },
    { key: 'indicatorCount', label: 'Indicators' },
    { key: 'narrative', label: 'Narrative' }
  ];

  readonly context$ = this.contextState.connect(this.route, {
    defaults: {
      ...DEFAULT_NBMS_CONTEXT,
      tab: 'list',
      report_cycle: 'NR7-2024',
      metric: 'coverage',
      agg: 'national'
    }
  });

  readonly vm$ = combineLatest([this.frameworks.frameworks(), this.context$]).pipe(
    map(([rows, context]) => this.buildVm(rows, context))
  );

  readonly barOptions = buildStandardBarOptions();
  readonly horizontalBarOptions = buildStandardBarOptions(true);
  readonly stackedBarOptions = {
    ...buildStandardBarOptions(),
    scales: {
      x: { stacked: false, beginAtZero: true },
      y: { stacked: false, beginAtZero: true }
    }
  };

  patchContext(patch: Record<string, unknown>): void {
    this.contextState.update(this.route, patch as any);
  }

  copyNarrative(sections: Array<{ title: string; body: string }>): void {
    const text = sections.map((section) => `${section.title}\n${section.body}`).join('\n\n');
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
  }

  trackByStat(_: number, stat: FrameworkStat): string {
    return stat.title;
  }

  private buildVm(
    rows: FrameworkSummaryRow[],
    context: ReturnType<ContextStateService['parseQueryParams']>
  ): FrameworkExplorerVm {
    const filteredRows = rows
      .filter((row) => matchesQuery(`${row.id} ${row.title} ${row.narrative}`, context.q))
      .sort((a, b) => b.indicatorCount - a.indicatorCount || a.title.localeCompare(b.title));

    const volumeChart = {
      labels: filteredRows.slice(0, 6).map((row) => row.id),
      datasets: [
        {
          label: 'Indicators',
          data: filteredRows.slice(0, 6).map((row) => row.indicatorCount),
          backgroundColor: filteredRows.slice(0, 6).map(() => readCssVar('--nbms-color-primary-500')),
          borderRadius: 10,
          maxBarThickness: 38
        }
      ]
    } satisfies ChartData<'bar'>;

    const matrixChart = {
      labels: filteredRows.slice(0, 6).map((row) => row.id),
      datasets: [
        {
          label: 'Targets',
          data: filteredRows.slice(0, 6).map((row) => row.targetCount),
          backgroundColor: filteredRows.slice(0, 6).map(() => withAlpha(readCssVar('--nbms-color-secondary-500'), 0.9)),
          borderRadius: 10,
          maxBarThickness: 32
        },
        {
          label: 'Indicators',
          data: filteredRows.slice(0, 6).map((row) => row.indicatorCount),
          backgroundColor: filteredRows.slice(0, 6).map(() => withAlpha(readCssVar('--nbms-color-primary-500'), 0.72)),
          borderRadius: 10,
          maxBarThickness: 32
        }
      ]
    } satisfies ChartData<'bar'>;

    const totalTargets = filteredRows.reduce((sum, row) => sum + row.targetCount, 0);
    const totalIndicators = filteredRows.reduce((sum, row) => sum + row.indicatorCount, 0);

    return {
      context: { ...context, tab: toFrameworkExplorerTab(context.tab) },
      rows: filteredRows,
      stats: [
        { title: 'Frameworks', value: String(filteredRows.length), hint: 'Frameworks in the current slice', icon: 'account_tree' },
        { title: 'Targets', value: String(totalTargets), hint: 'Target links currently visible', icon: 'flag' },
        { title: 'Indicators', value: String(totalIndicators), hint: 'Indicator links across filtered frameworks', icon: 'insights' },
        {
          title: 'Average targets',
          value: filteredRows.length ? String(Math.round(totalTargets / filteredRows.length)) : '0',
          hint: 'Average target count per framework',
          icon: 'analytics'
        }
      ],
      volumeChart,
      matrixChart,
      narrativeSections: [
        {
          id: 'coverage',
          title: 'Framework coverage',
          body: `${filteredRows.length} frameworks are visible with ${totalIndicators} linked indicators across ${totalTargets} targets.`
        },
        {
          id: 'drilldown',
          title: 'Drilldown path',
          body: 'Framework rows link directly into target detail pages, which then drill into indicator analytics using the same query context.'
        },
        {
          id: 'mapping',
          title: 'Mapping caveat',
          body: 'Framework explorer charts are derived from the published dashboard summary until a dedicated framework explorer API is available.'
        }
      ],
      reportCycleOptions: REPORT_CYCLE_OPTIONS,
      releaseOptions: RELEASE_OPTIONS,
      methodOptions: METHOD_OPTIONS,
      geoTypeOptions: GEO_TYPE_OPTIONS,
      yearOptions: [2020, 2021, 2022, 2023, 2024]
    };
  }
}

function toFrameworkExplorerTab(value: string): FrameworkExplorerTab {
  return value === 'matrix' || value === 'map' ? value : 'list';
}

function matchesQuery(text: string, query: string): boolean {
  return !query.trim() || text.toLowerCase().includes(query.trim().toLowerCase());
}
