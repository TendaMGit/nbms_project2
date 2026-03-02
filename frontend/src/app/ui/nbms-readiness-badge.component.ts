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
        border-color: color-mix(in srgb, var(--nbms-color-success) 40%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-success) 10%, transparent);
      }

      .status-warning {
        color: var(--nbms-color-accent-700);
        border-color: color-mix(in srgb, var(--nbms-color-accent-500) 40%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-accent-500) 10%, transparent);
      }

      .status-blocked {
        color: var(--nbms-color-error);
        border-color: color-mix(in srgb, var(--nbms-color-error) 40%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-error) 10%, transparent);
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
