import { NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

import type { IndicatorDetailResponse } from '../models/api.models';
import type { IndicatorViewSummary } from '../models/indicator-visual.models';
import { buildGovernanceCallouts } from './indicator-view.helpers';

@Component({
  selector: 'nbms-view-binary',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <section class="view-shell" *ngIf="indicatorDetail as detail">
      <article class="hero nbms-card-surface">
        <p class="eyebrow">Binary status</p>
        <h3>{{ statusLabel(detail) }}</h3>
        <p>{{ detail.narrative?.summary || detail.indicator.description || 'No binary interpretation is published.' }}</p>
      </article>

      <article class="panel nbms-card-surface">
        <p class="eyebrow">Evidence checklist</p>
        <div class="evidence-list" *ngIf="detail.evidence.length; else noEvidence">
          <article class="evidence-row" *ngFor="let item of detail.evidence">
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.evidence_type || 'Evidence item' }}</p>
            </div>
            <a *ngIf="item.source_url" [href]="item.source_url" target="_blank" rel="noreferrer">Open source</a>
          </article>
        </div>
      </article>

      <ng-template #noEvidence>
        <div class="empty-state">No evidence records are linked to this binary indicator.</div>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .view-shell,
      .hero,
      .panel,
      .evidence-list {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .hero,
      .panel {
        padding: var(--nbms-space-4);
      }

      .eyebrow {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      h3,
      p {
        margin: 0;
      }

      .evidence-row {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
        border: 1px solid var(--nbms-divider);
        border-radius: var(--nbms-radius-md);
        padding: var(--nbms-space-3);
      }

      .empty-state {
        border: 1px dashed var(--nbms-border);
        border-radius: var(--nbms-radius-lg);
        color: var(--nbms-text-muted);
        padding: var(--nbms-space-4);
        text-align: center;
      }

      @media (max-width: 900px) {
        .evidence-row {
          flex-direction: column;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NbmsViewBinaryComponent {
  @Input() indicatorDetail: IndicatorDetailResponse | null = null;
  @Output() readonly summaryChange = new EventEmitter<IndicatorViewSummary>();

  ngOnChanges(): void {
    if (!this.indicatorDetail) {
      return;
    }
    this.summaryChange.emit({
      kpis: [
        {
          title: 'Binary status',
          value: this.statusLabel(this.indicatorDetail),
          hint: 'Binary indicators lean on evidence and narrative rather than multidimensional analytics.',
          icon: 'rule',
          accent: true,
        },
        {
          title: 'Evidence links',
          value: String(this.indicatorDetail.evidence.length),
          hint: 'Evidence records currently linked to this indicator.',
          icon: 'link',
        },
      ],
      callouts: buildGovernanceCallouts(this.indicatorDetail, {
        tab: 'indicator',
        mode: 'table',
        report_cycle: '',
        release: 'latest_approved',
        method: 'current',
        geo_type: 'national',
        geo_code: '',
        start_year: null,
        end_year: null,
        agg: 'national',
        metric: 'value',
        published_only: 1,
        q: '',
        sort: '',
        view: 'binary',
        compare: '',
        left: '',
        right: '',
        dim: '',
        dim_value: '',
        tax_level: '',
        tax_code: '',
        top_n: 20,
      }),
    });
  }

  statusLabel(detail: IndicatorDetailResponse): string {
    return detail.pipeline?.release_workflow.status || detail.indicator.status || 'No published status';
  }
}
