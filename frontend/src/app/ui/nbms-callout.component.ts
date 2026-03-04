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
        background: var(--nbms-surface-2);
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
        color: var(--nbms-info);
        border-color: color-mix(in srgb, var(--nbms-info) 28%, var(--nbms-border));
        background: var(--nbms-info-subtle);
      }

      .callout[data-tone='warning'] {
        color: var(--nbms-warn);
        border-color: color-mix(in srgb, var(--nbms-warn) 28%, var(--nbms-border));
        background: var(--nbms-warn-subtle);
      }

      .callout[data-tone='error'] {
        color: var(--nbms-danger);
        border-color: color-mix(in srgb, var(--nbms-danger) 28%, var(--nbms-border));
        background: var(--nbms-danger-subtle);
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
