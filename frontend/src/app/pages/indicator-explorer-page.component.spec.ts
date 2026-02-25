import { describe, expect, it } from 'vitest';

import { buildIndicatorNarrative } from './indicator-explorer-page.component';

describe('buildIndicatorNarrative', () => {
  it('renders readiness counts and contextual filters', () => {
    const text = buildIndicatorNarrative({
      total: 42,
      summary: {
        readiness_bands: { green: 18, amber: 15, red: 9 },
        due_soon_count: 9,
        blockers: [
          { code: 'missing_approved_method', label: 'Missing approved method', count: 12 },
          { code: 'no_recent_release', label: 'No recent release', count: 9 }
        ],
        top_gbf_targets: []
      },
      filters: { gbf_target: '3', geography_type: 'municipality', geography_code: 'ZA-GP' }
    });

    expect(text).toContain('Showing 42 indicators mapped to GBF Target 3 in municipality ZA-GP.');
    expect(text).toContain('18 are Green');
    expect(text).toContain('missing approved method (12)');
  });

  it('handles empty summary payload', () => {
    const text = buildIndicatorNarrative({
      total: 0,
      summary: undefined,
      filters: { gbf_target: '', geography_type: 'national', geography_code: '' }
    });
    expect(text).toContain('Showing 0 indicators');
    expect(text).toContain('No major blockers');
  });
});
