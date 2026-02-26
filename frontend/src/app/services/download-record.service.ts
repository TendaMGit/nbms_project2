import { Injectable } from '@angular/core';

import {
  DownloadRecordCreateResponse,
  DownloadRecordDetailResponse,
  DownloadRecordListResponse,
  DownloadRecordType
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

export interface CreateDownloadRecordPayload {
  record_type: DownloadRecordType;
  object_type: string;
  object_uuid?: string;
  query_snapshot?: Record<string, unknown>;
  regen_params?: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class DownloadRecordService {
  constructor(private readonly api: ApiClientService) {}

  create(payload: CreateDownloadRecordPayload) {
    return this.api.post<DownloadRecordCreateResponse>('downloads/records', payload);
  }

  list(params: { record_type?: DownloadRecordType; page?: number; page_size?: number } = {}) {
    return this.api.get<DownloadRecordListResponse>('downloads/records', params);
  }

  detail(uuid: string) {
    return this.api.get<DownloadRecordDetailResponse>(`downloads/records/${uuid}`);
  }

  fileUrl(uuid: string): string {
    return `/api/downloads/records/${uuid}/file`;
  }
}

