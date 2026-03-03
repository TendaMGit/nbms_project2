import { NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

import type { IndicatorDetailResponse } from '../models/api.models';
import type { IndicatorViewSummary } from '../models/indicator-visual.models';

@Component({
  selector: 'nbms-view-binary',
  standalone: true,
  imports: [NgIf],
  template: `
    <section class="empty-state" *ngIf="indicatorDetail">
      Binary view scaffolding is wired. Evidence-focused rendering lands in a later commit.
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
export class NbmsViewBinaryComponent {
  @Input() indicatorDetail: IndicatorDetailResponse | null = null;
  @Output() readonly summaryChange = new EventEmitter<IndicatorViewSummary>();

  ngOnChanges(): void {
    this.summaryChange.emit({ kpis: [], callouts: [] });
  }
}
