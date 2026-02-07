import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import {
  TemplatePack,
  TemplatePackResponseRow,
  TemplatePackSection,
  TemplatePackValidationSummary
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class TemplatePackService {
  constructor(private readonly api: ApiClientService) {}

  list() {
    return this.api.get<{ packs: TemplatePack[] }>('template-packs').pipe(
      catchError(() => of({ packs: [] }))
    );
  }

  sections(packCode: string) {
    return this.api
      .get<{ pack: { code: string; title: string; mea_code: string; version: string }; sections: TemplatePackSection[] }>(
        `template-packs/${packCode}/sections`
      )
      .pipe(catchError(() => of({ pack: { code: packCode, title: packCode, mea_code: '', version: 'v1' }, sections: [] })));
  }

  responses(packCode: string, instanceUuid: string) {
    return this.api.get<{ responses: TemplatePackResponseRow[]; pack: Record<string, unknown> }>(
      `template-packs/${packCode}/instances/${instanceUuid}/responses`
    );
  }

  saveResponse(packCode: string, instanceUuid: string, sectionCode: string, responseJson: Record<string, unknown>) {
    return this.api.post<{ section_code: string; response_json: Record<string, unknown> }>(
      `template-packs/${packCode}/instances/${instanceUuid}/responses`,
      {
        section_code: sectionCode,
        response_json: responseJson
      }
    );
  }

  validate(packCode: string, instanceUuid: string) {
    return this.api.get<TemplatePackValidationSummary>(
      `template-packs/${packCode}/instances/${instanceUuid}/validate`
    );
  }

  exportJson(packCode: string, instanceUuid: string) {
    return this.api.get<Record<string, unknown>>(
      `template-packs/${packCode}/instances/${instanceUuid}/export`
    );
  }

  exportPdfUrl(packCode: string, instanceUuid: string) {
    return `/api/template-packs/${packCode}/instances/${instanceUuid}/export.pdf`;
  }
}
