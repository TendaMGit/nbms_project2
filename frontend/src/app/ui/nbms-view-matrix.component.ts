import { NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

import type { IndicatorDetailResponse, IndicatorDimension } from '../models/api.models';
import type { IndicatorViewRoutePatch, IndicatorViewRouteState, IndicatorViewSummary } from '../models/indicator-visual.models';
import { buildGovernanceCallouts } from './indicator-view.helpers';

@Component({
  selector: 'nbms-view-matrix',
  standalone: true,
  imports: [NgIf],
  template: `
    <section class="empty-state" *ngIf="indicatorDetail">
      Matrix view scaffolding is wired. Cross-dimension heatmap rendering lands in a later commit.
    </section>
  `,
  styles: [
    `
      .empty-state {
        border: 1px dashed var(--nbms-border);
        border-radius: var(--nbms-radius-lg);
        color: var(--nbms-text-muted);
        padding: var(--nbms-space-4);
        text-align: center;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NbmsViewMatrixComponent {
  @Input() indicatorUuid = '';
  @Input() indicatorDetail: IndicatorDetailResponse | null = null;
  @Input() dimensions: IndicatorDimension[] = [];
  @Input() state: IndicatorViewRouteState | null = null;

  @Output() readonly stateChange = new EventEmitter<IndicatorViewRoutePatch>();
  @Output() readonly summaryChange = new EventEmitter<IndicatorViewSummary>();

  ngOnChanges(): void {
    if (!this.indicatorDetail || !this.state) {
      return;
    }
    this.summaryChange.emit({
      kpis: [],
      callouts: buildGovernanceCallouts(this.indicatorDetail, this.state),
    });
  }
}
