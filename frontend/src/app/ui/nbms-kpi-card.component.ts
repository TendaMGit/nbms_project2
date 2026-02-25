import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'nbms-kpi-card',
  standalone: true,
  imports: [NgIf, MatIconModule],
  template: `
    <article class="kpi nbms-card-surface">
      <header>
        <span>{{ title }}</span>
        <mat-icon>{{ icon }}</mat-icon>
      </header>
      <div class="value">{{ value }}</div>
      <p *ngIf="hint">{{ hint }}</p>
    </article>
  `,
  styles: [
    `
      .kpi {
        padding: var(--nbms-space-4);
        display: grid;
        gap: var(--nbms-space-2);
      }

      .kpi header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: var(--nbms-text-secondary);
        font-size: var(--nbms-font-size-label);
      }

      .kpi .value {
        font-size: var(--nbms-font-size-h2);
        font-weight: 700;
        line-height: 1.1;
        color: var(--nbms-text-primary);
      }

      .kpi p {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsKpiCardComponent {
  @Input() title = '';
  @Input() value = '0';
  @Input() hint = '';
  @Input() icon = 'insights';
}
