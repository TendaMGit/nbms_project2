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
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { RegistryService } from '../services/registry.service';
import { UserPreferencesService } from '../services/user-preferences.service';

@Component({
  selector: 'app-taxon-registry-page',
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
    MatButtonModule,
    MatIconModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="registry-grid">
      <mat-card class="list-panel">
        <mat-card-title>
          Taxon Registry
          <app-help-tooltip text="Darwin Core-first taxon concepts with source records and voucher readiness." />
        </mat-card-title>
        <div class="toolbar-actions">
          <button mat-stroked-button type="button" (click)="saveCurrentView()">Save view</button>
        </div>
        <mat-card-content>
          <div class="filters">
            <mat-form-field appearance="outline">
              <mat-label>Search name/code</mat-label>
              <input matInput [formControl]="searchFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Rank</mat-label>
              <input matInput [formControl]="rankFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Source</mat-label>
              <input matInput [formControl]="sourceFilter" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Has voucher</mat-label>
              <mat-select [formControl]="voucherFilter">
                <mat-option value="">Any</mat-option>
                <mat-option value="true">Yes</mat-option>
                <mat-option value="false">No</mat-option>
              </mat-select>
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
                {{ item.taxon_rank || 'rank n/a' }} | vouchers {{ item.voucher_specimen_count }} | source
                {{ item.primary_source_system || 'n/a' }}
              </div>
            </button>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card class="detail-panel" *ngIf="detail$ | async as detail">
        <mat-card-title>{{ detail.taxon.taxon_code }} - {{ detail.taxon.scientific_name }}</mat-card-title>
        <mat-card-content>
          <mat-chip-listbox>
            <mat-chip-option>{{ detail.taxon.status }}</mat-chip-option>
            <mat-chip-option>{{ detail.taxon.sensitivity }}</mat-chip-option>
            <mat-chip-option>{{ detail.taxon.qa_status }}</mat-chip-option>
          </mat-chip-listbox>
          <p><strong>Classification:</strong> {{ detail.taxon.classification.kingdom }} / {{ detail.taxon.classification.family }} / {{ detail.taxon.classification.genus }}</p>
          <p><strong>GBIF key:</strong> {{ detail.taxon.gbif_taxon_key || 'n/a' }}</p>
          <p><strong>Voucher count:</strong> {{ detail.taxon.voucher_specimen_count }}</p>

          <h3>Names</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.names">
              {{ row.name }} ({{ row.name_type }}) {{ row.language ? '- ' + row.language : '' }}
            </mat-list-item>
          </mat-list>

          <h3>Source Records</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.source_records">
              {{ row.source_system }} - {{ row.retrieved_at }}
            </mat-list-item>
          </mat-list>

          <h3>Voucher Summary</h3>
          <mat-list>
            <mat-list-item *ngFor="let row of detail.vouchers">
              {{ row.occurrence_id }} - {{ row.locality }} ({{ row.country_code }})
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
      .toolbar-actions {
        margin-top: 0.5rem;
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
export class TaxonRegistryPageComponent {
  private readonly registryService = inject(RegistryService);
  private readonly preferences = inject(UserPreferencesService);

  readonly searchFilter = new FormControl<string>('', { nonNullable: true });
  readonly rankFilter = new FormControl<string>('', { nonNullable: true });
  readonly sourceFilter = new FormControl<string>('', { nonNullable: true });
  readonly voucherFilter = new FormControl<string>('', { nonNullable: true });
  readonly selectedUuid = new FormControl<string>('', { nonNullable: true });

  readonly list$ = combineLatest([
    this.searchFilter.valueChanges.pipe(startWith(this.searchFilter.value)),
    this.rankFilter.valueChanges.pipe(startWith(this.rankFilter.value)),
    this.sourceFilter.valueChanges.pipe(startWith(this.sourceFilter.value)),
    this.voucherFilter.valueChanges.pipe(startWith(this.voucherFilter.value))
  ]).pipe(
    switchMap(([search, rank, source, has_voucher]) =>
      this.registryService.listTaxa({
        search: search || undefined,
        rank: rank || undefined,
        source: source || undefined,
        has_voucher: has_voucher || undefined
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
    switchMap((uuid) => (uuid ? this.registryService.taxonDetail(uuid) : of(null)))
  );

  saveCurrentView(): void {
    const name = typeof window !== 'undefined' ? window.prompt('Name this registry view', 'Taxon registry view') : 'Taxon registry view';
    if (!name || !name.trim()) {
      return;
    }
    this.preferences
      .saveFilter(
        'registries',
        name.trim(),
        {
          search: this.searchFilter.value || undefined,
          rank: this.rankFilter.value || undefined,
          source: this.sourceFilter.value || undefined,
          has_voucher: this.voucherFilter.value || undefined
        },
        true
      )
      .subscribe();
  }
}
