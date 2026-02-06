import { AsyncPipe, JsonPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { Nr7BuilderSummary } from '../models/api.models';
import { Nr7BuilderService } from '../services/nr7-builder.service';

@Component({
  selector: 'app-reporting-page',
  standalone: true,
  imports: [
    AsyncPipe,
    JsonPipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatListModule,
    MatSelectModule,
    MatTooltipModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="builder-shell" *ngIf="instances$ | async as instancesPayload">
      <header class="qa-bar" *ngIf="summary$ | async as summary">
        <div class="qa-title">
          <h2>NR7 Report Builder</h2>
          <app-help-tooltip text="Author Sections I-V with live QA checks, preview, and deterministic export output." />
        </div>
        <div class="qa-chips">
          <mat-chip-set>
            <mat-chip [class.ok]="summary.validation.overall_ready" [class.block]="!summary.validation.overall_ready">
              {{ summary.validation.overall_ready ? 'Ready to export' : 'Not ready' }}
            </mat-chip>
            <mat-chip class="warn">
              Blockers: {{ blockers(summary) }}
            </mat-chip>
            <mat-chip>Warnings: {{ warnings(summary) }}</mat-chip>
          </mat-chip-set>
        </div>
      </header>

      <section class="instance-picker">
        <mat-form-field appearance="outline">
          <mat-label>Reporting instance</mat-label>
          <mat-select [formControl]="instanceControl">
            <mat-option *ngFor="let item of instancesPayload.instances" [value]="item.uuid">
              {{ item.cycle_code }} / {{ item.version_label }} ({{ item.status }})
            </mat-option>
          </mat-select>
        </mat-form-field>
        <a
          mat-flat-button
          color="primary"
          *ngIf="instanceControl.value"
          [href]="pdfUrl(instanceControl.value)"
          target="_blank"
          rel="noopener noreferrer"
        >
          Export PDF
        </a>
      </section>

      <section class="builder-grid" *ngIf="summary$ | async as summary">
        <mat-card class="left-nav">
          <mat-card-title>Sections I-V</mat-card-title>
          <mat-card-content>
            <mat-list>
              <mat-list-item *ngFor="let section of summary.validation.sections">
                <mat-icon matListItemIcon>{{ sectionIcon(section.state) }}</mat-icon>
                <div matListItemTitle>{{ section.title }}</div>
                <div matListItemLine>
                  {{ section.state }} - {{ section.completion }}%
                </div>
              </mat-list-item>
            </mat-list>
          </mat-card-content>
        </mat-card>

        <mat-card class="main-editor">
          <mat-card-title>Editor Links</mat-card-title>
          <mat-card-content>
            <p>Use structured Django editors while Angular authoring coverage expands:</p>
            <div class="editor-links">
              <a mat-stroked-button [href]="summary.links['section_i']">Section I</a>
              <a mat-stroked-button [href]="summary.links['section_ii']">Section II</a>
              <a mat-stroked-button [href]="summary.links['section_iii']">Section III</a>
              <a mat-stroked-button [href]="summary.links['section_iv_goals']">Section IV Goals</a>
              <a mat-stroked-button [href]="summary.links['section_iv_targets']">Section IV Targets</a>
              <a mat-stroked-button [href]="summary.links['section_v']">Section V</a>
            </div>
            <mat-divider></mat-divider>
            <h3>QA Findings</h3>
            <div class="qa-item" *ngFor="let item of summary.validation.qa_items">
              <span class="severity" [class.block]="item.severity === 'BLOCKER'" [class.warn]="item.severity !== 'BLOCKER'">
                {{ item.severity }}
              </span>
              <span>{{ item.message }}</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="preview-panel">
          <mat-card-title>Live Preview</mat-card-title>
          <mat-card-content>
            <p *ngIf="summary.preview_error" class="preview-error">
              {{ summary.preview_error }}
            </p>
            <pre *ngIf="summary.preview_payload">{{ summary.preview_payload | json }}</pre>
          </mat-card-content>
        </mat-card>
      </section>
    </section>
  `,
  styles: [
    `
      .builder-shell {
        display: grid;
        gap: 1rem;
      }

      .qa-bar {
        border-radius: 12px;
        border: 1px solid rgba(18, 106, 78, 0.16);
        padding: 0.9rem 1rem;
        background: linear-gradient(165deg, rgba(18, 106, 78, 0.1), rgba(249, 252, 247, 0.95));
      }

      .qa-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }

      .qa-chips {
        margin-top: 0.6rem;
      }

      .instance-picker {
        display: flex;
        align-items: center;
        gap: 1rem;
      }

      .builder-grid {
        display: grid;
        grid-template-columns: 260px minmax(0, 1fr) minmax(0, 1fr);
        gap: 1rem;
      }

      .left-nav,
      .main-editor,
      .preview-panel {
        min-height: 520px;
      }

      .editor-links {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 1rem;
      }

      .qa-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
      }

      .severity {
        border-radius: 999px;
        padding: 0.15rem 0.55rem;
        font-size: 0.73rem;
        letter-spacing: 0.02em;
      }

      .severity.block,
      mat-chip.block {
        background: #f3c6c6;
      }

      .severity.warn,
      mat-chip.warn {
        background: #f5dfb8;
      }

      mat-chip.ok {
        background: #c1e7cf;
      }

      .preview-error {
        color: #9b5e00;
      }

      pre {
        white-space: pre-wrap;
        border: 1px solid #dde7e0;
        border-radius: 8px;
        background: #f6f8f7;
        padding: 0.75rem;
        max-height: 440px;
        overflow: auto;
      }

      @media (max-width: 1240px) {
        .builder-grid {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 760px) {
        .instance-picker {
          flex-direction: column;
          align-items: stretch;
        }
      }
    `
  ]
})
export class ReportingPageComponent {
  private readonly service = inject(Nr7BuilderService);

  readonly instanceControl = new FormControl<string | null>(null);

  readonly instances$ = this.service.listInstances().pipe(
    map((payload) => {
      const first = payload.instances[0]?.uuid ?? null;
      if (!this.instanceControl.value && first) {
        this.instanceControl.setValue(first, { emitEvent: false });
      }
      return payload;
    }),
    shareReplay(1)
  );

  readonly summary$ = combineLatest([
    this.instances$,
    this.instanceControl.valueChanges.pipe(startWith<string | null>(null)),
  ]).pipe(
    map(([instancesPayload, selected]) => selected || this.instanceControl.value || instancesPayload.instances[0]?.uuid || null),
    switchMap((instanceUuid) => (instanceUuid ? this.service.getSummary(instanceUuid) : of<Nr7BuilderSummary | null>(null))),
    shareReplay(1)
  );

  blockers(summary: Nr7BuilderSummary): number {
    return summary.validation.qa_items.filter((item) => item.severity === 'BLOCKER').length;
  }

  warnings(summary: Nr7BuilderSummary): number {
    return summary.validation.qa_items.filter((item) => item.severity !== 'BLOCKER').length;
  }

  pdfUrl(instanceUuid: string): string {
    return this.service.getPdfUrl(instanceUuid);
  }

  sectionIcon(state: string): string {
    if (state === 'complete') {
      return 'check_circle';
    }
    if (state === 'draft') {
      return 'edit';
    }
    if (state === 'missing') {
      return 'error';
    }
    return 'help';
  }
}
