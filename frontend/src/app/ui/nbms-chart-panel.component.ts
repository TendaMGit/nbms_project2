import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';
import { PlotlyChartComponent } from '../components/plotly-chart.component';

@Component({
  selector: 'nbms-chart-panel',
  standalone: true,
  imports: [NgIf, PlotlyChartComponent],
  template: `
    <section class="chart nbms-card-surface">
      <header>
        <h3>{{ title }}</h3>
      </header>
      <app-plotly-chart
        *ngIf="data.length"
        [spec]="{ data: data, layout: layout, config: config }"
      ></app-plotly-chart>
      <p *ngIf="!data.length">No chart data available.</p>
    </section>
  `,
  styles: [
    `
      .chart {
        padding: var(--nbms-space-4);
        display: grid;
        gap: var(--nbms-space-2);
      }

      h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
      }

      p {
        margin: 0;
        color: var(--nbms-text-muted);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsChartPanelComponent {
  @Input() title = 'Chart';
  @Input() data: Array<Record<string, unknown>> = [];
  @Input() layout: Record<string, unknown> = {};
  @Input() config: Record<string, unknown> = {};
}
