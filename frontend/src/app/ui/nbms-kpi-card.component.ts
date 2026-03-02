import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'nbms-kpi-card',
  standalone: true,
  imports: [NgIf, MatIconModule],
  template: `
    <article class="kpi nbms-card-surface" [class.kpi-accent]="accent" [attr.data-tone]="tone">
      <header>
        <div class="heading">
          <span>{{ title }}</span>
          <small *ngIf="eyebrow">{{ eyebrow }}</small>
        </div>
        <mat-icon *ngIf="icon">{{ icon }}</mat-icon>
      </header>
      <div class="value-row">
        <div class="value-wrap">
          <div class="value">{{ value }}</div>
          <span class="unit" *ngIf="unit">{{ unit }}</span>
        </div>
        <span class="delta" *ngIf="deltaLabel">{{ deltaLabel }}</span>
      </div>
      <div class="progress" *ngIf="showProgress">
        <div class="progress-track" aria-hidden="true"><b [style.width.%]="progressPercent"></b></div>
        <span>{{ progressLabel || ('Progress ' + progressPercent + '%') }}</span>
      </div>
      <p *ngIf="hint">{{ hint }}</p>
    </article>
  `,
  styles: [
    `
      .kpi {
        --kpi-accent-color: var(--nbms-color-primary-500);
        padding: var(--nbms-space-4);
        display: grid;
        gap: var(--nbms-space-2);
        border: 1px solid color-mix(in srgb, var(--nbms-border) 88%, var(--nbms-surface));
      }

      .kpi.kpi-accent {
        background:
          linear-gradient(
            180deg,
            color-mix(in srgb, var(--nbms-color-primary-100) 40%, var(--nbms-surface)) 0%,
            var(--nbms-surface) 100%
          );
      }

      .kpi header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: var(--nbms-text-secondary);
        font-size: var(--nbms-font-size-label);
      }

      .heading {
        display: grid;
        gap: var(--nbms-space-1);
      }

      .heading small {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .value-row {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-2);
        align-items: flex-end;
        flex-wrap: wrap;
      }

      .value-wrap {
        display: flex;
        align-items: flex-end;
        gap: var(--nbms-space-1);
      }

      .kpi .value {
        font-size: clamp(var(--nbms-font-size-h2), 3vw, 2rem);
        font-weight: 700;
        line-height: 1.1;
        color: var(--nbms-text-primary);
      }

      .unit,
      .delta {
        font-size: var(--nbms-font-size-label);
        color: var(--nbms-text-secondary);
      }

      .delta {
        font-weight: 700;
      }

      .progress {
        display: grid;
        gap: var(--nbms-space-1);
      }

      .progress span {
        font-size: var(--nbms-font-size-label-sm);
        color: var(--nbms-text-muted);
      }

      .progress-track {
        height: 8px;
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-surface-muted);
        overflow: hidden;
      }

      .progress-track b {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: var(--kpi-accent-color);
      }

      .kpi p {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      .kpi[data-tone='positive'] {
        --kpi-accent-color: var(--nbms-color-success);
      }

      .kpi[data-tone='negative'] {
        --kpi-accent-color: var(--nbms-color-error);
      }

      .kpi[data-tone='info'] {
        --kpi-accent-color: var(--nbms-color-info);
      }

      .kpi[data-tone='positive'] .value,
      .kpi[data-tone='positive'] .delta {
        color: var(--nbms-color-success);
      }

      .kpi[data-tone='negative'] .value,
      .kpi[data-tone='negative'] .delta {
        color: var(--nbms-color-error);
      }

      .kpi[data-tone='info'] .value,
      .kpi[data-tone='info'] .delta {
        color: var(--nbms-color-info);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsKpiCardComponent {
  @Input() title = '';
  @Input() value = '0';
  @Input() hint = '';
  @Input() icon = 'insights';
  @Input() unit = '';
  @Input() deltaLabel = '';
  @Input() progressValue: number | null = null;
  @Input() progressMax = 100;
  @Input() progressLabel = '';
  @Input() eyebrow = '';
  @Input() accent = false;
  @Input() tone: 'neutral' | 'positive' | 'negative' | 'info' = 'neutral';

  get showProgress(): boolean {
    return typeof this.progressValue === 'number' && Number.isFinite(this.progressValue);
  }

  get progressPercent(): number {
    if (!this.showProgress || !Number.isFinite(this.progressMax) || this.progressMax <= 0) {
      return 0;
    }
    return Math.max(0, Math.min(100, Math.round(((this.progressValue as number) / this.progressMax) * 100)));
  }
}
