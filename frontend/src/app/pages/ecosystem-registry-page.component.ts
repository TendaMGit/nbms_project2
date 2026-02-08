import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { RegistryService } from '../services/registry.service';

@Component({
  selector: 'app-ecosystem-registry-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatListModule,
    MatChipsModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="registry-grid">
      <mat-card class="list-panel">
        <mat-card-title>
          Ecosystem Registry
          <app-help-tooltip text="VegMap-centric ecosystem baseline with GET crosswalk and RLE-ready assessment records." />
        </mat-card-title>
        <mat-card-content>
          <div class="filters">
            <mat-form-field appearance="outline">
              <mat-label>Biome</mat-label>
              <input matInput [formControl]="biomeFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Bioregion</mat-label>
              <input matInput [formControl]="bioregionFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>VegMap version</mat-label>
              <input matInput [formControl]="versionFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>GET code</mat-label>
              <input matInput [formControl]="getFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Threat category</mat-label>
              <input matInput [formControl]="threatCategoryFilter" placeholder="CR / EN / VU" />
            </mat-form-field>
          </div>

          <div class="results" *ngIf="list$ | async as listPayload">
            <p class="count">Records: {{ listPayload.count }}</p>
            <button
              type="button"
              class="row"
              *ngFor="let item of listPayload.results"
              (click)="selectedUuid.setValue(item.uuid)"
              [class.active]="(selectedUuid.value || '') === item.uuid"
            >
              <div class="row-title">{{ item.ecosystem_code }} - {{ item.name }}</div>
              <div class="row-sub">
                {{ item.realm || 'realm n/a' }} | {{ item.biome || 'biome n/a' }} | {{ item.vegmap_version || 'version n/a' }}
              </div>
            </button>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card class="detail-panel" *ngIf="detail$ | async as detail">
        <mat-card-title>{{ detail.ecosystem.ecosystem_code }} - {{ detail.ecosystem.name }}</mat-card-title>
        <mat-card-content>
          <mat-chip-listbox>
            <mat-chip-option>{{ detail.ecosystem.status }}</mat-chip-option>
            <mat-chip-option>{{ detail.ecosystem.sensitivity }}</mat-chip-option>
            <mat-chip-option>{{ detail.ecosystem.qa_status }}</mat-chip-option>
          </mat-chip-listbox>
          <p>{{ detail.ecosystem.description || 'No ecosystem description captured.' }}</p>
          <p><strong>Realm:</strong> {{ detail.ecosystem.realm || 'n/a' }}</p>
          <p><strong>Biome:</strong> {{ detail.ecosystem.biome || 'n/a' }}</p>
          <p><strong>Bioregion:</strong> {{ detail.ecosystem.bioregion || 'n/a' }}</p>
          <p><strong>VegMap version:</strong> {{ detail.ecosystem.vegmap_version || 'n/a' }}</p>

          <h3>GET Crosswalk</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.crosswalks">
              {{ row.get_code }} (L{{ row.get_level }}) - {{ row.review_status }} - confidence {{ row.confidence }}%
            </mat-list-item>
          </mat-list>

          <h3>RLE-ready Assessments</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.risk_assessments">
              {{ row.assessment_year }} - {{ row.category }} - {{ row.review_status }}
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .registry-grid {
        display: grid;
        grid-template-columns: minmax(360px, 440px) 1fr;
        gap: 1rem;
      }
      .filters {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.5rem;
      }
      .results {
        margin-top: 0.65rem;
        display: grid;
        gap: 0.45rem;
      }
      .count {
        margin: 0;
        color: #264d3b;
        font-size: 0.85rem;
      }
      .row {
        text-align: left;
        border: 1px solid rgba(20, 82, 61, 0.18);
        border-radius: 10px;
        padding: 0.55rem;
        background: #fff;
        cursor: pointer;
      }
      .row.active {
        border-color: var(--nbms-primary);
        background: rgba(24, 118, 84, 0.08);
      }
      .row-title {
        font-weight: 600;
      }
      .row-sub {
        font-size: 0.82rem;
        color: #2f5449;
      }
      @media (max-width: 1080px) {
        .registry-grid {
          grid-template-columns: 1fr;
        }
      }
    `
  ]
})
export class EcosystemRegistryPageComponent {
  private readonly registryService = inject(RegistryService);

  readonly biomeFilter = new FormControl<string>('', { nonNullable: true });
  readonly bioregionFilter = new FormControl<string>('', { nonNullable: true });
  readonly versionFilter = new FormControl<string>('', { nonNullable: true });
  readonly getFilter = new FormControl<string>('', { nonNullable: true });
  readonly threatCategoryFilter = new FormControl<string>('', { nonNullable: true });
  readonly selectedUuid = new FormControl<string>('', { nonNullable: true });

  readonly list$ = combineLatest([
    this.biomeFilter.valueChanges.pipe(startWith(this.biomeFilter.value)),
    this.bioregionFilter.valueChanges.pipe(startWith(this.bioregionFilter.value)),
    this.versionFilter.valueChanges.pipe(startWith(this.versionFilter.value)),
    this.getFilter.valueChanges.pipe(startWith(this.getFilter.value)),
    this.threatCategoryFilter.valueChanges.pipe(startWith(this.threatCategoryFilter.value))
  ]).pipe(
    switchMap(([biome, bioregion, version, get_efg, threat_category]) =>
      this.registryService.listEcosystems({
        biome: biome || undefined,
        bioregion: bioregion || undefined,
        version: version || undefined,
        get_efg: get_efg || undefined,
        threat_category: threat_category || undefined
      })
    ),
    map((payload) => {
      if (!this.selectedUuid.value && payload.results.length) {
        this.selectedUuid.setValue(payload.results[0].uuid, { emitEvent: false });
      }
      return payload;
    }),
    shareReplay(1)
  );

  readonly detail$ = this.selectedUuid.valueChanges.pipe(
    startWith(this.selectedUuid.value),
    switchMap((uuid) => (uuid ? this.registryService.ecosystemDetail(uuid) : of(null)))
  );
}
