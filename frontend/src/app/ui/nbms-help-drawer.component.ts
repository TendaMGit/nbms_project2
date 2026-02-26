import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { KeyValuePipe, NgFor, NgIf } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'nbms-help-drawer',
  standalone: true,
  imports: [NgIf, NgFor, KeyValuePipe, MatIconModule],
  template: `
    <section class="help-drawer">
      <h3>Context help</h3>
      <p *ngIf="!entries || !objectKeys(entries).length">No help notes available for this page.</p>
      <div class="help-row" *ngFor="let item of entries | keyvalue">
        <mat-icon>help_outline</mat-icon>
        <p><strong>{{ item.key }}:</strong> {{ item.value }}</p>
      </div>
    </section>
  `,
  styles: [
    `
      .help-drawer {
        display: grid;
        gap: var(--nbms-space-3);
      }

      .help-drawer h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
      }

      .help-drawer p {
        margin: 0;
        color: var(--nbms-text-secondary);
      }

      .help-row {
        display: grid;
        grid-template-columns: 1.4rem 1fr;
        gap: var(--nbms-space-2);
        align-items: flex-start;
      }

      .help-row mat-icon {
        margin-top: 0.1rem;
        color: var(--nbms-color-secondary-700);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsHelpDrawerComponent {
  @Input() entries: Record<string, string> | null = null;

  objectKeys(value: Record<string, string> | null): string[] {
    return value ? Object.keys(value) : [];
  }
}
