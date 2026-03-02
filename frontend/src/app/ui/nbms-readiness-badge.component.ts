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
        background: var(--nbms-surface-2);
        color: var(--nbms-text-secondary);
        min-height: 1.8rem;
        padding: 0.1rem 0.65rem;
        font-size: var(--nbms-font-size-label-sm);
        letter-spacing: 0.03em;
      }

      .badge strong {
        font-size: var(--nbms-font-size-label);
      }

      .status-ready {
        color: var(--nbms-success);
        border-color: color-mix(in srgb, var(--nbms-success) 38%, var(--nbms-border));
        background: var(--nbms-success-subtle);
      }

      .status-warning {
        color: var(--nbms-warn);
        border-color: color-mix(in srgb, var(--nbms-warn) 38%, var(--nbms-border));
        background: var(--nbms-warn-subtle);
      }

      .status-blocked {
        color: var(--nbms-danger);
        border-color: color-mix(in srgb, var(--nbms-danger) 38%, var(--nbms-border));
        background: var(--nbms-danger-subtle);
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
