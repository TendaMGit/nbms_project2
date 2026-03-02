import { ChartData, ChartOptions } from 'chart.js';

import type {
  IndicatorDatasetItem,
  IndicatorDatasetsResponse,
  IndicatorDetailResponse,
  IndicatorMethodProfileResponse,
  IndicatorSeriesResponse
} from '../models/api.models';

export type IndicatorTab = 'indicator' | 'details' | 'evidence' | 'audit';
export type GeographyFocus = 'national' | 'province' | 'biome';
export type PillTone = 'neutral' | 'success' | 'warn' | 'error' | 'info';
export type KpiTone = 'neutral' | 'positive' | 'negative' | 'info';
export type NoteTone = 'info' | 'warning' | 'error';

export interface IndicatorDetailContext {
  tab: IndicatorTab;
  report_cycle: string;
  method: string;
  dataset_release: string;
  geography: GeographyFocus;
  start_year: number | null;
  end_year: number | null;
}

export interface TrendPoint {
  year: number;
  value: number;
}

interface ProvinceTrendPoint extends TrendPoint {
  region: string;
}

export interface DistributionCard {
  region: string;
  geographyType: string;
  value: number;
  valueLabel: string;
  progress: number;
  note: string;
  active: boolean;
}

export interface DetailTableRow {
  year: number;
  region: string;
  geographyType: string;
  value: number;
  valueLabel: string;
  status: string;
  statusTone: PillTone;
  notes: string;
}

export interface InfoRow {
  label: string;
  value: string;
}

export interface QualityNote {
  tone: NoteTone;
  title: string;
  body: string;
}

export interface MethodologyVersionItem {
  title: string;
  subtitle: string;
  badgeLabel: string;
  badgeTone: PillTone;
  active: boolean;
}

export interface MethodProfileItem {
  title: string;
  subtitle: string;
  badgeLabel: string;
  badgeTone: PillTone;
}

export interface DatasetReleaseItem {
  title: string;
  subtitle: string;
  statusLabel: string;
  statusTone: PillTone;
  accessLabel: string;
  accessTone: PillTone;
}

export interface SpatialLayerItem {
  title: string;
  subtitle: string;
  statusLabel: string;
  statusTone: PillTone;
  accessLabel: string;
  accessTone: PillTone;
}

export interface RegistryCheckItem {
  key: string;
  detail: string;
  badgeLabel: string;
  badgeTone: PillTone;
}

export interface UsedByGroup {
  title: string;
  items: string[];
}

export interface EvidenceItem {
  title: string;
  subtitle: string;
  url: string;
}

export interface KpiCardVm {
  title: string;
  value: string;
  unit: string;
  hint: string;
  icon: string;
  tone: KpiTone;
  accent?: boolean;
  deltaLabel?: string;
  progressValue?: number | null;
  progressMax?: number;
  progressLabel?: string;
}

export interface DetailVm {
  detail: IndicatorDetailResponse;
  datasets: IndicatorDatasetsResponse;
  methods: IndicatorMethodProfileResponse;
  context: IndicatorDetailContext;
  activeRegion: string | null;
  leadSummary: string;
  reportCycleOptions: Array<{ value: string; label: string }>;
  methodOptions: Array<{ value: string; label: string }>;
  datasetOptions: Array<{ value: string; label: string }>;
  yearOptions: number[];
  defaultStartYear: number | null;
  defaultEndYear: number | null;
  headerBadges: Array<{ label: string; tone: PillTone }>;
  headerReadinessScore: number;
  headerReadinessState: 'ready' | 'warning' | 'blocked';
  kpis: KpiCardVm[];
  trendTitle: string;
  trendHint: string;
  trendChart: ChartData<'line'> | null;
  breakdownTitle: string;
  breakdownHint: string;
  breakdownChart: ChartData<'bar'> | null;
  breakdownRows: DistributionCard[];
  distributionTitle: string;
  distributionHelper: string;
  distributionCards: DistributionCard[];
  distributionEmptyMessage: string;
  tableRows: DetailTableRow[];
  interpretation: string;
  description: string;
  dataQualityNotes: QualityNote[];
  identityRows: InfoRow[];
  governanceRows: InfoRow[];
  governanceBadges: Array<{ label: string; tone: PillTone }>;
  methodologyVersions: MethodologyVersionItem[];
  methodProfiles: MethodProfileItem[];
  datasetReleases: DatasetReleaseItem[];
  pipelineRows: InfoRow[];
  pipelineCallout: QualityNote | null;
  spatialOverallLabel: string;
  spatialOverallTone: PillTone;
  spatialNotes: string;
  spatialLayers: SpatialLayerItem[];
  registryOverallLabel: string;
  registryOverallTone: PillTone;
  registryNotes: string;
  registryChecks: RegistryCheckItem[];
  usedByGroups: UsedByGroup[];
  evidenceItems: EvidenceItem[];
}

export const DEFAULT_REPORT_CYCLE = 'nr7_current';

export function emptySeries(uuid: string, aggregation: string): IndicatorSeriesResponse {
  return { indicator_uuid: uuid, aggregation, results: [] };
}

export function emptyDatasets(uuid: string): IndicatorDatasetsResponse {
  return { indicator_uuid: uuid, datasets: [] };
}

export function emptyMethods(uuid: string): IndicatorMethodProfileResponse {
  return { indicator_uuid: uuid, profiles: [] };
}

export function normalizeContext(value: Partial<IndicatorDetailContext>, years: number[]): IndicatorDetailContext {
  const defaultStart = years[0] ?? null;
  const defaultEnd = years[years.length - 1] ?? null;
  let startYear = toNullableNumber(value.start_year);
  let endYear = toNullableNumber(value.end_year);

  if (years.length) {
    if (!years.includes(startYear ?? Number.NaN)) {
      startYear = defaultStart;
    }
    if (!years.includes(endYear ?? Number.NaN)) {
      endYear = defaultEnd;
    }
    if ((startYear ?? 0) > (endYear ?? 0)) {
      [startYear, endYear] = [endYear, startYear];
    }
  } else {
    startYear = null;
    endYear = null;
  }

  return {
    tab: toTab(value.tab),
    report_cycle: String(value.report_cycle ?? DEFAULT_REPORT_CYCLE).trim() || DEFAULT_REPORT_CYCLE,
    method: String(value.method ?? '').trim(),
    dataset_release: String(value.dataset_release ?? '').trim(),
    geography: toGeography(value.geography),
    start_year: startYear,
    end_year: endYear
  };
}

export function buildIndicatorDetailVm(
  detail: IndicatorDetailResponse,
  datasets: IndicatorDatasetsResponse,
  methods: IndicatorMethodProfileResponse,
  yearSeries: IndicatorSeriesResponse,
  provinceHistory: IndicatorSeriesResponse,
  provinceSnapshot: IndicatorSeriesResponse,
  yearOptions: number[],
  context: IndicatorDetailContext,
  activeRegion: string | null
): DetailVm {
  const nationalTrendRows = nationalTrend(yearSeries, context.start_year, context.end_year);
  const provinceTrendRows = provinceTrend(provinceHistory, context.start_year, context.end_year);
  const provinceAverageRows = averageProvinceTrend(provinceTrendRows);
  const unit = primarySeriesUnit(detail);
  const latestNational = nationalTrendRows[nationalTrendRows.length - 1] ?? null;
  let trendRows: TrendPoint[] = nationalTrendRows;
  let trendTitle = 'Trend over time (National)';
  let trendHint = rangeHint(context.start_year, context.end_year);

  if (context.geography === 'province') {
    if (activeRegion) {
      trendRows = provinceTrendRows.filter((row) => row.region === activeRegion);
      trendTitle = `Trend over time (${activeRegion})`;
      trendHint = 'Focused on the currently selected province.';
    } else {
      trendRows = provinceAverageRows;
      trendTitle = 'Trend over time (Province average)';
      trendHint = 'Select a province from the breakdown chart or distribution cards to focus one region.';
    }
  } else if (context.geography === 'biome') {
    trendRows = [];
    trendTitle = 'Trend over time (Biome)';
    trendHint = 'Biome analytics are not yet wired to the series endpoint.';
  }

  const breakdownRows = provinceSnapshotCards(provinceSnapshot, unit, activeRegion);
  const distributionCards =
    context.geography === 'national'
      ? nationalDistributionCards(latestNational, unit)
      : context.geography === 'province'
        ? breakdownRows
        : [];

  return {
    detail,
    datasets,
    methods,
    context,
    activeRegion,
    leadSummary: detail.narrative?.summary || detail.indicator.description || 'Narrative summary not yet published.',
    reportCycleOptions: [
      { value: DEFAULT_REPORT_CYCLE, label: 'NR7 current' },
      { value: 'nr7_baseline', label: 'NR7 baseline' },
      { value: 'nr6_archive', label: 'NR6 archive' }
    ],
    methodOptions: methods.profiles.map((profile) => ({
      value: profile.uuid,
      label: `${profile.method_type} · ${profile.implementation_key}`
    })),
    datasetOptions: datasets.datasets.map((dataset) => ({ value: dataset.uuid, label: dataset.title })),
    yearOptions,
    defaultStartYear: yearOptions[0] ?? null,
    defaultEndYear: yearOptions[yearOptions.length - 1] ?? null,
    headerBadges: headerBadges(detail),
    headerReadinessScore: normalizeScore(detail.pipeline?.readiness_score ?? detail.indicator.readiness_score),
    headerReadinessState: readinessState(detail.pipeline?.readiness_status || detail.indicator.readiness_status),
    kpis: buildKpis(detail, nationalTrendRows, unit),
    trendTitle,
    trendHint,
    trendChart: trendRows.length ? buildTrendChart(trendRows, context.geography, Boolean(activeRegion)) : null,
    breakdownTitle: context.end_year ? `Breakdown (Province, ${context.end_year})` : 'Breakdown (Province)',
    breakdownHint: breakdownRows.length
      ? `${breakdownRows.length} province rows in the selected snapshot`
      : 'No province snapshot is published for the selected year.',
    breakdownChart: breakdownRows.length ? buildBreakdownChart(breakdownRows) : null,
    breakdownRows,
    distributionTitle:
      context.geography === 'national'
        ? 'Geographic distribution (National)'
        : context.geography === 'province'
          ? 'Geographic distribution (Province)'
          : 'Geographic distribution (Biome)',
    distributionHelper:
      context.geography === 'national'
        ? 'National is the active geography, so the card grid shows the latest published national reading.'
        : context.geography === 'province'
          ? 'Select a province to cross-filter the trend line and the detailed data table.'
          : 'Biome selection is stored in the URL but still needs backend support.',
    distributionCards,
    distributionEmptyMessage:
      context.geography === 'biome'
        ? 'Biome distribution is not yet available. Backend support is needed for GET /api/indicators/:uuid/series?agg=biome.'
        : 'No distribution cards are available for the current selection.',
    tableRows: buildTableRows(detail, context.geography, activeRegion, nationalTrendRows, provinceTrendRows, breakdownRows, unit, context.end_year),
    interpretation: detail.narrative?.summary || 'Interpretation text is not yet published for this indicator.',
    description: detail.indicator.description || 'Indicator description is not yet published.',
    dataQualityNotes: buildQualityNotes(detail, context),
    identityRows: buildIdentityRows(detail),
    governanceRows: buildGovernanceRows(detail),
    governanceBadges: governanceBadges(detail),
    methodologyVersions: detail.methodologies.map((item) => ({
      title: `${item.methodology_code} v${item.version}`,
      subtitle: `${item.methodology_title} · Effective ${formatDateLabel(item.effective_date)}`,
      badgeLabel: item.is_primary ? 'Current' : 'Version',
      badgeTone: item.is_primary ? 'success' : 'info',
      active: item.is_primary
    })),
    methodProfiles: methods.profiles.map((item) => ({
      title: `${item.method_type} · ${item.implementation_key}`,
      subtitle: item.summary || item.readiness_notes || 'Execution profile available.',
      badgeLabel: item.readiness_state || 'Unknown',
      badgeTone: toneForStatus(item.readiness_state, 'success')
    })),
    datasetReleases: datasets.datasets.map((item) => datasetReleaseItem(item)),
    pipelineRows: buildPipelineRows(detail),
    pipelineCallout: buildPipelineCallout(detail),
    spatialOverallLabel: detail.spatial_readiness?.overall_ready ? 'Spatially ready' : 'Spatial inputs incomplete',
    spatialOverallTone: detail.spatial_readiness?.overall_ready ? 'success' : 'warn',
    spatialNotes: detail.spatial_readiness?.notes || 'Spatial readiness notes are not published.',
    spatialLayers: (detail.spatial_readiness?.layer_requirements ?? []).map((layer) => ({
      title: layer.title,
      subtitle: `${layer.layer_code} · ${layer.last_ingestion_at ? `Last ingestion ${formatDateLabel(layer.last_ingestion_at)}` : 'No ingestion history'}`,
      statusLabel: layer.available ? 'Available' : 'Missing',
      statusTone: layer.available ? 'success' : 'warn',
      accessLabel: layer.sensitivity || 'Unknown access',
      accessTone: toneForSensitivity(layer.sensitivity)
    })),
    registryOverallLabel: detail.registry_readiness?.overall_ready ? 'Registry ready' : 'Registry gaps detected',
    registryOverallTone: detail.registry_readiness?.overall_ready ? 'success' : 'warn',
    registryNotes: detail.registry_readiness?.notes || 'Registry readiness notes are not published.',
    registryChecks: (detail.registry_readiness?.checks ?? []).map((check) => ({
      key: check.key,
      detail: `${check.available} available / minimum ${check.minimum}`,
      badgeLabel: check.required ? 'Required' : 'Optional',
      badgeTone: check.available >= check.minimum ? 'success' : check.required ? 'warn' : 'info'
    })),
    usedByGroups: buildUsedByGroups(detail),
    evidenceItems: detail.evidence.map((item) => ({
      title: item.title,
      subtitle: item.evidence_type || 'Evidence item',
      url: item.source_url
    }))
  };
}

function nationalTrend(series: IndicatorSeriesResponse, startYear: number | null, endYear: number | null): TrendPoint[] {
  return series.results
    .map((row) => ({ year: Number(row.bucket), value: row.numeric_mean }))
    .filter((row) => Number.isFinite(row.year) && typeof row.value === 'number' && inRange(row.year, startYear, endYear))
    .sort((a, b) => a.year - b.year)
    .map((row) => ({ year: row.year, value: row.value as number }));
}

function provinceTrend(series: IndicatorSeriesResponse, startYear: number | null, endYear: number | null): ProvinceTrendPoint[] {
  const rows: ProvinceTrendPoint[] = [];
  for (const bucket of series.results) {
    const region = String(bucket.bucket);
    for (const value of bucket.values) {
      if (typeof value.value_numeric !== 'number' || !Number.isFinite(value.year) || !inRange(value.year, startYear, endYear)) {
        continue;
      }
      rows.push({ region, year: value.year, value: value.value_numeric });
    }
  }
  return rows.sort((a, b) => a.year - b.year || a.region.localeCompare(b.region));
}

function averageProvinceTrend(rows: ProvinceTrendPoint[]): TrendPoint[] {
  const grouped = new Map<number, { total: number; count: number }>();
  for (const row of rows) {
    const entry = grouped.get(row.year) ?? { total: 0, count: 0 };
    entry.total += row.value;
    entry.count += 1;
    grouped.set(row.year, entry);
  }
  return Array.from(grouped.entries())
    .map(([year, entry]) => ({ year, value: entry.count ? entry.total / entry.count : 0 }))
    .sort((a, b) => a.year - b.year);
}

function provinceSnapshotCards(series: IndicatorSeriesResponse, unit: string, activeRegion: string | null): DistributionCard[] {
  const rows = series.results
    .map((row) => ({ region: String(row.bucket), value: typeof row.numeric_mean === 'number' ? row.numeric_mean : null }))
    .filter((row) => typeof row.value === 'number')
    .sort((a, b) => (b.value as number) - (a.value as number));
  const max = Math.max(...rows.map((row) => row.value as number), 0);
  return rows.map((row) => ({
    region: row.region,
    geographyType: 'Province',
    value: row.value as number,
    valueLabel: formatMetric(row.value as number, unit),
    progress: max > 0 ? Math.max(8, Math.round(((row.value as number) / max) * 100)) : 0,
    note: activeRegion === row.region ? 'Focused selection' : 'Snapshot value',
    active: activeRegion === row.region
  }));
}

function nationalDistributionCards(point: TrendPoint | null, unit: string): DistributionCard[] {
  if (!point) {
    return [];
  }
  return [
    {
      region: 'South Africa',
      geographyType: 'National',
      value: point.value,
      valueLabel: formatMetric(point.value, unit),
      progress: 100,
      note: `Latest national value (${point.year})`,
      active: false
    }
  ];
}

function buildTrendChart(rows: TrendPoint[], geography: GeographyFocus, focusedRegion: boolean): ChartData<'line'> {
  const stroke =
    geography === 'province' && focusedRegion ? tokenValue('--nbms-color-secondary-500') : tokenValue('--nbms-color-primary-500');
  return {
    labels: rows.map((row) => String(row.year)),
    datasets: [
      {
        data: rows.map((row) => row.value),
        borderColor: stroke,
        backgroundColor: withAlpha(stroke, 0.18),
        fill: true,
        tension: 0.32,
        pointRadius: 3,
        pointHoverRadius: 5
      }
    ]
  };
}

function buildBreakdownChart(rows: DistributionCard[]): ChartData<'bar'> {
  const active = tokenValue('--nbms-color-primary-500');
  const resting = withAlpha(tokenValue('--nbms-color-secondary-500'), 0.72);
  return {
    labels: rows.map((row) => row.region),
    datasets: [
      {
        data: rows.map((row) => row.value),
        backgroundColor: rows.map((row) => (row.active ? active : resting)),
        borderRadius: 10,
        maxBarThickness: 26
      }
    ]
  };
}

function buildKpis(detail: IndicatorDetailResponse, trend: TrendPoint[], unit: string): KpiCardVm[] {
  const first = trend[0] ?? null;
  const last = trend[trend.length - 1] ?? null;
  const delta = first && last ? last.value - first.value : null;
  const coverage = detail.indicator.coverage;
  const readiness = normalizeScore(detail.pipeline?.readiness_score ?? detail.indicator.readiness_score);
  return [
    {
      title: 'Latest value',
      value: last ? metricNumber(last.value) : '—',
      unit,
      hint: last ? `Latest published reading in ${last.year}` : 'No published series value.',
      icon: 'insights',
      tone: 'neutral',
      accent: true,
      deltaLabel: delta === null ? '' : `${signedMetric(delta)} vs baseline`
    },
    {
      title: 'Baseline',
      value: first ? metricNumber(first.value) : '—',
      unit,
      hint: first ? `Earliest value in range (${first.year})` : 'Baseline value not available.',
      icon: 'history',
      tone: 'neutral'
    },
    {
      title: 'Target',
      value: '—',
      unit: '',
      hint: 'No numeric target is published in the current payload.',
      icon: 'flag',
      tone: 'info'
    },
    {
      title: 'Coverage',
      value: coverage.geography || 'Not set',
      unit: '',
      hint:
        coverage.time_start_year && coverage.time_end_year
          ? `${coverage.time_start_year} to ${coverage.time_end_year}`
          : 'Temporal coverage not published.',
      icon: 'public',
      tone: 'neutral'
    },
    {
      title: 'Readiness score',
      value: String(readiness),
      unit: '/100',
      hint: detail.pipeline?.readiness_status || detail.indicator.readiness_status || 'Readiness status not published.',
      icon: 'checklist',
      tone: readiness >= 75 ? 'positive' : readiness <= 40 ? 'negative' : 'info',
      progressValue: readiness,
      progressMax: 100,
      progressLabel: `${readiness}% readiness`
    }
  ];
}

function buildTableRows(
  detail: IndicatorDetailResponse,
  geography: GeographyFocus,
  activeRegion: string | null,
  nationalRows: TrendPoint[],
  provinceRows: ProvinceTrendPoint[],
  breakdownRows: DistributionCard[],
  unit: string,
  selectedYear: number | null
): DetailTableRow[] {
  if (geography === 'biome') {
    return [];
  }

  const statusLabel = derivedStatus(detail);
  const statusTone = toneForStatus(statusLabel, 'success');

  if (geography === 'province') {
    const focusedRows = activeRegion ? provinceRows.filter((row) => row.region === activeRegion) : [];
    if (focusedRows.length) {
      return focusedRows.map((row) => ({
        year: row.year,
        region: row.region,
        geographyType: 'Province',
        value: row.value,
        valueLabel: formatMetric(row.value, unit),
        status: statusLabel,
        statusTone,
        notes: 'Focused provincial time series'
      }));
    }

    return breakdownRows.map((row) => ({
      year: selectedYear ?? nationalRows[nationalRows.length - 1]?.year ?? new Date().getUTCFullYear(),
      region: row.region,
      geographyType: row.geographyType,
      value: row.value,
      valueLabel: row.valueLabel,
      status: statusLabel,
      statusTone,
      notes: row.note
    }));
  }

  return nationalRows.map((row) => ({
    year: row.year,
    region: 'South Africa',
    geographyType: 'National',
    value: row.value,
    valueLabel: formatMetric(row.value, unit),
    status: statusLabel,
    statusTone,
    notes:
      detail.pipeline?.data_last_refreshed_at && row.year === selectedYear
        ? `Latest refresh ${formatDateLabel(detail.pipeline.data_last_refreshed_at)}`
        : 'National time-series value'
  }));
}

function buildQualityNotes(detail: IndicatorDetailResponse, context: IndicatorDetailContext): QualityNote[] {
  const notes: QualityNote[] = [];
  if (context.report_cycle !== DEFAULT_REPORT_CYCLE || context.method || context.dataset_release) {
    notes.push({
      tone: 'info',
      title: 'Filter wiring',
      body: 'Report cycle, methodology, and dataset release selections are stored in the URL but not yet wired to series refetching.'
    });
  }
  if (detail.narrative?.limitations) {
    notes.push({ tone: 'warning', title: 'Narrative limitations', body: detail.narrative.limitations });
  }
  if (detail.pipeline?.latest_pipeline_run_status) {
    notes.push({
      tone: detail.pipeline.latest_pipeline_run_status === 'succeeded' ? 'info' : 'warning',
      title: 'Pipeline status',
      body: `Latest run status: ${detail.pipeline.latest_pipeline_run_status}`
    });
  }
  if (context.geography === 'biome') {
    notes.push({
      tone: 'warning',
      title: 'Biome support pending',
      body: 'Biome analytics need backend support on the indicator series endpoint before this selection can render data.'
    });
  }
  if (detail.registry_readiness && !detail.registry_readiness.overall_ready) {
    notes.push({
      tone: 'warning',
      title: 'Registry readiness',
      body: detail.registry_readiness.notes || 'Registry dependencies still have gaps.'
    });
  }
  if (detail.indicator.qa_status && toneForStatus(detail.indicator.qa_status, 'success') === 'error') {
    notes.push({
      tone: 'error',
      title: 'QA status',
      body: `This indicator is currently marked as ${detail.indicator.qa_status}.`
    });
  }
  return notes;
}

function buildIdentityRows(detail: IndicatorDetailResponse): InfoRow[] {
  const series = detail.series[0];
  return [
    { label: 'Code', value: detail.indicator.code },
    { label: 'Indicator type', value: detail.indicator.indicator_type || 'Not published' },
    { label: 'Unit', value: series?.unit || 'Not published' },
    { label: 'Value type', value: series?.value_type || 'Not published' },
    { label: 'Update frequency', value: detail.indicator.update_frequency || 'Not published' },
    { label: 'Reporting capability', value: detail.indicator.reporting_capability || 'Not published' },
    { label: 'Organisation', value: detail.indicator.organisation.name || 'Not assigned' },
    { label: 'National target', value: detail.indicator.national_target.code || detail.indicator.national_target.title || 'Not linked' }
  ];
}

function buildGovernanceRows(detail: IndicatorDetailResponse): InfoRow[] {
  return [
    { label: 'Lifecycle status', value: detail.indicator.status || 'Unknown' },
    { label: 'QA status', value: detail.indicator.qa_status || 'Unknown' },
    { label: 'Sensitivity / access', value: detail.indicator.sensitivity || 'Unknown' },
    { label: 'Approval workflow', value: detail.pipeline?.release_workflow.status || 'No release workflow state published' },
    { label: 'Pipeline maturity', value: detail.pipeline?.pipeline_maturity || detail.indicator.pipeline_maturity || 'Not published' },
    { label: 'Method readiness', value: detail.indicator.method_readiness_state || 'Not published' }
  ];
}

function buildPipelineRows(detail: IndicatorDetailResponse): InfoRow[] {
  return [
    { label: 'Last refreshed', value: formatDateLabel(detail.pipeline?.data_last_refreshed_at) },
    { label: 'Next expected update', value: formatDateLabel(detail.pipeline?.next_expected_update_on || detail.indicator.next_expected_update_on) },
    { label: 'Latest year', value: detail.pipeline?.latest_year ? String(detail.pipeline.latest_year) : 'Unknown' },
    { label: 'Latest run UUID', value: detail.pipeline?.latest_pipeline_run_uuid || 'Not published' },
    { label: 'Latest run status', value: detail.pipeline?.latest_pipeline_run_status || 'Not published' },
    { label: 'Release workflow', value: detail.pipeline?.release_workflow.status || 'Not published' }
  ];
}

function buildPipelineCallout(detail: IndicatorDetailResponse): QualityNote | null {
  const workflow = detail.pipeline?.release_workflow;
  if (!workflow?.status) {
    return null;
  }
  if (workflow.status.toLowerCase().includes('pending')) {
    return { tone: 'warning', title: 'Workflow pending', body: `Current release workflow state: ${workflow.status}.` };
  }
  if (workflow.status.toLowerCase().includes('approved')) {
    return { tone: 'info', title: 'Workflow approved', body: `Current release workflow state: ${workflow.status}.` };
  }
  return null;
}

function buildUsedByGroups(detail: IndicatorDetailResponse): UsedByGroup[] {
  return [
    {
      title: 'Framework targets',
      items:
        detail.used_by_graph?.framework_targets.map((item) =>
          [item.framework_code, item.target_code, item.target_title].filter(Boolean).join(' · ')
        ) ?? []
    },
    {
      title: 'Monitoring programmes',
      items: detail.used_by_graph?.programmes.map((item) => `${item.programme_code} · ${item.title}`) ?? []
    },
    {
      title: 'Report products',
      items: detail.used_by_graph?.report_products.map((item) => `${item.code} · ${item.title} (${item.version})`) ?? []
    }
  ];
}

function headerBadges(detail: IndicatorDetailResponse): Array<{ label: string; tone: PillTone }> {
  return [
    { label: detail.indicator.status || 'Unknown status', tone: toneForStatus(detail.indicator.status, 'success') },
    { label: `QA: ${detail.indicator.qa_status || 'Unknown'}`, tone: toneForStatus(detail.indicator.qa_status, 'info') },
    { label: `Access: ${detail.indicator.sensitivity || 'Unknown'}`, tone: toneForSensitivity(detail.indicator.sensitivity) },
    { label: detail.pipeline?.release_workflow.status || 'Workflow not published', tone: toneForStatus(detail.pipeline?.release_workflow.status, 'success') }
  ];
}

function governanceBadges(detail: IndicatorDetailResponse): Array<{ label: string; tone: PillTone }> {
  return [
    { label: detail.indicator.status || 'Unknown status', tone: toneForStatus(detail.indicator.status, 'success') },
    { label: detail.indicator.qa_status || 'Unknown QA', tone: toneForStatus(detail.indicator.qa_status, 'info') },
    { label: detail.indicator.sensitivity || 'Unknown access', tone: toneForSensitivity(detail.indicator.sensitivity) }
  ];
}

function datasetReleaseItem(item: IndicatorDatasetItem): DatasetReleaseItem {
  return {
    title: item.title,
    subtitle: item.organisation ? `${item.organisation} · ${item.note || 'Linked dataset'}` : item.note || 'Linked dataset',
    statusLabel: item.status || 'Unknown',
    statusTone: toneForStatus(item.status, 'success'),
    accessLabel: item.sensitivity || 'Unknown access',
    accessTone: toneForSensitivity(item.sensitivity)
  };
}

function derivedStatus(detail: IndicatorDetailResponse): string {
  const qa = (detail.indicator.qa_status || '').toLowerCase();
  const seriesStatus = (detail.series[0]?.status || '').toLowerCase();
  if (/(approved|verified|passed)/.test(qa) || /(published|approved)/.test(seriesStatus)) {
    return 'Verified';
  }
  if (/(draft|review|pending|warning)/.test(qa) || /(draft|pending|review)/.test(seriesStatus)) {
    return 'Provisional';
  }
  return detail.indicator.qa_status || detail.series[0]?.status || 'Unknown';
}

function primarySeriesUnit(detail: IndicatorDetailResponse): string {
  return detail.series[0]?.unit || '';
}

function rangeHint(startYear: number | null, endYear: number | null): string {
  return startYear && endYear ? `${startYear} to ${endYear}` : 'Published time series';
}

function inRange(year: number, startYear: number | null, endYear: number | null): boolean {
  return startYear === null || endYear === null || (year >= startYear && year <= endYear);
}

function metricNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value);
}

function formatMetric(value: number, unit: string): string {
  const number = metricNumber(value);
  return unit ? `${number}${unit.startsWith('%') ? unit : ` ${unit}`}` : number;
}

function signedMetric(value: number): string {
  return `${value >= 0 ? '+' : ''}${metricNumber(value)}`;
}

function normalizeScore(value: number | null | undefined): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function readinessState(value: string | null | undefined): 'ready' | 'warning' | 'blocked' {
  const normalized = (value || '').toLowerCase();
  if (normalized === 'ready') {
    return 'ready';
  }
  if (normalized === 'warning') {
    return 'warning';
  }
  return 'blocked';
}

function toneForStatus(value: string | null | undefined, successTone: PillTone): PillTone {
  const normalized = (value || '').toLowerCase();
  if (!normalized) {
    return 'neutral';
  }
  if (/(approved|published|verified|passed|ready|succeeded|active)/.test(normalized)) {
    return successTone;
  }
  if (/(pending|draft|review|warning|partial)/.test(normalized)) {
    return 'warn';
  }
  if (/(failed|error|blocked|rejected|missing)/.test(normalized)) {
    return 'error';
  }
  return 'info';
}

function toneForSensitivity(value: string | null | undefined): PillTone {
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

export function toTab(value: string | null | undefined): IndicatorTab {
  if (value === 'details' || value === 'evidence' || value === 'audit') {
    return value;
  }
  return 'indicator';
}

export function toGeography(value: string | null | undefined): GeographyFocus {
  return value === 'province' || value === 'biome' ? value : 'national';
}

export function toNullableNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatDateLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Not published';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(parsed);
}

export function buildLineOptions(): ChartOptions<'line'> {
  const divider = tokenValue('--nbms-divider');
  const muted = tokenValue('--nbms-text-muted');
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: withAlpha(divider, 0.45) }, ticks: { color: muted } },
      y: { beginAtZero: true, grid: { color: withAlpha(divider, 0.45) }, ticks: { color: muted, precision: 0 } }
    }
  };
}

export function buildBarOptions(): ChartOptions<'bar'> {
  const divider = tokenValue('--nbms-divider');
  const muted = tokenValue('--nbms-text-muted');
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { beginAtZero: true, grid: { color: withAlpha(divider, 0.45) }, ticks: { color: muted, precision: 0 } },
      y: { grid: { display: false }, ticks: { color: muted } }
    }
  };
}

function tokenValue(name: string): string {
  if (typeof document === 'undefined') {
    return 'currentColor';
  }
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || 'currentColor';
}

function withAlpha(color: string, alpha: number): string {
  const channels = toRgbChannels(color);
  return channels ? `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})` : color;
}

function toRgbChannels(color: string): [number, number, number] | null {
  const hex = color.trim().match(/^#([0-9a-f]{6})$/i);
  if (hex) {
    const value = hex[1];
    return [Number.parseInt(value.slice(0, 2), 16), Number.parseInt(value.slice(2, 4), 16), Number.parseInt(value.slice(4, 6), 16)];
  }
  const rgb = color.match(/^rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
  if (rgb) {
    return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
  }
  return null;
}
