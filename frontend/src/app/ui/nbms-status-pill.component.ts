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
        background: rgb(25 122 67 / 12%);
        color: var(--nbms-color-success);
        border-color: rgb(25 122 67 / 35%);
      }

      .tone-warn {
        background: rgb(197 138 0 / 12%);
        color: var(--nbms-color-accent-700);
        border-color: rgb(197 138 0 / 35%);
      }

      .tone-error {
        background: rgb(179 38 30 / 12%);
        color: var(--nbms-color-error);
        border-color: rgb(179 38 30 / 36%);
      }

      .tone-info {
        background: rgb(22 100 162 / 12%);
        color: var(--nbms-color-info);
        border-color: rgb(22 100 162 / 36%);
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
