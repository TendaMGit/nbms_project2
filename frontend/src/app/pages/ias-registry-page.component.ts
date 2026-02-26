import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { RegistryService } from '../services/registry.service';

@Component({
  selector: 'app-ias-registry-page',
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
    MatSelectModule,
    MatChipsModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="registry-grid">
      <mat-card class="list-panel">
        <mat-card-title>
          IAS Registry
          <app-help-tooltip text="IAS profiles with establishment/pathway vocab plus EICAT and SEICAT assessments." />
        </mat-card-title>
        <mat-card-content>
          <div class="filters">
            <mat-form-field appearance="outline">
              <mat-label>Search species</mat-label>
              <input matInput [formControl]="searchFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Stage (degree)</mat-label>
              <input matInput [formControl]="stageFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Pathway</mat-label>
              <input matInput [formControl]="pathwayFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>EICAT</mat-label>
              <input matInput [formControl]="eicatFilter" placeholder="MC/MN/MO/MR/MV/DD/NE" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>SEICAT</mat-label>
              <input matInput [formControl]="seicatFilter" placeholder="MC/MN/MO/MR/MV/DD/NE" />
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
              <div class="row-title">{{ item.taxon_code }} - {{ item.scientific_name }}</div>
              <div class="row-sub">
                stage {{ item.degree_of_establishment_code }} | pathway {{ item.pathway_code }} | invasive
                {{ item.is_invasive ? 'yes' : 'no' }}
              </div>
            </button>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card class="detail-panel" *ngIf="detail$ | async as detail">
        <mat-card-title>{{ detail.profile.taxon_code }} - {{ detail.profile.scientific_name }}</mat-card-title>
        <mat-card-content>
          <mat-chip-listbox>
            <mat-chip-option>{{ detail.profile.status }}</mat-chip-option>
            <mat-chip-option>{{ detail.profile.sensitivity }}</mat-chip-option>
            <mat-chip-option>{{ detail.profile.qa_status }}</mat-chip-option>
          </mat-chip-listbox>
          <p><strong>Establishment:</strong> {{ detail.profile.establishment_means_code }}</p>
          <p><strong>Degree:</strong> {{ detail.profile.degree_of_establishment_code }}</p>
          <p><strong>Pathway:</strong> {{ detail.profile.pathway_code }}</p>
          <p><strong>Regulatory status:</strong> {{ detail.profile.regulatory_status || 'unknown' }}</p>

          <h3>EICAT Assessments</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.eicat_assessments">
              {{ row.category }} - {{ row.review_status }} - confidence {{ row.confidence }}%
            </mat-list-item>
          </mat-list>

          <h3>SEICAT Assessments</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.seicat_assessments">
              {{ row.category }} - {{ row.review_status }} - confidence {{ row.confidence }}%
            </mat-list-item>
          </mat-list>

          <h3>Checklist Provenance</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.checklist_records">
              {{ row.source_dataset }} - {{ row.source_identifier }} ({{ row.country_code }})
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
      .filters,
      .results {
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
export class IasRegistryPageComponent {
  private readonly registryService = inject(RegistryService);

  readonly searchFilter = new FormControl<string>('', { nonNullable: true });
  readonly stageFilter = new FormControl<string>('', { nonNullable: true });
  readonly pathwayFilter = new FormControl<string>('', { nonNullable: true });
  readonly eicatFilter = new FormControl<string>('', { nonNullable: true });
  readonly seicatFilter = new FormControl<string>('', { nonNullable: true });
  readonly selectedUuid = new FormControl<string>('', { nonNullable: true });

  readonly list$ = combineLatest([
    this.searchFilter.valueChanges.pipe(startWith(this.searchFilter.value)),
    this.stageFilter.valueChanges.pipe(startWith(this.stageFilter.value)),
    this.pathwayFilter.valueChanges.pipe(startWith(this.pathwayFilter.value)),
    this.eicatFilter.valueChanges.pipe(startWith(this.eicatFilter.value)),
    this.seicatFilter.valueChanges.pipe(startWith(this.seicatFilter.value))
  ]).pipe(
    switchMap(([search, stage, pathway, eicat, seicat]) =>
      this.registryService.listIas({
        search: search || undefined,
        stage: stage || undefined,
        pathway: pathway || undefined,
        eicat: eicat || undefined,
        seicat: seicat || undefined
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
    switchMap((uuid) => (uuid ? this.registryService.iasDetail(uuid) : of(null)))
  );
}
