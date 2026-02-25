import { AsyncPipe, DatePipe, JsonPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { map, shareReplay, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DownloadRecordService } from '../services/download-record.service';

@Component({
  selector: 'app-download-record-page',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    JsonPipe,
    NgFor,
    NgIf,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatSnackBarModule
  ],
  template: `
    <section class="landing-grid" *ngIf="record$ | async as payload">
      <mat-card>
        <mat-card-title>{{ payload.record.record_type }} download record</mat-card-title>
        <mat-card-subtitle>
          Created {{ payload.record.created_at | date: 'medium' }} | status {{ payload.record.status }}
        </mat-card-subtitle>
        <div class="action-row">
          <button mat-flat-button color="primary" *ngIf="payload.record.file.download_url" (click)="downloadFile(payload.record.uuid)">
            Download file
          </button>
          <button mat-stroked-button type="button" (click)="copyCitation(payload.record.citation_text)">Copy citation</button>
          <button mat-stroked-button type="button" (click)="openRelated(payload.record.object_type, payload.record.object_uuid)">
            Open related object
          </button>
          <button mat-button type="button" (click)="backToList()">Back to list</button>
        </div>
        <p class="warning" *ngIf="!payload.record.file.authorized">
          File access is currently restricted for your account. The record remains available for audit and citation.
        </p>
      </mat-card>

      <mat-card>
        <mat-card-title>Citation</mat-card-title>
        <mat-card-content>
          <p class="citation">{{ payload.record.citation_text }}</p>
          <p><strong>Citation ID:</strong> {{ payload.record.citation_id || 'n/a' }}</p>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Provenance snapshot</mat-card-title>
        <mat-card-content>
          <pre>{{ payload.record.query_snapshot | json }}</pre>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Contributing sources</mat-card-title>
        <mat-card-content>
          <div class="source-row" *ngFor="let row of payload.record.contributing_sources">
            <span>{{ row['kind'] || 'source' }}</span>
            <span>{{ row | json }}</span>
          </div>
          <p *ngIf="!payload.record.contributing_sources.length">No source details are available for this account context.</p>
        </mat-card-content>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .landing-grid {
        display: grid;
        gap: 1rem;
      }
      .action-row {
        margin-top: 0.8rem;
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
      }
      .citation {
        font-family: monospace;
        margin: 0;
        font-size: 0.86rem;
      }
      .warning {
        margin-top: 0.75rem;
        color: #8a2f1c;
      }
      pre {
        margin: 0;
        background: rgba(18, 106, 78, 0.06);
        border-radius: 10px;
        padding: 0.7rem;
        max-height: 320px;
        overflow: auto;
      }
      .source-row {
        display: grid;
        gap: 0.2rem;
        border-bottom: 1px dashed rgba(20, 82, 61, 0.2);
        padding: 0.45rem 0;
      }
    `
  ]
})
export class DownloadRecordPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly downloads = inject(DownloadRecordService);
  private readonly snackbar = inject(MatSnackBar);

  readonly record$ = this.route.paramMap.pipe(
    map((params) => params.get('uuid') ?? ''),
    switchMap((uuid) => this.downloads.detail(uuid)),
    shareReplay(1)
  );

  downloadFile(uuid: string): void {
    window.open(this.downloads.fileUrl(uuid), '_blank', 'noopener');
  }

  copyCitation(text: string): void {
    if (!text) {
      return;
    }
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      this.snackbar.open('Clipboard API is unavailable in this browser context.', 'Dismiss', { duration: 3000 });
      return;
    }
    navigator.clipboard
      .writeText(text)
      .then(() => this.snackbar.open('Citation copied.', 'Dismiss', { duration: 2000 }))
      .catch(() => this.snackbar.open('Copy failed. Select and copy manually.', 'Dismiss', { duration: 3000 }));
  }

  openRelated(objectType: string, objectUuid: string | null): void {
    if (!objectUuid) {
      this.router.navigate(['/downloads']);
      return;
    }
    if (objectType === 'indicator') {
      this.router.navigate(['/indicators', objectUuid]);
      return;
    }
    if (objectType === 'reporting_instance') {
      this.router.navigate(['/reports', objectUuid]);
      return;
    }
    this.router.navigate(['/downloads']);
  }

  backToList(): void {
    this.router.navigate(['/downloads']);
  }
}
