import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { ReportProductPreviewResponse, ReportProductSummary } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class ReportProductService {
  constructor(private readonly api: ApiClientService) {}

  list() {
    return this.api.get<{ report_products: ReportProductSummary[] }>('report-products').pipe(
      catchError(() => of({ report_products: [] }))
    );
  }

  preview(productCode: string, instanceUuid?: string) {
    const params = instanceUuid ? { instance_uuid: instanceUuid } : {};
    return this.api.get<ReportProductPreviewResponse>(`report-products/${productCode}/preview`, params);
  }

  exportHtmlUrl(productCode: string, instanceUuid?: string) {
    const params = instanceUuid ? `?instance_uuid=${encodeURIComponent(instanceUuid)}` : '';
    return `/api/report-products/${productCode}/export.html${params}`;
  }

  exportPdfUrl(productCode: string, instanceUuid?: string) {
    const params = instanceUuid ? `?instance_uuid=${encodeURIComponent(instanceUuid)}` : '';
    return `/api/report-products/${productCode}/export.pdf${params}`;
  }
}
