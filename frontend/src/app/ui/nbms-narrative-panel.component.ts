import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

type NarrativeSection = {
  id: string;
  title: string;
  body: string;
  helperText?: string;
};

@Component({
  selector: 'nbms-narrative-panel',
  standalone: true,
  imports: [NgFor, NgIf, MatButtonModule, MatIconModule],
  template: `
    <section class="narrative nbms-card-surface">
      <header class="head">
        <div>
          <p class="eyebrow">{{ eyebrow }}</p>
          <h2>{{ title }}</h2>
        </div>
        <div class="actions">
          <button mat-button type="button" (click)="copyRequested.emit()">
            <mat-icon>content_copy</mat-icon>
            Copy narrative
          </button>
          <button mat-stroked-button type="button" *ngIf="showInsertAction" (click)="insertRequested.emit()">
            <mat-icon>post_add</mat-icon>
            Insert to report
          </button>
        </div>
      </header>

      <article class="section" *ngFor="let section of sections; trackBy: trackBySection">
        <strong>{{ section.title }}</strong>
        <p>{{ section.body }}</p>
        <small *ngIf="section.helperText">{{ section.helperText }}</small>
      </article>
    </section>
  `,
  styles: [
    `
      .narrative,
      .section {
        display: grid;
        gap: var(--nbms-space-2);
      }

      .narrative {
        padding: var(--nbms-space-4);
      }

      .head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-3);
        align-items: flex-start;
      }

      .eyebrow {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      h2,
      strong,
      p,
      small {
        margin: 0;
      }

      p,
      small {
        color: var(--nbms-text-secondary);
        line-height: 1.6;
      }

      .actions {
        display: flex;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsNarrativePanelComponent {
  @Input() eyebrow = 'Narrative';
  @Input() title = 'Narrative';
  @Input() sections: NarrativeSection[] = [];
  @Input() showInsertAction = true;

  @Output() copyRequested = new EventEmitter<void>();
  @Output() insertRequested = new EventEmitter<void>();

  trackBySection(_: number, section: NarrativeSection): string {
    return section.id;
  }
}
