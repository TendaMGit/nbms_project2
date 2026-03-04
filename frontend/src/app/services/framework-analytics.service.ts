import { Injectable } from '@angular/core';
import { combineLatest, map, of, switchMap } from 'rxjs';
import { catchError } from 'rxjs/operators';

import type { DashboardSummary, IndicatorDetailResponse, IndicatorListItem, IndicatorListResponse } from '../models/api.models';
import type { NbmsContextQueryParams } from '../models/context.models';
import { DashboardService } from './dashboard.service';
import { IndicatorService } from './indicator.service';

export type FrameworkSummaryRow = {
  id: string;
  title: string;
  targetCount: number;
  indicatorCount: number;
  narrative: string;
};

export type FrameworkTargetRow = {
  id: string;
  label: string;
  indicatorCount: number;
  readinessScore: number;
  readyCount: number;
  warningCount: number;
  blockedCount: number;
};

export type FrameworkIndicatorRow = {
  uuid: string;
  code: string;
  title: string;
  status: string;
  readinessScore: number;
  readinessStatus: string;
  updatedAt: string | null;
  hasSpatial: boolean;
  targetCode: string;
};

export type FrameworkDetailData = {
  framework: FrameworkSummaryRow | null;
  targets: FrameworkTargetRow[];
  indicators: FrameworkIndicatorRow[];
};

export type TargetDetailData = {
  framework: FrameworkSummaryRow | null;
  target: FrameworkTargetRow | null;
  indicators: FrameworkIndicatorRow[];
  evidence: Array<{
    title: string;
    subtitle: string;
    type: string;
    date?: string | null;
    accessLabel?: string;
    accessTone?: 'neutral' | 'success' | 'warn' | 'error' | 'info';
    url?: string;
  }>;
  filterScopeLabel: string;
};

@Injectable({ providedIn: 'root' })
export class FrameworkAnalyticsService {
  constructor(
    private readonly dashboard: DashboardService,
    private readonly indicatorService: IndicatorService
  ) {}

  frameworks() {
    return this.dashboard.getSummary().pipe(map((summary) => buildFrameworkRows(summary)));
  }

  frameworkDetail(frameworkId: string, context: NbmsContextQueryParams) {
    return combineLatest([this.dashboard.getSummary(), this.frameworkIndicators(frameworkId, context)]).pipe(
      map(([summary, indicators]) => buildFrameworkDetail(summary, frameworkId, indicators.results))
    );
  }

  targetDetail(frameworkId: string, targetId: string, context: NbmsContextQueryParams) {
    return combineLatest([this.dashboard.getSummary(), this.frameworkIndicators(frameworkId, context)]).pipe(
      switchMap(([summary, indicators]) => {
        const frameworkDetail = buildFrameworkDetail(summary, frameworkId, indicators.results);
        const filtered = filterIndicatorsForTarget(frameworkId, targetId, frameworkDetail.indicators);
        const detailUuids = filtered.rows.slice(0, 5).map((row) => row.uuid);
        if (!detailUuids.length) {
          return of({
            framework: frameworkDetail.framework,
            target: frameworkDetail.targets.find((row) => row.id === targetId) ?? null,
            indicators: filtered.rows,
            evidence: [],
            filterScopeLabel: filtered.scopeLabel
          } satisfies TargetDetailData);
        }
        return combineLatest(
          detailUuids.map((uuid) => this.indicatorService.detail(uuid).pipe(catchError(() => of(null as IndicatorDetailResponse | null))))
        ).pipe(
          map((details) => ({
            framework: frameworkDetail.framework,
            target: frameworkDetail.targets.find((row) => row.id === targetId) ?? null,
            indicators: filtered.rows,
            evidence: details.flatMap((detail) => buildEvidenceRows(detail)),
            filterScopeLabel: filtered.scopeLabel
          }))
        );
      })
    );
  }

  private frameworkIndicators(frameworkId: string, context: NbmsContextQueryParams) {
    return this.indicatorService
      .list({
        framework: frameworkId,
        q: context.q || undefined,
        sort: context.sort || undefined,
        page_size: 200,
        geography_type: toLegacyGeoType(context.geo_type),
        geography_code: context.geo_code || undefined
      })
      .pipe(catchError(() => of(emptyList())));
  }
}

function buildFrameworkRows(summary: DashboardSummary): FrameworkSummaryRow[] {
  const grouped = new Map<string, { indicatorCount: number; targets: Set<string> }>();
  for (const row of summary.published_by_framework_target) {
    const id = row.framework_indicator__framework_target__framework__code || 'UNMAPPED';
    const entry = grouped.get(id) ?? { indicatorCount: 0, targets: new Set<string>() };
    entry.indicatorCount += row.total;
    if (row.framework_indicator__framework_target__code) {
      entry.targets.add(row.framework_indicator__framework_target__code);
    }
    grouped.set(id, entry);
  }
  return Array.from(grouped.entries())
    .map(([id, entry]) => ({
      id,
      title: frameworkTitle(id),
      targetCount: entry.targets.size,
      indicatorCount: entry.indicatorCount,
      narrative: `${frameworkTitle(id)} currently maps ${entry.indicatorCount} indicator links across ${entry.targets.size} framework targets.`
    }))
    .sort((a, b) => b.indicatorCount - a.indicatorCount || a.title.localeCompare(b.title));
}

function buildFrameworkDetail(
  summary: DashboardSummary,
  frameworkId: string,
  indicators: IndicatorListItem[]
): FrameworkDetailData {
  const framework = buildFrameworkRows(summary).find((row) => row.id === frameworkId) ?? null;
  const targets = summary.published_by_framework_target
    .filter((row) => row.framework_indicator__framework_target__framework__code === frameworkId)
    .map((row) => {
      const readiness = summary.indicator_readiness.by_target.find((item) => item.target_code === row.framework_indicator__framework_target__code);
      return {
        id: row.framework_indicator__framework_target__code,
        label: row.framework_indicator__framework_target__code,
        indicatorCount: row.total,
        readinessScore: readiness?.readiness_score_avg ?? 0,
        readyCount: readiness?.ready_count ?? 0,
        warningCount: readiness?.warning_count ?? 0,
        blockedCount: readiness?.blocked_count ?? 0
      } satisfies FrameworkTargetRow;
    })
    .sort((a, b) => b.indicatorCount - a.indicatorCount || a.label.localeCompare(b.label));

  return {
    framework,
    targets,
    indicators: indicators.map((item) => ({
      uuid: item.uuid,
      code: item.code,
      title: item.title,
      status: item.status,
      readinessScore: item.readiness_score,
      readinessStatus: item.readiness_status,
      updatedAt: item.last_updated_on || item.updated_at || null,
      hasSpatial: item.tags.includes('spatial') || item.coverage.geography.toLowerCase().includes('province'),
      targetCode: item.national_target.code || 'UNMAPPED'
    }))
  };
}

function filterIndicatorsForTarget(
  frameworkId: string,
  targetId: string,
  rows: FrameworkIndicatorRow[]
): { rows: FrameworkIndicatorRow[]; scopeLabel: string } {
  if (frameworkId === 'GBF') {
    const filtered = rows.filter((row) => matchesTarget(row, targetId));
    return {
      rows: filtered,
      scopeLabel: filtered.length
        ? 'Filtered with target-aware matching for the selected framework target.'
        : 'No indicators matched the selected framework target.'
    };
  }

  const filtered = rows.filter((row) => matchesTarget(row, targetId));
  if (filtered.length) {
    return {
      rows: filtered,
      scopeLabel: 'Filtered locally using currently available target identifiers.'
    };
  }
  return {
    rows,
    scopeLabel: 'Backend target-level filtering is not yet available for this framework. Showing the framework slice instead.'
  };
}

function matchesTarget(row: FrameworkIndicatorRow, targetId: string): boolean {
  const normalized = targetId.trim().toLowerCase();
  return row.targetCode.toLowerCase() === normalized || row.code.toLowerCase().includes(normalized) || row.title.toLowerCase().includes(normalized);
}

function buildEvidenceRows(detail: IndicatorDetailResponse | null) {
  if (!detail) {
    return [];
  }
  return detail.evidence.map((item) => ({
    title: item.title,
    subtitle: detail.indicator.code,
    type: item.evidence_type || 'Evidence',
    accessLabel: detail.indicator.sensitivity,
    accessTone: toneForSensitivity(detail.indicator.sensitivity),
    url: item.source_url
  }));
}

function frameworkTitle(code: string): string {
  const titles: Record<string, string> = {
    GBF: 'Global Biodiversity Framework',
    NBSAP: 'National Biodiversity Strategy and Action Plan',
    SDG: 'Sustainable Development Goals',
    RAMSAR: 'Ramsar Convention',
    CITES: 'CITES',
    CMS: 'Convention on Migratory Species'
  };
  return titles[code] || code;
}

function toneForSensitivity(value: string): 'neutral' | 'success' | 'warn' | 'error' | 'info' {
  const normalized = value.toLowerCase();
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

function toLegacyGeoType(value: string): string | undefined {
  return value === 'ecoregion' || value === 'custom' || value === 'biome' ? undefined : value || undefined;
}

function emptyList(): IndicatorListResponse {
  return {
    count: 0,
    page: 1,
    page_size: 0,
    results: [],
    facets: {}
  };
}
