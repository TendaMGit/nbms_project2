import type { IndicatorDimension, IndicatorVisualProfile } from './api.models';

export interface IndicatorPackDescriptor {
  indicatorUuid: string;
  packId: string;
  packLabel: string;
  profile: IndicatorVisualProfile;
  dimensions: IndicatorDimension[];
}

export interface IndicatorPackLegendItem {
  value: string;
  label: string;
  colorToken: string;
  description?: string;
}

export interface IndicatorPackLegend {
  id: string;
  title: string;
  dimensionId: string;
  items: IndicatorPackLegendItem[];
}

