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
        <nbms-share-menu [title]="vm.detail.indicator.code + ' - ' + vm.detail.indicator.title"></nbms-share-menu>
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
      <button
        type="button"
        class="tab"
        role="tab"
        [class.tab--active]="vm.context.tab === 'narrative'"
        [attr.aria-selected]="vm.context.tab === 'narrative'"
        [attr.tabindex]="vm.context.tab === 'narrative' ? 0 : -1"
        (click)="setTab('narrative')"
      >
        Narrative
      </button>
    </nav>

    <section [ngSwitch]="vm.context.tab">
      <ng-container *ngSwitchCase="'indicator'">
        <ng-container *ngIf="indicatorSurface$ | async as surface">
          <nbms-context-bar
            [state]="surface.state"
            [reportCycleOptions]="surface.reportCycleOptions"
            [releaseOptions]="surface.releaseOptions"
            [methodOptions]="surface.methodOptions"
            [geoTypeOptions]="surface.geoTypeOptions"
            [yearOptions]="surface.yearOptions"
            helperText="Indicator views share the canonical URL context model. View-specific drilldown parameters stay in sync with the current indicator route."
            (stateChange)="patchViewState($event)"
          ></nbms-context-bar>

          <div class="filter-actions nbms-card-surface">
            <p class="filter-note">
              Current slice:
              {{ surface.state.report_cycle || 'Current cycle' }}
              /
              {{ surface.state.geo_type }}
              <span *ngIf="surface.state.geo_code"> / {{ surface.state.geo_code }}</span>
              /
              {{ surface.state.metric }}
            </p>
            <button mat-stroked-button type="button" (click)="resetIndicatorContext()">Reset filters</button>
          </div>

          <nbms-indicator-view-host
            [indicatorUuid]="vm.detail.indicator.uuid"
            [indicatorDetail]="vm.detail"
            [visualProfile]="surface.visualProfile"
            [dimensions]="surface.dimensions"
            [state]="surface.state"
            (stateChange)="patchViewState($event)"
          ></nbms-indicator-view-host>
        </ng-container>
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

      <ng-container *ngSwitchCase="'narrative'">
        <section class="details-grid">
          <article class="detail-card detail-card--wide nbms-card-surface">
            <nbms-interpretation-editor
              eyebrow="Narrative"
              cardTitle="Indicator narrative blocks"
              entityType="indicator"
              [entityId]="vm.detail.indicator.uuid"
              [entityLabel]="vm.detail.indicator.title"
              [title]="vm.detail.indicator.code + ' narrative'"
              [provenanceUrl]="'/indicators/' + vm.detail.indicator.uuid"
              [seedSections]="narrativeSeed(vm)"
              [reportingQueryParamsInput]="{
                tab: vm.context.tab,
                report_cycle: vm.context.report_cycle,
                release: vm.context.dataset_release,
                method: vm.context.method,
                geo_type: vm.context.geography,
                start_year: vm.context.start_year,
                end_year: vm.context.end_year
              }"
            ></nbms-interpretation-editor>
          </article>
        </section>
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
            <div class="stack-list" *ngIf="audit$ | async as audit; else loadingAudit">
              <article class="stack-item" *ngFor="let row of audit.events; trackBy: trackByAuditEvent">
                <div>
                  <strong>{{ row.action }}</strong>
                  <p>
                    {{ row.timestamp || 'No timestamp' }}
                    <span *ngIf="row.actor"> · {{ row.actor }}</span>
                    <span *ngIf="row.from_state || row.to_state"> · {{ row.from_state || 'n/a' }} → {{ row.to_state || 'n/a' }}</span>
                  </p>
                  <p *ngIf="row.notes">{{ row.notes }}</p>
                </div>
              </article>
              <div class="empty-state" *ngIf="!audit.events.length">No audit events have been published for this indicator yet.</div>
            </div>
          </article>
        </section>

        <ng-template #loadingAudit>
          <div class="empty-state">Loading audit events.</div>
        </ng-template>
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
