import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

import { NbmsStatusPillComponent } from './nbms-status-pill.component';

type EvidenceRow = {
  title: string;
  subtitle: string;
  type: string;
  date?: string | null;
  accessLabel?: string;
  accessTone?: 'neutral' | 'success' | 'warn' | 'error' | 'info';
  url?: string;
};

@Component({
  selector: 'nbms-evidence-list',
  standalone: true,
  imports: [NgFor, NgIf, MatButtonModule, NbmsStatusPillComponent],
  template: `
    <section class="evidence-list">
      <article class="row" *ngFor="let row of rows; trackBy: trackByRow">
        <div>
          <strong>{{ row.title }}</strong>
          <p>{{ row.subtitle }}</p>
        </div>
        <div class="meta">
          <nbms-status-pill [label]="row.type" tone="info"></nbms-status-pill>
          <nbms-status-pill *ngIf="row.accessLabel" [label]="row.accessLabel" [tone]="row.accessTone || 'neutral'"></nbms-status-pill>
          <span *ngIf="row.date">{{ row.date }}</span>
          <a mat-stroked-button *ngIf="row.url" [href]="row.url" target="_blank" rel="noreferrer">Open</a>
        </div>
      </article>
    </section>
  `,
  styles: [
    `
      .evidence-list {
        display: grid;
        gap: var(--nbms-space-3);
      }

      .row {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
        border: 1px solid var(--nbms-divider);
        border-radius: var(--nbms-radius-md);
        background: color-mix(in srgb, var(--nbms-surface-2) 52%, var(--nbms-surface));
        padding: var(--nbms-space-3) var(--nbms-space-4);
      }

      strong,
      p {
        margin: 0;
      }

      p,
      .meta span {
        color: var(--nbms-text-secondary);
      }

      .meta {
        display: flex;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
        align-items: center;
        justify-content: flex-end;
      }

      @media (max-width: 860px) {
        .row {
          flex-direction: column;
        }

        .meta {
          justify-content: flex-start;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsEvidenceListComponent {
  @Input() rows: EvidenceRow[] = [];

  trackByRow(_: number, row: EvidenceRow): string {
    return `${row.title}-${row.type}`;
  }
}
