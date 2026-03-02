import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

type BlockerRow = {
  code: string;
  label: string;
  count: number;
};

@Component({
  selector: 'app-indicator-explorer-insights',
  standalone: true,
  imports: [NgFor, NgIf, RouterLink, MatButtonModule],
  template: `
    <aside class="insights nbms-card-surface">
      <header class="head">
        <div>
          <p class="eyebrow">Insights</p>
          <h2>Registry narrative</h2>
        </div>
        <span class="due-soon">{{ dueSoonCount }} due soon</span>
      </header>

      <p class="narrative">{{ narrative }}</p>

      <div class="actions">
        <button mat-stroked-button type="button" (click)="copyNarrative.emit()">Copy narrative</button>
        <a
          mat-button
          [routerLink]="['/reporting']"
          [queryParams]="reportingQueryParams"
        >
          Insert into report
        </a>
      </div>

      <section class="summary-grid">
        <article class="summary-card nbms-card-surface">
          <span>Current blockers</span>
          <strong>{{ blockers.length }}</strong>
        </article>
        <article class="summary-card nbms-card-surface">
          <span>Compare set</span>
          <strong>{{ compareCount }}</strong>
        </article>
      </section>

      <section class="blockers">
        <div class="blockers-head">
          <h3>Blockers</h3>
          <span>{{ blockers.length }}</span>
        </div>
        <div class="blocker-list" *ngIf="blockers.length; else noBlockers">
          <article class="blocker-row" *ngFor="let blocker of blockers; trackBy: trackByBlocker">
            <span>{{ blocker.label }}</span>
            <strong>{{ blocker.count }}</strong>
          </article>
        </div>
      </section>
    </aside>

    <ng-template #noBlockers>
      <p class="empty">No blocker counts match the current filter set.</p>
    </ng-template>
  `,
  styles: [
    `
      .insights {
        display: grid;
        gap: var(--nbms-space-4);
        padding: var(--nbms-space-4) var(--nbms-space-5);
      }

      .head,
      .blockers-head,
      .blocker-row {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-2);
        align-items: flex-start;
      }

      .eyebrow,
      .summary-card span {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }

      .head h2,
      .blockers-head h3 {
        margin: var(--nbms-space-1) 0 0;
      }

      .due-soon {
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-warn-subtle);
        color: var(--nbms-warn);
        padding: var(--nbms-space-1) var(--nbms-space-2);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
      }

      .narrative,
      .empty {
        margin: 0;
        color: var(--nbms-text-secondary);
        line-height: 1.6;
      }

      .actions {
        display: flex;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }

      .summary-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: var(--nbms-space-2);
      }

      .summary-card {
        display: grid;
        gap: var(--nbms-space-1);
        padding: var(--nbms-space-3);
      }

      .summary-card strong {
        color: var(--nbms-text-primary);
        font-size: var(--nbms-font-size-h3);
      }

      .blockers {
        display: grid;
        gap: var(--nbms-space-2);
      }

      .blocker-list {
        display: grid;
        gap: var(--nbms-space-2);
      }

      .blocker-row {
        border-bottom: 1px solid var(--nbms-divider);
        padding-bottom: var(--nbms-space-2);
      }

      .blocker-row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
      }

      .blocker-row span {
        color: var(--nbms-text-secondary);
      }

      .blocker-row strong {
        color: var(--nbms-text-primary);
      }

      @media (max-width: 640px) {
        .summary-grid {
          grid-template-columns: 1fr;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IndicatorExplorerInsightsComponent {
  @Input() narrative = '';
  @Input() dueSoonCount = 0;
  @Input() compareCount = 0;
  @Input() blockers: BlockerRow[] = [];
  @Input() reportingQueryParams: Record<string, unknown> = {};

  @Output() copyNarrative = new EventEmitter<void>();

  trackByBlocker(_: number, row: BlockerRow): string {
    return row.code;
  }
}
