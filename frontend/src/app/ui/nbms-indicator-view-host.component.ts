import { NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault, TitleCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

import type { IndicatorDetailResponse, IndicatorDimension, IndicatorVisualProfile } from '../models/api.models';
import type { IndicatorViewKey, IndicatorViewRoutePatch, IndicatorViewRouteState, IndicatorViewSummary } from '../models/indicator-visual.models';
import { NbmsCalloutComponent } from './nbms-callout.component';
import { NbmsInterpretationEditorComponent } from './nbms-interpretation-editor.component';
import { NbmsKpiCardComponent } from './nbms-kpi-card.component';
import { NbmsTabStripComponent } from './nbms-tab-strip.component';
import { pickDistributionDimension, pickTaxonomyLevel, toIndicatorView } from './indicator-view.helpers';
import { NbmsViewBinaryComponent } from './nbms-view-binary.component';
import { NbmsViewDistributionComponent } from './nbms-view-distribution.component';
import { NbmsViewMatrixComponent } from './nbms-view-matrix.component';
import { NbmsViewTaxonomyDrilldownComponent } from './nbms-view-taxonomy-drilldown.component';
import { NbmsViewTimeseriesComponent } from './nbms-view-timeseries.component';

@Component({
  selector: 'nbms-indicator-view-host',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    NgSwitchDefault,
    TitleCasePipe,
    NbmsCalloutComponent,
    NbmsInterpretationEditorComponent,
    NbmsKpiCardComponent,
    NbmsTabStripComponent,
    NbmsViewBinaryComponent,
    NbmsViewDistributionComponent,
    NbmsViewMatrixComponent,
    NbmsViewTaxonomyDrilldownComponent,
    NbmsViewTimeseriesComponent,
  ],
  template: `
    <section class="view-host" *ngIf="indicatorDetail && visualProfile && state">
      <nbms-tab-strip
        [tabs]="viewTabs"
        [activeTab]="effectiveView"
        (tabChange)="selectView($any($event))"
      ></nbms-tab-strip>

      <section class="kpi-strip" *ngIf="summary.kpis.length">
        <nbms-kpi-card
          *ngFor="let kpi of summary.kpis; trackBy: trackByKpi"
          [title]="kpi.title"
          [value]="kpi.value"
          [hint]="kpi.hint || ''"
          [icon]="kpi.icon || 'insights'"
          [unit]="kpi.unit || ''"
          [tone]="kpi.tone || 'neutral'"
          [accent]="kpi.accent ?? false"
          [deltaLabel]="kpi.deltaLabel || ''"
        ></nbms-kpi-card>
      </section>

      <div class="layout">
        <div class="main-column">
          <ng-container [ngSwitch]="effectiveView">
            <nbms-view-timeseries
              *ngSwitchCase="'timeseries'"
              [indicatorUuid]="indicatorUuid"
              [indicatorDetail]="indicatorDetail"
              [visualProfile]="visualProfile"
              [dimensions]="dimensions"
              [state]="state"
              (stateChange)="stateChange.emit($event)"
              (summaryChange)="summary = $event"
            ></nbms-view-timeseries>

            <nbms-view-distribution
              *ngSwitchCase="'distribution'"
              [indicatorUuid]="indicatorUuid"
              [indicatorDetail]="indicatorDetail"
              [visualProfile]="visualProfile"
              [dimensions]="dimensions"
              [state]="state"
              (stateChange)="stateChange.emit($event)"
              (summaryChange)="summary = $event"
            ></nbms-view-distribution>

            <nbms-view-taxonomy-drilldown
              *ngSwitchCase="'taxonomy'"
              [indicatorUuid]="indicatorUuid"
              [indicatorDetail]="indicatorDetail"
              [visualProfile]="visualProfile"
              [dimensions]="dimensions"
              [state]="state"
              (stateChange)="stateChange.emit($event)"
              (summaryChange)="summary = $event"
            ></nbms-view-taxonomy-drilldown>

            <nbms-view-matrix
              *ngSwitchCase="'matrix'"
              [indicatorUuid]="indicatorUuid"
              [indicatorDetail]="indicatorDetail"
              [dimensions]="dimensions"
              [state]="state"
              (stateChange)="stateChange.emit($event)"
              (summaryChange)="summary = $event"
            ></nbms-view-matrix>

            <nbms-view-binary
              *ngSwitchCase="'binary'"
              [indicatorDetail]="indicatorDetail"
              (summaryChange)="summary = $event"
            ></nbms-view-binary>

            <div class="empty-state" *ngSwitchDefault>
              {{ effectiveView | titlecase }} view is not available for this indicator.
            </div>
          </ng-container>
        </div>

        <div class="rail-toggle-wrap">
          <button
            type="button"
            class="rail-toggle"
            [attr.aria-expanded]="railOpen"
            aria-label="Toggle indicator narrative and governance rail"
            (click)="railOpen = !railOpen"
          >
            {{ railOpen ? 'Hide rail' : 'Show rail' }}
          </button>
        </div>

        <aside class="rail" [class.rail--open]="railOpen">
          <nbms-interpretation-editor
            eyebrow="Interpretation"
            cardTitle="Indicator narrative"
            entityType="indicator"
            [entityId]="indicatorDetail.indicator.uuid"
            [entityLabel]="indicatorDetail.indicator.title"
            [title]="indicatorDetail.indicator.code + ' narrative'"
            [provenanceUrl]="'/indicators/' + indicatorDetail.indicator.uuid"
            [seedSections]="seedSections"
            [reportingQueryParamsInput]="{
              tab: state.tab,
              report_cycle: state.report_cycle,
              release: state.release,
              method: state.method,
              geo_type: state.geo_type,
              geo_code: state.geo_code,
              start_year: state.start_year,
              end_year: state.end_year
            }"
          ></nbms-interpretation-editor>

          <section class="panel nbms-card-surface">
            <p class="eyebrow">Governance</p>
            <h3>QA, sensitivity, provenance</h3>
            <div class="callout-stack" *ngIf="summary.callouts.length; else noCallouts">
              <nbms-callout
                *ngFor="let callout of summary.callouts; trackBy: trackByCallout"
                [tone]="callout.tone"
                [title]="callout.title"
                [message]="callout.message"
              ></nbms-callout>
            </div>
          </section>
        </aside>
      </div>

      <ng-template #noCallouts>
        <div class="empty-state">No governance callouts are available for the current indicator view.</div>
      </ng-template>
    </section>
  `,
  styles: [
    `
      .view-host,
      .kpi-strip,
      .layout,
      .rail,
      .callout-stack {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .kpi-strip {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }

      .layout {
        grid-template-columns: minmax(0, 1.6fr) minmax(0, 0.8fr);
        align-items: start;
      }

      .rail {
        position: sticky;
        top: 5.3rem;
      }

      .rail-toggle-wrap {
        display: none;
      }

      .rail-toggle {
        min-height: 2.5rem;
        border: 1px solid var(--nbms-border-strong);
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-surface);
        color: var(--nbms-text-primary);
        cursor: pointer;
        font: inherit;
        font-weight: 700;
        padding: 0 var(--nbms-space-3);
      }

      .panel {
        display: grid;
        gap: var(--nbms-space-3);
        padding: var(--nbms-space-4);
      }

      .eyebrow {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      h3 {
        margin: var(--nbms-space-1) 0 0;
      }

      .empty-state {
        border: 1px dashed var(--nbms-border);
        border-radius: var(--nbms-radius-lg);
        color: var(--nbms-text-muted);
        padding: var(--nbms-space-4);
        text-align: center;
      }

      @media (max-width: 1280px) {
        .kpi-strip {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }

      @media (max-width: 900px) {
        .layout,
        .kpi-strip {
          grid-template-columns: 1fr;
        }

        .rail {
          display: none;
          position: static;
        }

        .rail--open {
          display: grid;
        }

        .rail-toggle-wrap {
          display: block;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NbmsIndicatorViewHostComponent {
  @Input() indicatorUuid = '';
  @Input() indicatorDetail: IndicatorDetailResponse | null = null;
  @Input() visualProfile: IndicatorVisualProfile | null = null;
  @Input() dimensions: IndicatorDimension[] = [];
  @Input() state: IndicatorViewRouteState | null = null;

  @Output() readonly stateChange = new EventEmitter<IndicatorViewRoutePatch>();

  railOpen = false;
  summary: IndicatorViewSummary = { kpis: [], callouts: [] };

  ngOnChanges(): void {
    if (!this.visualProfile || !this.state) {
      return;
    }
    if (!this.state.view) {
      this.selectView(toIndicatorView(this.visualProfile.defaultView));
    }
  }

  get viewTabs(): Array<{ id: IndicatorViewKey; label: string }> {
    const available = this.visualProfile?.availableViews || ['timeseries'];
    return available.map((view) => ({ id: toIndicatorView(view), label: toIndicatorView(view) }));
  }

  get effectiveView(): IndicatorViewKey {
    if (!this.visualProfile) {
      return 'timeseries';
    }
    if (!this.state?.view) {
      return toIndicatorView(this.visualProfile.defaultView);
    }
    return toIndicatorView(this.state.view);
  }

  get seedSections(): Array<{ id: string; title: string; body: string }> {
    if (!this.indicatorDetail) {
      return [];
    }
    return [
      {
        id: 'interpretation',
        title: 'Interpretation',
        body: this.indicatorDetail.narrative?.summary || this.indicatorDetail.indicator.description || 'No interpretation is published yet.',
      },
      {
        id: 'key-messages',
        title: 'Key messages',
        body: `${this.indicatorDetail.indicator.title}\n\nLifecycle: ${this.indicatorDetail.indicator.status}\nQA: ${this.indicatorDetail.indicator.qa_status}`,
      },
      {
        id: 'data-limitations',
        title: 'Data limitations',
        body: this.indicatorDetail.narrative?.limitations || 'No data limitations are currently published.',
      },
      {
        id: 'what-changed',
        title: 'What changed',
        body: `Last updated: ${this.indicatorDetail.pipeline?.data_last_refreshed_at || this.indicatorDetail.indicator.updated_at || 'n/a'}`,
      },
    ];
  }

  trackByKpi(_: number, row: IndicatorViewSummary['kpis'][number]): string {
    return row.title;
  }

  trackByCallout(_: number, row: IndicatorViewSummary['callouts'][number]): string {
    return `${row.title}-${row.message}`;
  }

  selectView(view: IndicatorViewKey): void {
    const patch = this.defaultsForView(view);
    this.summary = { kpis: [], callouts: [] };
    this.stateChange.emit({ view, ...patch });
  }

  private defaultsForView(view: IndicatorViewKey): IndicatorViewRoutePatch {
    if (view === 'distribution') {
      return {
        dim: pickDistributionDimension(this.dimensions, this.state?.dim || ''),
        dim_value: '',
        tax_level: '',
        tax_code: '',
      };
    }
    if (view === 'taxonomy') {
      return {
        dim: '',
        dim_value: '',
        tax_level: pickTaxonomyLevel(this.dimensions, this.state?.tax_level || ''),
        tax_code: '',
      };
    }
    if (view === 'timeseries') {
      return {
        agg: this.state?.agg || this.visualProfile?.defaultGroupBy || 'province',
        dim: '',
        dim_value: '',
        tax_level: '',
        tax_code: '',
      };
    }
    return {};
  }
}
