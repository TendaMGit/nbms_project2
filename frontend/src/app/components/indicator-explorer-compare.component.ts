import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgFor } from '@angular/common';
import { RouterLink } from '@angular/router';

import type { IndicatorListItem } from '../models/api.models';
import { NbmsReadinessBadgeComponent } from '../ui/nbms-readiness-badge.component';
import { NbmsStatusPillComponent } from '../ui/nbms-status-pill.component';

@Component({
  selector: 'app-indicator-explorer-compare',
  standalone: true,
  imports: [NgFor, RouterLink, NbmsReadinessBadgeComponent, NbmsStatusPillComponent],
  template: `
    <section class="compare nbms-card-surface">
      <header class="head">
        <div>
          <p class="eyebrow">Compare</p>
          <h2>Selected indicators</h2>
        </div>
        <span>{{ rows.length }} indicators</span>
      </header>

      <article class="row" *ngFor="let row of rows; trackBy: trackByIndicator">
        <div class="identity">
          <a [routerLink]="['/indicators', row.uuid]">{{ row.code }}</a>
          <span>{{ row.title }}</span>
        </div>
        <div class="meta">
          <nbms-readiness-badge
            [score]="row.readiness_score"
            [status]="readinessState(row.readiness_status)"
          ></nbms-readiness-badge>
          <nbms-status-pill [label]="row.status" [tone]="statusTone(row.status)"></nbms-status-pill>
        </div>
        <div class="dates">
          <span>Updated {{ row.last_updated_on || 'n/a' }}</span>
          <span>Next {{ row.next_expected_update_on || 'n/a' }}</span>
        </div>
      </article>
    </section>
  `,
  styles: [
    `
      .compare {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4) var(--nbms-space-5);
      }

      .head,
      .row {
        display: grid;
        grid-template-columns: minmax(0, 1.4fr) auto minmax(180px, auto);
        gap: var(--nbms-space-3);
        align-items: center;
      }

      .eyebrow {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }

      .head h2 {
        margin: var(--nbms-space-1) 0 0;
      }

      .head span {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        justify-self: end;
      }

      .row {
        border-top: 1px solid var(--nbms-divider);
        padding-top: var(--nbms-space-3);
      }

      .identity,
      .dates {
        display: grid;
        gap: var(--nbms-space-1);
      }

      .identity span,
      .dates span {
        color: var(--nbms-text-secondary);
      }

      .meta {
        display: flex;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }

      @media (max-width: 920px) {
        .head,
        .row {
          grid-template-columns: 1fr;
        }

        .head span {
          justify-self: start;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IndicatorExplorerCompareComponent {
  @Input() rows: IndicatorListItem[] = [];

  trackByIndicator(_: number, row: IndicatorListItem): string {
    return row.uuid;
  }

  readinessState(status: string): 'ready' | 'warning' | 'blocked' {
    const normalized = status.toLowerCase();
    if (normalized === 'ready') {
      return 'ready';
    }
    if (normalized === 'warning') {
      return 'warning';
    }
    return 'blocked';
  }

  statusTone(status: string): 'neutral' | 'success' | 'warn' | 'error' | 'info' {
    const normalized = status.toLowerCase();
    if (normalized === 'published' || normalized === 'approved') {
      return 'success';
    }
    if (normalized.includes('review') || normalized.includes('pending')) {
      return 'warn';
    }
    if (normalized.includes('reject') || normalized.includes('blocked')) {
      return 'error';
    }
    return 'neutral';
  }
}
