import type { ChartData } from 'chart.js';

import type { IndicatorDetailResponse, IndicatorDimension, IndicatorMapResponse } from '../models/api.models';
import type {
  IndicatorDimensionGroup,
  IndicatorViewCallout,
  IndicatorViewKey,
  IndicatorViewKpi,
  IndicatorViewRouteState,
} from '../models/indicator-visual.models';
import { readCssVar, withAlpha } from '../utils/theme.utils';

const TAXONOMY_LEVELS = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species'];

export function groupIndicatorDimensions(dimensions: IndicatorDimension[]): IndicatorDimensionGroup {
  return {
    categorical: dimensions.filter((row) => row.type === 'categorical' && row.id !== 'release'),
    geographic: dimensions.filter((row) => row.type === 'geo'),
    taxonomy: dimensions
      .filter((row) => row.id.startsWith('taxonomy_'))
      .sort((a, b) => taxonomyLevelOrder(a.id) - taxonomyLevelOrder(b.id)),
  };
}

export function toIndicatorView(value: string | null | undefined): IndicatorViewKey {
  if (value === 'distribution' || value === 'taxonomy' || value === 'matrix' || value === 'binary') {
    return value;
  }
  return 'timeseries';
}

export function pickDistributionDimension(dimensions: IndicatorDimension[], current: string): string {
  const grouped = groupIndicatorDimensions(dimensions).categorical;
  if (grouped.some((row) => row.id === current)) {
    return current;
  }
  return grouped.find((row) => row.id === 'threat_category')?.id || grouped[0]?.id || '';
}

export function pickTaxonomyLevel(dimensions: IndicatorDimension[], current: string): string {
  const grouped = groupIndicatorDimensions(dimensions).taxonomy;
  if (grouped.some((row) => row.id === current || row.id === `taxonomy_${current}`)) {
    return current.startsWith('taxonomy_') ? current.replace('taxonomy_', '') : current;
  }
  const family = grouped.find((row) => row.id === 'taxonomy_family');
  return family?.id.replace('taxonomy_', '') || grouped[0]?.id.replace('taxonomy_', '') || '';
}

export function taxonomyPath(state: IndicatorViewRouteState): string[] {
  return String(state.tax_code || '')
    .split('>')
    .map((value) => value.trim())
    .filter(Boolean);
}

export function withTaxonomyPath(path: string[]): string {
  return path.join('>');
}

export function nextTaxonomyLevel(dimensions: IndicatorDimension[], current: string): string {
  const ordered = groupIndicatorDimensions(dimensions).taxonomy.map((row) => row.id.replace('taxonomy_', ''));
  const index = ordered.indexOf(current);
  if (index === -1 || index === ordered.length - 1) {
    return current;
  }
  return ordered[index + 1];
}

export function previousTaxonomyLevel(dimensions: IndicatorDimension[], current: string): string {
  const ordered = groupIndicatorDimensions(dimensions).taxonomy.map((row) => row.id.replace('taxonomy_', ''));
  const index = ordered.indexOf(current);
  if (index <= 0) {
    return ordered[0] || current;
  }
  return ordered[index - 1];
}

export function taxonomyLevelOrder(value: string): number {
  const normalized = value.replace('taxonomy_', '');
  const index = TAXONOMY_LEVELS.indexOf(normalized);
  return index === -1 ? TAXONOMY_LEVELS.length + 1 : index;
}

export function buildGovernanceCallouts(
  detail: IndicatorDetailResponse,
  state: IndicatorViewRouteState,
  mapPayload?: IndicatorMapResponse | null,
): IndicatorViewCallout[] {
  const callouts: IndicatorViewCallout[] = [
    {
      tone: 'info',
      title: 'Governance',
      message: `Lifecycle ${detail.indicator.status || 'unknown'}, QA ${detail.indicator.qa_status || 'unknown'}, sensitivity ${detail.indicator.sensitivity || 'unknown'}.`,
    },
  ];
  const workflowStatus = detail.pipeline?.release_workflow.status;
  if (workflowStatus) {
    callouts.push({
      tone: workflowStatus.toLowerCase().includes('approved') ? 'info' : 'warning',
      title: 'Release workflow',
      message: `Current workflow state: ${workflowStatus}.`,
    });
  }
  if (detail.pipeline?.data_last_refreshed_at) {
    callouts.push({
      tone: 'info',
      title: 'Last updated',
      message: `Latest refresh ${formatDate(detail.pipeline.data_last_refreshed_at)} for the ${state.report_cycle || 'current'} context.`,
    });
  }
  const provenanceUrl =
    detail.evidence.find((row) => !!row.source_url)?.source_url ||
    detail.used_by_graph?.report_products[0]?.code ||
    `/indicators/${detail.indicator.uuid}`;
  callouts.push({
    tone: 'info',
    title: 'Explainability',
    message: `Provenance anchor: ${provenanceUrl}.`,
  });
  if (mapPayload?.meta?.legend?.metric) {
    callouts.push({
      tone: 'info',
      title: 'Map layer',
      message: `Spatial layer is showing ${mapPayload.meta.legend.metric}.`,
    });
  }
  return callouts;
}

export function buildSparklineChart(labels: string[], values: Array<number | null | undefined>): ChartData<'line'> {
  return {
    labels,
    datasets: [
      {
        data: values.map((value) => (typeof value === 'number' ? value : null)),
        borderColor: readCssVar('--nbms-color-secondary-500'),
        backgroundColor: withAlpha(readCssVar('--nbms-color-secondary-500'), 0.18),
        fill: true,
        tension: 0.32,
        pointRadius: 2,
        pointHoverRadius: 4,
      },
    ],
  };
}

export function formatMetric(value: number | null | undefined, unit = '', digits = 1): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'n/a';
  }
  const formatted = new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
  return unit ? `${formatted}${unit.startsWith('%') ? unit : ` ${unit}`}` : formatted;
}

export function formatWholeNumber(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'n/a';
  }
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);
}

export function percentOf(value: number, total: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round((value / total) * 100)));
}

export function buildSliceKpis(options: {
  latestValue?: number | null;
  comparisonValue?: number | null;
  rowCount: number;
  unit?: string;
  primaryLabel: string;
  helper: string;
  provenanceLabel: string;
}): IndicatorViewKpi[] {
  const latest = options.latestValue ?? null;
  const baseline = options.comparisonValue ?? null;
  const delta = typeof latest === 'number' && typeof baseline === 'number' ? latest - baseline : null;
  return [
    {
      title: options.primaryLabel,
      value: formatMetric(latest, options.unit),
      unit: '',
      hint: options.helper,
      icon: 'insights',
      accent: true,
      deltaLabel: delta === null ? '' : `${delta >= 0 ? '+' : ''}${formatMetric(delta, options.unit)}`,
    },
    {
      title: 'Baseline',
      value: formatMetric(baseline, options.unit),
      hint: 'Earliest comparable value in the current slice.',
      icon: 'history',
      tone: 'neutral',
    },
    {
      title: 'Rows',
      value: formatWholeNumber(options.rowCount),
      hint: 'Auditable records in the current slice.',
      icon: 'table_rows',
      tone: 'info',
    },
    {
      title: 'Provenance',
      value: options.provenanceLabel,
      hint: 'Release and methodology applied server-side.',
      icon: 'verified',
      tone: 'neutral',
    },
  ];
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return 'n/a';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(parsed);
}
