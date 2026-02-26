import { AsyncPipe, DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';

import { DashboardService } from '../services/dashboard.service';
import { HelpTooltipComponent } from '../components/help-tooltip.component';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    NgFor,
    NgIf,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatChipsModule,
    BaseChartDirective,
    HelpTooltipComponent
  ],
  template: `
    <section class="page-grid" *ngIf="summary$ | async as summary">
      <article class="metric-card" *ngFor="let metric of metrics(summary.counts)">
        <h3>{{ metric.label }}</h3>
        <p class="metric-value">{{ metric.value }}</p>
      </article>

      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>Approvals Queue</mat-card-title>
          <app-help-tooltip text="Shows indicators pending review and decision." />
        </mat-card-header>
        <mat-card-content>
          <p class="metric-value">{{ summary.approvals_queue }}</p>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel chart-panel">
        <mat-card-header>
          <mat-card-title>Published Indicators by Framework Target</mat-card-title>
          <app-help-tooltip text="Counts of published indicators mapped to framework targets." />
        </mat-card-header>
        <mat-card-content *ngIf="targetChartData$ | async as chartData">
          <canvas
            baseChart
            [data]="chartData"
            [type]="'bar'"
            [options]="barOptions"
          ></canvas>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel chart-panel">
        <mat-card-header>
          <mat-card-title>Approvals Over Time</mat-card-title>
          <app-help-tooltip text="Daily workflow approvals and publish actions from audit events." />
        </mat-card-header>
        <mat-card-content *ngIf="approvalChartData$ | async as approvalChartData">
          <canvas
            baseChart
            [data]="approvalChartData"
            [type]="'line'"
            [options]="lineOptions"
          ></canvas>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>Latest Published Indicator Updates</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let item of summary.latest_published_updates">
              <mat-icon matListItemIcon>insights</mat-icon>
              <div matListItemTitle>{{ item.code }} - {{ item.title }}</div>
              <div matListItemLine>{{ item.updated_at | date: 'mediumDate' }}</div>
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>Data Quality Alerts</mat-card-title>
          <app-help-tooltip text="Flags indicators with QA or data completeness issues." />
        </mat-card-header>
        <mat-card-content>
          <div *ngIf="!summary.data_quality_alerts.length">No active alerts.</div>
          <div class="alert-row" *ngFor="let alert of summary.data_quality_alerts">
            <strong>{{ alert.indicator_code }}</strong>
            <mat-chip-set>
              <mat-chip *ngFor="let issue of alert.issues">{{ issue }}</mat-chip>
            </mat-chip-set>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>Progress Signals</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="signal-row" *ngFor="let signal of summary.trend_signals">
            <span>{{ signal.indicator_code }}</span>
            <span
              class="signal-chip"
              [class.up]="signal.trend === 'up'"
              [class.down]="signal.trend === 'down'"
            >
              {{ signal.trend }}
            </span>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>Indicator Readiness Dashboard</mat-card-title>
          <app-help-tooltip text="Readiness totals and average score by target from published indicator releases." />
        </mat-card-header>
        <mat-card-content>
          <mat-chip-set *ngIf="summary.indicator_readiness as readiness">
            <mat-chip>Ready: {{ readiness.totals.ready }}</mat-chip>
            <mat-chip>Warning: {{ readiness.totals.warning }}</mat-chip>
            <mat-chip>Blocked: {{ readiness.totals.blocked }}</mat-chip>
          </mat-chip-set>
          <div class="signal-row" *ngFor="let row of summary.indicator_readiness.by_target">
            <span>{{ row.target_code }} - {{ row.target_title }}</span>
            <span class="signal-chip">Avg {{ row.readiness_score_avg }}</span>
          </div>
        </mat-card-content>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .page-grid {
        display: grid;
        grid-template-columns: repeat(12, minmax(0, 1fr));
        gap: 1rem;
      }

      .metric-card {
        grid-column: span 3;
        border-radius: 14px;
        padding: 1rem;
        background: linear-gradient(160deg, rgba(18, 106, 78, 0.11), rgba(250, 252, 248, 0.95));
        border: 1px solid rgba(18, 106, 78, 0.2);
      }

      .panel {
        grid-column: span 6;
      }

      .chart-panel {
        min-height: 280px;
      }

      .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--nbms-primary);
      }

      .alert-row,
      .signal-row {
        margin-bottom: 0.7rem;
      }

      .signal-chip {
        border-radius: 999px;
        padding: 0.15rem 0.6rem;
        text-transform: uppercase;
        background: #d7d7d7;
      }

      .signal-chip.up {
        background: #b6dfc7;
      }

      .signal-chip.down {
        background: #f7b7b7;
      }

      @media (max-width: 980px) {
        .metric-card,
        .panel {
          grid-column: span 12;
        }
      }
    `
  ]
})
export class DashboardPageComponent {
  private readonly dashboardService = inject(DashboardService);

  readonly summary$ = this.dashboardService.getSummary();

  readonly targetChartData$ = this.summary$.pipe(
    map((summary): ChartData<'bar'> => {
      const labels = summary.published_by_framework_target.map(
        (row) =>
          `${row.framework_indicator__framework_target__framework__code} ${row.framework_indicator__framework_target__code}`
      );
      const values = summary.published_by_framework_target.map((row) => row.total);
      return {
        labels,
        datasets: [
          {
            label: 'Published indicators',
            data: values,
            borderRadius: 4,
            backgroundColor: '#2f855a'
          }
        ]
      };
    })
  );

  readonly barOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0 } }
    }
  };

  readonly approvalChartData$ = this.summary$.pipe(
    map((summary): ChartData<'line'> => {
      const labels = summary.approvals_over_time.map((row) => row.day);
      const values = summary.approvals_over_time.map((row) => row.total);
      return {
        labels,
        datasets: [
          {
            label: 'Approvals/publishes',
            data: values,
            borderColor: '#0c7c6b',
            backgroundColor: 'rgba(12, 124, 107, 0.18)',
            tension: 0.25,
            fill: true
          }
        ]
      };
    })
  );

  readonly lineOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: true } },
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0 } }
    }
  };

  metrics(counts: Record<string, number>) {
    return [
      { label: 'Draft instances', value: counts['instances_draft'] ?? 0 },
      { label: 'In review', value: counts['instances_in_review'] ?? 0 },
      { label: 'Approved', value: counts['instances_approved'] ?? 0 },
      { label: 'Released', value: counts['instances_released'] ?? 0 }
    ];
  }
}
