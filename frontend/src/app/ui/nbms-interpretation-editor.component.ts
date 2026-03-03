import { AsyncPipe, DatePipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  UntypedFormArray,
  UntypedFormBuilder,
  UntypedFormGroup,
  ReactiveFormsModule
} from '@angular/forms';
import { RouterLink } from '@angular/router';
import { BehaviorSubject, combineLatest, debounceTime, filter, map, of, shareReplay, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

import {
  GovernedNarrativeRecord,
  GovernedNarrativeSection,
  GovernedNarrativeVersionsResponse
} from '../models/api.models';
import {
  GovernedNarrativeEntityType,
  GovernedNarrativeService
} from '../services/governed-narrative.service';
import { PermissionsService } from '../services/permissions.service';
import { NbmsStatusPillComponent } from './nbms-status-pill.component';
import { NbmsToastService } from './nbms-toast.service';

type SeedSection = {
  id: string;
  title: string;
  body: string;
};

type NarrativeConfig = {
  entityType: GovernedNarrativeEntityType;
  entityId: string;
  entityLabel: string;
  title: string;
  provenanceUrl: string;
  seedSections: SeedSection[];
  reportingQueryParams: Record<string, unknown>;
};

type EditorSectionVm = {
  id: string;
  title: string;
  body: string;
  html: string;
};

type CompareSectionVm = {
  id: string;
  title: string;
  previousBody: string;
  currentBody: string;
  changed: boolean;
};

type NarrativeVm = {
  record: GovernedNarrativeRecord;
  sections: EditorSectionVm[];
  versions: GovernedNarrativeVersionsResponse['versions'];
  canEdit: boolean;
  canInsert: boolean;
  compareSections: CompareSectionVm[];
};

@Component({
  selector: 'nbms-interpretation-editor',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    NgFor,
    NgIf,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    NbmsStatusPillComponent
  ],
  template: `
    <section class="editor nbms-card-surface" *ngIf="vm$ | async as vm">
      <header class="head">
        <div class="head-copy">
          <p class="eyebrow">{{ eyebrow }}</p>
          <h2>{{ cardTitle }}</h2>
          <p class="sub-copy">{{ vm.record.entity_label || vm.record.title }}</p>
        </div>

        <div class="actions">
          <button mat-button type="button" aria-label="Copy narrative text" (click)="copyNarrative()">
            <mat-icon aria-hidden="true">content_copy</mat-icon>
            Copy
          </button>
          <a
            *ngIf="showInsertAction && vm.canInsert"
            mat-stroked-button
            [routerLink]="['/reporting']"
            [queryParams]="reportingQueryParams()"
            aria-label="Insert narrative into report workspace"
          >
            <mat-icon aria-hidden="true">post_add</mat-icon>
            Insert into report
          </a>
          <button
            *ngIf="vm.canEdit"
            mat-stroked-button
            type="button"
            aria-label="Toggle narrative edit mode"
            (click)="editing = !editing"
          >
            <mat-icon aria-hidden="true">{{ editing ? 'visibility' : 'edit' }}</mat-icon>
            {{ editing ? 'View' : 'Edit' }}
          </button>
          <button
            *ngIf="vm.canEdit && editing"
            mat-stroked-button
            type="button"
            [disabled]="savePending"
            aria-label="Save governed narrative draft"
            (click)="saveDraft()"
          >
            <mat-icon aria-hidden="true">save</mat-icon>
            {{ savePending ? 'Saving' : 'Save' }}
          </button>
          <button
            *ngIf="vm.canEdit && editing"
            mat-flat-button
            type="button"
            [disabled]="submitPending"
            aria-label="Submit governed narrative for review"
            (click)="submitDraft()"
          >
            <mat-icon aria-hidden="true">send</mat-icon>
            {{ submitPending ? 'Submitting' : 'Submit for review' }}
          </button>
        </div>
      </header>

      <section class="governance">
        <div class="pill-row">
          <nbms-status-pill [label]="vm.record.status || 'Draft'" [tone]="toneForStatus(vm.record.status)"></nbms-status-pill>
          <nbms-status-pill [label]="vm.record.qa_status || 'QA pending'" [tone]="toneForStatus(vm.record.qa_status, 'info')"></nbms-status-pill>
          <nbms-status-pill [label]="vm.record.sensitivity || 'public'" [tone]="toneForSensitivity(vm.record.sensitivity)"></nbms-status-pill>
          <nbms-status-pill [label]="'v' + vm.record.current_version" tone="neutral"></nbms-status-pill>
        </div>
        <div class="meta-row">
          <span>Last updated {{ vm.record.updated_at | date: 'mediumDate' }}</span>
          <span *ngIf="vm.record.updated_by">by {{ vm.record.updated_by }}</span>
          <a *ngIf="vm.record.provenance_url" [href]="vm.record.provenance_url" target="_blank" rel="noreferrer">
            Provenance and explainability
          </a>
        </div>
        <p class="draft-note" *ngIf="localDraftRestored">A browser draft was restored for this narrative.</p>
        <p class="draft-note" *ngIf="vm.canEdit">Editing autosaves locally on this device until you explicitly save or submit.</p>
      </section>

      <section *ngIf="!editing; else editMode" class="section-list">
        <article class="section" *ngFor="let section of vm.sections; trackBy: trackBySection">
          <header class="section-head">
            <strong>{{ section.title }}</strong>
            <span>{{ section.id }}</span>
          </header>
          <div class="markdown-body" [innerHTML]="section.html"></div>
        </article>
      </section>

      <ng-template #editMode>
        <form class="edit-form" [formGroup]="form">
          <div formArrayName="sections" class="section-list">
            <article class="section" *ngFor="let section of sectionGroups; let index = index; trackBy: trackByControl" [formGroupName]="index">
              <header class="section-head">
                <strong>{{ section.get('title')?.value }}</strong>
                <span>{{ section.get('id')?.value }}</span>
              </header>
              <mat-form-field appearance="outline" subscriptSizing="dynamic">
                <mat-label>{{ section.get('title')?.value }}</mat-label>
                <textarea
                  matInput
                  rows="7"
                  formControlName="body"
                  [attr.aria-label]="'Edit ' + section.get('title')?.value"
                ></textarea>
              </mat-form-field>
            </article>
          </div>
        </form>
      </ng-template>

      <section class="history" *ngIf="vm.versions.length">
        <div class="history-head">
          <div>
            <p class="eyebrow">Versions</p>
            <h3>History</h3>
          </div>
          <span>{{ vm.versions.length }} versions</span>
        </div>

        <div class="version-list">
          <article class="version-row" *ngFor="let version of vm.versions.slice(0, 6); trackBy: trackByVersion">
            <div>
              <strong>v{{ version.version }}</strong>
              <p>{{ version.created_at | date: 'mediumDate' }}<span *ngIf="version.created_by"> · {{ version.created_by }}</span></p>
            </div>
            <div class="pill-row">
              <nbms-status-pill [label]="version.status || 'draft'" [tone]="toneForStatus(version.status)"></nbms-status-pill>
              <nbms-status-pill [label]="version.qa_status || 'qa'" [tone]="toneForStatus(version.qa_status, 'info')"></nbms-status-pill>
            </div>
          </article>
        </div>
      </section>

      <section class="compare" *ngIf="vm.compareSections.length">
        <div class="history-head">
          <div>
            <p class="eyebrow">Compare</p>
            <h3>Latest saved vs current</h3>
          </div>
        </div>

        <article class="compare-row" *ngFor="let section of vm.compareSections; trackBy: trackByCompare">
          <header class="section-head">
            <strong>{{ section.title }}</strong>
            <nbms-status-pill [label]="section.changed ? 'Changed' : 'No changes'" [tone]="section.changed ? 'warn' : 'success'"></nbms-status-pill>
          </header>

          <div class="compare-grid" *ngIf="section.changed">
            <div class="compare-card">
              <p class="compare-label">Latest saved</p>
              <pre>{{ section.previousBody || 'Empty' }}</pre>
            </div>
            <div class="compare-card">
              <p class="compare-label">Current draft</p>
              <pre>{{ section.currentBody || 'Empty' }}</pre>
            </div>
          </div>
        </article>
      </section>
    </section>
  `,
  styles: [
    `
      .editor,
      .head,
      .head-copy,
      .actions,
      .governance,
      .meta-row,
      .section-list,
      .section,
      .history,
      .version-list,
      .version-row,
      .compare,
      .compare-row {
        display: grid;
        gap: var(--nbms-space-3);
      }

      .editor {
        padding: var(--nbms-space-4) var(--nbms-space-5);
      }

      .head {
        align-items: start;
        grid-template-columns: minmax(0, 1fr) auto;
      }

      .eyebrow,
      .sub-copy,
      .draft-note,
      .meta-row,
      .compare-label,
      .section-head span,
      .version-row p {
        margin: 0;
        color: var(--nbms-text-muted);
      }

      .eyebrow,
      .compare-label,
      .section-head span {
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      .actions,
      .pill-row,
      .meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: var(--nbms-space-2);
        align-items: center;
      }

      .meta-row {
        font-size: var(--nbms-font-size-label-sm);
      }

      .meta-row a {
        color: var(--nbms-text-primary);
      }

      .section {
        padding-top: var(--nbms-space-3);
        border-top: 1px solid var(--nbms-divider);
      }

      .section-head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-2);
        align-items: center;
      }

      .markdown-body {
        color: var(--nbms-text-secondary);
        line-height: 1.7;
      }

      .markdown-body :is(p, ul, li, h3) {
        margin: 0 0 var(--nbms-space-2);
      }

      .markdown-body ul {
        padding-left: 1.2rem;
      }

      .edit-form mat-form-field {
        width: 100%;
      }

      .history-head {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-2);
        align-items: start;
      }

      .history-head h3 {
        margin: var(--nbms-space-1) 0 0;
      }

      .version-row {
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        border-top: 1px solid var(--nbms-divider);
        padding-top: var(--nbms-space-3);
      }

      .compare-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: var(--nbms-space-3);
      }

      .compare-card {
        border: 1px solid var(--nbms-divider);
        border-radius: var(--nbms-radius-md);
        padding: var(--nbms-space-3);
        background: color-mix(in srgb, var(--nbms-surface-2) 68%, var(--nbms-surface));
      }

      .compare-card pre {
        margin: 0;
        color: var(--nbms-text-secondary);
        font: inherit;
        white-space: pre-wrap;
      }

      @media (max-width: 900px) {
        .head {
          grid-template-columns: 1fr;
        }

        .compare-grid,
        .version-row {
          grid-template-columns: 1fr;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsInterpretationEditorComponent implements OnChanges {
  private readonly fb = inject(UntypedFormBuilder);
  private readonly narratives = inject(GovernedNarrativeService);
  private readonly permissions = inject(PermissionsService);
  private readonly toast = inject(NbmsToastService);
  private readonly destroyRef = inject(DestroyRef);

  @Input({ required: true }) entityType!: GovernedNarrativeEntityType;
  @Input({ required: true }) entityId!: string;
  @Input() entityLabel = '';
  @Input() title = '';
  @Input() provenanceUrl = '';
  @Input() seedSections: SeedSection[] = [];
  @Input() reportingQueryParamsInput: Record<string, unknown> = {};
  @Input() eyebrow = 'Narrative';
  @Input() cardTitle = 'Governed narrative';
  @Input() showInsertAction = true;

  readonly form = this.fb.group({
    sections: this.fb.array([])
  });

  editing = false;
  localDraftRestored = false;
  savePending = false;
  submitPending = false;

  private readonly configSubject = new BehaviorSubject<NarrativeConfig | null>(null);
  private readonly refreshSubject = new BehaviorSubject<number>(0);
  private currentConfig: NarrativeConfig | null = null;
  private currentRecord: GovernedNarrativeRecord | null = null;

  readonly sections$ = this.sectionsArray.valueChanges.pipe(
    startWith(this.sectionsArray.getRawValue()),
    map((rows) => this.normalizeSectionRows(rows)),
    shareReplay(1)
  );

  readonly resource$ = combineLatest([
    this.configSubject.pipe(filter((config): config is NarrativeConfig => config !== null)),
    this.refreshSubject
  ]).pipe(
    switchMap(([config]) =>
      this.narratives.get(config.entityType, config.entityId).pipe(
        map((response) => ({ config, record: response.narrative })),
        switchMap((resource) => of(resource))
      )
    ),
    shareReplay(1)
  );

  readonly versions$ = combineLatest([
    this.configSubject.pipe(filter((config): config is NarrativeConfig => config !== null)),
    this.refreshSubject
  ]).pipe(
    switchMap(([config]) =>
      this.narratives.versions(config.entityType, config.entityId).pipe(
        map((response) => response.versions),
        switchMap((versions) => of(versions))
      )
    ),
    shareReplay(1)
  );

  readonly canEdit$ = combineLatest([
    this.permissions.has$('can_edit_narratives'),
    this.resource$
  ]).pipe(
    map(([hasCapability, resource]) => hasCapability && resource.record.can_edit),
    shareReplay(1)
  );

  readonly canInsert$ = this.permissions.has$('can_view_reporting_builder').pipe(shareReplay(1));

  readonly vm$ = combineLatest([
    this.resource$,
    this.sections$,
    this.versions$,
    this.canEdit$,
    this.canInsert$
  ]).pipe(
    map(([resource, sections, versions, canEdit, canInsert]) => ({
      record: resource.record,
      sections,
      versions,
      canEdit,
      canInsert,
      compareSections: compareSections(sections, versions[0]?.sections ?? [])
    })),
    shareReplay(1)
  );

  constructor() {
    this.sectionsArray.valueChanges
      .pipe(debounceTime(300), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.persistLocalDraft());

    this.resource$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(({ config, record }) => {
      this.currentConfig = config;
      this.currentRecord = record;
      this.loadSections(config, record);
    });
  }

  get sectionsArray(): UntypedFormArray {
    return this.form.get('sections') as UntypedFormArray;
  }

  get sectionGroups(): UntypedFormGroup[] {
    return this.sectionsArray.controls as UntypedFormGroup[];
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (
      changes['entityType'] ||
      changes['entityId'] ||
      changes['entityLabel'] ||
      changes['title'] ||
      changes['provenanceUrl'] ||
      changes['seedSections'] ||
      changes['reportingQueryParamsInput']
    ) {
      if (!this.entityType || !this.entityId) {
        return;
      }
      this.configSubject.next({
        entityType: this.entityType,
        entityId: this.entityId,
        entityLabel: this.entityLabel,
        title: this.title,
        provenanceUrl: this.provenanceUrl,
        seedSections: this.seedSections,
        reportingQueryParams: this.reportingQueryParamsInput
      });
    }
  }

  async copyNarrative(): Promise<void> {
    const compiled = compileNarrative(this.normalizeSectionRows(this.sectionsArray.getRawValue()));
    if (!globalThis.navigator?.clipboard) {
      this.toast.warn('Clipboard access is not available.');
      return;
    }
    try {
      await globalThis.navigator.clipboard.writeText(compiled);
      this.toast.success('Narrative copied.');
    } catch {
      this.toast.error('Could not copy the narrative.');
    }
  }

  reportingQueryParams(): Record<string, unknown> {
    const config = this.currentConfig;
    const sections = this.normalizeSectionRows(this.sectionsArray.getRawValue());
    return {
      narrative: compileNarrative(sections),
      narrative_title: this.title || this.currentRecord?.title || '',
      source_entity_type: config?.entityType || '',
      source_entity_id: config?.entityId || '',
      ...config?.reportingQueryParams
    };
  }

  saveDraft(): void {
    const config = this.currentConfig;
    if (!config) {
      return;
    }
    this.savePending = true;
    this.narratives
      .saveDraft(config.entityType, config.entityId, this.buildPayload(config))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.savePending = false;
          this.clearLocalDraft();
          this.refreshSubject.next(Date.now());
          this.toast.success('Narrative draft saved.');
        },
        error: () => {
          this.savePending = false;
          this.toast.error('Could not save the narrative draft.');
        }
      });
  }

  submitDraft(): void {
    const config = this.currentConfig;
    if (!config) {
      return;
    }
    this.submitPending = true;
    this.narratives
      .submit(config.entityType, config.entityId, this.buildPayload(config))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.submitPending = false;
          this.editing = false;
          this.clearLocalDraft();
          this.refreshSubject.next(Date.now());
          this.toast.success('Narrative submitted for review.');
        },
        error: () => {
          this.submitPending = false;
          this.toast.error('Could not submit the narrative.');
        }
      });
  }

  toneForStatus(value: string | null | undefined, defaultTone: 'neutral' | 'success' | 'warn' | 'error' | 'info' = 'neutral') {
    const normalized = (value || '').toLowerCase();
    if (!normalized) {
      return defaultTone;
    }
    if (/(approved|published|ready|active|review)/.test(normalized)) {
      return 'success';
    }
    if (/(pending|draft|warning)/.test(normalized)) {
      return 'warn';
    }
    if (/(failed|rejected|blocked|error)/.test(normalized)) {
      return 'error';
    }
    return defaultTone === 'neutral' ? 'info' : defaultTone;
  }

  toneForSensitivity(value: string | null | undefined): 'neutral' | 'success' | 'warn' | 'error' | 'info' {
    const normalized = (value || '').toLowerCase();
    if (normalized === 'public') {
      return 'info';
    }
    if (normalized === 'restricted' || normalized === 'internal') {
      return 'warn';
    }
    if (normalized === 'confidential') {
      return 'error';
    }
    return 'neutral';
  }

  trackBySection(_: number, section: EditorSectionVm): string {
    return section.id;
  }

  trackByControl(_: number, control: UntypedFormGroup): string {
    return String(control.get('id')?.value ?? '');
  }

  trackByVersion(_: number, version: GovernedNarrativeVersionsResponse['versions'][number]): string {
    return version.uuid;
  }

  trackByCompare(_: number, section: CompareSectionVm): string {
    return section.id;
  }

  private buildPayload(config: NarrativeConfig) {
    return {
      title: this.title || this.currentRecord?.title || config.title,
      entity_label: config.entityLabel || this.currentRecord?.entity_label || config.entityId,
      provenance_url: config.provenanceUrl || this.currentRecord?.provenance_url || '',
      sections: this.normalizeSectionRows(this.sectionsArray.getRawValue()).map((section) => ({
        id: section.id,
        title: section.title,
        body: section.body
      }))
    };
  }

  private loadSections(config: NarrativeConfig, record: GovernedNarrativeRecord): void {
    const localDraft = this.readLocalDraft(config);
    const sourceSections = localDraft.length
      ? localDraft
      : selectSeedSections(record.sections, record.available_block_types, config.seedSections);
    this.localDraftRestored = localDraft.length > 0;
    this.sectionsArray.clear({ emitEvent: false });
    sourceSections.forEach((section) => {
      this.sectionsArray.push(
        this.fb.group({
          id: [section.id],
          title: [section.title],
          body: [section.body]
        }),
        { emitEvent: false }
      );
    });
    this.form.updateValueAndValidity({ emitEvent: true });
  }

  private normalizeSectionRows(rows: unknown): EditorSectionVm[] {
    return Array.isArray(rows)
      ? rows.map((row, index) => normalizeSectionRow(row, index))
      : [];
  }

  private persistLocalDraft(): void {
    const config = this.currentConfig;
    if (!config) {
      return;
    }
    const payload = this.normalizeSectionRows(this.sectionsArray.getRawValue()).map((section) => ({
      id: section.id,
      title: section.title,
      body: section.body
    }));
    try {
      globalThis.localStorage?.setItem(storageKey(config), JSON.stringify(payload));
    } catch {
      // ignore local draft write failures
    }
  }

  private readLocalDraft(config: NarrativeConfig): SeedSection[] {
    try {
      const raw = globalThis.localStorage?.getItem(storageKey(config));
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed.map((row, index) => normalizeSectionRow(row, index));
    } catch {
      return [];
    }
  }

  private clearLocalDraft(): void {
    if (!this.currentConfig) {
      return;
    }
    try {
      globalThis.localStorage?.removeItem(storageKey(this.currentConfig));
    } catch {
      // ignore local draft cleanup failures
    }
    this.localDraftRestored = false;
  }
}

function selectSeedSections(
  recordSections: GovernedNarrativeSection[],
  availableBlockTypes: Array<{ id: string; title: string; body: string }>,
  seedSections: SeedSection[]
): SeedSection[] {
  const fromRecord = recordSections
    .map((section) => ({
      id: section.id,
      title: section.title,
      body: section.body
    }))
    .filter((section) => section.title || section.body);
  if (fromRecord.some((section) => section.body.trim())) {
    return fromRecord;
  }
  if (seedSections.length) {
    return seedSections;
  }
  return availableBlockTypes.map((section) => ({
    id: section.id,
    title: section.title,
    body: section.body
  }));
}

function normalizeSectionRow(row: unknown, index: number): EditorSectionVm {
  const value = typeof row === 'object' && row !== null ? (row as Record<string, unknown>) : {};
  const title = String(value['title'] || `Section ${index + 1}`).trim();
  const body = String(value['body'] || '').trim();
  return {
    id: String(value['id'] || slugify(title) || `section-${index + 1}`),
    title,
    body,
    html: renderMarkdown(body)
  };
}

function compareSections(
  currentSections: EditorSectionVm[],
  previousSections: Array<{ id: string; title: string; body: string }>
): CompareSectionVm[] {
  return currentSections.map((section) => {
    const previous = previousSections.find((candidate) => candidate.id === section.id);
    return {
      id: section.id,
      title: section.title,
      previousBody: previous?.body || '',
      currentBody: section.body,
      changed: normalizeBody(previous?.body || '') !== normalizeBody(section.body)
    };
  });
}

function compileNarrative(sections: SeedSection[]): string {
  return sections
    .map((section) => `## ${section.title}\n${section.body}`.trim())
    .join('\n\n')
    .trim();
}

function storageKey(config: NarrativeConfig): string {
  return `nbms.narrative.${config.entityType}.${config.entityId}`;
}

function normalizeBody(value: string): string {
  return value.replace(/\r\n/g, '\n').trim();
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function renderMarkdown(value: string): string {
  if (!value.trim()) {
    return '<p>No narrative text has been captured yet.</p>';
  }
  const blocks = value
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

  return blocks
    .map((block) => {
      const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
      if (lines.every((line) => /^[-*]\s+/.test(line))) {
        return `<ul>${lines.map((line) => `<li>${inlineMarkdown(line.replace(/^[-*]\s+/, ''))}</li>`).join('')}</ul>`;
      }
      if (/^#{1,3}\s+/.test(lines[0] || '')) {
        const heading = lines[0].replace(/^#{1,3}\s+/, '');
        const rest = lines.slice(1).join(' ');
        const parts = [`<h3>${inlineMarkdown(heading)}</h3>`];
        if (rest) {
          parts.push(`<p>${inlineMarkdown(rest)}</p>`);
        }
        return parts.join('');
      }
      return `<p>${inlineMarkdown(lines.join(' '))}</p>`;
    })
    .join('');
}

function inlineMarkdown(value: string): string {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
