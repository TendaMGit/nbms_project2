import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'nbms-readiness-badge',
  standalone: true,
  imports: [NgClass],
  template: `
    <div class="badge" [ngClass]="statusClass">
      <strong>{{ score }}</strong>
      <span>{{ statusLabel }}</span>
    </div>
  `,
  styles: [
    `
      .badge {
        display: inline-flex;
        gap: 0.35rem;
        align-items: center;
        border-radius: var(--nbms-radius-pill);
        border: 1px solid var(--nbms-border);
        background: var(--nbms-surface-muted);
        color: var(--nbms-text-secondary);
        padding: 0.15rem 0.55rem;
        font-size: var(--nbms-font-size-label-sm);
      }

      .badge strong {
        font-size: var(--nbms-font-size-label);
      }

      .status-ready {
        color: var(--nbms-color-success);
        border-color: rgb(25 122 67 / 40%);
        background: rgb(25 122 67 / 10%);
      }

      .status-warning {
        color: var(--nbms-color-accent-700);
        border-color: rgb(197 138 0 / 40%);
        background: rgb(197 138 0 / 10%);
      }

      .status-blocked {
        color: var(--nbms-color-error);
        border-color: rgb(179 38 30 / 40%);
        background: rgb(179 38 30 / 10%);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsReadinessBadgeComponent {
  @Input() score = 0;
  @Input() status: 'ready' | 'warning' | 'blocked' = 'blocked';

  get statusClass(): string {
    return `status-${this.status}`;
  }

  get statusLabel(): string {
    if (this.status === 'ready') {
      return 'Ready';
    }
    if (this.status === 'warning') {
      return 'Warning';
    }
    return 'Blocked';
  }
}
