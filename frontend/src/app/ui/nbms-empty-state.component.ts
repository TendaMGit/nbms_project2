import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'nbms-empty-state',
  standalone: true,
  imports: [NgIf, MatButtonModule, MatIconModule],
  template: `
    <section class="empty nbms-card-surface">
      <mat-icon>{{ icon }}</mat-icon>
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
      <button mat-flat-button color="primary" *ngIf="ctaLabel">{{ ctaLabel }}</button>
    </section>
  `,
  styles: [
    `
      .empty {
        padding: var(--nbms-space-8);
        text-align: center;
        display: grid;
        gap: var(--nbms-space-3);
        justify-items: center;
      }

      .empty mat-icon {
        width: 2rem;
        height: 2rem;
        font-size: 2rem;
        color: var(--nbms-color-primary-700);
      }

      .empty h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h3);
      }

      .empty p {
        margin: 0;
        max-width: 38rem;
        color: var(--nbms-text-secondary);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsEmptyStateComponent {
  @Input() icon = 'info';
  @Input() title = 'No records found';
  @Input() description = 'Adjust filters or try a broader search.';
  @Input() ctaLabel = '';
}
