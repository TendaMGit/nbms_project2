import { NgFor, NgIf } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subject, debounceTime, forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatStepperModule } from '@angular/material/stepper';
import { Router } from '@angular/router';

import {
  ReportContextPayload,
  ReportNarrativeRenderPayload,
  ReportSectionChartsPayload,
  ReportCommentThreadPayload,
  ReportSectionHistory,
  ReportSuggestionPayload,
  ReportWorkspaceSection,
  ReportWorkspaceSummary,
  ReportingInstanceSummary
} from '../models/api.models';
import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { PlotlyChartComponent } from '../components/plotly-chart.component';
import { DownloadRecordService } from '../services/download-record.service';
import { NationalReportService } from '../services/national-report.service';
import { Nr7BuilderService } from '../services/nr7-builder.service';

type SectionField = {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  allowed_values?: string[];
};

@Component({
  selector: 'app-reporting-page',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDividerModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatStepperModule,
    HelpTooltipComponent,
    PlotlyChartComponent
  ],
  template: `
    <section class="workspace-shell">
      <mat-card class="workspace-header">
        <div class="header-title">
          <h2>National Report Workspace</h2>
          <app-help-tooltip text="Unified CBD National Report authoring for NR7 and NR8 with review, sign-off, and integrity controls." />
        </div>
        <div class="header-grid">
          <mat-form-field appearance="outline">
            <mat-label>Reporting instance</mat-label>
            <mat-select [formControl]="instanceControl" (selectionChange)="onInstanceChange()">
              <mat-option *ngFor="let item of instances" [value]="item.uuid">
                {{ item.cycle_code }} / {{ item.version_label }} ({{ item.status }})
              </mat-option>
            </mat-select>
          </mat-form-field>
          <mat-slide-toggle [(ngModel)]="suggestionMode">Suggestion mode</mat-slide-toggle>
          <mat-form-field appearance="outline" *ngIf="suggestionMode">
            <mat-label>Suggestion rationale</mat-label>
            <input matInput [(ngModel)]="suggestionRationale" />
          </mat-form-field>
          <div class="export-actions" *ngIf="workspace">
            <button mat-stroked-button type="button" (click)="createReportExport('pdf')">Export PDF</button>
            <button mat-stroked-button type="button" (click)="createReportExport('docx')">Export DOCX</button>
            <button mat-stroked-button type="button" (click)="createReportExport('json')">Export ORT JSON</button>
            <button mat-flat-button color="primary" (click)="generateDossier()">Generate dossier</button>
            <a
              mat-stroked-button
              *ngIf="workspace.latest_dossier"
              [href]="reportService.latestDossierDownloadUrl(workspace.instance.uuid)"
              target="_blank"
              rel="noopener"
            >
              Download dossier
            </a>
          </div>
        </div>
        <mat-expansion-panel>
          <mat-expansion-panel-header>
            <mat-panel-title>Create National Report</mat-panel-title>
            <mat-panel-description>Unified NR7/NR8 template pack</mat-panel-description>
          </mat-expansion-panel-header>
          <div class="create-grid">
            <mat-form-field appearance="outline">
              <mat-label>Report label</mat-label>
              <mat-select [(ngModel)]="newReport.label">
                <mat-option value="NR7">NR7</mat-option>
                <mat-option value="NR8">NR8</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Period start</mat-label>
              <input matInput type="date" [(ngModel)]="newReport.periodStart" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Period end</mat-label>
              <input matInput type="date" [(ngModel)]="newReport.periodEnd" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Report title</mat-label>
              <input matInput [(ngModel)]="newReport.reportTitle" />
            </mat-form-field>
            <mat-slide-toggle [(ngModel)]="newReport.isPublic">Public availability</mat-slide-toggle>
            <button mat-flat-button color="primary" (click)="createNationalReport()">Create report</button>
            <button mat-stroked-button (click)="createNr8FromNr7()" [disabled]="!workspace || workspace.instance.report_label !== 'NR7'">
              Create NR8 from this NR7
            </button>
          </div>
        </mat-expansion-panel>
      </mat-card>

      <mat-card *ngIf="workspace" class="context-bar">
        <div class="context-grid">
          <mat-form-field appearance="outline">
            <mat-label>Report label</mat-label>
            <mat-select [ngModel]="contextFilters['report_label']" (ngModelChange)="setContextFilter('report_label', $event)">
              <mat-option value="">Current instance</mat-option>
              <mat-option value="NR7">NR7</mat-option>
              <mat-option value="NR8">NR8</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Geography</mat-label>
            <input matInput [ngModel]="contextFilters['geography']" (ngModelChange)="setContextFilter('geography', $event)" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Disaggregation</mat-label>
            <input matInput [ngModel]="contextFilters['disaggregation']" (ngModelChange)="setContextFilter('disaggregation', $event)" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Indicator</mat-label>
            <input matInput [ngModel]="contextFilters['indicator']" (ngModelChange)="setContextFilter('indicator', $event)" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Programme</mat-label>
            <input matInput [ngModel]="contextFilters['programme']" (ngModelChange)="setContextFilter('programme', $event)" />
          </mat-form-field>
          <button mat-stroked-button (click)="refreshContextViews()">Refresh context</button>
        </div>
        <p class="context-hash">Context hash: {{ contextHash || 'none' }}</p>
      </mat-card>

      <mat-card *ngIf="workspace" class="qa-bar">
        <mat-chip-set>
          <mat-chip [class.ok]="workspace.validation.overall_ready" [class.warn]="!workspace.validation.overall_ready">
            {{ workspace.validation.overall_ready ? 'QA Ready' : 'QA Issues' }}
          </mat-chip>
          <mat-chip>Workflow: {{ workspace.workflow.current_step }}</mat-chip>
          <mat-chip>Status: {{ workspace.instance.status }}</mat-chip>
          <mat-chip [class.warn]="!workspace.instance.is_public">
            {{ workspace.instance.is_public ? 'Public' : 'Internal' }}
          </mat-chip>
          <mat-chip [class.warn]="autosaveStatus !== 'idle'">Autosave: {{ autosaveStatus }}</mat-chip>
        </mat-chip-set>
        <div class="workflow-actions">
          <button mat-stroked-button (click)="workflowAction('start_progress')">Start progress</button>
          <button mat-stroked-button (click)="workflowAction('request_internal_review')">Internal review</button>
          <button mat-stroked-button (click)="workflowAction('request_technical_committee_review')">Technical Committee review</button>
          <button mat-stroked-button (click)="workflowAction('technical_committee_approve')">Technical Committee approve</button>
          <button mat-stroked-button (click)="workflowAction('dffe_clearance_approve')">DFFE clearance</button>
          <button mat-stroked-button (click)="workflowAction('final_signoff')">Final sign-off</button>
          <button mat-stroked-button color="primary" (click)="workflowAction('freeze')">Freeze & snapshot</button>
          <button mat-stroked-button color="warn" (click)="workflowAction('reject')">Reject to draft</button>
        </div>
      </mat-card>

      <div class="workspace-grid" *ngIf="workspace && activeSection; else emptyState">
        <mat-card class="left-nav">
          <mat-card-title>Sections</mat-card-title>
          <mat-list>
            <button
              mat-list-item
              *ngFor="let section of workspace.sections"
              (click)="selectSection(section.section_code)"
              [class.active]="section.section_code === activeSection.section_code"
            >
              <span matListItemTitle>{{ section.section_title }}</span>
              <span matListItemLine>v{{ section.current_version }} - {{ section.updated_by || 'unassigned' }}</span>
            </button>
          </mat-list>
          <mat-divider></mat-divider>
          <div class="helper-actions">
            <button mat-button (click)="generateSectionIiiSkeleton()">Generate Section III skeleton</button>
            <button mat-button (click)="refreshSectionIv()">Refresh Section IV rollup</button>
            <button mat-button (click)="loadDiffAgainstLatestNr7()" [disabled]="!workspace || workspace.instance.report_label !== 'NR8'">
              Diff against latest NR7
            </button>
          </div>
        </mat-card>

        <mat-card class="editor">
          <mat-card-title>{{ activeSection.section_title }}</mat-card-title>
          <mat-card-subtitle>
            {{ activeSection.section_code }} - version {{ activeSection.current_version }}
            <span *ngIf="activeSection.locked_for_editing">(locked)</span>
          </mat-card-subtitle>

          <div class="field-grid" *ngIf="sectionFields().length; else fallbackJsonEditor">
            <ng-container *ngFor="let field of sectionFields()">
              <mat-form-field appearance="outline" class="full-width" *ngIf="isScalarField(field)">
                <mat-label>{{ field.label }}</mat-label>
                <input
                  matInput
                  *ngIf="field.type !== 'textarea' && field.type !== 'date' && field.type !== 'select'"
                  [(ngModel)]="draftResponse[field.key]"
                  (ngModelChange)="onFieldValueChange()"
                />
                <input
                  matInput
                  type="date"
                  *ngIf="field.type === 'date'"
                  [(ngModel)]="draftResponse[field.key]"
                  (ngModelChange)="onFieldValueChange()"
                />
                <mat-select
                  *ngIf="field.type === 'select'"
                  [(ngModel)]="draftResponse[field.key]"
                  (ngModelChange)="onFieldValueChange()"
                >
                  <mat-option *ngFor="let value of (field.allowed_values || [])" [value]="value">{{ value }}</mat-option>
                </mat-select>
                <textarea
                  matInput
                  rows="4"
                  *ngIf="field.type === 'textarea'"
                  [(ngModel)]="draftResponse[field.key]"
                  (ngModelChange)="onFieldValueChange()"
                ></textarea>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width" *ngIf="field.type === 'multivalue'">
                <mat-label>{{ field.label }} (comma separated)</mat-label>
                <input matInput [ngModel]="multivalueAsText(field.key)" (ngModelChange)="setMultivalue(field.key, $event)" />
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width" *ngIf="field.type === 'table'">
                <mat-label>{{ field.label }} (JSON array)</mat-label>
                <textarea
                  matInput
                  rows="6"
                  [ngModel]="tableAsJson(field.key)"
                  (ngModelChange)="setTableJson(field.key, $event)"
                ></textarea>
              </mat-form-field>
            </ng-container>
          </div>

          <ng-template #fallbackJsonEditor>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Section JSON</mat-label>
              <textarea matInput rows="12" [ngModel]="jsonEditorText" (ngModelChange)="setJsonEditor($event)"></textarea>
            </mat-form-field>
          </ng-template>

          <div class="editor-actions">
            <button mat-flat-button color="primary" (click)="saveSection()" [disabled]="activeSection.locked_for_editing">
              {{ suggestionMode ? 'Submit suggestion' : 'Save section' }}
            </button>
            <button mat-stroked-button (click)="reloadActiveSection()">Discard changes</button>
            <button mat-stroked-button (click)="markSectionComplete()" [disabled]="missingRequiredFields().length > 0">Mark section complete</button>
            <button mat-stroked-button (click)="loadOrtValidation()">ORT validation</button>
          </div>

          <mat-divider></mat-divider>

          <div class="narrative-tools">
            <mat-form-field appearance="outline">
              <mat-label>Narrative block</mat-label>
              <mat-select [ngModel]="activeNarrativeBlockKey" (ngModelChange)="selectNarrativeBlock($event)">
                <mat-option *ngFor="let block of narrativeBlocks" [value]="block.block_key">
                  {{ block.title }} (v{{ block.current_version }})
                </mat-option>
              </mat-select>
            </mat-form-field>
            <button mat-stroked-button (click)="saveNarrativeBlock()" [disabled]="!activeNarrativeBlockKey">Save narrative block</button>
            <button mat-stroked-button (click)="openOnlyOffice()" [disabled]="!activeNarrativeBlockKey">Open ONLYOFFICE doc</button>
          </div>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Narrative (plain text helper)</mat-label>
            <textarea matInput rows="6" [(ngModel)]="narrativeEditorText"></textarea>
          </mat-form-field>

          <div class="preview-wrap" [innerHTML]="previewHtml"></div>
          <div class="chart-wrap" *ngFor="let chart of charts.charts">
            <h4>{{ chart.title }}</h4>
            <app-plotly-chart [spec]="chart.spec"></app-plotly-chart>
          </div>
          <div class="ort-box" *ngIf="ortValidation">
            <strong>ORT {{ ortValidation.contract }}</strong>
            <p>Overall valid: {{ ortValidation.overall_valid ? 'yes' : 'no' }}</p>
            <p>Blocking issues: {{ ortValidation.blocking_issues.length }}</p>
          </div>
        </mat-card>

        <mat-card class="side-panel">
          <mat-card-title>Review & QA</mat-card-title>
          <div class="side-actions">
            <button mat-button (click)="refreshHistory()">Refresh history</button>
            <button mat-button (click)="refreshComments()">Refresh comments</button>
            <button mat-button (click)="refreshSuggestions()">Refresh suggestions</button>
          </div>

          <h3>QA findings</h3>
          <div class="qa-item" *ngFor="let item of workspace.validation.qa_items">
            <span class="qa-badge" [class.warn]="item.severity !== 'BLOCKER'" [class.block]="item.severity === 'BLOCKER'">
              {{ item.severity }}
            </span>
            <span>{{ item.section }} - {{ item.message }}</span>
          </div>

          <h3>Comments</h3>
          <div class="comment-new">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Field</mat-label>
              <mat-select [(ngModel)]="newCommentField">
                <mat-option *ngFor="let field of sectionFields()" [value]="field.key">{{ field.label }}</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Comment</mat-label>
              <textarea matInput rows="2" [(ngModel)]="newCommentBody"></textarea>
            </mat-form-field>
            <button mat-stroked-button (click)="addComment()">Add comment thread</button>
          </div>
          <div class="thread" *ngFor="let thread of comments.threads">
            <div class="thread-head">
              <strong>{{ thread.field_name || thread.json_path }}</strong>
              <button mat-button *ngIf="thread.status === 'open'" (click)="setThreadStatus(thread.uuid, 'resolved')">Resolve</button>
            </div>
            <div *ngFor="let comment of thread.comments" class="thread-comment">
              {{ comment.author || 'unknown' }}: {{ comment.body }}
            </div>
          </div>

          <h3>Suggestions</h3>
          <div class="comment-new">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Field to suggest</mat-label>
              <mat-select [(ngModel)]="newSuggestionField">
                <mat-option *ngFor="let field of sectionFields()" [value]="field.key">{{ field.label }}</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Proposed value</mat-label>
              <textarea matInput rows="2" [(ngModel)]="newSuggestionValue"></textarea>
            </mat-form-field>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Rationale</mat-label>
              <textarea matInput rows="2" [(ngModel)]="newSuggestionRationale"></textarea>
            </mat-form-field>
            <button mat-stroked-button (click)="createFieldSuggestion()">Submit field suggestion</button>
          </div>
          <div class="suggestion" *ngFor="let row of suggestions.suggestions">
            <div>{{ row.field_name || 'section patch' }} - v{{ row.base_version }} - {{ row.created_by || 'unknown' }} - {{ row.status }}</div>
            <div class="rationale">{{ row.rationale }}</div>
            <div class="suggest-actions" *ngIf="row.status === 'pending' || row.status === 'proposed'">
              <button mat-stroked-button color="primary" (click)="decideSuggestion(row.uuid, 'accept')">Accept</button>
              <button mat-stroked-button color="warn" (click)="decideSuggestion(row.uuid, 'reject')">Reject</button>
            </div>
          </div>

          <h3>History</h3>
          <div class="history-item" *ngFor="let rev of history.revisions">
            v{{ rev.version }} - {{ rev.author || 'unknown' }} - {{ rev.created_at }}
          </div>
          <p *ngIf="history.diff">Diff keys: {{ history.diff.changed_keys.join(', ') }}</p>
          <h3 *ngIf="changeSummary">Carry-forward change summary</h3>
          <p *ngIf="changeSummary">{{ changeSummary }}</p>
        </mat-card>
      </div>

      <ng-template #emptyState>
        <mat-card>
          <mat-card-title>Select a reporting instance</mat-card-title>
          <mat-card-content>Workspace data will load once an instance is selected.</mat-card-content>
        </mat-card>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .workspace-shell {
        display: grid;
        gap: 1rem;
      }
      .workspace-header {
        border: 1px solid rgba(18, 106, 78, 0.16);
      }
      .header-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }
      .header-grid,
      .create-grid,
      .context-grid {
        margin-top: 0.8rem;
        display: grid;
        gap: 0.8rem;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        align-items: end;
      }
      .context-bar {
        position: sticky;
        top: 0.6rem;
        z-index: 5;
        border: 1px solid rgba(18, 106, 78, 0.2);
        background: linear-gradient(120deg, #f2faf7, #f9fcfb);
      }
      .context-hash {
        margin: 0.25rem 0 0;
        font-size: 0.82rem;
        color: #3f5f53;
      }
      .export-actions {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
      }
      .qa-bar {
        display: grid;
        gap: 0.8rem;
      }
      .workflow-actions {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
      }
      .workspace-grid {
        display: grid;
        grid-template-columns: 260px 1fr 360px;
        gap: 1rem;
        align-items: start;
      }
      .left-nav button.active {
        background: rgba(20, 80, 63, 0.08);
        border-left: 3px solid #14503f;
      }
      .helper-actions {
        display: grid;
        margin-top: 0.6rem;
      }
      .editor,
      .side-panel,
      .left-nav {
        min-height: 560px;
      }
      .field-grid {
        display: grid;
        gap: 0.75rem;
      }
      .full-width {
        width: 100%;
      }
      .editor-actions {
        margin-top: 0.8rem;
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
      }
      .narrative-tools {
        display: flex;
        gap: 0.6rem;
        align-items: end;
        margin-top: 0.9rem;
        flex-wrap: wrap;
      }
      .preview-wrap {
        margin-top: 0.9rem;
        border: 1px solid rgba(15, 80, 58, 0.18);
        border-radius: 8px;
        padding: 0.8rem;
        background: #ffffff;
      }
      .chart-wrap {
        margin-top: 0.9rem;
      }
      .ort-box {
        margin-top: 0.9rem;
        border: 1px solid rgba(15, 80, 58, 0.18);
        border-radius: 8px;
        padding: 0.65rem;
        background: #f7fbf9;
      }
      .side-actions {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
      }
      .qa-item {
        display: flex;
        gap: 0.4rem;
        margin-bottom: 0.35rem;
      }
      .qa-badge {
        border-radius: 999px;
        padding: 0.1rem 0.5rem;
        font-size: 0.72rem;
      }
      .qa-badge.block {
        background: #f3c6c6;
      }
      .qa-badge.warn {
        background: #f5dfb8;
      }
      mat-chip.ok {
        background: #c1e7cf;
      }
      mat-chip.warn {
        background: #f5dfb8;
      }
      .comment-new,
      .thread,
      .suggestion,
      .history-item {
        margin-bottom: 0.6rem;
      }
      .thread-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .thread-comment {
        font-size: 0.88rem;
        margin-top: 0.2rem;
      }
      .rationale {
        font-size: 0.88rem;
        color: #47695a;
      }
      .suggest-actions {
        display: flex;
        gap: 0.4rem;
        margin-top: 0.25rem;
      }
      @media (max-width: 1280px) {
        .workspace-grid {
          grid-template-columns: 1fr;
        }
      }
    `
  ]
})
export class ReportingPageComponent implements OnInit {
  readonly reportService = inject(NationalReportService);
  private readonly downloadRecords = inject(DownloadRecordService);
  private readonly nr7Service = inject(Nr7BuilderService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

  readonly instanceControl = new FormControl<string | null>(null);
  instances: ReportingInstanceSummary[] = [];
  workspace: ReportWorkspaceSummary | null = null;
  activeSection: ReportWorkspaceSection | null = null;
  draftResponse: Record<string, unknown> = {};
  jsonEditorText = '{}';
  suggestionMode = false;
  suggestionRationale = '';
  history: ReportSectionHistory = { section_code: '', current_version: 0, revisions: [], diff: null };
  comments: ReportCommentThreadPayload = { threads: [] };
  suggestions: ReportSuggestionPayload = { suggestions: [] };
  newCommentField = '';
  newCommentBody = '';
  newSuggestionField = '';
  newSuggestionValue = '';
  newSuggestionRationale = '';
  changeSummary = '';

  newReport = {
    label: 'NR8' as 'NR7' | 'NR8',
    periodStart: '',
    periodEnd: '',
    reportTitle: '',
    isPublic: false
  };

  contextFilters: Record<string, string> = {
    report_label: '',
    geography: '',
    disaggregation: '',
    indicator: '',
    programme: ''
  };
  contextHash = '';

  charts: ReportSectionChartsPayload = {
    charts: [],
    context: {},
    context_hash: ''
  };
  previewHtml = '';
  ortValidation: {
    contract: string;
    overall_valid: boolean;
    blocking_issues: Array<Record<string, unknown>>;
    validation: Record<string, unknown>;
  } | null = null;
  narrativeRender: ReportNarrativeRenderPayload = {
    section_code: '',
    raw_html: '',
    rendered_html: '',
    resolved_values_manifest: [],
    context: {},
    context_hash: ''
  };
  narrativeBlocks: Array<{
    uuid: string;
    block_key: string;
    title: string;
    current_version: number;
    current_content_hash: string;
    html_snapshot: string;
    text_snapshot: string;
  }> = [];
  activeNarrativeBlockKey = '';
  narrativeEditorText = '';

  autosaveStatus: 'idle' | 'queued' | 'saving' | 'saved' | 'error' = 'idle';
  private readonly autosaveDebounce$ = new Subject<void>();
  private readonly contextDebounce$ = new Subject<void>();
  private autosaveInFlight = false;
  private pendingAutosave = false;

  ngOnInit(): void {
    this.autosaveDebounce$
      .pipe(debounceTime(1200), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.autosaveSection());

    this.contextDebounce$
      .pipe(debounceTime(400), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.persistContext());

    this.nr7Service
      .listInstances()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (payload) => {
          this.instances = payload.instances;
          if (!this.instanceControl.value && this.instances.length) {
            this.instanceControl.setValue(this.instances[0].uuid);
          }
          this.onInstanceChange();
        },
        error: () => this.show('Unable to load report instances.')
      });
  }

  onInstanceChange(): void {
    const instanceUuid = this.instanceControl.value;
    if (!instanceUuid) {
      return;
    }
    this.reportService.workspace(instanceUuid).subscribe({
      next: (workspace) => {
        this.workspace = workspace;
        this.contextFilters = {
          report_label: String(workspace.context?.filters_json?.['report_label'] || workspace.instance.report_label || ''),
          geography: String(workspace.context?.filters_json?.['geography'] || ''),
          disaggregation: String(workspace.context?.filters_json?.['disaggregation'] || ''),
          indicator: String(workspace.context?.filters_json?.['indicator'] || ''),
          programme: String(workspace.context?.filters_json?.['programme'] || '')
        };
        this.contextHash = workspace.context?.context_hash || '';
        const firstSectionCode = workspace.sections[0]?.section_code;
        if (firstSectionCode) {
          this.selectSection(firstSectionCode);
        }
      },
      error: () => this.show('Failed to load workspace.')
    });
  }

  createNationalReport(): void {
    this.reportService
      .createNationalReport({
        report_label: this.newReport.label,
        reporting_period_start: this.newReport.periodStart || undefined,
        reporting_period_end: this.newReport.periodEnd || undefined,
        is_public: this.newReport.isPublic,
        report_title: this.newReport.reportTitle || undefined
      })
      .subscribe({
        next: (payload) => {
          this.show(`${this.newReport.label} instance created.`);
          this.nr7Service.listInstances().subscribe((rows) => {
            this.instances = rows.instances;
            this.instanceControl.setValue(payload.instance.uuid);
            this.onInstanceChange();
          });
        },
        error: (err) => this.show(err?.error?.detail || 'Unable to create national report.')
      });
  }

  createNr8FromNr7(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    const svc = this.reportService as unknown as { createNr8FromNr7?: (instanceUuid: string) => unknown };
    if (!svc.createNr8FromNr7) {
      this.show('NR8 carry-forward is unavailable in this environment.');
      return;
    }
    this.reportService.createNr8FromNr7(instanceUuid).subscribe({
      next: (payload) => {
        this.show('NR8 draft created from NR7.');
        this.nr7Service.listInstances().subscribe((rows) => {
          this.instances = rows.instances;
          this.instanceControl.setValue(payload.new_instance_uuid);
          this.onInstanceChange();
        });
      },
      error: (err) => this.show(err?.error?.detail || 'Unable to create NR8 from NR7.')
    });
  }

  setContextFilter(key: string, value: string): void {
    this.contextFilters = {
      ...this.contextFilters,
      [key]: String(value || '').trim()
    };
    this.contextDebounce$.next();
  }

  refreshContextViews(): void {
    this.persistContext();
  }

  selectSection(sectionCode: string): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.reportService.section(instanceUuid, sectionCode).subscribe({
      next: (section) => {
        this.activeSection = section;
        this.draftResponse = { ...(section.response_json || {}) };
        this.jsonEditorText = JSON.stringify(this.draftResponse, null, 2);
        this.autosaveStatus = 'idle';
        this.refreshHistory();
        this.refreshComments();
        this.refreshSuggestions();
        this.loadNarrativeBlocks();
        this.refreshContextViews();
      },
      error: () => this.show('Failed to load section.')
    });
  }

  sectionFields(): SectionField[] {
    const schema = this.activeSection?.schema_json as { fields?: unknown[] } | undefined;
    return ((schema?.fields || []) as SectionField[]).filter((field) => !!field.key);
  }

  isScalarField(field: SectionField): boolean {
    return ['text', 'textarea', 'date', 'select'].includes(field.type);
  }

  multivalueAsText(key: string): string {
    const value = this.draftResponse[key];
    return Array.isArray(value) ? value.join(', ') : '';
  }

  setMultivalue(key: string, value: string): void {
    this.draftResponse[key] = value
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    this.syncJsonEditorFromDraft();
    this.queueAutosave();
  }

  tableAsJson(key: string): string {
    const value = this.draftResponse[key];
    return JSON.stringify(Array.isArray(value) ? value : [], null, 2);
  }

  setTableJson(key: string, raw: string): void {
    try {
      const parsed = JSON.parse(raw);
      this.draftResponse[key] = Array.isArray(parsed) ? parsed : [];
      this.syncJsonEditorFromDraft();
      this.queueAutosave();
    } catch {
      // keep editing until valid JSON
    }
  }

  setJsonEditor(raw: string): void {
    this.jsonEditorText = raw;
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        this.draftResponse = parsed;
        this.queueAutosave();
      }
    } catch {
      // ignore invalid json while typing
    }
  }

  onFieldValueChange(): void {
    this.syncJsonEditorFromDraft();
    this.queueAutosave();
  }

  saveSection(): void {
    this.performSave(false);
  }

  reloadActiveSection(): void {
    if (this.activeSection) {
      this.selectSection(this.activeSection.section_code);
    }
  }

  refreshHistory(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      return;
    }
    this.reportService.sectionHistory(instanceUuid, sectionCode).subscribe((history) => (this.history = history));
  }

  refreshComments(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      return;
    }
    this.reportService.comments(instanceUuid, sectionCode).subscribe((rows) => (this.comments = rows));
  }

  refreshSuggestions(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      return;
    }
    this.reportService.suggestions(instanceUuid, sectionCode).subscribe((rows) => (this.suggestions = rows));
  }

  addComment(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    const sectionUuid = this.activeSection?.uuid;
    if (!instanceUuid || !sectionCode || !sectionUuid || !this.newCommentBody) {
      return;
    }
    this.reportService
      .addComment(instanceUuid, sectionCode, {
        json_path: this.newCommentField || 'section',
        field_name: this.newCommentField || undefined,
        object_uuid: sectionUuid,
        body: this.newCommentBody
      })
      .subscribe({
        next: () => {
          this.newCommentBody = '';
          this.refreshComments();
          this.show('Comment added.');
        },
        error: () => this.show('Unable to add comment.')
      });
  }

  createFieldSuggestion(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    const sectionUuid = this.activeSection?.uuid;
    if (!instanceUuid || !sectionCode || !sectionUuid || !this.newSuggestionField) {
      return;
    }
    let proposedValue: unknown = this.newSuggestionValue;
    try {
      proposedValue = JSON.parse(this.newSuggestionValue);
    } catch {
      proposedValue = this.newSuggestionValue;
    }
    const fieldName = this.newSuggestionField.trim();
    const patch: Record<string, unknown> = { [fieldName]: proposedValue };
    this.reportService
      .createSuggestion(instanceUuid, sectionCode, {
        base_version: this.activeSection?.current_version || 1,
        object_uuid: sectionUuid,
        field_name: fieldName,
        patch_json: patch,
        diff_patch: patch,
        old_value_hash: this.simpleHash(JSON.stringify(this.activeSection?.response_json?.[fieldName] ?? null)),
        proposed_value: proposedValue,
        rationale: this.newSuggestionRationale || 'Field suggestion'
      })
      .subscribe({
        next: () => {
          this.newSuggestionValue = '';
          this.newSuggestionRationale = '';
          this.refreshSuggestions();
          this.show('Suggestion submitted.');
        },
        error: (err) => this.show(err?.error?.detail || 'Unable to submit suggestion.')
      });
  }

  markSectionComplete(): void {
    if (!this.activeSection) {
      return;
    }
    if (this.missingRequiredFields().length > 0) {
      this.show('Required fields are still missing.');
      return;
    }
    this.workflowAction('section_complete', this.activeSection.section_code);
  }

  loadOrtValidation(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    const svc = this.reportService as unknown as { ortValidation?: (instanceUuid: string) => unknown };
    if (!svc.ortValidation) {
      return;
    }
    this.reportService.ortValidation(instanceUuid).subscribe({
      next: (payload) => {
        this.ortValidation = payload;
      },
      error: (err) => this.show(err?.error?.detail || 'ORT validation failed.')
    });
  }

  loadDiffAgainstLatestNr7(): void {
    const current = this.workspace;
    if (!current) {
      return;
    }
    const baseline = this.instances.find(
      (row) => row.uuid !== current.instance.uuid && (row.report_label || row.cycle_code) === 'NR7'
    );
    if (!baseline) {
      this.show('No baseline NR7 available for diff.');
      return;
    }
    const svc = this.reportService as unknown as { diff?: (instanceUuid: string, fromInstanceUuid: string) => unknown };
    if (!svc.diff) {
      this.show('Diff endpoint unavailable.');
      return;
    }
    this.reportService.diff(current.instance.uuid, baseline.uuid).subscribe({
      next: (payload) => {
        this.changeSummary = payload.change_summary || '';
      },
      error: (err) => this.show(err?.error?.detail || 'Unable to compute diff.')
    });
  }

  selectNarrativeBlock(blockKey: string): void {
    this.activeNarrativeBlockKey = blockKey;
    const row = this.narrativeBlocks.find((item) => item.block_key === blockKey);
    this.narrativeEditorText = row?.text_snapshot || '';
  }

  loadNarrativeBlocks(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      this.narrativeBlocks = [];
      this.activeNarrativeBlockKey = '';
      this.narrativeEditorText = '';
      return;
    }
    const svc = this.reportService as unknown as { narrativeBlocks?: (instanceUuid: string, sectionCode: string) => unknown };
    if (!svc.narrativeBlocks) {
      this.narrativeBlocks = [];
      this.activeNarrativeBlockKey = '';
      this.narrativeEditorText = '';
      return;
    }
    this.reportService.narrativeBlocks(instanceUuid, sectionCode).subscribe({
      next: (payload) => {
        this.narrativeBlocks = (payload.blocks || []).map((row) => {
          const item = row as Record<string, unknown>;
          return {
            uuid: String(item['uuid'] || ''),
            block_key: String(item['block_key'] || 'main'),
            title: String(item['title'] || 'Main narrative'),
            current_version: Number(item['current_version'] || 1),
            current_content_hash: String(item['current_content_hash'] || ''),
            html_snapshot: String(item['html_snapshot'] || ''),
            text_snapshot: String(item['text_snapshot'] || '')
          };
        });
        if (this.narrativeBlocks.length > 0) {
          const selected = this.narrativeBlocks[0];
          this.activeNarrativeBlockKey = selected.block_key;
          this.narrativeEditorText = selected.text_snapshot || '';
        }
      },
      error: () => {
        this.narrativeBlocks = [];
      }
    });
  }

  saveNarrativeBlock(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode || !this.activeNarrativeBlockKey) {
      return;
    }
    const svc = this.reportService as unknown as { saveNarrativeBlock?: (instanceUuid: string, sectionCode: string, payload: unknown) => unknown };
    if (!svc.saveNarrativeBlock) {
      return;
    }
    this.reportService
      .saveNarrativeBlock(instanceUuid, sectionCode, {
        block_key: this.activeNarrativeBlockKey,
        content_text: this.narrativeEditorText
      })
      .subscribe({
        next: () => {
          this.show('Narrative block saved.');
          this.loadNarrativeBlocks();
          this.refreshContextViews();
        },
        error: (err) => this.show(err?.error?.detail || 'Unable to save narrative block.')
      });
  }

  openOnlyOffice(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode || !this.activeNarrativeBlockKey) {
      return;
    }
    const url = this.reportService.narrativeDocumentUrl(instanceUuid, sectionCode, this.activeNarrativeBlockKey);
    window.open(url, '_blank', 'noopener');
  }

  setThreadStatus(threadUuid: string, statusValue: string): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      return;
    }
    this.reportService.updateCommentThreadStatus(instanceUuid, sectionCode, threadUuid, statusValue).subscribe({
      next: () => this.refreshComments(),
      error: () => this.show('Unable to update thread status.')
    });
  }

  decideSuggestion(suggestionUuid: string, action: 'accept' | 'reject'): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      return;
    }
    this.reportService.decideSuggestion(instanceUuid, sectionCode, suggestionUuid, action).subscribe({
      next: () => {
        this.refreshSuggestions();
        this.onInstanceChange();
      },
      error: () => this.show('Unable to decide suggestion.')
    });
  }

  workflowAction(action: string, sectionCode = ''): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.reportService.workflowAction(instanceUuid, action, '', sectionCode).subscribe({
      next: () => this.onInstanceChange(),
      error: (err) => this.show(err?.error?.detail || 'Workflow action failed.')
    });
  }

  generateSectionIiiSkeleton(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.reportService.generateSectionIiiSkeleton(instanceUuid).subscribe({
      next: () => {
        this.show('Section III skeleton generated.');
        this.onInstanceChange();
      },
      error: () => this.show('Unable to generate section III skeleton.')
    });
  }

  refreshSectionIv(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.reportService.refreshSectionIvRollup(instanceUuid).subscribe({
      next: () => {
        this.show('Section IV rollup refreshed from current section inputs.');
        this.onInstanceChange();
      },
      error: () => this.show('Unable to refresh section IV rollup.')
    });
  }

  generateDossier(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.reportService.generateDossier(instanceUuid).subscribe({
      next: () => {
        this.show('Dossier generated.');
        this.onInstanceChange();
      },
      error: (err) => this.show(err?.error?.detail || 'Unable to generate dossier.')
    });
  }

  createReportExport(format: 'pdf' | 'docx' | 'json'): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.downloadRecords
      .create({
        record_type: 'report_export',
        object_type: 'reporting_instance',
        object_uuid: instanceUuid,
        query_snapshot: {
          format,
          context_filters: this.contextFilters
        }
      })
      .subscribe({
        next: (payload) => {
          this.router.navigate(['/downloads', payload.uuid]);
        },
        error: (err) => this.show(err?.error?.detail || 'Unable to create download record.')
      });
  }

  missingRequiredFields(): string[] {
    const missing: string[] = [];
    this.sectionFields().forEach((field) => {
      if (!field.required) {
        return;
      }
      const value = this.draftResponse[field.key];
      if (value === null || value === undefined || value === '') {
        missing.push(field.label || field.key);
        return;
      }
      if (Array.isArray(value) && value.length === 0) {
        missing.push(field.label || field.key);
      }
    });
    return missing;
  }

  private queueAutosave(): void {
    if (this.suggestionMode || !this.activeSection || this.activeSection.locked_for_editing) {
      return;
    }
    this.autosaveStatus = 'queued';
    this.autosaveDebounce$.next();
  }

  private autosaveSection(): void {
    if (this.autosaveInFlight) {
      this.pendingAutosave = true;
      return;
    }
    if (this.missingRequiredFields().length > 0) {
      this.autosaveStatus = 'idle';
      return;
    }
    this.performSave(true);
  }

  private performSave(isAutosave: boolean): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const section = this.activeSection;
    if (!instanceUuid || !section) {
      return;
    }
    const payload: {
      response_json: Record<string, unknown>;
      base_version: number;
      suggestion_mode?: boolean;
      patch_json?: Record<string, unknown>;
      rationale?: string;
    } = {
      response_json: this.draftResponse,
      base_version: section.current_version
    };
    if (this.suggestionMode) {
      payload.suggestion_mode = true;
      payload.patch_json = this.diffPatch(section.response_json || {}, this.draftResponse);
      payload.rationale = this.suggestionRationale;
    }
    this.autosaveInFlight = true;
    this.autosaveStatus = isAutosave ? 'saving' : this.autosaveStatus;
    this.reportService.saveSection(instanceUuid, section.section_code, payload).subscribe({
      next: () => {
        this.autosaveInFlight = false;
        this.autosaveStatus = isAutosave ? 'saved' : 'idle';
        if (!isAutosave) {
          this.show(this.suggestionMode ? 'Suggestion submitted.' : 'Section saved.');
        }
        this.onInstanceChange();
        if (this.pendingAutosave) {
          this.pendingAutosave = false;
          this.autosaveDebounce$.next();
        }
      },
      error: (err) => {
        this.autosaveInFlight = false;
        this.autosaveStatus = 'error';
        this.show(err?.error?.detail || 'Unable to save section.');
      }
    });
  }

  private persistContext(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    const sectionCode = this.activeSection?.section_code;
    if (!instanceUuid || !sectionCode) {
      return;
    }
    const svc = this.reportService as unknown as {
      saveContext?: (instanceUuid: string, context: Record<string, string>) => unknown;
    };
    if (!svc.saveContext) {
      this.loadContextViews(instanceUuid, sectionCode);
      return;
    }
    this.reportService.saveContext(instanceUuid, this.contextFilters).subscribe({
      next: (payload: ReportContextPayload) => {
        this.contextHash = payload.context_hash;
        this.loadContextViews(instanceUuid, sectionCode);
      },
      error: () => this.show('Unable to save context filters.')
    });
  }

  private loadContextViews(instanceUuid: string, sectionCode: string): void {
    const svc = this.reportService as unknown as {
      sectionPreview?: (instanceUuid: string, sectionCode: string, context?: Record<string, string>) => unknown;
      sectionCharts?: (instanceUuid: string, sectionCode: string, context?: Record<string, string>) => unknown;
      renderNarrative?: (instanceUuid: string, sectionCode: string, context?: Record<string, string>) => unknown;
    };
    const preview$ = svc.sectionPreview
      ? this.reportService.sectionPreview(instanceUuid, sectionCode, this.contextFilters).pipe(
          catchError(() => of({ section_code: sectionCode, html: '', resolved_values_manifest: [], context_hash: '' }))
        )
      : of({ section_code: sectionCode, html: '', resolved_values_manifest: [], context_hash: '' });
    const charts$ = svc.sectionCharts
      ? this.reportService.sectionCharts(instanceUuid, sectionCode, this.contextFilters).pipe(
          catchError(() => of({ charts: [], context: this.contextFilters, context_hash: '' }))
        )
      : of({ charts: [], context: this.contextFilters, context_hash: '' });
    const narrative$ = svc.renderNarrative
      ? this.reportService.renderNarrative(instanceUuid, sectionCode, this.contextFilters).pipe(
          catchError(() =>
            of({
              section_code: sectionCode,
              raw_html: '',
              rendered_html: '',
              resolved_values_manifest: [],
              context: this.contextFilters,
              context_hash: ''
            })
          )
        )
      : of({
          section_code: sectionCode,
          raw_html: '',
          rendered_html: '',
          resolved_values_manifest: [],
          context: this.contextFilters,
          context_hash: ''
        });
    forkJoin({ preview: preview$, charts: charts$, narrative: narrative$ }).subscribe(({ preview, charts, narrative }) => {
      this.previewHtml = preview.html || '';
      this.contextHash = preview.context_hash || this.contextHash;
      this.charts = charts as ReportSectionChartsPayload;
      this.narrativeRender = narrative as ReportNarrativeRenderPayload;
    });
  }

  private syncJsonEditorFromDraft(): void {
    this.jsonEditorText = JSON.stringify(this.draftResponse, null, 2);
  }

  private diffPatch(before: Record<string, unknown>, after: Record<string, unknown>): Record<string, unknown> {
    const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]);
    const patch: Record<string, unknown> = {};
    keys.forEach((key) => {
      if (JSON.stringify(before?.[key]) !== JSON.stringify(after?.[key])) {
        patch[key] = after[key];
      }
    });
    return patch;
  }

  private simpleHash(raw: string): string {
    let hash = 0;
    for (let i = 0; i < raw.length; i += 1) {
      hash = (hash << 5) - hash + raw.charCodeAt(i);
      hash |= 0;
    }
    return `h${Math.abs(hash)}`;
  }

  private show(message: string): void {
    this.snackBar.open(message, 'Close', { duration: 2500 });
  }
}
