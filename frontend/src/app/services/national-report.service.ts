import { Injectable } from '@angular/core';

import {
  ReportContextPayload,
  ReportCommentThreadPayload,
  ReportNarrativeRenderPayload,
  ReportSectionHistory,
  ReportSectionChartsPayload,
  ReportSuggestionPayload,
  ReportWorkspaceSection,
  ReportWorkspaceSummary
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class NationalReportService {
  constructor(private readonly api: ApiClientService) {}

  workspace(instanceUuid: string) {
    return this.api.get<ReportWorkspaceSummary>(`reports/${instanceUuid}/workspace`);
  }

  createNationalReport(payload: {
    report_label: 'NR7' | 'NR8';
    reporting_period_start?: string;
    reporting_period_end?: string;
    is_public: boolean;
    report_title?: string;
    country_name?: string;
  }) {
    return this.api.post<{ instance: { uuid: string } }>('reporting/instances', payload);
  }

  section(instanceUuid: string, sectionCode: string) {
    return this.api.get<ReportWorkspaceSection>(`reports/${instanceUuid}/sections/${sectionCode}`);
  }

  saveSection(
    instanceUuid: string,
    sectionCode: string,
    payload: {
      response_json: Record<string, unknown>;
      base_version: number;
      suggestion_mode?: boolean;
      patch_json?: Record<string, unknown>;
      rationale?: string;
    }
  ) {
    return this.api.post<ReportWorkspaceSection | Record<string, unknown>>(
      `reports/${instanceUuid}/sections/${sectionCode}`,
      payload
    );
  }

  sectionHistory(instanceUuid: string, sectionCode: string, fromVersion?: number, toVersion?: number) {
    const params: Record<string, string | number> = {};
    if (fromVersion !== undefined && toVersion !== undefined) {
      params['from'] = fromVersion;
      params['to'] = toVersion;
    }
    return this.api.get<ReportSectionHistory>(`reports/${instanceUuid}/sections/${sectionCode}/history`, params);
  }

  comments(instanceUuid: string, sectionCode: string) {
    return this.api.get<ReportCommentThreadPayload>(`reports/${instanceUuid}/sections/${sectionCode}/comments`);
  }

  addComment(
    instanceUuid: string,
    sectionCode: string,
    payload: {
      thread_uuid?: string;
      json_path?: string;
      body: string;
      object_uuid?: string;
      field_name?: string;
    }
  ) {
    return this.api.post<ReportCommentThreadPayload>(
      `reports/${instanceUuid}/sections/${sectionCode}/comments`,
      payload
    );
  }

  updateCommentThreadStatus(instanceUuid: string, sectionCode: string, threadUuid: string, statusValue: string) {
    return this.api.post<{ thread_uuid: string; status: string }>(
      `reports/${instanceUuid}/sections/${sectionCode}/comments/${threadUuid}/status`,
      { status: statusValue }
    );
  }

  suggestions(instanceUuid: string, sectionCode: string) {
    return this.api.get<ReportSuggestionPayload>(
      `reports/${instanceUuid}/sections/${sectionCode}/suggestions`
    );
  }

  createSuggestion(
    instanceUuid: string,
    sectionCode: string,
    payload: {
      base_version: number;
      object_uuid?: string;
      field_name?: string;
      patch_json?: Record<string, unknown>;
      diff_patch?: Record<string, unknown>;
      old_value_hash?: string;
      proposed_value?: unknown;
      rationale?: string;
    }
  ) {
    return this.api.post<{ uuid: string; status: string }>(
      `reports/${instanceUuid}/sections/${sectionCode}/suggestions`,
      payload
    );
  }

  decideSuggestion(
    instanceUuid: string,
    sectionCode: string,
    suggestionUuid: string,
    action: 'accept' | 'reject',
    note = ''
  ) {
    return this.api.post<{ uuid: string; status: string; revision_uuid: string | null }>(
      `reports/${instanceUuid}/sections/${sectionCode}/suggestions/${suggestionUuid}/decision`,
      { action, note }
    );
  }

  workflow(instanceUuid: string) {
    return this.api.get<Record<string, unknown>>(`reports/${instanceUuid}/workflow`);
  }

  workflowAction(instanceUuid: string, action: string, comment = '', sectionCode = '') {
    return this.api.post<Record<string, unknown>>(`reports/${instanceUuid}/workflow/action`, {
      action,
      comment,
      section_code: sectionCode
    });
  }

  context(instanceUuid: string) {
    return this.api.get<ReportContextPayload>(`reports/${instanceUuid}/context`);
  }

  saveContext(instanceUuid: string, context: Record<string, string>) {
    return this.api.post<ReportContextPayload>(`reports/${instanceUuid}/context`, { context });
  }

  sectionPreview(instanceUuid: string, sectionCode: string, context?: Record<string, string>) {
    const params: Record<string, string> = {};
    if (context) {
      params['context'] = JSON.stringify(context);
    }
    return this.api.get<{ section_code: string; html: string; resolved_values_manifest: unknown[]; context_hash: string }>(
      `reports/${instanceUuid}/sections/${sectionCode}/preview`,
      params
    );
  }

  sectionCharts(instanceUuid: string, sectionCode: string, context?: Record<string, string>) {
    const params: Record<string, string> = {};
    if (context) {
      params['context'] = JSON.stringify(context);
    }
    return this.api.get<ReportSectionChartsPayload>(`reports/${instanceUuid}/sections/${sectionCode}/charts`, params);
  }

  renderNarrative(instanceUuid: string, sectionCode: string, context?: Record<string, string>) {
    const params: Record<string, string> = {};
    if (context) {
      params['context'] = JSON.stringify(context);
    }
    return this.api.get<ReportNarrativeRenderPayload>(
      `reports/${instanceUuid}/sections/${sectionCode}/narrative/render`,
      params
    );
  }

  narrativeBlocks(instanceUuid: string, sectionCode: string) {
    return this.api.get<{ blocks: Array<Record<string, unknown>> }>(
      `reports/${instanceUuid}/sections/${sectionCode}/narrative/blocks`
    );
  }

  saveNarrativeBlock(
    instanceUuid: string,
    sectionCode: string,
    payload: { block_key?: string; title?: string; content_text?: string; docx_base64?: string }
  ) {
    return this.api.post<{ blocks: Array<Record<string, unknown>> }>(
      `reports/${instanceUuid}/sections/${sectionCode}/narrative/blocks`,
      payload
    );
  }

  narrativeEditorConfig(instanceUuid: string, sectionCode: string, blockKey: string) {
    return this.api.get<{ editor_config: Record<string, unknown> }>(
      `reports/${instanceUuid}/sections/${sectionCode}/narrative/blocks/${blockKey}/editor-config`
    );
  }

  narrativeDocumentUrl(instanceUuid: string, sectionCode: string, blockKey: string): string {
    return `/api/reports/${instanceUuid}/sections/${sectionCode}/narrative/blocks/${blockKey}/document`;
  }

  generateSectionIiiSkeleton(instanceUuid: string) {
    return this.api.post<Record<string, unknown>>(
      `reports/${instanceUuid}/sections/section-iii/generate-skeleton`,
      {}
    );
  }

  recomputeSectionIvRollup(instanceUuid: string) {
    return this.api.post<Record<string, unknown>>(
      `reports/${instanceUuid}/sections/section-iv/recompute-rollup`,
      {}
    );
  }

  exportPdfUrl(instanceUuid: string): string {
    return `/api/reports/${instanceUuid}/export.pdf`;
  }

  exportDocxUrl(instanceUuid: string): string {
    return `/api/reports/${instanceUuid}/export.docx`;
  }

  exportJsonUrl(instanceUuid: string): string {
    return `/api/reports/${instanceUuid}/export`;
  }

  generateDossier(instanceUuid: string) {
    return this.api.post<{ dossier: Record<string, unknown> }>(`reports/${instanceUuid}/dossier`, {});
  }

  latestDossier(instanceUuid: string) {
    return this.api.get<{ dossier: Record<string, unknown> }>(`reports/${instanceUuid}/dossier/latest`);
  }

  latestDossierDownloadUrl(instanceUuid: string): string {
    return `/api/reports/${instanceUuid}/dossier/latest?download=1`;
  }

  ortValidation(instanceUuid: string) {
    return this.api.get<{
      contract: string;
      overall_valid: boolean;
      blocking_issues: Array<Record<string, unknown>>;
      validation: Record<string, unknown>;
    }>(`reports/${instanceUuid}/ort-validation`);
  }

  createNr8FromNr7(instanceUuid: string) {
    return this.api.post<{ source_instance_uuid: string; new_instance_uuid: string }>(
      `reports/${instanceUuid}/carry-forward/nr8`,
      {}
    );
  }

  diff(instanceUuid: string, fromInstanceUuid: string) {
    return this.api.get<{
      baseline_instance_uuid: string;
      instance_uuid: string;
      section_diffs: Array<Record<string, unknown>>;
      narrative_diffs: Array<Record<string, unknown>>;
      change_summary: string;
    }>(`reports/${instanceUuid}/diff`, { from_instance_uuid: fromInstanceUuid });
  }
}
