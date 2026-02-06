import { AsyncPipe, DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, catchError, of } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { SystemHealthService } from '../services/system-health.service';

@Component({
  selector: 'app-system-health-page',
  standalone: true,
  imports: [AsyncPipe, DatePipe, NgFor, NgIf, MatCardModule, MatIconModule, MatChipsModule, HelpTooltipComponent],
  template: `
    <section class="page-grid" *ngIf="summary$ | async as summary">
      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>System Status</mat-card-title>
          <app-help-tooltip text="Operational status of key NBMS runtime services." />
        </mat-card-header>
        <mat-card-content>
          <div class="overall-row">
            <span>Overall</span>
            <span class="status-chip" [class.ok]="summary.overall_status === 'ok'">
              {{ summary.overall_status }}
            </span>
          </div>
          <div class="service-row" *ngFor="let item of summary.services">
            <strong>{{ item.service }}</strong>
            <mat-chip-set>
              <mat-chip [class.ok]="item.status === 'ok'" [class.degraded]="item.status === 'degraded'">
                {{ item.status }}
              </mat-chip>
            </mat-chip-set>
            <p class="detail" *ngIf="item.detail">{{ item.detail }}</p>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card class="panel">
        <mat-card-header>
          <mat-card-title>Recent Workflow Failures</mat-card-title>
          <app-help-tooltip text="Recent audit events that indicate workflow or consent failures." />
        </mat-card-header>
        <mat-card-content>
          <div *ngIf="!summary.recent_failures.length" class="empty-state">No failures logged in the past 7 days.</div>
          <div class="failure-row" *ngFor="let event of summary.recent_failures">
            <mat-icon>warning</mat-icon>
            <div>
              <div>{{ event.action }} - {{ event.object_type }}</div>
              <small>{{ event.created_at | date: 'medium' }}</small>
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </section>

    <section *ngIf="error$ | async as error" class="error-panel">
      <mat-icon>error</mat-icon>
      <p>{{ error }}</p>
    </section>
  `,
  styles: [
    `
      .page-grid {
        display: grid;
        grid-template-columns: repeat(12, minmax(0, 1fr));
        gap: 1rem;
      }

      .panel {
        grid-column: span 6;
      }

      .overall-row,
      .service-row,
      .failure-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
      }

      .status-chip,
      mat-chip {
        text-transform: uppercase;
      }

      .status-chip {
        border-radius: 999px;
        padding: 0.1rem 0.75rem;
        background: #f1f4f2;
      }

      .status-chip.ok,
      mat-chip.ok {
        background: #bfe8ce;
      }

      mat-chip.degraded {
        background: #f6d9b6;
      }

      .detail {
        margin: 0;
        color: #555;
      }

      .empty-state {
        color: #666;
      }

      .error-panel {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border: 1px solid #d6b3b3;
        background: #fbeeee;
        border-radius: 8px;
        padding: 0.8rem;
      }

      @media (max-width: 980px) {
        .panel {
          grid-column: span 12;
        }
      }
    `
  ]
})
export class SystemHealthPageComponent {
  private readonly service = inject(SystemHealthService);

  readonly error$ = new BehaviorSubject<string | null>(null);
  readonly summary$ = this.service.getSummary().pipe(
    catchError((error) => {
      const message = error?.error?.detail || 'System health data unavailable.';
      this.error$.next(message);
      return of({
        overall_status: 'degraded',
        services: [],
        recent_failures: []
      });
    })
  );
}
