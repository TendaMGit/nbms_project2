import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { NbmsStatusPillComponent } from './nbms-status-pill.component';

@Component({
  selector: 'nbms-page-header',
  standalone: true,
  imports: [NgFor, NgIf, MatButtonModule, NbmsStatusPillComponent],
  template: `
    <header class="page-header">
      <div class="header-main">
        <div class="breadcrumbs" *ngIf="breadcrumbs.length">
          <span *ngFor="let crumb of breadcrumbs; let last = last; trackBy: trackByValue">
            {{ crumb }}<span *ngIf="!last"> / </span>
          </span>
        </div>
        <h1>{{ title }}</h1>
        <p *ngIf="subtitle">{{ subtitle }}</p>
      </div>
      <div class="header-actions">
        <nbms-status-pill
          *ngIf="statusLabel"
          [label]="statusLabel"
          [tone]="statusTone"
        ></nbms-status-pill>
        <button mat-flat-button color="primary" *ngIf="primaryActionLabel">{{ primaryActionLabel }}</button>
      </div>
    </header>
  `,
  styles: [
    `
      .page-header {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-4);
        align-items: flex-start;
        margin-bottom: var(--nbms-space-4);
      }

      .header-main h1 {
        font-size: var(--nbms-font-size-h2);
        margin-bottom: var(--nbms-space-1);
      }

      .header-main p {
        margin: 0;
        color: var(--nbms-text-secondary);
      }

      .breadcrumbs {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        margin-bottom: var(--nbms-space-1);
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: var(--nbms-space-2);
      }

      @media (max-width: 900px) {
        .page-header {
          flex-direction: column;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsPageHeaderComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() breadcrumbs: string[] = [];
  @Input() statusLabel = '';
  @Input() statusTone: 'neutral' | 'success' | 'warn' | 'error' | 'info' = 'neutral';
  @Input() primaryActionLabel = '';

  trackByValue(_: number, value: string): string {
    return value;
  }
}
