import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { type NbmsContextOption, type NbmsContextQueryParams } from '../models/context.models';

@Component({
  selector: 'nbms-context-bar',
  standalone: true,
  imports: [NgFor, NgIf, MatFormFieldModule, MatInputModule, MatSelectModule, MatSlideToggleModule],
  template: `
    <section class="context-bar nbms-card-surface">
      <header class="context-head">
        <div>
          <p class="eyebrow">Context</p>
          <h2>Filter the current slice</h2>
        </div>
        <div class="context-head-actions">
          <button type="button" class="filter-toggle" (click)="mobileFiltersOpen = !mobileFiltersOpen" [attr.aria-expanded]="mobileFiltersOpen">
            Filters
          </button>
          <mat-slide-toggle [checked]="state.published_only === 1" (change)="emitPatch('published_only', $event.checked ? 1 : 0)">
            Published only
          </mat-slide-toggle>
        </div>
      </header>

      <div class="context-grid-wrap" [class.context-grid-wrap--open]="mobileFiltersOpen">
        <div class="context-grid">
          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>Report cycle</mat-label>
            <mat-select [value]="state.report_cycle" (valueChange)="emitPatch('report_cycle', $event)">
              <mat-option *ngFor="let option of reportCycleOptions; trackBy: trackByOption" [value]="option.value" [disabled]="option.disabled">
                {{ option.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>Release</mat-label>
            <mat-select [value]="state.release" (valueChange)="emitPatch('release', $event)">
              <mat-option *ngFor="let option of releaseOptions; trackBy: trackByOption" [value]="option.value" [disabled]="option.disabled">
                {{ option.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>Method</mat-label>
            <mat-select [value]="state.method" (valueChange)="emitPatch('method', $event)">
              <mat-option *ngFor="let option of methodOptions; trackBy: trackByOption" [value]="option.value" [disabled]="option.disabled">
                {{ option.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>Geography</mat-label>
            <mat-select [value]="state.geo_type" (valueChange)="emitPatch('geo_type', $event)">
              <mat-option *ngFor="let option of geoTypeOptions; trackBy: trackByOption" [value]="option.value" [disabled]="option.disabled">
                {{ option.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field *ngIf="showGeoCode" appearance="outline" subscriptSizing="dynamic">
            <mat-label>Geography code</mat-label>
            <mat-select *ngIf="geoCodeOptions.length; else geoCodeInput" [value]="state.geo_code" (valueChange)="emitPatch('geo_code', $event)">
              <mat-option value="">All</mat-option>
              <mat-option *ngFor="let option of geoCodeOptions; trackBy: trackByOption" [value]="option.value" [disabled]="option.disabled">
                {{ option.label }}
              </mat-option>
            </mat-select>
            <ng-template #geoCodeInput>
              <input matInput [value]="state.geo_code" (input)="emitPatch('geo_code', $any($event.target).value)" />
            </ng-template>
          </mat-form-field>

          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>Start year</mat-label>
            <mat-select [value]="state.start_year" (valueChange)="emitPatch('start_year', $event)">
              <mat-option [value]="null">Auto</mat-option>
              <mat-option *ngFor="let year of yearOptions; trackBy: trackByYear" [value]="year">{{ year }}</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>End year</mat-label>
            <mat-select [value]="state.end_year" (valueChange)="emitPatch('end_year', $event)">
              <mat-option [value]="null">Auto</mat-option>
              <mat-option *ngFor="let year of yearOptions; trackBy: trackByYear" [value]="year">{{ year }}</mat-option>
            </mat-select>
          </mat-form-field>
        </div>
      </div>

      <div class="context-actions">
        <p class="helper-text" *ngIf="helperText">{{ helperText }}</p>
      </div>
    </section>
  `,
  styles: [
    `
      .context-bar {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4) var(--nbms-space-5);
      }

      .context-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--nbms-space-3);
      }

      .context-head-actions {
        display: flex;
        align-items: center;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }

      .eyebrow,
      h2 {
        margin: 0;
      }

      .eyebrow {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .context-grid {
        display: grid;
        grid-template-columns: repeat(7, minmax(0, 1fr));
        gap: var(--nbms-space-3);
      }

      .filter-toggle {
        display: none;
        min-height: 2.5rem;
        border: 1px solid var(--nbms-border-strong);
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-surface);
        color: var(--nbms-text-primary);
        cursor: pointer;
        font: inherit;
        font-weight: 700;
        padding: 0 var(--nbms-space-3);
      }

      .context-actions {
        display: flex;
        justify-content: flex-end;
      }

      .helper-text {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      @media (max-width: 1380px) {
        .context-grid {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }
      }

      @media (max-width: 860px) {
        .context-head {
          flex-direction: column;
          align-items: flex-start;
        }

        .filter-toggle {
          display: inline-flex;
          align-items: center;
        }

        .context-grid-wrap {
          display: none;
          width: 100%;
        }

        .context-grid-wrap--open {
          display: block;
        }

        .context-grid {
          grid-template-columns: 1fr;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsContextBarComponent {
  @Input() state!: NbmsContextQueryParams;
  @Input() reportCycleOptions: NbmsContextOption[] = [];
  @Input() releaseOptions: NbmsContextOption[] = [];
  @Input() methodOptions: NbmsContextOption[] = [];
  @Input() geoTypeOptions: NbmsContextOption[] = [];
  @Input() geoCodeOptions: NbmsContextOption[] = [];
  @Input() yearOptions: number[] = [];
  @Input() helperText = '';

  @Output() stateChange = new EventEmitter<Partial<NbmsContextQueryParams>>();

  mobileFiltersOpen = false;

  get showGeoCode(): boolean {
    return this.state.geo_type !== 'national';
  }

  emitPatch<K extends keyof NbmsContextQueryParams>(key: K, value: NbmsContextQueryParams[K]): void {
    this.stateChange.emit({ [key]: value } as Partial<NbmsContextQueryParams>);
  }

  trackByOption(_: number, option: NbmsContextOption): string {
    return option.value;
  }

  trackByYear(_: number, year: number): number {
    return year;
  }
}
