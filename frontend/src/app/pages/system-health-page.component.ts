import { AsyncPipe, DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BehaviorSubject, catchError, of } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { SystemHealthService } from '../services/system-health.service';

@Component({
  selector: 'app-system-health-page',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    NgFor,
    NgIf,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatButtonModule,
    HelpTooltipComponent
  ],
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
          <div class="overall-row">
            <span>API uptime</span>
            <span>{{ formatUptime(summary.uptime_seconds) }}</span>
          </div>
          <div class="overall-row">
            <span>Downloads backlog</span>
            <span>{{ summary.download_record_backlog ?? 0 }}</span>
          </div>
          <div class="overall-row">
            <span>Export failures (24h)</span>
            <span>{{ summary.export_failures_last_24h ?? 0 }}</span>
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
          <mat-card-title>Observability Controls</mat-card-title>
          <app-help-tooltip text="Operational signals for metrics, logs, tracing, and error monitoring." />
        </mat-card-header>
        <mat-card-content>
          <div class="service-row">
            <strong>Metrics</strong>
            <mat-chip-set>
              <mat-chip [class.ok]="summary.observability?.metrics_enabled">{{ summary.observability?.metrics_enabled ? 'enabled' : 'disabled' }}</mat-chip>
            </mat-chip-set>
          </div>
          <div class="service-row">
            <strong>Structured logs</strong>
            <mat-chip-set>
              <mat-chip [class.ok]="summary.observability?.logs_json_enabled">{{ summary.observability?.logs_json_enabled ? 'json' : 'plain' }}</mat-chip>
            </mat-chip-set>
          </div>
          <div class="service-row">
            <strong>Tracing</strong>
            <mat-chip-set>
              <mat-chip [class.ok]="summary.observability?.tracing_enabled">{{ summary.observability?.tracing_enabled ? 'enabled' : 'disabled' }}</mat-chip>
            </mat-chip-set>
          </div>
          <div class="service-row">
            <strong>Sentry</strong>
            <mat-chip-set>
              <mat-chip [class.ok]="summary.observability?.sentry_enabled">{{ summary.observability?.sentry_enabled ? 'enabled' : 'disabled' }}</mat-chip>
            </mat-chip-set>
          </div>
          <p class="detail">
            Include the response <code>X-Request-ID</code> from failing API calls when escalating incidents.
          </p>
          <button mat-stroked-button type="button" (click)="copyDebugBundle(summary)">Copy debug bundle</button>
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
        uptime_seconds: 0,
        services: [],
        observability: {
          metrics_enabled: false,
          logs_json_enabled: false,
          tracing_enabled: false,
          sentry_enabled: false
        },
        download_record_backlog: 0,
        export_failures_last_24h: 0,
        recent_failures: []
      });
    })
  );

  formatUptime(seconds: number | undefined): string {
    if (!seconds || seconds <= 0) {
      return 'n/a';
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }

  copyDebugBundle(summary: {
    overall_status: string;
    services: Array<{ service: string; status: string }>;
    uptime_seconds?: number;
    download_record_backlog?: number;
    export_failures_last_24h?: number;
  }): void {
    const payload = {
      captured_at: new Date().toISOString(),
      overall_status: summary.overall_status,
      uptime_seconds: summary.uptime_seconds ?? null,
      download_record_backlog: summary.download_record_backlog ?? null,
      export_failures_last_24h: summary.export_failures_last_24h ?? null,
      services: summary.services,
      location: typeof window !== 'undefined' ? window.location.href : ''
    };
    const text = JSON.stringify(payload, null, 2);
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(text);
      return;
    }
    if (typeof window !== 'undefined') {
      window.prompt('Copy debug bundle', text);
    }
  }
}
