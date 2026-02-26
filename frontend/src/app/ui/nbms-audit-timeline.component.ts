import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { DatePipe, NgFor, NgIf } from '@angular/common';

type AuditEntry = {
  action: string;
  actor: string | null;
  created_at: string;
  note?: string;
};

@Component({
  selector: 'nbms-audit-timeline',
  standalone: true,
  imports: [NgFor, NgIf, DatePipe],
  template: `
    <section class="timeline nbms-card-surface">
      <h3>{{ title }}</h3>
      <div class="event" *ngFor="let entry of events; trackBy: trackByEntry">
        <div class="dot"></div>
        <div>
          <p class="action">{{ entry.action }}</p>
          <p class="meta">{{ entry.actor || 'system' }} • {{ entry.created_at | date: 'medium' }}</p>
          <p class="note" *ngIf="entry.note">{{ entry.note }}</p>
        </div>
      </div>
    </section>
  `,
  styles: [
    `
      .timeline {
        padding: var(--nbms-space-4);
        display: grid;
        gap: var(--nbms-space-3);
      }

      .timeline h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
      }

      .event {
        display: grid;
        grid-template-columns: 0.8rem 1fr;
        gap: var(--nbms-space-2);
      }

      .dot {
        width: 0.65rem;
        height: 0.65rem;
        border-radius: 50%;
        margin-top: 0.35rem;
        background: var(--nbms-color-secondary-500);
      }

      .action {
        margin: 0;
        font-weight: 700;
      }

      .meta,
      .note {
        margin: 0;
        color: var(--nbms-text-secondary);
        font-size: var(--nbms-font-size-label-sm);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsAuditTimelineComponent {
  @Input() title = 'Audit timeline';
  @Input() events: AuditEntry[] = [];

  trackByEntry(index: number, entry: AuditEntry): string {
    return `${entry.action}-${entry.created_at}-${index}`;
  }
}
