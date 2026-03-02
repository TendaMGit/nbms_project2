import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';

type DistributionCard = {
  id: string;
  label: string;
  value: string;
  helperText?: string;
  progress?: number;
  active?: boolean;
};

@Component({
  selector: 'nbms-distribution-card-grid',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <div class="grid">
      <button
        *ngFor="let card of cards; trackBy: trackByCard"
        type="button"
        class="card"
        [class.card--active]="card.active"
        (click)="select.emit(card.id)"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <div class="bar" *ngIf="card.progress !== undefined"><b [style.width.%]="card.progress"></b></div>
        <small *ngIf="card.helperText">{{ card.helperText }}</small>
      </button>
    </div>
  `,
  styles: [
    `
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: var(--nbms-space-3);
      }

      .card {
        display: grid;
        gap: var(--nbms-space-2);
        border: 1px solid var(--nbms-border);
        border-radius: var(--nbms-radius-md);
        background: var(--nbms-surface);
        color: var(--nbms-text-primary);
        cursor: pointer;
        font: inherit;
        padding: var(--nbms-space-3);
        text-align: left;
      }

      .card--active {
        border-color: color-mix(in srgb, var(--nbms-color-primary-500) 30%, var(--nbms-surface));
        background: color-mix(in srgb, var(--nbms-color-primary-100) 18%, var(--nbms-surface));
      }

      .card span,
      .card small {
        color: var(--nbms-text-muted);
      }

      .bar {
        height: 8px;
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-surface-muted);
        overflow: hidden;
      }

      .bar b {
        display: block;
        height: 100%;
        background: var(--nbms-color-primary-500);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsDistributionCardGridComponent {
  @Input() cards: DistributionCard[] = [];
  @Output() select = new EventEmitter<string>();

  trackByCard(_: number, card: DistributionCard): string {
    return card.id;
  }
}
