import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'nbms-status-pill',
  standalone: true,
  imports: [NgClass],
  template: `
    <span class="pill" [ngClass]="toneClass">{{ label }}</span>
  `,
  styles: [
    `
      .pill {
        display: inline-flex;
        align-items: center;
        border-radius: var(--nbms-radius-pill);
        border: 1px solid transparent;
        min-height: 1.7rem;
        padding: 0.05rem 0.65rem;
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }

      .tone-neutral {
        background: var(--nbms-surface-2);
        color: var(--nbms-text-secondary);
        border-color: var(--nbms-border);
      }

      .tone-success {
        background: var(--nbms-success-subtle);
        color: var(--nbms-success);
        border-color: color-mix(in srgb, var(--nbms-success) 28%, var(--nbms-border));
      }

      .tone-warn {
        background: var(--nbms-warn-subtle);
        color: var(--nbms-warn);
        border-color: color-mix(in srgb, var(--nbms-warn) 28%, var(--nbms-border));
      }

      .tone-error {
        background: var(--nbms-danger-subtle);
        color: var(--nbms-danger);
        border-color: color-mix(in srgb, var(--nbms-danger) 28%, var(--nbms-border));
      }

      .tone-info {
        background: var(--nbms-info-subtle);
        color: var(--nbms-info);
        border-color: color-mix(in srgb, var(--nbms-info) 28%, var(--nbms-border));
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsStatusPillComponent {
  @Input() label = 'Unknown';
  @Input() tone: 'neutral' | 'success' | 'warn' | 'error' | 'info' = 'neutral';

  get toneClass(): string {
    return `tone-${this.tone}`;
  }
}
