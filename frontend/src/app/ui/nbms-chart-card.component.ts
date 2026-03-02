import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';

@Component({
  selector: 'nbms-chart-card',
  standalone: true,
  imports: [NgIf],
  template: `
    <section class="chart-card nbms-card-surface">
      <header class="head">
        <div>
          <p class="eyebrow" *ngIf="eyebrow">{{ eyebrow }}</p>
          <h2>{{ title }}</h2>
          <p class="subtitle" *ngIf="subtitle">{{ subtitle }}</p>
        </div>
        <ng-content select="[card-actions]"></ng-content>
      </header>
      <div class="body">
        <ng-content></ng-content>
      </div>
      <footer class="footer" *ngIf="footerText">{{ footerText }}</footer>
    </section>
  `,
  styles: [
    `
      .chart-card {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4) var(--nbms-space-5);
      }

      .head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
      }

      .eyebrow,
      .subtitle,
      .footer {
        margin: 0;
        color: var(--nbms-text-muted);
      }

      .eyebrow {
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      h2 {
        margin: var(--nbms-space-1) 0 0;
        line-height: 1.15;
      }

      .body {
        min-height: 220px;
      }

      .footer {
        border-top: 1px solid var(--nbms-divider);
        padding-top: var(--nbms-space-3);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsChartCardComponent {
  @Input() title = 'Chart';
  @Input() eyebrow = '';
  @Input() subtitle = '';
  @Input() footerText = '';
}
