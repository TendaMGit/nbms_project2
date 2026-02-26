import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

import {
  ReportingInstanceSummary,
  TemplatePack,
  TemplatePackSection,
  TemplatePackValidationSummary
} from '../models/api.models';
import { Nr7BuilderService } from '../services/nr7-builder.service';
import { TemplatePackService } from '../services/template-pack.service';
import { DownloadRecordService } from '../services/download-record.service';

type FieldType = 'text' | 'textarea' | 'date' | 'multivalue' | 'questionnaire';

interface SectionField {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  question_catalog?: Array<{ code: string; title: string }>;
  allowed_values?: string[];
}

interface QuestionRow {
  question_code: string;
  question_title: string;
  response: string;
  notes: string;
  linked_indicator_codes: string[];
  linked_programme_codes: string[];
  linked_evidence_uuids: string[];
}

@Component({
  selector: 'app-template-packs-page',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatSelectModule,
    MatSnackBarModule
  ],
  template: `
    <div class="pack-builder">
      <mat-card class="header">
        <mat-card-title>MEA Template Packs</mat-card-title>
        <mat-card-subtitle>Runtime editor and QA for CBD, Ramsar, CITES, and CMS packs.</mat-card-subtitle>
        <div class="selectors">
          <mat-form-field appearance="outline">
            <mat-label>Template pack</mat-label>
            <mat-select [(ngModel)]="selectedPackCode" (selectionChange)="reloadWorkspace()">
              <mat-option *ngFor="let pack of packs" [value]="pack.code">
                {{ pack.title }} ({{ pack.code }})
              </mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Reporting instance</mat-label>
            <mat-select [(ngModel)]="selectedInstanceUuid" (selectionChange)="reloadWorkspace()">
              <mat-option *ngFor="let instance of instances" [value]="instance.uuid">
                {{ instance.cycle_code }} / {{ instance.version_label }}
              </mat-option>
            </mat-select>
          </mat-form-field>
          <div class="actions">
            <button mat-flat-button color="primary" (click)="saveActiveSection()" [disabled]="!activeSection">
              Save section
            </button>
            <button mat-stroked-button (click)="runValidation()" [disabled]="!selectedInstanceUuid || !selectedPackCode">
              Run QA
            </button>
            <button mat-stroked-button *ngIf="selectedPackCode && selectedInstanceUuid" (click)="createPackExport('template_pack_pdf')">
              Export PDF
            </button>
            <button mat-stroked-button *ngIf="selectedPackCode && selectedInstanceUuid" (click)="createPackExport('template_pack_export_json')">
              Export JSON
            </button>
          </div>
        </div>
      </mat-card>

      <div class="workspace" *ngIf="sections.length; else emptyState">
        <mat-card class="sections">
          <mat-card-title>Sections</mat-card-title>
          <mat-list>
            <button
              mat-list-item
              *ngFor="let section of sections"
              (click)="setActiveSection(section.code)"
              [class.active]="section.code === activeSectionCode"
            >
              <span matListItemTitle>{{ section.title }}</span>
              <span matListItemLine>{{ section.code }}</span>
            </button>
          </mat-list>
        </mat-card>

        <mat-card class="editor" *ngIf="activeSection">
          <mat-card-title>{{ activeSection.title }}</mat-card-title>
          <mat-card-subtitle>{{ activeSection.code }}</mat-card-subtitle>

          <div class="field-grid">
            <ng-container *ngFor="let field of sectionFields(activeSection)">
              <div *ngIf="field.type === 'text' || field.type === 'date'">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>{{ field.label }}</mat-label>
                  <input
                    matInput
                    [type]="field.type === 'date' ? 'date' : 'text'"
                    [ngModel]="fieldValue(activeSection.code, field.key)"
                    (ngModelChange)="setFieldValue(activeSection.code, field.key, $event)"
                  />
                </mat-form-field>
              </div>

              <div *ngIf="field.type === 'textarea'">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>{{ field.label }}</mat-label>
                  <textarea
                    matInput
                    rows="4"
                    [ngModel]="fieldValue(activeSection.code, field.key)"
                    (ngModelChange)="setFieldValue(activeSection.code, field.key, $event)"
                  ></textarea>
                </mat-form-field>
              </div>

              <div *ngIf="field.type === 'multivalue'">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>{{ field.label }} (comma separated)</mat-label>
                  <input
                    matInput
                    [ngModel]="multivalueText(activeSection.code, field.key)"
                    (ngModelChange)="setMultivalueField(activeSection.code, field.key, $event)"
                  />
                </mat-form-field>
              </div>
            </ng-container>
          </div>

          <div
            class="questionnaire"
            *ngIf="questionnaireField(activeSection) as questionnaire"
          >
            <h3>Implementation Questions</h3>
            <p class="helper">Link indicators/programmes/evidence for each response where applicable.</p>
            <table>
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Response</th>
                  <th>Notes</th>
                  <th>Indicators</th>
                  <th>Programmes</th>
                  <th>Evidence UUIDs</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let row of questionnaireRows(activeSection.code, questionnaire.key); let idx = index">
                  <td>{{ row.question_code }} - {{ row.question_title }}</td>
                  <td>
                    <mat-form-field appearance="outline">
                      <mat-select
                        [ngModel]="row.response"
                        (ngModelChange)="setQuestionRowField(activeSection.code, questionnaire.key, idx, 'response', $event)"
                      >
                        <mat-option *ngFor="let option of (questionnaire.allowed_values || [])" [value]="option">
                          {{ option }}
                        </mat-option>
                      </mat-select>
                    </mat-form-field>
                  </td>
                  <td>
                    <mat-form-field appearance="outline">
                      <input
                        matInput
                        [ngModel]="row.notes"
                        (ngModelChange)="setQuestionRowField(activeSection.code, questionnaire.key, idx, 'notes', $event)"
                      />
                    </mat-form-field>
                  </td>
                  <td>
                    <mat-form-field appearance="outline">
                      <input
                        matInput
                        [ngModel]="listToText(row.linked_indicator_codes)"
                        (ngModelChange)="setQuestionRowList(activeSection.code, questionnaire.key, idx, 'linked_indicator_codes', $event)"
                      />
                    </mat-form-field>
                  </td>
                  <td>
                    <mat-form-field appearance="outline">
                      <input
                        matInput
                        [ngModel]="listToText(row.linked_programme_codes)"
                        (ngModelChange)="setQuestionRowList(activeSection.code, questionnaire.key, idx, 'linked_programme_codes', $event)"
                      />
                    </mat-form-field>
                  </td>
                  <td>
                    <mat-form-field appearance="outline">
                      <input
                        matInput
                        [ngModel]="listToText(row.linked_evidence_uuids)"
                        (ngModelChange)="setQuestionRowList(activeSection.code, questionnaire.key, idx, 'linked_evidence_uuids', $event)"
                      />
                    </mat-form-field>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </mat-card>

        <mat-card class="qa">
          <mat-card-title>QA Readiness</mat-card-title>
          <div class="qa-state" [class.ready]="validation?.overall_ready" [class.blocked]="validation && !validation.overall_ready">
            <mat-icon>{{ validation?.overall_ready ? 'check_circle' : 'warning' }}</mat-icon>
            <span>{{ validation?.overall_ready ? 'Ready for export' : 'Action required before export' }}</span>
          </div>
          <mat-chip-set *ngIf="validation">
            <mat-chip *ngFor="let row of validation.sections">
              {{ row.code }} {{ row.completion }}%
            </mat-chip>
          </mat-chip-set>
          <div class="qa-items" *ngIf="validation?.qa_items?.length">
            <div *ngFor="let item of validation?.qa_items" [class.blocker]="item.severity === 'BLOCKER'">
              [{{ item.severity }}] {{ item.section }} - {{ item.message }}
            </div>
          </div>
          <div *ngIf="!validation">Run QA to see readiness and reference checks.</div>
        </mat-card>
      </div>

      <ng-template #emptyState>
        <mat-card>
          <mat-card-title>Open a template workspace</mat-card-title>
          <mat-card-content>Select a template pack and reporting instance to begin editing.</mat-card-content>
        </mat-card>
      </ng-template>
    </div>
  `,
  styles: `
    .pack-builder {
      display: grid;
      gap: 1rem;
    }
    .selectors {
      margin-top: 0.8rem;
      display: grid;
      gap: 0.8rem;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      align-items: end;
    }
    .actions {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
    }
    .workspace {
      display: grid;
      grid-template-columns: 260px 1fr 360px;
      gap: 1rem;
      align-items: start;
    }
    .sections button.active {
      background: rgba(20, 80, 63, 0.08);
      border-left: 3px solid #14503f;
    }
    .field-grid {
      display: grid;
      gap: 0.8rem;
    }
    .full-width {
      width: 100%;
    }
    .questionnaire table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.6rem;
    }
    .questionnaire th,
    .questionnaire td {
      border: 1px solid #d6e4dc;
      padding: 0.4rem;
      vertical-align: top;
    }
    .questionnaire th {
      background: #eef6f1;
      text-align: left;
    }
    .qa-state {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      margin-bottom: 0.6rem;
    }
    .qa-state.ready {
      color: #1d7a3d;
    }
    .qa-state.blocked {
      color: #9b2b1c;
    }
    .qa-items {
      margin-top: 0.8rem;
      display: grid;
      gap: 0.35rem;
      font-size: 0.86rem;
    }
    .qa-items .blocker {
      color: #9b2b1c;
    }
    .helper {
      color: #47695a;
      margin: 0 0 0.5rem;
    }
    @media (max-width: 1200px) {
      .workspace {
        grid-template-columns: 1fr;
      }
    }
  `
})
export class TemplatePacksPageComponent implements OnInit {
  readonly templatePackService = inject(TemplatePackService);
  private readonly downloadRecords = inject(DownloadRecordService);
  private readonly nr7Service = inject(Nr7BuilderService);
  private readonly snackbar = inject(MatSnackBar);
  private readonly router = inject(Router);

  packs: TemplatePack[] = [];
  instances: ReportingInstanceSummary[] = [];
  sections: TemplatePackSection[] = [];
  responsesBySection: Record<string, Record<string, unknown>> = {};
  validation: TemplatePackValidationSummary | null = null;

  selectedPackCode = '';
  selectedInstanceUuid = '';
  activeSectionCode = '';

  ngOnInit(): void {
    this.templatePackService.list().subscribe((payload) => {
      this.packs = payload.packs;
      if (!this.selectedPackCode && this.packs.length) {
        this.selectedPackCode = this.packs[0].code;
      }
      this.reloadWorkspace();
    });
    this.nr7Service.listInstances().subscribe((rows) => {
      this.instances = rows.instances;
      if (!this.selectedInstanceUuid && this.instances.length) {
        this.selectedInstanceUuid = this.instances[0].uuid;
      }
      this.reloadWorkspace();
    });
  }

  get activeSection(): TemplatePackSection | null {
    return this.sections.find((item) => item.code === this.activeSectionCode) ?? null;
  }

  reloadWorkspace(): void {
    if (!this.selectedPackCode || !this.selectedInstanceUuid) {
      return;
    }
    this.templatePackService.sections(this.selectedPackCode).subscribe((payload) => {
      this.sections = payload.sections;
      if (!this.sections.length) {
        this.activeSectionCode = '';
        this.responsesBySection = {};
        return;
      }
      if (!this.activeSectionCode || !this.sections.some((item) => item.code === this.activeSectionCode)) {
        this.activeSectionCode = this.sections[0].code;
      }
      this.templatePackService.responses(this.selectedPackCode, this.selectedInstanceUuid).subscribe((responsePayload) => {
        this.responsesBySection = {};
        for (const row of responsePayload.responses) {
          this.responsesBySection[row.section_code] = { ...(row.response_json || {}) };
        }
      });
    });
    this.validation = null;
  }

  setActiveSection(code: string): void {
    this.activeSectionCode = code;
  }

  sectionFields(section: TemplatePackSection): SectionField[] {
    const schema = section.schema_json as { fields?: unknown[] };
    return (schema.fields || [])
      .map((item) => item as SectionField)
      .filter((item) => Boolean(item.key) && Boolean(item.type));
  }

  fieldValue(sectionCode: string, key: string): any {
    return this.ensureSectionResponse(sectionCode)[key] ?? '';
  }

  setFieldValue(sectionCode: string, key: string, value: any): void {
    const response = this.ensureSectionResponse(sectionCode);
    response[key] = value;
  }

  multivalueText(sectionCode: string, key: string): string {
    const value = this.fieldValue(sectionCode, key);
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return String(value || '');
  }

  setMultivalueField(sectionCode: string, key: string, text: string): void {
    const response = this.ensureSectionResponse(sectionCode);
    response[key] = text
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  questionnaireField(section: TemplatePackSection): SectionField | null {
    return this.sectionFields(section).find((item) => item.type === 'questionnaire') ?? null;
  }

  questionnaireRows(sectionCode: string, key: string): QuestionRow[] {
    const response = this.ensureSectionResponse(sectionCode);
    if (!Array.isArray(response[key])) {
      response[key] = [];
    }
    return response[key] as QuestionRow[];
  }

  setQuestionRowField(sectionCode: string, key: string, index: number, fieldKey: string, value: any): void {
    const rows = this.questionnaireRows(sectionCode, key);
    rows[index] = { ...rows[index], [fieldKey]: value };
  }

  setQuestionRowList(sectionCode: string, key: string, index: number, fieldKey: string, text: string): void {
    const rows = this.questionnaireRows(sectionCode, key);
    rows[index] = {
      ...rows[index],
      [fieldKey]: text
        .split(',')
        .map((item) => item.trim())
        .filter((item) => item.length > 0)
    };
  }

  listToText(value: unknown): string {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return '';
  }

  saveActiveSection(): void {
    if (!this.activeSection || !this.selectedPackCode || !this.selectedInstanceUuid) {
      return;
    }
    const responseJson = this.ensureSectionResponse(this.activeSection.code);
    this.templatePackService
      .saveResponse(this.selectedPackCode, this.selectedInstanceUuid, this.activeSection.code, responseJson)
      .subscribe(() => {
        this.snackbar.open('Section saved.', 'Close', { duration: 2000 });
      });
  }

  runValidation(): void {
    if (!this.selectedPackCode || !this.selectedInstanceUuid) {
      return;
    }
    this.templatePackService.validate(this.selectedPackCode, this.selectedInstanceUuid).subscribe((payload) => {
      this.validation = payload;
      });
  }

  createPackExport(kind: 'template_pack_pdf' | 'template_pack_export_json'): void {
    if (!this.selectedPackCode || !this.selectedInstanceUuid) {
      return;
    }
    this.downloadRecords
      .create({
        record_type: 'custom_bundle',
        object_type: 'template_pack',
        query_snapshot: {
          kind,
          pack_code: this.selectedPackCode,
          instance_uuid: this.selectedInstanceUuid
        }
      })
      .subscribe({
        next: (payload) => {
          this.router.navigate(['/downloads', payload.uuid]);
        },
        error: (error) => {
          this.snackbar.open(error?.error?.detail || 'Unable to create template pack export record.', 'Close', {
            duration: 4500
          });
        }
      });
  }

  private ensureSectionResponse(sectionCode: string): Record<string, unknown> {
    if (!this.responsesBySection[sectionCode]) {
      this.responsesBySection[sectionCode] = {};
      const section = this.sections.find((item) => item.code === sectionCode);
      const fields = section ? this.sectionFields(section) : [];
      for (const field of fields) {
        if (!field.key) {
          continue;
        }
        if (field.type === 'multivalue') {
          this.responsesBySection[sectionCode][field.key] = [];
        } else if (field.type === 'questionnaire') {
          this.responsesBySection[sectionCode][field.key] = (field.question_catalog || []).map((question) => ({
            question_code: question.code,
            question_title: question.title,
            response: '',
            notes: '',
            linked_indicator_codes: [],
            linked_programme_codes: [],
            linked_evidence_uuids: []
          })) as QuestionRow[];
        } else {
          this.responsesBySection[sectionCode][field.key] = '';
        }
      }
    }
    return this.responsesBySection[sectionCode];
  }
}
