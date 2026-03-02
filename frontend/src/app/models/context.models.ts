export type NbmsTabKey = string;
export type NbmsModeKey = 'table' | 'cards' | 'map';
export type NbmsGeoType = 'national' | 'province' | 'biome' | 'ecoregion' | 'municipality' | 'custom';
export type NbmsPublishedOnly = 0 | 1;

export interface NbmsContextQueryParams {
  tab: NbmsTabKey;
  mode: NbmsModeKey;
  report_cycle: string;
  release: string;
  method: string;
  geo_type: NbmsGeoType;
  geo_code: string;
  start_year: number | null;
  end_year: number | null;
  agg: string;
  metric: string;
  published_only: NbmsPublishedOnly;
  q: string;
  sort: string;
  view: string;
  compare: string;
  left: string;
  right: string;
}

export type NbmsContextPatch = Partial<NbmsContextQueryParams>;

export type NbmsContextOption = {
  value: string;
  label: string;
  helperText?: string;
  disabled?: boolean;
};

export type NbmsContextOptions = {
  reportCycles?: NbmsContextOption[];
  releases?: NbmsContextOption[];
  methods?: NbmsContextOption[];
  geoTypes?: NbmsContextOption[];
  geoCodes?: NbmsContextOption[];
  years?: number[];
};

export const DEFAULT_NBMS_CONTEXT: NbmsContextQueryParams = {
  tab: 'overview',
  mode: 'table',
  report_cycle: '',
  release: 'latest_approved',
  method: 'current',
  geo_type: 'national',
  geo_code: '',
  start_year: null,
  end_year: null,
  agg: 'national',
  metric: 'value',
  published_only: 1,
  q: '',
  sort: 'last_updated_desc',
  view: '',
  compare: '',
  left: '',
  right: ''
};
