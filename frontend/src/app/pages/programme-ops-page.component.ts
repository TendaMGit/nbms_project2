import { DatePipe, JsonPipe, NgFor, NgIf, SlicePipe, UpperCasePipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { ProgrammeDetailResponse, ProgrammeRun, ProgrammeSummary } from '../models/api.models';
import { ProgrammeOpsService } from '../services/programme-ops.service';

@Component({
  selector: 'app-programme-ops-page',
  standalone: true,
  imports: [
    DatePipe,
    JsonPipe,
    NgFor,
    NgIf,
    SlicePipe,
    UpperCasePipe,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatSnackBarModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="programme-shell">
      <mat-card class="programme-list-card">
        <mat-card-header>
          <mat-card-title>Programme Registry</mat-card-title>
          <app-help-tooltip text="Monitoring programmes orchestrate ingest, QA, compute, and publish workflows." />
        </mat-card-header>
        <mat-card-content>
          <mat-form-field appearance="outline" class="search-field">
            <mat-label>Search programmes</mat-label>
            <input matInput [value]="searchText" (input)="onSearch($event)" />
            <mat-icon matSuffix>search</mat-icon>
          </mat-form-field>
          <mat-progress-bar *ngIf="loadingList" mode="indeterminate"></mat-progress-bar>
          <mat-nav-list>
            <a
              mat-list-item
              *ngFor="let programme of programmes"
              (click)="selectProgramme(programme.uuid)"
              [class.active]="programme.uuid === selectedProgrammeUuid"
            >
              <mat-icon matListItemIcon>hub</mat-icon>
              <div matListItemTitle>{{ programme.programme_code }} - {{ programme.title }}</div>
              <div matListItemLine>
                {{ programme.refresh_cadence | uppercase }} | alerts: {{ programme.open_alert_count }}
              </div>
            </a>
          </mat-nav-list>
        </mat-card-content>
      </mat-card>

      <div class="programme-detail" *ngIf="detail as payload">
        <mat-card class="summary-card">
          <mat-card-header>
            <mat-card-title>{{ payload.programme.title }}</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <p>{{ payload.programme.description }}</p>
            <div class="chip-row">
              <mat-chip-set>
                <mat-chip>{{ payload.programme.programme_code }}</mat-chip>
                <mat-chip>{{ payload.programme.programme_type || 'unspecified type' }}</mat-chip>
                <mat-chip [class.scheduler-on]="payload.programme.scheduler_enabled">
                  scheduler {{ payload.programme.scheduler_enabled ? 'on' : 'off' }}
                </mat-chip>
                <mat-chip>cadence {{ payload.programme.refresh_cadence }}</mat-chip>
              </mat-chip-set>
            </div>
            <div class="stats-grid">
              <div><strong>Lead:</strong> {{ payload.programme.lead_org || 'not set' }}</div>
              <div><strong>Last run:</strong> {{ payload.programme.last_run_at | date: 'short' }}</div>
              <div><strong>Next run:</strong> {{ payload.programme.next_run_at | date: 'short' }}</div>
              <div><strong>Datasets:</strong> {{ payload.programme.dataset_link_count }}</div>
              <div><strong>Indicators:</strong> {{ payload.programme.indicator_link_count }}</div>
              <div><strong>Open alerts:</strong> {{ payload.programme.open_alert_count }}</div>
            </div>
            <div class="action-row">
              <button mat-flat-button color="primary" [disabled]="!payload.can_manage || runningAction" (click)="runNow(false)">
                <mat-icon>play_arrow</mat-icon>
                Run now
              </button>
              <button mat-stroked-button [disabled]="!payload.can_manage || runningAction" (click)="runNow(true)">
                <mat-icon>science</mat-icon>
                Dry-run
              </button>
              <span class="hint" *ngIf="!payload.can_manage">You have read-only access to this programme.</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Stewards and Institutions</mat-card-title>
            <app-help-tooltip text="Stewards are the accountable operators for programme execution and review." />
          </mat-card-header>
          <mat-card-content>
            <div class="two-col">
              <div>
                <h4>Stewards</h4>
                <ul>
                  <li *ngFor="let steward of payload.programme.stewards">
                    {{ steward.username }} ({{ steward.role }}){{ steward.is_primary ? ' - primary' : '' }}
                  </li>
                </ul>
              </div>
              <div>
                <h4>Operating institutions</h4>
                <ul>
                  <li *ngFor="let org of payload.programme.operating_institutions">
                    {{ org.org_code }} - {{ org.name }}
                  </li>
                </ul>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Pipeline and QA Rules</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="two-col">
              <div>
                <h4>Pipeline definition</h4>
                <pre>{{ payload.programme.pipeline_definition_json | json }}</pre>
              </div>
              <div>
                <h4>Quality rules</h4>
                <pre>{{ payload.programme.data_quality_rules_json | json }}</pre>
              </div>
            </div>
            <p class="lineage"><strong>Lineage notes:</strong> {{ payload.programme.lineage_notes || 'No lineage notes recorded.' }}</p>
          </mat-card-content>
        </mat-card>

        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Recent Runs</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="run-row" *ngFor="let run of payload.runs | slice:0:10">
              <div>
                <strong>{{ run.run_type }}</strong> via {{ run.trigger }} | {{ run.created_at | date: 'short' }}
              </div>
              <mat-chip [class]="statusClass(run.status)">{{ run.status }}</mat-chip>
              <button mat-button (click)="rerun(run)" *ngIf="payload.can_manage">Run again</button>
              <button mat-button (click)="downloadRunReport(run)">Report JSON</button>
            </div>
            <div class="step-grid" *ngIf="payload.runs.length">
              <div class="step-pill" *ngFor="let step of payload.runs[0].steps">
                {{ step.ordering }}. {{ step.step_key }} ({{ step.status }})
              </div>
            </div>
            <div class="two-col" *ngIf="payload.runs.length">
              <div>
                <h4>QA Results (latest run)</h4>
                <ul>
                  <li *ngFor="let qa of payload.runs[0].qa_results || []">
                    <strong>{{ qa.code }}</strong>: {{ qa.status }} - {{ qa.message }}
                  </li>
                </ul>
              </div>
              <div>
                <h4>Artefacts (latest run)</h4>
                <ul>
                  <li *ngFor="let artefact of payload.runs[0].artefacts || []">
                    <strong>{{ artefact.label }}</strong> - {{ artefact.storage_path }}
                  </li>
                </ul>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="panel">
          <mat-card-header>
            <mat-card-title>Open Alerts</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="alert-row" *ngFor="let alert of payload.alerts | slice:0:15">
              <mat-icon [class]="'severity-' + alert.severity">warning</mat-icon>
              <div>
                <strong>{{ alert.code }}</strong> ({{ alert.severity }})
                <div>{{ alert.message }}</div>
              </div>
            </div>
            <div *ngIf="!payload.alerts.length">No active alerts.</div>
          </mat-card-content>
        </mat-card>
      </div>
    </section>
  `,
  styles: [
    `
      .programme-shell {
        display: grid;
        grid-template-columns: 320px minmax(0, 1fr);
        gap: 1rem;
      }

      .programme-list-card {
        position: sticky;
        top: 1rem;
        align-self: start;
      }

      .search-field {
        width: 100%;
      }

      .programme-detail {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }

      .summary-card {
        grid-column: span 2;
      }

      .panel {
        grid-column: span 1;
      }

      .chip-row,
      .action-row {
        margin: 0.9rem 0;
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.6rem;
      }

      .two-col {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }

      .run-row,
      .alert-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        margin-bottom: 0.65rem;
      }

      .step-grid {
        display: flex;
        gap: 0.45rem;
        flex-wrap: wrap;
      }

      .step-pill {
        border-radius: 999px;
        border: 1px solid rgba(0, 0, 0, 0.15);
        padding: 0.2rem 0.55rem;
        font-size: 0.85rem;
      }

      .scheduler-on {
        background: #d7f5de;
      }

      .status-succeeded {
        background: #cbeed7;
      }

      .status-blocked,
      .status-failed {
        background: #ffd2d2;
      }

      .severity-warning {
        color: #b06c00;
      }

      .severity-error,
      .severity-critical {
        color: #c0382b;
      }

      .lineage {
        margin-top: 0.6rem;
      }

      .hint {
        font-size: 0.85rem;
        color: rgba(0, 0, 0, 0.64);
      }

      a.active {
        background: rgba(18, 106, 78, 0.12);
      }

      pre {
        margin: 0;
        max-height: 220px;
        overflow: auto;
        background: rgba(18, 106, 78, 0.06);
        border-radius: 10px;
        padding: 0.7rem;
      }

      @media (max-width: 1080px) {
        .programme-shell {
          grid-template-columns: 1fr;
        }

        .programme-list-card {
          position: static;
        }

        .programme-detail,
        .stats-grid,
        .two-col {
          grid-template-columns: 1fr;
        }

        .summary-card,
        .panel {
          grid-column: span 1;
        }
      }
    `
  ]
})
export class ProgrammeOpsPageComponent {
  private readonly service = inject(ProgrammeOpsService);
  private readonly snackbar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  programmes: ProgrammeSummary[] = [];
  detail: ProgrammeDetailResponse | null = null;
  selectedProgrammeUuid: string | null = null;
  loadingList = false;
  loadingDetail = false;
  runningAction = false;
  searchText = '';

  constructor() {
    this.loadProgrammes();
  }

  onSearch(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.searchText = value;
    this.loadProgrammes();
  }

  selectProgramme(programmeUuid: string) {
    this.selectedProgrammeUuid = programmeUuid;
    this.loadingDetail = true;
    this.service
      .detail(programmeUuid)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (payload) => {
          this.detail = payload;
          this.loadingDetail = false;
        },
        error: (error) => {
          this.loadingDetail = false;
          const message = error?.error?.detail || 'Could not load programme details.';
          this.snackbar.open(message, 'Dismiss', { duration: 5000 });
        }
      });
  }

  runNow(dryRun: boolean) {
    if (!this.detail?.programme?.uuid) {
      return;
    }
    this.runningAction = true;
    this.service
      .run(this.detail.programme.uuid, { run_type: 'full', dry_run: dryRun, execute_now: true })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.runningAction = false;
          this.snackbar.open(dryRun ? 'Dry-run completed.' : 'Programme run completed.', 'Dismiss', {
            duration: 4000
          });
          this.selectProgramme(this.detail?.programme.uuid as string);
          this.loadProgrammes();
        },
        error: (error) => {
          this.runningAction = false;
          const message = error?.error?.detail || 'Programme run failed.';
          this.snackbar.open(message, 'Dismiss', { duration: 6000 });
        }
      });
  }

  rerun(run: ProgrammeRun) {
    this.runningAction = true;
    this.service
      .rerun(run.uuid)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.runningAction = false;
          this.snackbar.open('Run re-executed.', 'Dismiss', { duration: 3000 });
          if (this.selectedProgrammeUuid) {
            this.selectProgramme(this.selectedProgrammeUuid);
          }
          this.loadProgrammes();
        },
        error: (error) => {
          this.runningAction = false;
          const message = error?.error?.detail || 'Could not rerun pipeline.';
          this.snackbar.open(message, 'Dismiss', { duration: 5000 });
        }
      });
  }

  downloadRunReport(run: ProgrammeRun) {
    this.service
      .runReport(run.uuid)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (payload) => {
          const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = `programme-run-${run.uuid}.json`;
          anchor.click();
          URL.revokeObjectURL(url);
        },
        error: (error) => {
          const message = error?.error?.detail || 'Could not download programme run report.';
          this.snackbar.open(message, 'Dismiss', { duration: 5000 });
        }
      });
  }

  statusClass(status: string) {
    return `status-${status}`;
  }

  private loadProgrammes() {
    this.loadingList = true;
    this.service
      .list(this.searchText)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (payload) => {
          this.programmes = payload.programmes;
          this.loadingList = false;
          const selectedStillExists = this.selectedProgrammeUuid
            ? this.programmes.some((item) => item.uuid === this.selectedProgrammeUuid)
            : false;
          if (selectedStillExists && this.selectedProgrammeUuid) {
            this.selectProgramme(this.selectedProgrammeUuid);
            return;
          }
          if (this.programmes.length) {
            this.selectProgramme(this.programmes[0].uuid);
          } else {
            this.detail = null;
            this.selectedProgrammeUuid = null;
          }
        },
        error: (error) => {
          this.loadingList = false;
          const message = error?.error?.detail || 'Could not load programme registry.';
          this.snackbar.open(message, 'Dismiss', { duration: 5000 });
        }
      });
  }
}
