import { Injectable } from '@angular/core';

import {
  ReportCommentThreadPayload,
  ReportSectionHistory,
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
    payload: { thread_uuid?: string; json_path?: string; body: string }
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
}
