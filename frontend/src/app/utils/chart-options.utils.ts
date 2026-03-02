import { ChartOptions } from 'chart.js';

import { readCssVar, withAlpha } from './theme.utils';

export function buildStandardBarOptions(horizontal = false): ChartOptions<'bar'> {
  const divider = readCssVar('--nbms-divider');
  const muted = readCssVar('--nbms-text-muted');
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? 'y' : 'x',
    plugins: { legend: { display: false } },
    scales: {
      x: {
        beginAtZero: true,
        grid: { color: horizontal ? withAlpha(divider, 0.45) : 'transparent' },
        ticks: { color: muted, precision: 0 }
      },
      y: {
        beginAtZero: !horizontal,
        grid: { color: horizontal ? 'transparent' : withAlpha(divider, 0.45) },
        ticks: { color: muted, precision: 0 }
      }
    }
  };
}

export function buildStandardLineOptions(): ChartOptions<'line'> {
  const divider = readCssVar('--nbms-divider');
  const muted = readCssVar('--nbms-text-muted');
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        grid: { color: withAlpha(divider, 0.35) },
        ticks: { color: muted }
      },
      y: {
        beginAtZero: true,
        grid: { color: withAlpha(divider, 0.35) },
        ticks: { color: muted, precision: 0 }
      }
    }
  };
}

export function buildStandardDoughnutOptions(): ChartOptions<'doughnut'> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '68%',
    plugins: { legend: { display: false } }
  };
}
