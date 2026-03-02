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
        padding: 0.1rem 0.55rem;
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.02em;
      }

      .tone-neutral {
        background: var(--nbms-slate-100);
        color: var(--nbms-slate-800);
        border-color: var(--nbms-slate-200);
      }

      .tone-success {
        background: color-mix(in srgb, var(--nbms-color-success) 12%, transparent);
        color: var(--nbms-color-success);
        border-color: color-mix(in srgb, var(--nbms-color-success) 35%, var(--nbms-surface));
      }

      .tone-warn {
        background: color-mix(in srgb, var(--nbms-color-accent-500) 12%, transparent);
        color: var(--nbms-color-accent-700);
        border-color: color-mix(in srgb, var(--nbms-color-accent-500) 35%, var(--nbms-surface));
      }

      .tone-error {
        background: color-mix(in srgb, var(--nbms-color-error) 12%, transparent);
        color: var(--nbms-color-error);
        border-color: color-mix(in srgb, var(--nbms-color-error) 36%, var(--nbms-surface));
      }

      .tone-info {
        background: color-mix(in srgb, var(--nbms-color-info) 12%, transparent);
        color: var(--nbms-color-info);
        border-color: color-mix(in srgb, var(--nbms-color-info) 36%, var(--nbms-surface));
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
