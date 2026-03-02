export const indicatorDetailPageTemplate = `
  <section *ngIf="vm$ | async as vm" class="page">
    <header class="hero nbms-card-surface">
      <div class="hero-main">
        <div class="breadcrumbs">
          <a [routerLink]="['/indicators']">Indicators</a>
          <span>/</span>
          <span>{{ vm.detail.indicator.code }}</span>
        </div>

        <div class="hero-heading">
          <div class="hero-copy">
            <p class="eyebrow">Indicator registry</p>
            <h1>{{ vm.detail.indicator.title }}</h1>
            <p class="hero-summary">{{ vm.leadSummary }}</p>
          </div>

          <div class="hero-badges">
            <nbms-status-pill
              *ngFor="let badge of vm.headerBadges; trackBy: trackByText"
              [label]="badge.label"
              [tone]="badge.tone"
            ></nbms-status-pill>
            <nbms-readiness-badge
              [score]="vm.headerReadinessScore"
              [status]="vm.headerReadinessState"
            ></nbms-readiness-badge>
          </div>
        </div>
      </div>

      <div class="hero-actions">
        <button mat-stroked-button type="button" (click)="createSeriesDownload()">
          <mat-icon>download</mat-icon>
          Export series
        </button>
        <button mat-button type="button" (click)="copyPageLink()">
          <mat-icon>share</mat-icon>
          Share
        </button>
        <button mat-flat-button type="button" class="request-action" (click)="requestApproval()">
          <mat-icon>approval</mat-icon>
          Request approval
        </button>
      </div>
    </header>

    <nav class="tab-strip nbms-card-surface" role="tablist" aria-label="Indicator detail views">
      <button
        type="button"
        class="tab"
        role="tab"
        [class.tab--active]="vm.context.tab === 'indicator'"
        [attr.aria-selected]="vm.context.tab === 'indicator'"
        [attr.tabindex]="vm.context.tab === 'indicator' ? 0 : -1"
        (click)="setTab('indicator')"
      >
        Indicator
      </button>
      <button
        type="button"
        class="tab"
        role="tab"
        [class.tab--active]="vm.context.tab === 'details'"
        [attr.aria-selected]="vm.context.tab === 'details'"
        [attr.tabindex]="vm.context.tab === 'details' ? 0 : -1"
        (click)="setTab('details')"
      >
        Indicator details
      </button>
      <button
        type="button"
        class="tab"
        role="tab"
        [class.tab--active]="vm.context.tab === 'evidence'"
        [attr.aria-selected]="vm.context.tab === 'evidence'"
        [attr.tabindex]="vm.context.tab === 'evidence' ? 0 : -1"
        (click)="setTab('evidence')"
      >
        Evidence
      </button>
      <button
        type="button"
        class="tab"
        role="tab"
        [class.tab--active]="vm.context.tab === 'audit'"
        [attr.aria-selected]="vm.context.tab === 'audit'"
        [attr.tabindex]="vm.context.tab === 'audit' ? 0 : -1"
        (click)="setTab('audit')"
      >
        Audit
      </button>
    </nav>

    <section [ngSwitch]="vm.context.tab">
      <ng-container *ngSwitchCase="'indicator'">
        <section class="filter-bar nbms-card-surface">
          <div class="filter-grid">
            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Report cycle</mat-label>
              <mat-select [formControl]="contextForm.controls.report_cycle">
                <mat-option *ngFor="let option of vm.reportCycleOptions; trackBy: trackByValue" [value]="option.value">
                  {{ option.label }}
                </mat-option>
              </mat-select>
              <mat-hint>(not yet wired)</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Methodology</mat-label>
              <mat-select [formControl]="contextForm.controls.method">
                <mat-option value="">Current published method</mat-option>
                <mat-option *ngFor="let option of vm.methodOptions; trackBy: trackByValue" [value]="option.value">
                  {{ option.label }}
                </mat-option>
              </mat-select>
              <mat-hint>(not yet wired)</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Dataset release</mat-label>
              <mat-select [formControl]="contextForm.controls.dataset_release">
                <mat-option value="">Current published release</mat-option>
                <mat-option *ngFor="let option of vm.datasetOptions; trackBy: trackByValue" [value]="option.value">
                  {{ option.label }}
                </mat-option>
              </mat-select>
              <mat-hint>(not yet wired)</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Geography</mat-label>
              <mat-select [formControl]="contextForm.controls.geography">
                <mat-option value="national">National</mat-option>
                <mat-option value="province">Province</mat-option>
                <mat-option value="biome">Biome</mat-option>
              </mat-select>
              <mat-hint *ngIf="vm.context.geography === 'biome'">(not yet wired)</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Start year</mat-label>
              <mat-select [formControl]="contextForm.controls.start_year" [disabled]="!vm.yearOptions.length">
                <mat-option *ngFor="let year of vm.yearOptions; trackBy: trackByYear" [value]="year">{{ year }}</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>End year</mat-label>
              <mat-select [formControl]="contextForm.controls.end_year" [disabled]="!vm.yearOptions.length">
                <mat-option *ngFor="let year of vm.yearOptions; trackBy: trackByYear" [value]="year">{{ year }}</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="filter-actions">
            <p class="filter-note">{{ vm.activeRegion ? 'Focused on ' + vm.activeRegion : 'No region focus applied.' }}</p>
            <button
              mat-stroked-button
              type="button"
              (click)="resetAnalyticsFilters(vm)"
              [disabled]="!vm.yearOptions.length"
            >
              Reset filters
            </button>
          </div>
        </section>

        <section class="kpi-strip">
          <nbms-kpi-card
            *ngFor="let kpi of vm.kpis; trackBy: trackByText"
            [title]="kpi.title"
            [value]="kpi.value"
            [unit]="kpi.unit"
            [hint]="kpi.hint"
            [icon]="kpi.icon"
            [tone]="kpi.tone"
            [accent]="kpi.accent ?? false"
            [deltaLabel]="kpi.deltaLabel || ''"
            [progressValue]="kpi.progressValue ?? null"
            [progressMax]="kpi.progressMax ?? 100"
            [progressLabel]="kpi.progressLabel || ''"
          ></nbms-kpi-card>
        </section>

        <section class="analytics-layout">
          <div class="analytics-main">
            <section class="chart-grid">
              <article class="panel nbms-card-surface">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">Trend</p>
                    <h2>{{ vm.trendTitle }}</h2>
                  </div>
                  <span class="panel-hint">{{ vm.trendHint }}</span>
                </div>

                <div class="chart-wrap" *ngIf="vm.trendChart; else noTrend">
                  <canvas baseChart [type]="'line'" [data]="vm.trendChart" [options]="lineOptions"></canvas>
                </div>
              </article>

              <article class="panel nbms-card-surface">
                <div class="panel-head">
                  <div>
                    <p class="eyebrow">Breakdown</p>
                    <h2>{{ vm.breakdownTitle }}</h2>
                  </div>
                  <span class="panel-hint">{{ vm.breakdownHint }}</span>
                </div>

                <div class="chart-wrap" *ngIf="vm.breakdownChart; else noBreakdown">
                  <canvas
                    baseChart
                    [type]="'bar'"
                    [data]="vm.breakdownChart"
                    [options]="barOptions"
                    (chartClick)="onBreakdownChartClick($event, vm)"
                  ></canvas>
                </div>
              </article>
            </section>

            <article class="panel nbms-card-surface">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">Distribution</p>
                  <h2>{{ vm.distributionTitle }}</h2>
                </div>
                <button *ngIf="vm.activeRegion" mat-button type="button" class="clear-focus" (click)="clearRegionFocus()">
                  Clear focus
                </button>
              </div>

              <p class="panel-copy">{{ vm.distributionHelper }}</p>

              <div class="distribution-grid" *ngIf="vm.distributionCards.length; else noDistribution">
                <button
                  *ngFor="let card of vm.distributionCards; trackBy: trackByText"
                  type="button"
                  class="distribution-card"
                  [class.distribution-card--active]="card.active"
                  [disabled]="vm.context.geography === 'national'"
                  (click)="toggleRegionFocus(card.region)"
                >
                  <span class="distribution-label">{{ card.geographyType }}</span>
                  <strong>{{ card.region }}</strong>
                  <span class="distribution-value">{{ card.valueLabel }}</span>
                  <div class="distribution-bar" aria-hidden="true"><b [style.width.%]="card.progress"></b></div>
                  <span class="distribution-note">{{ card.note }}</span>
                </button>
              </div>

              <ng-template #noDistribution>
                <div class="empty-state">{{ vm.distributionEmptyMessage }}</div>
              </ng-template>
            </article>

            <article class="panel nbms-card-surface">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">Detailed data</p>
                  <h2>Detailed data table</h2>
                </div>
                <span class="panel-hint">{{ vm.tableRows.length }} rows</span>
              </div>

              <nbms-data-table
                title="Indicator data points"
                [rows]="vm.tableRows"
                [columns]="tableColumns"
                [cellTemplate]="detailTableCellTemplate"
                [itemSize]="48"
              >
                <span table-actions class="table-actions-count">{{ vm.tableRows.length }} rows</span>
              </nbms-data-table>
            </article>
          </div>

          <aside class="narrative-rail">
            <section class="panel nbms-card-surface">
              <p class="eyebrow">Interpretation</p>
              <h2>What the indicator is showing</h2>
              <p class="rail-copy">{{ vm.interpretation }}</p>
            </section>

            <section class="panel nbms-card-surface">
              <p class="eyebrow">Description</p>
              <h2>Indicator description</h2>
              <p class="rail-copy">{{ vm.description }}</p>
            </section>

            <section class="panel nbms-card-surface">
              <p class="eyebrow">Data quality notes</p>
              <h2>Quality and readiness</h2>
              <div class="callout-stack" *ngIf="vm.dataQualityNotes.length; else noNotes">
                <nbms-callout
                  *ngFor="let note of vm.dataQualityNotes; trackBy: trackByText"
                  [tone]="note.tone"
                  [title]="note.title"
                  [message]="note.body"
                ></nbms-callout>
              </div>
            </section>
          </aside>
        </section>

        <ng-template #noTrend>
          <div class="empty-state">No time-series values are available for the selected geography and year range.</div>
        </ng-template>

        <ng-template #noBreakdown>
          <div class="empty-state">No provincial breakdown is available for the selected year.</div>
        </ng-template>

        <ng-template #noNotes>
          <div class="empty-state">No quality notes have been published for this indicator.</div>
        </ng-template>
      </ng-container>

      <ng-container *ngSwitchCase="'details'">
        <section class="details-grid">
          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Identity</p>
                <h2>Identity & classification</h2>
              </div>
            </div>
            <dl class="info-grid">
              <div *ngFor="let row of vm.identityRows; trackBy: trackByText">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
            </dl>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Governance</p>
                <h2>Status & governance</h2>
              </div>
            </div>
            <div class="badge-row">
              <nbms-status-pill
                *ngFor="let badge of vm.governanceBadges; trackBy: trackByText"
                [label]="badge.label"
                [tone]="badge.tone"
              ></nbms-status-pill>
            </div>
            <dl class="info-grid">
              <div *ngFor="let row of vm.governanceRows; trackBy: trackByText">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
            </dl>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Methodology</p>
                <h2>Methodology versions</h2>
              </div>
            </div>
            <div class="stack-list" *ngIf="vm.methodologyVersions.length; else noMethodology">
              <article
                class="stack-item"
                *ngFor="let item of vm.methodologyVersions; trackBy: trackByText"
                [class.stack-item--active]="item.active"
              >
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <nbms-status-pill [label]="item.badgeLabel" [tone]="item.badgeTone"></nbms-status-pill>
              </article>
            </div>

            <section class="subsection" *ngIf="vm.methodProfiles.length">
              <h3>Execution profiles</h3>
              <div class="stack-list">
                <article class="stack-item" *ngFor="let item of vm.methodProfiles; trackBy: trackByText">
                  <div>
                    <strong>{{ item.title }}</strong>
                    <p>{{ item.subtitle }}</p>
                  </div>
                  <nbms-status-pill [label]="item.badgeLabel" [tone]="item.badgeTone"></nbms-status-pill>
                </article>
              </div>
            </section>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Datasets</p>
                <h2>Datasets & releases</h2>
              </div>
            </div>
            <div class="stack-list" *ngIf="vm.datasetReleases.length; else noDatasets">
              <article class="stack-item" *ngFor="let item of vm.datasetReleases; trackBy: trackByText">
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <div class="badge-row">
                  <nbms-status-pill [label]="item.statusLabel" [tone]="item.statusTone"></nbms-status-pill>
                  <nbms-status-pill [label]="item.accessLabel" [tone]="item.accessTone"></nbms-status-pill>
                </div>
              </article>
            </div>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Pipeline</p>
                <h2>Pipeline provenance & refresh</h2>
              </div>
            </div>
            <dl class="info-grid">
              <div *ngFor="let row of vm.pipelineRows; trackBy: trackByText">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
            </dl>
            <nbms-callout
              *ngIf="vm.pipelineCallout"
              [tone]="vm.pipelineCallout.tone"
              [title]="vm.pipelineCallout.title"
              [message]="vm.pipelineCallout.body"
            ></nbms-callout>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Spatial</p>
                <h2>Spatial readiness</h2>
              </div>
            </div>
            <div class="badge-row">
              <nbms-status-pill [label]="vm.spatialOverallLabel" [tone]="vm.spatialOverallTone"></nbms-status-pill>
            </div>
            <p class="section-copy">{{ vm.spatialNotes }}</p>
            <div class="stack-list" *ngIf="vm.spatialLayers.length; else noSpatial">
              <article class="stack-item" *ngFor="let item of vm.spatialLayers; trackBy: trackByText">
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <div class="badge-row">
                  <nbms-status-pill [label]="item.statusLabel" [tone]="item.statusTone"></nbms-status-pill>
                  <nbms-status-pill [label]="item.accessLabel" [tone]="item.accessTone"></nbms-status-pill>
                </div>
              </article>
            </div>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Registry</p>
                <h2>Registry readiness</h2>
              </div>
            </div>
            <div class="badge-row">
              <nbms-status-pill [label]="vm.registryOverallLabel" [tone]="vm.registryOverallTone"></nbms-status-pill>
            </div>
            <p class="section-copy">{{ vm.registryNotes }}</p>
            <div class="check-grid" *ngIf="vm.registryChecks.length; else noRegistry">
              <article class="check-card" *ngFor="let item of vm.registryChecks; trackBy: trackByKey">
                <strong>{{ item.key }}</strong>
                <p>{{ item.detail }}</p>
                <nbms-status-pill [label]="item.badgeLabel" [tone]="item.badgeTone"></nbms-status-pill>
              </article>
            </div>
          </article>

          <article class="detail-card detail-card--wide nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Usage</p>
                <h2>Used by</h2>
              </div>
            </div>
            <div class="used-by-grid">
              <section class="used-by-column" *ngFor="let group of vm.usedByGroups; trackBy: trackByText">
                <h3>{{ group.title }}</h3>
                <ul *ngIf="group.items.length; else emptyUsedBy">
                  <li *ngFor="let item of group.items">{{ item }}</li>
                </ul>
              </section>
            </div>
          </article>

          <article class="detail-card detail-card--wide nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Evidence</p>
                <h2>Evidence items</h2>
              </div>
            </div>
            <div class="stack-list" *ngIf="vm.evidenceItems.length; else noEvidence">
              <article class="stack-item" *ngFor="let item of vm.evidenceItems; trackBy: trackByText">
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <a mat-stroked-button *ngIf="item.url" [href]="item.url" target="_blank" rel="noreferrer">Open source</a>
              </article>
            </div>
          </article>
        </section>

        <ng-template #noMethodology>
          <div class="empty-state">No methodology versions are published for this indicator.</div>
        </ng-template>
        <ng-template #noDatasets>
          <div class="empty-state">No linked datasets are published for this indicator.</div>
        </ng-template>
        <ng-template #noSpatial>
          <div class="empty-state">No spatial layer requirements are published for this indicator.</div>
        </ng-template>
        <ng-template #noRegistry>
          <div class="empty-state">No registry readiness checks are available.</div>
        </ng-template>
        <ng-template #emptyUsedBy><p class="empty-inline">No linked records.</p></ng-template>
        <ng-template #noEvidence>
          <div class="empty-state">No evidence items are linked to this indicator.</div>
        </ng-template>
      </ng-container>

      <ng-container *ngSwitchCase="'evidence'">
        <section class="details-grid">
          <article class="detail-card detail-card--wide nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Evidence</p>
                <h2>Evidence items & citations</h2>
              </div>
            </div>
            <div class="stack-list" *ngIf="vm.evidenceItems.length; else noEvidenceTab">
              <article class="stack-item" *ngFor="let item of vm.evidenceItems; trackBy: trackByText">
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <a mat-stroked-button *ngIf="item.url" [href]="item.url" target="_blank" rel="noreferrer">Open source</a>
              </article>
            </div>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Validation</p>
                <h2>Method profiles</h2>
              </div>
            </div>
            <div class="stack-list" *ngIf="vm.methodProfiles.length; else noEvidenceProfiles">
              <article class="stack-item" *ngFor="let item of vm.methodProfiles; trackBy: trackByText">
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <nbms-status-pill [label]="item.badgeLabel" [tone]="item.badgeTone"></nbms-status-pill>
              </article>
            </div>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Releases</p>
                <h2>Datasets & releases</h2>
              </div>
            </div>
            <div class="stack-list" *ngIf="vm.datasetReleases.length; else noEvidenceDatasets">
              <article class="stack-item" *ngFor="let item of vm.datasetReleases; trackBy: trackByText">
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.subtitle }}</p>
                </div>
                <div class="badge-row">
                  <nbms-status-pill [label]="item.statusLabel" [tone]="item.statusTone"></nbms-status-pill>
                  <nbms-status-pill [label]="item.accessLabel" [tone]="item.accessTone"></nbms-status-pill>
                </div>
              </article>
            </div>
          </article>
        </section>

        <ng-template #noEvidenceTab>
          <div class="empty-state">No evidence items are linked to this indicator.</div>
        </ng-template>
        <ng-template #noEvidenceProfiles>
          <div class="empty-state">No validation or execution profiles are available.</div>
        </ng-template>
        <ng-template #noEvidenceDatasets>
          <div class="empty-state">No release metadata is published for this indicator.</div>
        </ng-template>
      </ng-container>

      <ng-container *ngSwitchCase="'audit'">
        <section class="details-grid">
          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Workflow</p>
                <h2>Status & approval state</h2>
              </div>
            </div>
            <div class="badge-row">
              <nbms-status-pill
                *ngFor="let badge of vm.governanceBadges; trackBy: trackByText"
                [label]="badge.label"
                [tone]="badge.tone"
              ></nbms-status-pill>
            </div>
            <dl class="info-grid">
              <div *ngFor="let row of vm.governanceRows; trackBy: trackByText">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
            </dl>
          </article>

          <article class="detail-card nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Provenance</p>
                <h2>Pipeline provenance & refresh</h2>
              </div>
            </div>
            <dl class="info-grid">
              <div *ngFor="let row of vm.pipelineRows; trackBy: trackByText">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
            </dl>
            <nbms-callout
              *ngIf="vm.pipelineCallout"
              [tone]="vm.pipelineCallout.tone"
              [title]="vm.pipelineCallout.title"
              [message]="vm.pipelineCallout.body"
            ></nbms-callout>
          </article>

          <article class="detail-card detail-card--wide nbms-card-surface">
            <div class="section-head">
              <div>
                <p class="eyebrow">Audit</p>
                <h2>Approval workflow timeline</h2>
              </div>
            </div>
            <div class="stack-list">
              <article class="stack-item" *ngFor="let row of vm.pipelineRows; trackBy: trackByText">
                <div>
                  <strong>{{ row.label }}</strong>
                  <p>{{ row.value }}</p>
                </div>
              </article>
            </div>
            <nbms-callout
              tone="info"
              title="Audit trail availability"
              message="A dedicated audit-log endpoint is still needed for a full event timeline. This tab currently reflects the auditable workflow and pipeline fields already published on the indicator detail payload."
            ></nbms-callout>
          </article>
        </section>
      </ng-container>
    </section>

    <ng-template #detailTableCell let-row let-key="key">
      <ng-container [ngSwitch]="key">
        <ng-container *ngSwitchCase="'value'">{{ row.valueLabel }}</ng-container>
        <ng-container *ngSwitchCase="'status'">
          <nbms-status-pill [label]="row.status" [tone]="row.statusTone"></nbms-status-pill>
        </ng-container>
        <ng-container *ngSwitchDefault>{{ row[key] }}</ng-container>
      </ng-container>
    </ng-template>
  </section>
`;
