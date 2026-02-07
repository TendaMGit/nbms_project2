import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { map, startWith, switchMap } from 'rxjs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChip, MatChipSet } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';

import { IndicatorService } from '../services/indicator.service';
import { HelpTooltipComponent } from '../components/help-tooltip.component';

@Component({
  selector: 'app-indicator-explorer-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    RouterLink,
    ReactiveFormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCardModule,
    MatChipSet,
    MatChip,
    MatIconModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="explorer-layout">
      <aside class="filters">
        <h2>Filters <app-help-tooltip text="Filter by framework, status, geography and timeline." /></h2>
        <mat-accordion multi>
          <mat-expansion-panel [expanded]="true">
            <mat-expansion-panel-header>
              <mat-panel-title>Search</mat-panel-title>
            </mat-expansion-panel-header>
            <mat-form-field appearance="outline">
              <mat-label>Keyword</mat-label>
              <input matInput [formControl]="filters.controls.search" />
            </mat-form-field>
          </mat-expansion-panel>
          <mat-expansion-panel [expanded]="true">
            <mat-expansion-panel-header>
              <mat-panel-title>Classification</mat-panel-title>
            </mat-expansion-panel-header>
            <mat-form-field appearance="outline">
              <mat-label>Framework</mat-label>
              <input matInput [formControl]="filters.controls.framework" placeholder="GBF / SDG / ..." />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Status</mat-label>
              <mat-select [formControl]="filters.controls.status">
                <mat-option value="">Any</mat-option>
                <mat-option value="draft">Draft</mat-option>
                <mat-option value="pending_review">Pending review</mat-option>
                <mat-option value="approved">Approved</mat-option>
                <mat-option value="published">Published</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Sensitivity</mat-label>
              <mat-select [formControl]="filters.controls.sensitivity">
                <mat-option value="">Any</mat-option>
                <mat-option value="public">Public</mat-option>
                <mat-option value="internal">Internal</mat-option>
                <mat-option value="restricted">Restricted</mat-option>
                <mat-option value="iplc_sensitive">IPLC sensitive</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Readiness</mat-label>
              <mat-select [formControl]="filters.controls.method_readiness">
                <mat-option value="">Any</mat-option>
                <mat-option value="ready">Ready</mat-option>
                <mat-option value="partial">Partial</mat-option>
                <mat-option value="blocked">Blocked</mat-option>
              </mat-select>
            </mat-form-field>
          </mat-expansion-panel>
          <mat-expansion-panel>
            <mat-expansion-panel-header>
              <mat-panel-title>Coverage</mat-panel-title>
            </mat-expansion-panel-header>
            <mat-form-field appearance="outline">
              <mat-label>Geography</mat-label>
              <input matInput [formControl]="filters.controls.geography" />
            </mat-form-field>
            <div class="inline-fields">
              <mat-form-field appearance="outline">
                <mat-label>Year from</mat-label>
                <input matInput type="number" [formControl]="filters.controls.year_from" />
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Year to</mat-label>
                <input matInput type="number" [formControl]="filters.controls.year_to" />
              </mat-form-field>
            </div>
          </mat-expansion-panel>
          <mat-expansion-panel>
            <mat-expansion-panel-header>
              <mat-panel-title>Sort</mat-panel-title>
            </mat-expansion-panel-header>
            <mat-form-field appearance="outline">
              <mat-label>Sort order</mat-label>
              <mat-select [formControl]="filters.controls.sort">
                <mat-option value="title">Title</mat-option>
                <mat-option value="recently_updated">Recently updated</mat-option>
                <mat-option value="relevance">Relevance</mat-option>
              </mat-select>
            </mat-form-field>
          </mat-expansion-panel>
        </mat-accordion>
      </aside>

      <section class="results" *ngIf="results$ | async as results">
        <header class="results-header">
          <h2>Indicators ({{ results.count }})</h2>
        </header>
        <mat-card class="indicator-card" *ngFor="let item of results.results">
          <mat-card-title>
            <a [routerLink]="['/indicators', item.uuid]">{{ item.code }} - {{ item.title }}</a>
          </mat-card-title>
          <mat-card-subtitle>{{ item.coverage.geography || 'Coverage not specified' }}</mat-card-subtitle>
          <mat-card-content>
            <p>{{ item.description || 'No summary provided yet.' }}</p>
            <mat-chip-set>
              <mat-chip>{{ item.status }}</mat-chip>
              <mat-chip>{{ item.sensitivity }}</mat-chip>
              <mat-chip class="readiness-chip" [class]="'readiness-' + item.method_readiness_state">
                {{ item.method_readiness_state }}
              </mat-chip>
              <mat-chip *ngFor="let method of item.method_types">{{ method }}</mat-chip>
              <mat-chip *ngFor="let tag of item.tags">{{ tag }}</mat-chip>
            </mat-chip-set>
          </mat-card-content>
        </mat-card>
      </section>
    </section>
  `,
  styles: [
    `
      .explorer-layout {
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: 1rem;
      }

      .filters {
        border-radius: 14px;
        padding: 1rem;
        background: #f7fbf8;
        border: 1px solid rgba(47, 133, 90, 0.16);
      }

      .inline-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
      }

      .results {
        display: grid;
        gap: 1rem;
      }

      .results-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .indicator-card a {
        color: var(--nbms-primary);
        text-decoration: none;
      }

      .readiness-ready {
        background: #c7edcf;
      }

      .readiness-partial {
        background: #ffe2b6;
      }

      .readiness-blocked {
        background: #ffd2d2;
      }

      @media (max-width: 980px) {
        .explorer-layout {
          grid-template-columns: 1fr;
        }
      }
    `
  ]
})
export class IndicatorExplorerPageComponent {
  private readonly indicatorService = inject(IndicatorService);

  readonly filters = new FormGroup({
    search: new FormControl<string>(''),
    framework: new FormControl<string>(''),
    status: new FormControl<string>('published'),
    sensitivity: new FormControl<string>(''),
    method_readiness: new FormControl<string>(''),
    geography: new FormControl<string>(''),
    year_from: new FormControl<number | null>(null),
    year_to: new FormControl<number | null>(null),
    sort: new FormControl<string>('title')
  });

  readonly results$ = this.filters.valueChanges.pipe(
    startWith(this.filters.getRawValue()),
    map((filters) => ({
      search: filters.search ?? undefined,
      framework: filters.framework ?? undefined,
      status: filters.status ?? undefined,
      sensitivity: filters.sensitivity ?? undefined,
      method_readiness: filters.method_readiness ?? undefined,
      geography: filters.geography ?? undefined,
      year_from: filters.year_from ?? undefined,
      year_to: filters.year_to ?? undefined,
      sort: filters.sort ?? undefined
    })),
    switchMap((filters) => this.indicatorService.list(filters))
  );
}
