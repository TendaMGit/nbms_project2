import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgIf } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-indicator-explorer-toolbar',
  standalone: true,
  imports: [
    NgIf,
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule
  ],
  template: `
    <section class="toolbar nbms-card-surface">
      <div class="control-group">
        <span class="label">View</span>
        <mat-button-toggle-group
          [formControl]="modeControl"
          aria-label="Indicator explorer display mode"
        >
          <mat-button-toggle value="table">Table</mat-button-toggle>
          <mat-button-toggle value="cards">Cards</mat-button-toggle>
          <mat-button-toggle value="map">Map-first</mat-button-toggle>
        </mat-button-toggle-group>
      </div>

      <mat-form-field appearance="outline" class="sort-field" subscriptSizing="dynamic">
        <mat-label>Sort</mat-label>
        <mat-select [formControl]="sortControl" aria-label="Indicator explorer sort order">
          <mat-option value="last_updated_desc">Recently updated</mat-option>
          <mat-option value="readiness_desc">Readiness</mat-option>
          <mat-option value="due_soon">Due soon</mat-option>
          <mat-option value="title">Title</mat-option>
        </mat-select>
      </mat-form-field>

      <div class="actions">
        <span class="selection" *ngIf="compareCount > 0">{{ compareCount }} in compare</span>
        <button mat-stroked-button type="button" (click)="exportRequested.emit()">
          <mat-icon>download</mat-icon>
          Export CSV
        </button>
        <button mat-button type="button" (click)="insightsToggle.emit()">
          {{ insightsOpen ? 'Hide insights' : 'Show insights' }}
        </button>
      </div>
    </section>
  `,
  styles: [
    `
      .toolbar {
        display: grid;
        grid-template-columns: auto minmax(180px, 220px) minmax(0, 1fr);
        gap: var(--nbms-space-3);
        align-items: center;
        padding: var(--nbms-space-3) var(--nbms-space-4);
      }

      .control-group {
        display: grid;
        gap: var(--nbms-space-1);
      }

      .label,
      .selection {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }

      .sort-field {
        width: 100%;
      }

      .actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }

      .actions button {
        white-space: nowrap;
      }

      @media (max-width: 960px) {
        .toolbar {
          grid-template-columns: 1fr;
        }

        .actions {
          justify-content: flex-start;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IndicatorExplorerToolbarComponent {
  @Input({ required: true }) modeControl!: FormControl;
  @Input({ required: true }) sortControl!: FormControl;
  @Input() insightsOpen = false;
  @Input() compareCount = 0;

  @Output() exportRequested = new EventEmitter<void>();
  @Output() insightsToggle = new EventEmitter<void>();
}
