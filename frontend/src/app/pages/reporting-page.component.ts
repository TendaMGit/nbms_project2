import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import {
  ReportCommentThreadPayload,
  ReportSectionHistory,
  ReportSuggestionPayload,
  ReportWorkspaceSection,
  ReportWorkspaceSummary,
  ReportingInstanceSummary
} from '../models/api.models';
import { HelpTooltipComponent } from '../components/help-tooltip.component';
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
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    HelpTooltipComponent
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
            <a mat-stroked-button [href]="reportService.exportPdfUrl(workspace.instance.uuid)" target="_blank" rel="noopener">Export PDF</a>
            <a mat-stroked-button [href]="reportService.exportDocxUrl(workspace.instance.uuid)" target="_blank" rel="noopener">Export DOCX</a>
            <a mat-stroked-button [href]="reportService.exportJsonUrl(workspace.instance.uuid)" target="_blank" rel="noopener">Export JSON</a>
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
        </mat-chip-set>
        <div class="workflow-actions">
          <button mat-stroked-button (click)="workflowAction('submit')">Submit</button>
          <button mat-stroked-button (click)="workflowAction('technical_approve')">Technical approve</button>
          <button mat-stroked-button (click)="workflowAction('consolidate')">Secretariat consolidate</button>
          <button mat-stroked-button color="primary" (click)="workflowAction('publishing_approve')">Publishing authority approve</button>
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
              <span matListItemLine>v{{ section.current_version }} • {{ section.updated_by || 'unassigned' }}</span>
            </button>
          </mat-list>
          <mat-divider></mat-divider>
          <div class="helper-actions">
            <button mat-button (click)="generateSectionIiiSkeleton()">Generate Section III skeleton</button>
            <button mat-button (click)="recomputeSectionIv()">Recompute Section IV rollup</button>
          </div>
        </mat-card>

        <mat-card class="editor">
          <mat-card-title>{{ activeSection.section_title }}</mat-card-title>
          <mat-card-subtitle>
            {{ activeSection.section_code }} • version {{ activeSection.current_version }}
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
                />
                <input matInput type="date" *ngIf="field.type === 'date'" [(ngModel)]="draftResponse[field.key]" />
                <mat-select *ngIf="field.type === 'select'" [(ngModel)]="draftResponse[field.key]">
                  <mat-option *ngFor="let value of (field.allowed_values || [])" [value]="value">{{ value }}</mat-option>
                </mat-select>
                <textarea matInput rows="4" *ngIf="field.type === 'textarea'" [(ngModel)]="draftResponse[field.key]"></textarea>
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
            <button mat-stroked-button (click)="workflowAction('section_approve', activeSection.section_code)">Approve section</button>
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
              <mat-label>JSON path (e.g. target_progress_rows[0].actions_taken)</mat-label>
              <input matInput [(ngModel)]="newCommentPath" />
            </mat-form-field>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Comment</mat-label>
              <textarea matInput rows="2" [(ngModel)]="newCommentBody"></textarea>
            </mat-form-field>
            <button mat-stroked-button (click)="addComment()">Add comment thread</button>
          </div>
          <div class="thread" *ngFor="let thread of comments.threads">
            <div class="thread-head">
              <strong>{{ thread.json_path }}</strong>
              <button mat-button *ngIf="thread.status === 'open'" (click)="setThreadStatus(thread.uuid, 'resolved')">Resolve</button>
            </div>
            <div *ngFor="let comment of thread.comments" class="thread-comment">
              {{ comment.author || 'unknown' }}: {{ comment.body }}
            </div>
          </div>

          <h3>Suggestions</h3>
          <div class="suggestion" *ngFor="let row of suggestions.suggestions">
            <div>v{{ row.base_version }} • {{ row.created_by || 'unknown' }} • {{ row.status }}</div>
            <div class="rationale">{{ row.rationale }}</div>
            <div class="suggest-actions" *ngIf="row.status === 'pending'">
              <button mat-stroked-button color="primary" (click)="decideSuggestion(row.uuid, 'accept')">Accept</button>
              <button mat-stroked-button color="warn" (click)="decideSuggestion(row.uuid, 'reject')">Reject</button>
            </div>
          </div>

          <h3>History</h3>
          <div class="history-item" *ngFor="let rev of history.revisions">
            v{{ rev.version }} • {{ rev.author || 'unknown' }} • {{ rev.created_at }}
          </div>
          <p *ngIf="history.diff">Diff keys: {{ history.diff.changed_keys.join(', ') }}</p>
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
      .header-grid {
        margin-top: 0.8rem;
        display: grid;
        gap: 0.8rem;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        align-items: end;
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
  private readonly nr7Service = inject(Nr7BuilderService);
  private readonly snackBar = inject(MatSnackBar);

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
  newCommentPath = '';
  newCommentBody = '';

  ngOnInit(): void {
    this.nr7Service.listInstances().subscribe((payload) => {
      this.instances = payload.instances;
      if (!this.instanceControl.value && this.instances.length) {
        this.instanceControl.setValue(this.instances[0].uuid);
      }
      this.onInstanceChange();
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
        const firstSectionCode = workspace.sections[0]?.section_code;
        if (firstSectionCode) {
          this.selectSection(firstSectionCode);
        }
      },
      error: () => this.show('Failed to load workspace.')
    });
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
        this.refreshHistory();
        this.refreshComments();
        this.refreshSuggestions();
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
      }
    } catch {
      // ignore invalid json while typing
    }
  }

  saveSection(): void {
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
    this.reportService.saveSection(instanceUuid, section.section_code, payload).subscribe({
      next: () => {
        this.show(this.suggestionMode ? 'Suggestion submitted.' : 'Section saved.');
        this.onInstanceChange();
      },
      error: (err) => this.show(err?.error?.detail || 'Unable to save section.')
    });
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
    if (!instanceUuid || !sectionCode || !this.newCommentPath || !this.newCommentBody) {
      return;
    }
    this.reportService
      .addComment(instanceUuid, sectionCode, {
        json_path: this.newCommentPath,
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

  recomputeSectionIv(): void {
    const instanceUuid = this.workspace?.instance.uuid;
    if (!instanceUuid) {
      return;
    }
    this.reportService.recomputeSectionIvRollup(instanceUuid).subscribe({
      next: () => {
        this.show('Section IV rollup recomputed.');
        this.onInstanceChange();
      },
      error: () => this.show('Unable to recompute section IV rollup.')
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

  private show(message: string): void {
    this.snackBar.open(message, 'Close', { duration: 2500 });
  }
}
