import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';

type LegendItem = {
  label: string;
  color: string;
  value?: string | number | null;
};

@Component({
  selector: 'nbms-legend',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <div class="legend">
      <article class="legend-item" *ngFor="let item of items; trackBy: trackByItem">
        <span class="swatch" [style.background]="item.color"></span>
        <span class="label">{{ item.label }}</span>
        <strong *ngIf="item.value !== undefined && item.value !== null">{{ item.value }}</strong>
      </article>
    </div>
  `,
  styles: [
    `
      .legend {
        display: flex;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }

      .legend-item {
        display: inline-flex;
        align-items: center;
        gap: var(--nbms-space-1);
        min-height: 1.8rem;
        border-radius: var(--nbms-radius-pill);
        border: 1px solid var(--nbms-border);
        background: color-mix(in srgb, var(--nbms-surface-2) 72%, var(--nbms-surface));
        color: var(--nbms-text-secondary);
        font-size: var(--nbms-font-size-label-sm);
        padding: 0 var(--nbms-space-2);
      }

      .swatch {
        width: 0.75rem;
        height: 0.75rem;
        border-radius: 50%;
        border: 1px solid color-mix(in srgb, var(--nbms-border-strong) 72%, transparent);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsLegendComponent {
  @Input() items: LegendItem[] = [];

  trackByItem(_: number, item: LegendItem): string {
    return item.label;
  }
}
