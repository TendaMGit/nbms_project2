import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'nbms-callout',
  standalone: true,
  imports: [NgIf, MatIconModule],
  template: `
    <article class="callout" [attr.data-tone]="tone">
      <mat-icon aria-hidden="true">{{ icon }}</mat-icon>
      <div class="copy">
        <strong *ngIf="title">{{ title }}</strong>
        <p>{{ message }}</p>
      </div>
    </article>
  `,
  styles: [
    `
      .callout {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: var(--nbms-space-3);
        border-radius: var(--nbms-radius-md);
        border: 1px solid var(--nbms-border);
        background: var(--nbms-surface-muted);
        padding: var(--nbms-space-3);
      }

      .callout mat-icon {
        color: inherit;
      }

      .copy {
        display: grid;
        gap: var(--nbms-space-1);
      }

      .copy strong,
      .copy p {
        margin: 0;
      }

      .copy p {
        color: var(--nbms-text-secondary);
      }

      .callout[data-tone='info'] {
        color: var(--nbms-color-info);
        border-color: color-mix(in srgb, var(--nbms-color-info) 28%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-info) 10%, transparent);
      }

      .callout[data-tone='warning'] {
        color: var(--nbms-color-accent-700);
        border-color: color-mix(in srgb, var(--nbms-color-accent-500) 28%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-accent-500) 10%, transparent);
      }

      .callout[data-tone='error'] {
        color: var(--nbms-color-error);
        border-color: color-mix(in srgb, var(--nbms-color-error) 28%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-error) 10%, transparent);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsCalloutComponent {
  @Input() title = '';
  @Input() message = '';
  @Input() tone: 'info' | 'warning' | 'error' = 'info';

  get icon(): string {
    if (this.tone === 'warning') {
      return 'warning_amber';
    }
    if (this.tone === 'error') {
      return 'error_outline';
    }
    return 'info';
  }
}
