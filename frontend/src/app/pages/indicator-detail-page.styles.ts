export const indicatorDetailPageStyles = `
  .page {
    display: grid;
    gap: var(--nbms-space-4);
  }

  .hero,
  .tab-strip,
  .filter-bar,
  .panel,
  .detail-card {
    padding: var(--nbms-space-4);
  }

  .hero {
    display: grid;
    gap: var(--nbms-space-4);
    background:
      linear-gradient(
        145deg,
        color-mix(in srgb, var(--nbms-color-primary-100) 36%, var(--nbms-surface)) 0%,
        var(--nbms-surface) 62%,
        color-mix(in srgb, var(--nbms-color-secondary-100) 24%, var(--nbms-surface)) 100%
      );
  }

  .hero-main,
  .hero-heading,
  .hero-actions,
  .panel-head,
  .filter-actions,
  .section-head {
    display: flex;
    justify-content: space-between;
    gap: var(--nbms-space-3);
    align-items: flex-start;
  }

  .hero-main,
  .hero-copy,
  .hero-badges,
  .filter-grid,
  .kpi-strip,
  .analytics-main,
  .narrative-rail,
  .details-grid,
  .stack-list,
  .callout-stack,
  .used-by-grid,
  .check-grid,
  .distribution-grid {
    display: grid;
    gap: var(--nbms-space-3);
  }

  .breadcrumbs,
  .eyebrow,
  .distribution-label,
  .table-actions-count {
    color: var(--nbms-text-muted);
    font-size: var(--nbms-font-size-label-sm);
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  .breadcrumbs {
    display: flex;
    gap: var(--nbms-space-2);
    align-items: center;
  }

  .hero-copy h1,
  .panel h2,
  .detail-card h2 {
    margin: var(--nbms-space-1) 0 0;
  }

  .hero-copy h1 {
    font-size: clamp(2rem, 4vw, 3rem);
    line-height: 1.05;
  }

  .hero-summary,
  .panel-hint,
  .panel-copy,
  .rail-copy,
  .section-copy,
  .stack-item p,
  .check-card p,
  .empty-inline,
  .filter-note {
    margin: 0;
    color: var(--nbms-text-secondary);
    line-height: 1.6;
  }

  .hero-badges,
  .badge-row {
    display: flex;
    gap: var(--nbms-space-2);
    flex-wrap: wrap;
    align-items: center;
  }

  .hero-actions {
    flex-wrap: wrap;
  }

  .request-action {
    background: var(--nbms-color-primary-500);
    color: var(--nbms-surface);
  }

  .tab-strip {
    display: inline-flex;
    gap: var(--nbms-space-2);
    align-items: center;
  }

  .tab {
    border: 1px solid transparent;
    border-radius: var(--nbms-radius-pill);
    background: transparent;
    color: var(--nbms-text-secondary);
    cursor: pointer;
    font: inherit;
    font-weight: 700;
    padding: var(--nbms-space-2) var(--nbms-space-3);
  }

  .tab:focus-visible,
  .distribution-card:focus-visible {
    outline: none;
    box-shadow: var(--nbms-focus-ring);
  }

  .tab--active {
    background: color-mix(in srgb, var(--nbms-color-primary-500) 10%, transparent);
    border-color: color-mix(in srgb, var(--nbms-color-primary-500) 30%, var(--nbms-surface));
    color: var(--nbms-color-primary-700);
  }

  .filter-bar {
    display: grid;
    gap: var(--nbms-space-3);
  }

  .filter-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .filter-actions {
    align-items: center;
  }

  .kpi-strip {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .analytics-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.9fr);
    gap: var(--nbms-space-4);
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--nbms-space-4);
  }

  .chart-wrap {
    min-height: 320px;
  }

  .narrative-rail {
    align-self: start;
    position: sticky;
    top: 5.3rem;
  }

  .distribution-grid {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .distribution-card {
    display: grid;
    gap: var(--nbms-space-2);
    border: 1px solid var(--nbms-border);
    border-radius: var(--nbms-radius-lg);
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--nbms-surface) 92%, var(--nbms-color-secondary-100)) 0%,
      var(--nbms-surface) 100%
    );
    color: var(--nbms-text-primary);
    cursor: pointer;
    font: inherit;
    padding: var(--nbms-space-3);
    text-align: left;
  }

  .distribution-card[disabled] {
    cursor: default;
  }

  .distribution-card--active {
    border-color: color-mix(in srgb, var(--nbms-color-primary-500) 36%, var(--nbms-surface));
    background: color-mix(in srgb, var(--nbms-color-primary-100) 20%, var(--nbms-surface));
  }

  .distribution-card strong {
    font-size: var(--nbms-font-size-h3);
  }

  .distribution-value,
  .distribution-note {
    color: var(--nbms-text-secondary);
  }

  .distribution-bar {
    height: 8px;
    border-radius: var(--nbms-radius-pill);
    background: var(--nbms-surface-muted);
    overflow: hidden;
  }

  .distribution-bar b {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--nbms-color-primary-500);
  }

  .detail-card,
  .panel {
    display: grid;
    gap: var(--nbms-space-3);
  }

  .details-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-card--wide {
    grid-column: 1 / -1;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--nbms-space-3);
    margin: 0;
  }

  .info-grid div,
  .stack-item,
  .check-card {
    border: 1px solid var(--nbms-divider);
    border-radius: var(--nbms-radius-md);
    padding: var(--nbms-space-3);
    background: var(--nbms-surface);
  }

  .info-grid dt {
    color: var(--nbms-text-muted);
    font-size: var(--nbms-font-size-label-sm);
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .info-grid dd {
    margin: var(--nbms-space-1) 0 0;
    color: var(--nbms-text-primary);
    font-weight: 700;
  }

  .stack-item,
  .check-card {
    display: flex;
    justify-content: space-between;
    gap: var(--nbms-space-3);
    align-items: flex-start;
  }

  .stack-item--active {
    border-color: color-mix(in srgb, var(--nbms-color-primary-500) 26%, var(--nbms-surface));
    background: color-mix(in srgb, var(--nbms-color-primary-100) 18%, var(--nbms-surface));
  }

  .stack-item strong,
  .check-card strong {
    display: block;
  }

  .subsection {
    display: grid;
    gap: var(--nbms-space-2);
  }

  .subsection h3,
  .used-by-column h3 {
    margin: 0;
  }

  .check-grid,
  .used-by-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .used-by-column {
    display: grid;
    gap: var(--nbms-space-2);
  }

  .used-by-column ul {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--nbms-text-secondary);
  }

  .empty-state {
    border: 1px dashed var(--nbms-border);
    border-radius: var(--nbms-radius-lg);
    color: var(--nbms-text-muted);
    padding: var(--nbms-space-4);
    text-align: center;
  }

  @media (max-width: 1400px) {
    .filter-grid,
    .kpi-strip {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 1180px) {
    .analytics-layout,
    .chart-grid,
    .details-grid,
    .check-grid,
    .used-by-grid,
    .info-grid {
      grid-template-columns: 1fr;
    }

    .narrative-rail {
      position: static;
    }
  }

  @media (max-width: 860px) {
    .hero-main,
    .hero-heading,
    .hero-actions,
    .panel-head,
    .filter-actions,
    .section-head,
    .stack-item,
    .check-card {
      flex-direction: column;
    }

    .filter-grid,
    .kpi-strip {
      grid-template-columns: 1fr;
    }
  }
`;
