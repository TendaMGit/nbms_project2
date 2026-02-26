import { AsyncPipe, DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { combineLatest, shareReplay, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';

import { DownloadRecordType } from '../models/api.models';
import { DownloadRecordService } from '../services/download-record.service';

@Component({
  selector: 'app-downloads-page',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule
  ],
  template: `
    <section class="downloads-grid">
      <mat-card>
        <mat-card-title>Downloads Center</mat-card-title>
        <mat-card-subtitle>Persistent download records with citation and provenance snapshots.</mat-card-subtitle>
        <div class="toolbar">
          <mat-form-field appearance="outline">
            <mat-label>Record type</mat-label>
            <mat-select [formControl]="typeControl">
              <mat-option value="">All</mat-option>
              <mat-option *ngFor="let type of recordTypes" [value]="type">{{ type }}</mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-stroked-button type="button" (click)="refresh()">Refresh</button>
        </div>
      </mat-card>

      <mat-card *ngIf="records$ | async as payload">
        <mat-card-title>My Downloads ({{ payload.count }})</mat-card-title>
        <mat-card-content>
          <button type="button" class="row" *ngFor="let row of payload.results" (click)="openRecord(row.uuid)">
            <div class="title">{{ row.record_type }} | {{ row.object_type || 'n/a' }}</div>
            <div class="meta">
              {{ row.created_at | date: 'medium' }} | status {{ row.status }} | access {{ row.access_level_at_time }}
            </div>
            <div class="citation">{{ row.citation_id || 'Citation pending' }}</div>
          </button>
          <p class="empty" *ngIf="!payload.results.length">No download records yet.</p>
        </mat-card-content>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .downloads-grid {
        display: grid;
        gap: 1rem;
      }
      .toolbar {
        margin-top: 0.8rem;
        display: flex;
        gap: 0.7rem;
        align-items: center;
        flex-wrap: wrap;
      }
      .row {
        width: 100%;
        text-align: left;
        display: grid;
        gap: 0.25rem;
        border: 1px solid rgba(20, 82, 61, 0.18);
        border-radius: 10px;
        padding: 0.65rem;
        background: #fff;
        margin-bottom: 0.55rem;
        cursor: pointer;
      }
      .row:hover {
        border-color: var(--nbms-primary);
        background: rgba(24, 118, 84, 0.06);
      }
      .title {
        font-weight: 600;
      }
      .meta {
        font-size: 0.84rem;
        color: #2f5449;
      }
      .citation {
        font-family: monospace;
        font-size: 0.78rem;
        color: #355a4b;
      }
      .empty {
        margin: 0;
        color: #4e5f58;
      }
    `
  ]
})
export class DownloadsPageComponent {
  private readonly downloads = inject(DownloadRecordService);
  private readonly router = inject(Router);

  readonly typeControl = new FormControl<string>('', { nonNullable: true });
  readonly refreshControl = new FormControl<number>(0, { nonNullable: true });
  readonly recordTypes: DownloadRecordType[] = [
    'indicator_series',
    'spatial_layer',
    'report_export',
    'registry_export',
    'custom_bundle'
  ];

  readonly records$ = combineLatest([
    this.typeControl.valueChanges.pipe(startWith(this.typeControl.value)),
    this.refreshControl.valueChanges.pipe(startWith(this.refreshControl.value))
  ]).pipe(
    switchMap(([record_type]) =>
      this.downloads.list({
        record_type: (record_type as DownloadRecordType) || undefined,
        page_size: 50
      })
    ),
    shareReplay(1)
  );

  refresh(): void {
    this.refreshControl.setValue(this.refreshControl.value + 1);
  }

  openRecord(uuid: string): void {
    this.router.navigate(['/downloads', uuid]);
  }
}

