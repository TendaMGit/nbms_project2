import { AsyncPipe, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault, TitleCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { combineLatest, debounceTime, distinctUntilChanged, map, startWith, switchMap, tap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { IndicatorExplorerCompareComponent } from '../components/indicator-explorer-compare.component';
import { IndicatorExplorerInsightsComponent } from '../components/indicator-explorer-insights.component';
import { IndicatorExplorerToolbarComponent } from '../components/indicator-explorer-toolbar.component';
import type { IndicatorListItem, IndicatorListResponse, SavedFilterEntry } from '../models/api.models';
import { IndicatorService } from '../services/indicator.service';
import { UserPreferencesService } from '../services/user-preferences.service';
import { NbmsDataTableComponent } from '../ui/nbms-data-table.component';
import { NbmsFilterRailComponent } from '../ui/nbms-filter-rail.component';
import { NbmsMapPanelComponent } from '../ui/nbms-map-panel.component';
import { NbmsPageHeaderComponent } from '../ui/nbms-page-header.component';
import { NbmsReadinessBadgeComponent } from '../ui/nbms-readiness-badge.component';
import { NbmsStatusPillComponent } from '../ui/nbms-status-pill.component';

type ExplorerMode = 'table' | 'cards' | 'map';

type ExplorerFilters = {
  q: string;
  framework: string;
  gbf_goal: string;
  gbf_target: string;
  readiness_band: string;
  readiness_min: number | null;
  readiness_max: number | null;
  geography_type: string;
  geography_code: string;
  has_spatial: boolean;
  access_level: string;
  due_soon_only: boolean;
  recency_days: string;
  sort: string;
  mode: ExplorerMode;
};

const LAST_VISIT_KEY = 'nbms.watch.indicators.lastVisitAt';

export function buildIndicatorNarrative(input: {
  total: number;
  summary: IndicatorListResponse['summary'] | undefined;
  filters: Pick<ExplorerFilters, 'gbf_target' | 'geography_type' | 'geography_code'>;
}): string {
  const readiness = input.summary?.readiness_bands ?? { green: 0, amber: 0, red: 0 };
  const gbfText = input.filters.gbf_target ? ` mapped to GBF Target ${input.filters.gbf_target}` : '';
  const geoText = input.filters.geography_code
    ? ` in ${input.filters.geography_type} ${input.filters.geography_code}`
    : '';
  const blockers = (input.summary?.blockers ?? []).filter((item) => item.count > 0).sort((a, b) => b.count - a.count);
  const blockerText = blockers.length
    ? ` Most common blockers: ${blockers.slice(0, 2).map((item) => `${item.label.toLowerCase()} (${item.count})`).join(', ')}.`
    : ' No major blockers detected.';
  return `Showing ${input.total} indicators${gbfText}${geoText}. ${readiness.green} are Green, ${readiness.amber} Amber, and ${readiness.red} Red readiness.${blockerText}`;
}

@Component({
  selector: 'app-indicator-explorer-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    NgSwitchDefault,
    TitleCasePipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    IndicatorExplorerCompareComponent,
    IndicatorExplorerInsightsComponent,
    IndicatorExplorerToolbarComponent,
    NbmsDataTableComponent,
    NbmsFilterRailComponent,
    NbmsMapPanelComponent,
    NbmsPageHeaderComponent,
    NbmsReadinessBadgeComponent,
    NbmsStatusPillComponent
  ],
  template: `
    <section class="explorer-page" *ngIf="vm$ | async as vm">
      <nbms-page-header
        title="Indicator Database"
        subtitle="Interactive explorer for narratives, aggregations, map-backed availability, and auditable indicator drilldowns."
        [breadcrumbs]="[
          { label: 'Dashboard', route: ['/dashboard'] },
          { label: 'Indicators', route: ['/indicators'] }
        ]"
        [badges]="[
          { label: vm.filters.geography_type || 'national', tone: 'neutral' },
          { label: vm.filters.mode === 'map' ? 'Map mode' : (vm.filters.mode | titlecase), tone: 'info' }
        ]"
        [actions]="[
          { id: 'frameworks', label: 'Frameworks', route: ['/frameworks'], icon: 'account_tree', variant: 'stroked' },
          { id: 'reset', label: 'Reset filters', icon: 'restart_alt', variant: 'text' }
        ]"
        (actionSelected)="onHeaderAction($event)"
      ></nbms-page-header>

      <section class="layout" [class.layout--insights]="insightsOpen">
      <nbms-filter-rail class="rail" title="Filters">
        <mat-form-field appearance="outline">
          <mat-label>Search</mat-label>
          <input matInput [formControl]="filters.controls.q" />
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Saved views</mat-label>
          <mat-select (selectionChange)="applySavedView($event.value)">
            <mat-option [value]="''">Choose saved view</mat-option>
            <mat-option *ngFor="let view of vm.savedViews; trackBy: trackBySavedView" [value]="view.id">{{ view.name }}</mat-option>
          </mat-select>
        </mat-form-field>

        <div class="grid-2">
          <mat-form-field appearance="outline">
            <mat-label>Framework</mat-label>
            <mat-select [formControl]="filters.controls.framework">
              <mat-option value="">All</mat-option>
              <mat-option value="GBF">GBF</mat-option>
              <mat-option value="SDG">SDG</mat-option>
              <mat-option value="RAMSAR">Ramsar</mat-option>
              <mat-option value="CITES">CITES</mat-option>
              <mat-option value="CMS">CMS</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>GBF Goal</mat-label>
            <mat-select [formControl]="filters.controls.gbf_goal">
              <mat-option value="">All</mat-option>
              <mat-option value="A">A</mat-option>
              <mat-option value="B">B</mat-option>
              <mat-option value="C">C</mat-option>
              <mat-option value="D">D</mat-option>
            </mat-select>
          </mat-form-field>
        </div>

        <div class="grid-2">
          <mat-form-field appearance="outline">
            <mat-label>GBF Target</mat-label>
            <input matInput [formControl]="filters.controls.gbf_target" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Access</mat-label>
            <mat-select [formControl]="filters.controls.access_level">
              <mat-option value="">All</mat-option>
              <mat-option value="public">Public</mat-option>
              <mat-option value="internal">Internal</mat-option>
              <mat-option value="restricted">Restricted</mat-option>
            </mat-select>
          </mat-form-field>
        </div>

        <div class="grid-2">
          <mat-form-field appearance="outline">
            <mat-label>Geography type</mat-label>
            <mat-select [formControl]="filters.controls.geography_type">
              <mat-option value="national">National</mat-option>
              <mat-option value="province">Province</mat-option>
              <mat-option value="district">District</mat-option>
              <mat-option value="municipality">Municipality</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Geography code</mat-label>
            <input matInput [formControl]="filters.controls.geography_code" />
          </mat-form-field>
        </div>

        <div class="grid-2">
          <mat-form-field appearance="outline">
            <mat-label>Readiness</mat-label>
            <mat-select [formControl]="filters.controls.readiness_band">
              <mat-option value="">All</mat-option>
              <mat-option value="green">Green</mat-option>
              <mat-option value="amber">Amber</mat-option>
              <mat-option value="red">Red</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Updated in last</mat-label>
            <mat-select [formControl]="filters.controls.recency_days">
              <mat-option value="">Any</mat-option>
              <mat-option value="30">30 days</mat-option>
              <mat-option value="90">90 days</mat-option>
              <mat-option value="365">365 days</mat-option>
            </mat-select>
          </mat-form-field>
        </div>

        <div class="grid-2">
          <mat-form-field appearance="outline">
            <mat-label>Readiness min</mat-label>
            <input matInput type="number" [formControl]="filters.controls.readiness_min" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Readiness max</mat-label>
            <input matInput type="number" [formControl]="filters.controls.readiness_max" />
          </mat-form-field>
        </div>

        <mat-slide-toggle [formControl]="filters.controls.has_spatial">Has spatial output</mat-slide-toggle>
        <mat-slide-toggle [formControl]="filters.controls.due_soon_only">Due within 60 days</mat-slide-toggle>

        <div class="rail-actions">
          <button mat-stroked-button type="button" (click)="saveCurrentView()">Save view</button>
          <button mat-button type="button" (click)="clearFilters()">Clear</button>
        </div>
      </nbms-filter-rail>

      <section class="main">
        <app-indicator-explorer-toolbar
          [modeControl]="filters.controls.mode"
          [sortControl]="filters.controls.sort"
          [insightsOpen]="insightsOpen"
          [compareCount]="selectedCompare.length"
          (exportRequested)="downloadCsv(vm.results.results)"
          (insightsToggle)="toggleInsights()"
        ></app-indicator-explorer-toolbar>

        <section [ngSwitch]="vm.filters.mode">
          <ng-container *ngSwitchCase="'table'">
            <nbms-data-table
              title="Indicators"
              [rows]="vm.results.results"
              [columns]="columns"
              [itemSize]="vm.density === 'compact' ? 40 : 48"
              [cellTemplate]="tableCellTemplate"
            ></nbms-data-table>
          </ng-container>

          <ng-container *ngSwitchCase="'cards'">
            <div class="cards">
              <article class="indicator-card nbms-card-surface" *ngFor="let item of vm.results.results; trackBy: trackByIndicator">
                <div class="card-head">
                  <div class="card-title">
                    <a [routerLink]="['/indicators', item.uuid]">{{ item.code }} - {{ item.title }}</a>
                    <span class="card-caption">{{ extractGbfTargets(item).join(', ') || 'No GBF target tags' }}</span>
                  </div>
                  <button
                    mat-icon-button
                    type="button"
                    (click)="toggleWatch(item.uuid)"
                    [attr.aria-label]="isWatched(item.uuid) ? 'Unwatch indicator' : 'Watch indicator'"
                  >
                    <mat-icon>{{ isWatched(item.uuid) ? 'star' : 'star_border' }}</mat-icon>
                  </button>
                </div>
                <p>{{ item.description || 'No summary provided.' }}</p>
                <div class="card-meta">
                  <nbms-readiness-badge [score]="item.readiness_score" [status]="toReadinessStatus(item)"></nbms-readiness-badge>
                  <nbms-status-pill [label]="item.status" [tone]="toStatusTone(item.status)"></nbms-status-pill>
                  <span class="changed" *ngIf="isChangedSinceLastVisit(item)">Changed since last visit</span>
                </div>
              </article>
            </div>
          </ng-container>

          <ng-container *ngSwitchCase="'map'">
            <nbms-map-panel title="Map-first availability">
              <div class="map-summary">
                <p>Tile-first map rendering is available in Spatial Viewer; this panel summarizes current filtered availability.</p>
                <div class="map-grid">
                  <article class="map-stat nbms-card-surface">
                    <strong>{{ vm.results.summary?.readiness_bands?.green || 0 }}</strong>
                    <span>Green</span>
                  </article>
                  <article class="map-stat nbms-card-surface">
                    <strong>{{ vm.results.summary?.readiness_bands?.amber || 0 }}</strong>
                    <span>Amber</span>
                  </article>
                  <article class="map-stat nbms-card-surface">
                    <strong>{{ vm.results.summary?.readiness_bands?.red || 0 }}</strong>
                    <span>Red</span>
                  </article>
                </div>
                <button mat-stroked-button type="button" [routerLink]="['/spatial/map']">Open spatial map</button>
              </div>
            </nbms-map-panel>
          </ng-container>

          <ng-container *ngSwitchDefault><p>Unsupported mode.</p></ng-container>
        </section>

        <app-indicator-explorer-compare
          *ngIf="selectedCompare.length >= 2"
          [rows]="compareRows(vm.results.results)"
        ></app-indicator-explorer-compare>
      </section>

      <app-indicator-explorer-insights
        *ngIf="insightsOpen"
        class="insights"
        [narrative]="vm.narrative"
        [dueSoonCount]="vm.results.summary?.due_soon_count || 0"
        [compareCount]="selectedCompare.length"
        [blockers]="vm.results.summary?.blockers || []"
        [reportingQueryParams]="{ narrative: vm.narrative }"
        (copyNarrative)="copyNarrative(vm.narrative)"
      ></app-indicator-explorer-insights>
      </section>
    </section>

    <ng-template #tableCell let-item let-key="key">
      <ng-container [ngSwitch]="key">
        <ng-container *ngSwitchCase="'code_title'">
          <a [routerLink]="['/indicators', item.uuid]">{{ item.code }} - {{ item.title }}</a>
          <span class="changed" *ngIf="isChangedSinceLastVisit(item)">Changed</span>
        </ng-container>
        <ng-container *ngSwitchCase="'gbf_targets'">{{ extractGbfTargets(item).join(', ') || 'n/a' }}</ng-container>
        <ng-container *ngSwitchCase="'readiness'"><nbms-readiness-badge [score]="item.readiness_score" [status]="toReadinessStatus(item)"></nbms-readiness-badge></ng-container>
        <ng-container *ngSwitchCase="'last_updated'">{{ item.last_updated_on || 'n/a' }}</ng-container>
        <ng-container *ngSwitchCase="'next_expected'">{{ item.next_expected_update_on || 'n/a' }}</ng-container>
        <ng-container *ngSwitchCase="'status'"><nbms-status-pill [label]="item.status" [tone]="toStatusTone(item.status)"></nbms-status-pill></ng-container>
        <ng-container *ngSwitchCase="'actions'">
          <button
            mat-icon-button
            type="button"
            (click)="toggleWatch(item.uuid)"
            [attr.aria-label]="isWatched(item.uuid) ? 'Unwatch indicator' : 'Watch indicator'"
          >
            <mat-icon>{{ isWatched(item.uuid) ? 'star' : 'star_border' }}</mat-icon>
          </button>
          <button
            mat-icon-button
            type="button"
            (click)="toggleCompare(item.uuid)"
            [attr.aria-label]="selectedCompare.includes(item.uuid) ? 'Remove from compare' : 'Add to compare'"
          >
            <mat-icon>{{ selectedCompare.includes(item.uuid) ? 'check_box' : 'check_box_outline_blank' }}</mat-icon>
          </button>
          <a mat-icon-button [routerLink]="['/indicators', item.uuid]"><mat-icon>open_in_new</mat-icon></a>
        </ng-container>
        <ng-container *ngSwitchDefault>{{ item[key] }}</ng-container>
      </ng-container>
    </ng-template>
  `,
  styles: [
    `
      .layout {
        display: grid;
        grid-template-columns: minmax(280px, 308px) minmax(0, 1fr);
        gap: var(--nbms-space-4);
      }

      .layout.layout--insights {
        grid-template-columns: minmax(280px, 308px) minmax(0, 1fr) minmax(296px, 332px);
      }

      .explorer-page {
        display: grid;
        gap: var(--nbms-space-4);
      }

      .rail { position: sticky; top: 5.4rem; align-self: start; }
      .main { display: grid; gap: var(--nbms-space-4); }
      .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--nbms-space-2); }
      .rail-actions { display: flex; gap: var(--nbms-space-2); }
      .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--nbms-space-3); }
      .indicator-card { display: grid; gap: var(--nbms-space-3); padding: var(--nbms-space-4); min-height: 100%; }
      .card-head { display: flex; justify-content: space-between; gap: var(--nbms-space-2); align-items: flex-start; }
      .card-title { display: grid; gap: var(--nbms-space-1); }
      .card-caption { color: var(--nbms-text-muted); font-size: var(--nbms-font-size-label-sm); }
      .indicator-card p { margin: 0; color: var(--nbms-text-secondary); line-height: 1.6; }
      .card-meta { display: flex; flex-wrap: wrap; gap: var(--nbms-space-2); align-items: center; }
      .changed { color: var(--nbms-info); font-size: var(--nbms-font-size-label-sm); font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
      .insights { align-self: start; position: sticky; top: 5.4rem; }
      .map-summary { padding: var(--nbms-space-4); display: grid; gap: var(--nbms-space-3); }
      .map-summary p { margin: 0; color: var(--nbms-text-secondary); }
      .map-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--nbms-space-2); }
      .map-stat { padding: var(--nbms-space-3); display: grid; gap: var(--nbms-space-1); min-height: 100%; }
      .map-stat strong { font-size: var(--nbms-font-size-h3); color: var(--nbms-text-primary); }
      .map-stat span { color: var(--nbms-text-muted); font-size: var(--nbms-font-size-label-sm); text-transform: uppercase; letter-spacing: 0.04em; }
      @media (max-width: 1400px) { .layout.layout--insights { grid-template-columns: 300px minmax(0, 1fr); } .insights { grid-column: 1 / -1; position: static; } }
      @media (max-width: 980px) { .layout, .layout.layout--insights { grid-template-columns: 1fr; } .rail { position: static; } }
      @media (max-width: 640px) { .grid-2, .map-grid { grid-template-columns: 1fr; } }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IndicatorExplorerPageComponent {
  @ViewChild('tableCell', { static: true }) tableCellTemplate!: TemplateRef<{ $implicit: IndicatorListItem; key: string }>;

  private readonly indicatorService = inject(IndicatorService);
  private readonly preferences = inject(UserPreferencesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly columns: Array<{ key: string; label: string }> = [
    { key: 'code_title', label: 'Indicator' },
    { key: 'gbf_targets', label: 'GBF target(s)' },
    { key: 'readiness', label: 'Readiness' },
    { key: 'last_updated', label: 'Last updated' },
    { key: 'next_expected', label: 'Next expected' },
    { key: 'status', label: 'Status' },
    { key: 'actions', label: 'Actions' }
  ];

  readonly filters = new FormGroup({
    q: new FormControl<string>('', { nonNullable: true }),
    framework: new FormControl<string>('', { nonNullable: true }),
    gbf_goal: new FormControl<string>('', { nonNullable: true }),
    gbf_target: new FormControl<string>('', { nonNullable: true }),
    readiness_band: new FormControl<string>('', { nonNullable: true }),
    readiness_min: new FormControl<number | null>(null),
    readiness_max: new FormControl<number | null>(null),
    geography_type: new FormControl<string>('national', { nonNullable: true }),
    geography_code: new FormControl<string>('', { nonNullable: true }),
    has_spatial: new FormControl<boolean>(false, { nonNullable: true }),
    access_level: new FormControl<string>('', { nonNullable: true }),
    due_soon_only: new FormControl<boolean>(false, { nonNullable: true }),
    recency_days: new FormControl<string>('', { nonNullable: true }),
    sort: new FormControl<string>('last_updated_desc', { nonNullable: true }),
    mode: new FormControl<ExplorerMode>('table', { nonNullable: true })
  });

  readonly previousVisit = this.getPreviousVisit();
  readonly selectedCompare: string[] = [];
  insightsOpen = false;

  readonly filterState$ = this.filters.valueChanges.pipe(
    startWith(this.filters.getRawValue()),
    debounceTime(220),
    map((value) => this.normalizeFilters(value)),
    distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
    tap((filters) => this.syncUrl(filters))
  );

  readonly results$ = this.filterState$.pipe(
    map((filters) => this.toApiQuery(filters)),
    switchMap((params) => this.indicatorService.list(params))
  );

  readonly vm$ = combineLatest([this.results$, this.filterState$, this.preferences.preferences$]).pipe(
    map(([results, filters, preferences]) => ({
      filters,
      density: preferences.density,
      results,
      savedViews: preferences.saved_filters.indicators,
      narrative: buildIndicatorNarrative({
        total: results.count,
        summary: results.summary,
        filters: {
          gbf_target: filters.gbf_target,
          geography_type: filters.geography_type,
          geography_code: filters.geography_code
        }
      })
    }))
  );

  constructor() {
    this.preferences.bootstrap();
    const params = this.route.snapshot.queryParamMap;
    const pref = this.preferences.snapshot;
    this.filters.patchValue(
      {
        q: params.get('q') ?? params.get('search') ?? '',
        framework: params.get('framework') ?? '',
        gbf_goal: params.get('gbf_goal') ?? '',
        gbf_target: params.get('gbf_target') ?? '',
        readiness_band: params.get('readiness_band') ?? '',
        readiness_min: this.toNullableNumber(params.get('readiness_min')),
        readiness_max: this.toNullableNumber(params.get('readiness_max')),
        geography_type: params.get('geography_type') ?? params.get('geo_type') ?? pref.default_geography.type,
        geography_code: params.get('geography_code') ?? params.get('geo_code') ?? pref.default_geography.code ?? '',
        has_spatial: this.toBool(params.get('has_spatial')),
        access_level: params.get('access_level') ?? '',
        due_soon_only: this.toBool(params.get('due_soon_only')),
        recency_days: params.get('recency_days') ?? '',
        sort: params.get('sort') ?? 'last_updated_desc',
        mode: (params.get('mode') as ExplorerMode) || 'table'
      },
      { emitEvent: false }
    );
    this.markVisit();
  }

  clearFilters(): void {
    const pref = this.preferences.snapshot;
    this.filters.setValue(
      {
        q: '',
        framework: '',
        gbf_goal: '',
        gbf_target: '',
        readiness_band: '',
        readiness_min: null,
        readiness_max: null,
        geography_type: pref.default_geography.type,
        geography_code: pref.default_geography.code ?? '',
        has_spatial: false,
        access_level: '',
        due_soon_only: false,
        recency_days: '',
        sort: 'last_updated_desc',
        mode: 'table'
      },
      { emitEvent: true }
    );
  }

  saveCurrentView(): void {
    const name = window.prompt('Saved view name', 'Indicator Explorer View')?.trim();
    if (!name) {
      return;
    }
    const filters = this.normalizeFilters(this.filters.getRawValue());
    this.preferences
      .saveFilter(
        'indicators',
        name,
        {
          ...this.toApiQuery(filters),
          geo_type: filters.geography_type,
          geo_code: filters.geography_code
        },
        true
      )
      .subscribe();
  }

  applySavedView(filterId: string): void {
    if (!filterId) {
      return;
    }
    const row = this.preferences.snapshot.saved_filters.indicators.find((entry) => entry.id === filterId);
    if (!row) {
      return;
    }
    this.filters.patchValue(
      {
        q: String(row.params['q'] ?? ''),
        framework: String(row.params['framework'] ?? ''),
        gbf_goal: String(row.params['gbf_goal'] ?? ''),
        gbf_target: String(row.params['gbf_target'] ?? ''),
        readiness_band: String(row.params['readiness_band'] ?? ''),
        readiness_min: this.toNullableNumber(row.params['readiness_min']),
        readiness_max: this.toNullableNumber(row.params['readiness_max']),
        geography_type: String(
          row.params['geography_type'] ?? row.params['geo_type'] ?? this.preferences.snapshot.default_geography.type
        ),
        geography_code: String(
          row.params['geography_code'] ?? row.params['geo_code'] ?? this.preferences.snapshot.default_geography.code ?? ''
        ),
        has_spatial: this.toBool(row.params['has_spatial']),
        access_level: String(row.params['access_level'] ?? ''),
        due_soon_only: this.toBool(row.params['due_soon_only']),
        recency_days: String(row.params['recency_days'] ?? ''),
        sort: String(row.params['sort'] ?? 'last_updated_desc'),
        mode: ((row.params['mode'] as ExplorerMode) || 'table')
      },
      { emitEvent: true }
    );
  }

  toggleWatch(indicatorUuid: string): void {
    if (this.preferences.isWatched('indicators', indicatorUuid)) {
      this.preferences.removeWatchlist('indicators', indicatorUuid).subscribe();
      return;
    }
    this.preferences.addWatchlist('indicators', indicatorUuid).subscribe();
  }

  isWatched(indicatorUuid: string): boolean {
    return this.preferences.isWatched('indicators', indicatorUuid);
  }

  isChangedSinceLastVisit(item: IndicatorListItem): boolean {
    if (!this.previousVisit || !this.isWatched(item.uuid) || !item.updated_at) {
      return false;
    }
    return new Date(item.updated_at).getTime() > this.previousVisit.getTime();
  }

  toggleCompare(indicatorUuid: string): void {
    const index = this.selectedCompare.indexOf(indicatorUuid);
    if (index >= 0) {
      this.selectedCompare.splice(index, 1);
      return;
    }
    if (this.selectedCompare.length < 5) {
      this.selectedCompare.push(indicatorUuid);
    }
  }

  compareRows(rows: IndicatorListItem[]): IndicatorListItem[] {
    return rows.filter((row) => this.selectedCompare.includes(row.uuid));
  }

  copyNarrative(text: string): void {
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(text);
      return;
    }
    window.prompt('Copy narrative', text);
  }

  toggleInsights(): void {
    this.insightsOpen = !this.insightsOpen;
  }

  onHeaderAction(actionId: string): void {
    if (actionId === 'reset') {
      this.clearFilters();
    }
  }

  extractGbfTargets(item: IndicatorListItem): string[] {
    return item.tags.filter((tag) => tag.startsWith('GBF:')).map((tag) => tag.split(':')[1] || tag);
  }

  toReadinessStatus(item: IndicatorListItem): 'ready' | 'warning' | 'blocked' {
    if (item.readiness_status === 'ready') {
      return 'ready';
    }
    if (item.readiness_status === 'warning') {
      return 'warning';
    }
    return 'blocked';
  }

  toStatusTone(status: string): 'neutral' | 'success' | 'warn' | 'error' | 'info' {
    const normalized = (status || '').toLowerCase();
    if (normalized === 'published' || normalized === 'approved') {
      return 'success';
    }
    if (normalized.includes('review') || normalized.includes('pending')) {
      return 'warn';
    }
    if (normalized.includes('reject') || normalized.includes('blocked')) {
      return 'error';
    }
    return 'neutral';
  }

  downloadCsv(rows: IndicatorListItem[]): void {
    const header = ['uuid', 'code', 'title', 'readiness_score', 'status', 'last_updated_on', 'next_expected_update_on', 'coverage_geography'];
    const lines = [
      header.join(','),
      ...rows.map((row) =>
        [row.uuid, row.code, row.title, row.readiness_score, row.status, row.last_updated_on ?? '', row.next_expected_update_on ?? '', row.coverage.geography ?? '']
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(',')
      )
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = 'indicator-explorer.csv';
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }

  trackByIndicator(_: number, row: IndicatorListItem): string {
    return row.uuid;
  }

  trackBySavedView(_: number, row: SavedFilterEntry): string {
    return row.id;
  }

  private normalizeFilters(value: Partial<ExplorerFilters>): ExplorerFilters {
    return {
      q: String(value.q ?? '').trim(),
      framework: String(value.framework ?? '').trim(),
      gbf_goal: String(value.gbf_goal ?? '').trim(),
      gbf_target: String(value.gbf_target ?? '').trim(),
      readiness_band: String(value.readiness_band ?? '').trim(),
      readiness_min: this.toNullableNumber(value.readiness_min),
      readiness_max: this.toNullableNumber(value.readiness_max),
      geography_type: String(value.geography_type ?? 'national').trim() || 'national',
      geography_code: String(value.geography_code ?? '').trim(),
      has_spatial: Boolean(value.has_spatial),
      access_level: String(value.access_level ?? '').trim(),
      due_soon_only: Boolean(value.due_soon_only),
      recency_days: String(value.recency_days ?? '').trim(),
      sort: String(value.sort ?? 'last_updated_desc').trim() || 'last_updated_desc',
      mode: ((value.mode as ExplorerMode) || 'table')
    };
  }

  private toApiQuery(filters: ExplorerFilters): Record<string, string | number | boolean | undefined> {
    const query: Record<string, string | number | boolean | undefined> = {
      q: filters.q || undefined,
      framework: filters.framework || undefined,
      gbf_goal: filters.gbf_goal || undefined,
      gbf_target: filters.gbf_target || undefined,
      readiness_band: filters.readiness_band || undefined,
      readiness_min: filters.readiness_min ?? undefined,
      readiness_max: filters.readiness_max ?? undefined,
      geography_type: filters.geography_type || undefined,
      geography_code: filters.geography_code || undefined,
      has_spatial: filters.has_spatial ? true : undefined,
      access_level: filters.access_level || undefined,
      sort: filters.sort || undefined,
      mode: filters.mode
    };
    if (filters.due_soon_only) {
      query['next_expected_update_to'] = this.isoDateFromToday(60);
    }
    if (filters.recency_days) {
      const days = Number.parseInt(filters.recency_days, 10);
      if (!Number.isNaN(days) && days > 0) {
        query['last_updated_from'] = this.isoDateFromToday(-days);
      }
    }
    return query;
  }

  private syncUrl(filters: ExplorerFilters): void {
    const query = this.toApiQuery(filters);
    const queryParams: Record<string, string | null> = {};
    for (const [key, value] of Object.entries(query)) {
      queryParams[key] = value === undefined || value === '' ? null : String(value);
    }
    queryParams['geo_type'] = filters.geography_type || null;
    queryParams['geo_code'] = filters.geography_code || null;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams,
      queryParamsHandling: '',
      replaceUrl: true
    });
  }

  private isoDateFromToday(offsetDays: number): string {
    const date = new Date();
    date.setDate(date.getDate() + offsetDays);
    return date.toISOString().slice(0, 10);
  }

  private toNullableNumber(value: unknown): number | null {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  private toBool(value: unknown): boolean {
    if (typeof value === 'boolean') {
      return value;
    }
    return ['1', 'true', 'yes', 'on'].includes(String(value ?? '').toLowerCase());
  }

  private getPreviousVisit(): Date | null {
    try {
      const raw = localStorage.getItem(LAST_VISIT_KEY);
      if (!raw) {
        return null;
      }
      const parsed = new Date(raw);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    } catch {
      return null;
    }
  }

  private markVisit(): void {
    try {
      localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString());
    } catch {
      // Ignore localStorage failures.
    }
  }
}
