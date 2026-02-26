import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgFor } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'nbms-evidence-panel',
  standalone: true,
  imports: [NgFor, MatIconModule],
  template: `
    <section class="evidence nbms-card-surface">
      <header>
        <h3>{{ title }}</h3>
      </header>
      <div class="row" *ngFor="let entry of entries; trackBy: trackByEntry">
        <mat-icon>attach_file</mat-icon>
        <span>{{ entry }}</span>
      </div>
      <ng-content></ng-content>
    </section>
  `,
  styles: [
    `
      .evidence {
        padding: var(--nbms-space-4);
        display: grid;
        gap: var(--nbms-space-2);
      }

      header h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
      }

      .row {
        display: grid;
        grid-template-columns: 1.2rem 1fr;
        gap: var(--nbms-space-2);
        align-items: center;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsEvidencePanelComponent {
  @Input() title = 'Evidence';
  @Input() entries: string[] = [];

  trackByEntry(_: number, value: string): string {
    return value;
  }
}
