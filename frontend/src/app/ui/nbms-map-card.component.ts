import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';

import { IndicatorMapPanelComponent } from '../components/indicator-map-panel.component';
import { IndicatorMapResponse } from '../models/api.models';
import { NbmsLegendComponent } from './nbms-legend.component';

@Component({
  selector: 'nbms-map-card',
  standalone: true,
  imports: [NgIf, IndicatorMapPanelComponent, NbmsLegendComponent],
  template: `
    <section class="map-card nbms-card-surface">
      <header class="head">
        <div>
          <p class="eyebrow" *ngIf="eyebrow">{{ eyebrow }}</p>
          <h2>{{ title }}</h2>
          <p class="subtitle" *ngIf="subtitle">{{ subtitle }}</p>
        </div>
      </header>

      <app-indicator-map-panel [featureCollection]="featureCollection"></app-indicator-map-panel>

      <nbms-legend *ngIf="legendItems.length" [items]="legendItems"></nbms-legend>
      <p class="helper" *ngIf="helperText">{{ helperText }}</p>
    </section>
  `,
  styles: [
    `
      .map-card {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4);
      }

      .eyebrow,
      .subtitle,
      .helper {
        margin: 0;
        color: var(--nbms-text-muted);
      }

      .eyebrow {
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      h2 {
        margin: var(--nbms-space-1) 0 0;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsMapCardComponent {
  @Input() title = 'Map';
  @Input() eyebrow = '';
  @Input() subtitle = '';
  @Input() helperText = '';
  @Input() featureCollection: IndicatorMapResponse | null = null;
  @Input() legendItems: Array<{ label: string; color: string; value?: string | number | null }> = [];
}
