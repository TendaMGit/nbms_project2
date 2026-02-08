import { AsyncPipe, KeyValuePipe, NgFor, NgIf } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { combineLatest, debounceTime, map, of, startWith, Subject, switchMap, takeUntil } from 'rxjs';
import * as maplibregl from 'maplibre-gl';

import { SpatialLayer } from '../models/api.models';
import { HelpService } from '../services/help.service';
import { SpatialService } from '../services/spatial.service';
import { ApiClientService } from '../services/api-client.service';

type LayerState = { enabled: boolean; opacity: number; wmsEnabled: boolean };

@Component({
  selector: 'app-map-viewer-page',
  standalone: true,
  imports: [
    AsyncPipe,
    KeyValuePipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSlideToggleModule,
    MatTooltipModule,
    MatSnackBarModule
  ],
  template: `
    <section class="map-layout">
      <aside class="sidebar">
        <mat-card class="panel">
          <mat-card-title>
            Map Workspace
            <button
              mat-icon-button
              class="hint"
              [matTooltip]="helpText || 'Filter layers, inspect features, and export map-ready datasets.'"
            >
              <mat-icon>help_outline</mat-icon>
            </button>
          </mat-card-title>
          <mat-card-content>
            <mat-form-field appearance="outline">
              <mat-label>Search layers</mat-label>
              <input matInput [formControl]="layerSearch" placeholder="GBF, province, Ramsar..." />
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Property filter key</mat-label>
              <input matInput [formControl]="propertyKey" placeholder="e.g. province_code" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Property filter value</mat-label>
              <input matInput [formControl]="propertyValue" placeholder="e.g. WC" />
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Province shortcut</mat-label>
              <input matInput [formControl]="provinceFilter" placeholder="WC, EC, KZN..." />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Year</mat-label>
              <input matInput [formControl]="yearFilter" type="number" />
            </mat-form-field>

            <section class="aoi-block">
              <div class="aoi-title">Area of Interest</div>
              <div class="aoi-actions">
                <button mat-stroked-button type="button" (click)="toggleAoiDraw()">
                  <mat-icon>{{ drawAoiEnabled ? 'close' : 'polyline' }}</mat-icon>
                  {{ drawAoiEnabled ? 'Cancel draw' : 'Draw AOI' }}
                </button>
                <button mat-stroked-button type="button" (click)="useViewportAsAoi()">Use current viewport</button>
              </div>
              <button mat-button type="button" (click)="clearAoi()">Clear AOI</button>
              <div class="aoi-value" *ngIf="drawAoiEnabled && !drawAoiStartPoint">
                Click the map to set the first AOI corner.
              </div>
              <div class="aoi-value" *ngIf="drawAoiEnabled && drawAoiStartPoint">
                Click the opposite corner to complete AOI.
              </div>
              <div class="aoi-value" *ngIf="aoiBbox">{{ aoiBbox }}</div>
            </section>
          </mat-card-content>
        </mat-card>

        <mat-card class="panel layer-catalog">
          <mat-card-title>Layer Catalog</mat-card-title>
          <mat-card-content *ngIf="layers$ | async as layerPayload">
            <ng-container *ngFor="let group of groupedLayers(layerPayload.layers) | keyvalue">
              <h3>{{ group.key }}</h3>
              <section class="layer-row" *ngFor="let layer of group.value">
                <div class="row-head">
                  <mat-slide-toggle
                    [checked]="layerState(layer).enabled"
                    (change)="toggleLayer(layer, $event.checked)"
                  >
                    {{ layer.title || layer.name }}
                  </mat-slide-toggle>
                  <button
                    mat-icon-button
                    [matTooltip]="
                      (layer.description || 'Layer metadata') +
                      (layer.attribution ? ' | Attribution: ' + layer.attribution : '') +
                      (layer.license ? ' | License: ' + layer.license : '')
                    "
                    (click)="selectLayer(layer)"
                    type="button"
                  >
                    <mat-icon>info</mat-icon>
                  </button>
                </div>
                <div class="row-sub">
                  <span>{{ layer.layer_code }}</span>
                  <span>{{ layer.source_type }}</span>
                  <span *ngIf="layer.license">licence: {{ layer.license }}</span>
                </div>
                <label class="opacity-row">
                  Opacity {{ displayOpacity(layerState(layer).opacity) }}
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    [value]="layerState(layer).opacity"
                    (input)="setLayerOpacity(layer, +$any($event.target).value)"
                  />
                </label>
                <mat-slide-toggle
                  [checked]="layerState(layer).wmsEnabled"
                  (change)="toggleWms(layer, $event.checked)"
                  matTooltip="Render using GeoServer WMS for this layer"
                >
                  GeoServer WMS
                </mat-slide-toggle>
                <div class="layer-actions">
                  <button mat-stroked-button type="button" (click)="exportLayer(layer)">
                    <mat-icon>download</mat-icon>
                    GeoJSON
                  </button>
                  <button mat-button type="button" (click)="addToReportProduct(layer)">
                    <mat-icon>post_add</mat-icon>
                    Add to report
                  </button>
                </div>
              </section>
            </ng-container>
          </mat-card-content>
        </mat-card>
      </aside>

      <section class="map-pane">
        <div #mapContainer class="map-canvas"></div>
        <article class="legend-panel" *ngIf="activeLegendRows().length">
          <header><h3>Legend</h3></header>
          <div class="legend-row" *ngFor="let item of activeLegendRows()">
            <span class="swatch" [style.background]="item.fill" [style.border-color]="item.line"></span>
            <div>
              <strong>{{ item.title }}</strong>
              <div class="legend-meta" *ngIf="item.attribution || item.license">
                {{ item.attribution || 'No attribution' }}{{ item.license ? ' | ' + item.license : '' }}
              </div>
            </div>
          </div>
        </article>
        <article class="inspect-panel" *ngIf="selectedFeature">
          <header>
            <h3>Feature Inspector</h3>
            <button mat-icon-button type="button" (click)="selectedFeature = null"><mat-icon>close</mat-icon></button>
          </header>
          <div class="feature-grid">
            <div class="feature-row" *ngFor="let item of selectedFeature | keyvalue">
              <strong>{{ item.key }}</strong>
              <span>{{ item.value }}</span>
            </div>
          </div>
        </article>
      </section>
    </section>
  `,
  styles: [
    `
      .map-layout {
        display: grid;
        grid-template-columns: minmax(320px, 420px) 1fr;
        gap: 1rem;
        align-items: start;
      }
      .sidebar {
        display: grid;
        gap: 1rem;
        max-height: 82vh;
        overflow: auto;
        padding-right: 0.2rem;
      }
      .panel {
        border-radius: 14px;
      }
      .hint {
        margin-left: 0.4rem;
      }
      .layer-catalog .layer-row {
        border: 1px solid rgba(27, 67, 50, 0.2);
        border-radius: 10px;
        padding: 0.6rem;
        margin-bottom: 0.7rem;
        background: rgba(255, 255, 255, 0.65);
      }
      .layer-row .row-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .layer-row .row-sub {
        display: flex;
        gap: 0.7rem;
        font-size: 0.78rem;
        color: #466;
      }
      .layer-actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.5rem;
      }
      .opacity-row {
        display: grid;
        gap: 0.2rem;
        font-size: 0.82rem;
        color: #264;
      }
      .aoi-block {
        display: grid;
        gap: 0.4rem;
      }
      .aoi-actions {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
      }
      .aoi-title {
        font-size: 0.85rem;
        font-weight: 600;
      }
      .aoi-value {
        font-family: monospace;
        font-size: 0.78rem;
        color: #244;
      }
      .map-pane {
        position: relative;
        min-height: 82vh;
        border: 1px solid rgba(27, 67, 50, 0.2);
        border-radius: 14px;
        overflow: hidden;
      }
      .map-canvas {
        height: 82vh;
      }
      .inspect-panel {
        position: absolute;
        right: 0.8rem;
        top: 0.8rem;
        width: min(360px, 45%);
        max-height: 72vh;
        overflow: auto;
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid rgba(27, 67, 50, 0.2);
        border-radius: 12px;
        padding: 0.6rem;
      }
      .legend-panel {
        position: absolute;
        left: 0.8rem;
        bottom: 0.8rem;
        width: min(360px, 45%);
        max-height: 42vh;
        overflow: auto;
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(27, 67, 50, 0.2);
        border-radius: 12px;
        padding: 0.55rem;
      }
      .legend-row {
        display: flex;
        gap: 0.45rem;
        align-items: center;
        border-bottom: 1px dashed rgba(20, 50, 40, 0.2);
        padding: 0.35rem 0;
      }
      .swatch {
        width: 22px;
        height: 14px;
        border: 2px solid #1b4332;
        border-radius: 3px;
      }
      .legend-meta {
        font-size: 0.75rem;
        color: #355;
      }
      .inspect-panel header {
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .feature-grid {
        display: grid;
        gap: 0.45rem;
      }
      .feature-row {
        display: grid;
        gap: 0.1rem;
        border-bottom: 1px dashed rgba(20, 50, 40, 0.2);
        padding-bottom: 0.35rem;
      }
      @media (max-width: 1080px) {
        .map-layout {
          grid-template-columns: 1fr;
        }
        .sidebar {
          max-height: unset;
        }
        .map-canvas {
          height: 62vh;
        }
        .legend-panel,
        .inspect-panel {
          width: calc(100% - 1.6rem);
          max-height: 32vh;
        }
      }
    `
  ]
})
export class MapViewerPageComponent implements AfterViewInit, OnDestroy {
  private readonly spatialService = inject(SpatialService);
  private readonly helpService = inject(HelpService);
  private readonly api = inject(ApiClientService);
  private readonly snackBar = inject(MatSnackBar);

  @ViewChild('mapContainer', { static: true }) mapContainer!: ElementRef<HTMLDivElement>;

  readonly layerSearch = new FormControl<string>('', { nonNullable: true });
  readonly propertyKey = new FormControl<string>('', { nonNullable: true });
  readonly propertyValue = new FormControl<string>('', { nonNullable: true });
  readonly provinceFilter = new FormControl<string>('', { nonNullable: true });
  readonly yearFilter = new FormControl<number | null>(null);

  readonly layers$ = this.spatialService.layers();
  helpText = '';

  selectedFeature: Record<string, unknown> | null = null;
  private map?: maplibregl.Map;
  private readonly destroy$ = new Subject<void>();
  private readonly layerStateMap = new Map<string, LayerState>();
  private currentLayers: SpatialLayer[] = [];
  aoiBbox: string | null = null;
  drawAoiEnabled = false;
  drawAoiStartPoint: maplibregl.LngLat | null = null;

  displayOpacity = (value: number): string => `${Math.round(value * 100)}%`;

  ngAfterViewInit(): void {
    this.map = new maplibregl.Map({
      container: this.mapContainer.nativeElement,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '(c) OpenStreetMap contributors'
          }
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
      },
      center: [24.0, -29.0],
      zoom: 4.4
    });

    this.helpService
      .getSections()
      .pipe(takeUntil(this.destroy$))
      .subscribe((payload) => {
        this.helpText = payload.sections?.['section_iv']?.['summary'] || '';
      });

    const map = this.map;
    if (!map) {
      return;
    }
    map.on('load', () => {
      this.layers$
        .pipe(takeUntil(this.destroy$))
        .subscribe((payload) => {
          this.currentLayers = payload.layers;
          for (const layer of payload.layers) {
            if (!this.layerStateMap.has(layer.layer_code)) {
              this.layerStateMap.set(layer.layer_code, { enabled: true, opacity: 0.55, wmsEnabled: false });
            }
          }
          this.syncMapLayers();
        });

      combineLatest([
        this.layerSearch.valueChanges.pipe(startWith(this.layerSearch.value)),
        this.propertyKey.valueChanges.pipe(startWith(this.propertyKey.value)),
        this.propertyValue.valueChanges.pipe(startWith(this.propertyValue.value)),
        this.provinceFilter.valueChanges.pipe(startWith(this.provinceFilter.value)),
        this.yearFilter.valueChanges.pipe(startWith(this.yearFilter.value))
      ])
        .pipe(debounceTime(350), takeUntil(this.destroy$))
        .subscribe(() => this.syncMapLayers(true));

      map.on('moveend', () => this.syncMapLayers(true));
      map.on('click', (event) => {
        if (this.drawAoiEnabled) {
          this.captureAoiPoint(event.lngLat);
          return;
        }
        this.inspectFeature(event.point.x, event.point.y);
      });
    });
  }

  layerState(layer: SpatialLayer): LayerState {
    const current = this.layerStateMap.get(layer.layer_code);
    if (current) {
      return current;
    }
    const fallback: LayerState = { enabled: true, opacity: 0.55, wmsEnabled: false };
    this.layerStateMap.set(layer.layer_code, fallback);
    return fallback;
  }

  toggleLayer(layer: SpatialLayer, enabled: boolean): void {
    this.layerStateMap.set(layer.layer_code, { ...this.layerState(layer), enabled });
    this.syncMapLayers();
  }

  setLayerOpacity(layer: SpatialLayer, opacity: number): void {
    this.layerStateMap.set(layer.layer_code, { ...this.layerState(layer), opacity: Number(opacity) || 0.4 });
    this.applyLayerOpacity(layer);
  }

  toggleWms(layer: SpatialLayer, enabled: boolean): void {
    this.layerStateMap.set(layer.layer_code, { ...this.layerState(layer), wmsEnabled: enabled });
    this.syncMapLayers(true);
  }

  selectLayer(layer: SpatialLayer): void {
    this.snackBar.open(
      `${layer.title || layer.name} | ${layer.layer_code} | ${layer.sensitivity}`,
      'Close',
      { duration: 3000 }
    );
  }

  useViewportAsAoi(): void {
    if (!this.map) {
      return;
    }
    const b = this.map.getBounds();
    this.aoiBbox = `${b.getWest().toFixed(6)},${b.getSouth().toFixed(6)},${b.getEast().toFixed(6)},${b.getNorth().toFixed(6)}`;
    this.renderAoiFromBbox(this.aoiBbox);
    this.syncMapLayers(true);
  }

  clearAoi(): void {
    this.aoiBbox = null;
    this.drawAoiEnabled = false;
    this.drawAoiStartPoint = null;
    this.removeAoiOverlay();
    this.syncMapLayers(true);
  }

  toggleAoiDraw(): void {
    this.drawAoiEnabled = !this.drawAoiEnabled;
    this.drawAoiStartPoint = null;
    if (!this.drawAoiEnabled) {
      this.snackBar.open('AOI drawing cancelled.', 'Close', { duration: 2000 });
    } else {
      this.snackBar.open('Click two corners on the map to draw AOI.', 'Close', { duration: 2600 });
    }
  }

  groupedLayers(layers: SpatialLayer[]) {
    const needle = (this.layerSearch.value || '').trim().toLowerCase();
    const grouped: Record<string, SpatialLayer[]> = {};
    for (const layer of layers) {
      const haystack = `${layer.layer_code} ${layer.title || layer.name} ${layer.theme} ${layer.description}`.toLowerCase();
      if (needle && !haystack.includes(needle)) {
        continue;
      }
      const groupKey = (layer.theme || 'Other').trim() || 'Other';
      grouped[groupKey] = grouped[groupKey] || [];
      grouped[groupKey].push(layer);
    }
    for (const key of Object.keys(grouped)) {
      grouped[key] = grouped[key].sort((a, b) => (a.title || a.name).localeCompare(b.title || b.name));
    }
    return grouped;
  }

  exportLayer(layer: SpatialLayer): void {
    const params = this.queryParams();
    this.spatialService
      .exportGeoJson(layer.layer_code, { ...params, limit: 20000 })
      .pipe(
        switchMap((payload) => {
          const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/geo+json' });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = `${layer.layer_code}.geojson`;
          anchor.click();
          URL.revokeObjectURL(url);
          return of(payload);
        }),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (payload) => {
          this.snackBar.open(`Exported ${payload.numberReturned ?? payload.features.length} features`, 'Close', {
            duration: 3000
          });
        },
        error: (error) => {
          this.snackBar.open(error?.error?.detail || 'GeoJSON export failed.', 'Close', { duration: 4500 });
        }
      });
  }

  addToReportProduct(layer: SpatialLayer): void {
    this.api
      .get(`report-products/nba_v1/preview`, { map_layer_code: layer.layer_code })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (payload: any) => {
          this.snackBar.open(`Added to NBA preview. Run ${payload?.run_uuid ?? ''}`, 'Close', { duration: 3500 });
        },
        error: (error) => {
          this.snackBar.open(error?.error?.detail || 'Could not add layer to report product.', 'Close', {
            duration: 4500
          });
        }
      });
  }

  private inspectFeature(x: number, y: number): void {
    if (!this.map) {
      return;
    }
    const ids = this.activeLayerIds();
    if (!ids.length) {
      this.selectedFeature = null;
      return;
    }
    const features = this.map.queryRenderedFeatures([x, y], { layers: ids });
    if (!features.length) {
      this.selectedFeature = null;
      return;
    }
    this.selectedFeature = { ...(features[0].properties ?? {}) };
  }

  private queryParams() {
    const filters: string[] = [];
    const key = this.propertyKey.value.trim();
    const value = this.propertyValue.value.trim();
    if (key && value) {
      filters.push(`${key}=${value}`);
    }
    const province = this.provinceFilter.value.trim();
    if (province) {
      filters.push(`province_code=${province}`);
    }
    const year = this.yearFilter.value;
    if (typeof year === 'number') {
      filters.push(`year=${year}`);
    }
    return {
      bbox: this.aoiBbox ?? this.currentMapBbox(),
      filter: filters.join(',') || undefined
    };
  }

  private currentMapBbox(): string | undefined {
    if (!this.map) {
      return undefined;
    }
    const b = this.map.getBounds();
    return `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`;
  }

  private activeLayerIds(): string[] {
    const ids: string[] = [];
    for (const layer of this.currentLayers) {
      const state = this.layerState(layer);
      if (!state.enabled) {
        continue;
      }
      ids.push(`lyr-fill-${layer.layer_code}`, `lyr-line-${layer.layer_code}`, `lyr-circle-${layer.layer_code}`);
    }
    return ids.filter((id) => !!this.map?.getLayer(id));
  }

  private syncMapLayers(forceReload = false): void {
    if (!this.map || !this.currentLayers.length) {
      return;
    }
    for (const layer of this.currentLayers) {
      const state = this.layerState(layer);
      if (!state.enabled) {
        this.removeLayer(layer);
        continue;
      }
      if (state.wmsEnabled) {
        this.addOrRefreshWmsLayer(layer, forceReload);
        this.applyLayerOpacity(layer);
        continue;
      }
      this.addOrRefreshLayer(layer, forceReload);
      this.applyLayerOpacity(layer);
    }
  }

  activeLegendRows() {
    return this.currentLayers
      .filter((layer) => this.layerState(layer).enabled)
      .map((layer) => ({
        title: layer.title || layer.name,
        fill: (layer.default_style_json['fillColor'] as string) || '#2f855a',
        line: (layer.default_style_json['lineColor'] as string) || '#1b4332',
        attribution: layer.attribution,
        license: layer.license
      }));
  }

  private captureAoiPoint(point: maplibregl.LngLat): void {
    if (!this.drawAoiStartPoint) {
      this.drawAoiStartPoint = point;
      return;
    }
    const minx = Math.min(this.drawAoiStartPoint.lng, point.lng);
    const miny = Math.min(this.drawAoiStartPoint.lat, point.lat);
    const maxx = Math.max(this.drawAoiStartPoint.lng, point.lng);
    const maxy = Math.max(this.drawAoiStartPoint.lat, point.lat);
    this.aoiBbox = `${minx.toFixed(6)},${miny.toFixed(6)},${maxx.toFixed(6)},${maxy.toFixed(6)}`;
    this.drawAoiEnabled = false;
    this.drawAoiStartPoint = null;
    this.renderAoiFromBbox(this.aoiBbox);
    this.syncMapLayers(true);
  }

  private renderAoiFromBbox(bbox: string | null): void {
    if (!this.map || !bbox) {
      return;
    }
    const parts = bbox.split(',').map((item) => Number(item));
    if (parts.length !== 4 || parts.some((item) => Number.isNaN(item))) {
      return;
    }
    const [minx, miny, maxx, maxy] = parts;
    const sourceId = 'aoi-draw-source';
    const fillId = 'aoi-draw-fill';
    const lineId = 'aoi-draw-line';
    const featureCollection = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Polygon',
            coordinates: [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]]
          }
        }
      ]
    } as GeoJSON.FeatureCollection;
    if (!this.map.getSource(sourceId)) {
      this.map.addSource(sourceId, { type: 'geojson', data: featureCollection });
      this.map.addLayer({
        id: fillId,
        type: 'fill',
        source: sourceId,
        paint: { 'fill-color': '#38a169', 'fill-opacity': 0.15 }
      });
      this.map.addLayer({
        id: lineId,
        type: 'line',
        source: sourceId,
        paint: { 'line-color': '#1b4332', 'line-width': 1.4 }
      });
    } else {
      const source = this.map.getSource(sourceId) as maplibregl.GeoJSONSource;
      source.setData(featureCollection);
    }
  }

  private removeAoiOverlay(): void {
    if (!this.map) {
      return;
    }
    if (this.map.getLayer('aoi-draw-fill')) {
      this.map.removeLayer('aoi-draw-fill');
    }
    if (this.map.getLayer('aoi-draw-line')) {
      this.map.removeLayer('aoi-draw-line');
    }
    if (this.map.getSource('aoi-draw-source')) {
      this.map.removeSource('aoi-draw-source');
    }
  }

  private addOrRefreshLayer(layer: SpatialLayer, forceReload: boolean): void {
    if (!this.map) {
      return;
    }
    const sourceId = `src-${layer.layer_code}`;
    const fillId = `lyr-fill-${layer.layer_code}`;
    const lineId = `lyr-line-${layer.layer_code}`;
    const circleId = `lyr-circle-${layer.layer_code}`;
    this.removeWmsLayer(layer);
    if (forceReload) {
      this.removeLayer(layer);
    }
    if (!this.map.getSource(sourceId)) {
      const params = this.queryParams();
      const query = new URLSearchParams();
      if (params.bbox) {
        query.set('bbox', params.bbox);
      }
      if (params.filter) {
        query.set('filter', params.filter);
      }
      const tileUrl = `/api/tiles/${layer.layer_code}/{z}/{x}/{y}.pbf${query.toString() ? `?${query.toString()}` : ''}`;
      this.map.addSource(sourceId, {
        type: 'vector',
        tiles: [tileUrl],
        minzoom: 0,
        maxzoom: 14
      });
    }
    const sourceLayer = layer.layer_code.toLowerCase();
    if (!this.map.getLayer(fillId)) {
      this.map.addLayer({
        id: fillId,
        type: 'fill',
        source: sourceId,
        'source-layer': sourceLayer,
        paint: {
          'fill-color': (layer.default_style_json['fillColor'] as string) || '#2f855a',
          'fill-opacity': this.layerState(layer).opacity
        }
      });
    }
    if (!this.map.getLayer(lineId)) {
      this.map.addLayer({
        id: lineId,
        type: 'line',
        source: sourceId,
        'source-layer': sourceLayer,
        paint: {
          'line-color': (layer.default_style_json['lineColor'] as string) || '#1b4332',
          'line-width': 1.1
        }
      });
    }
    if (!this.map.getLayer(circleId)) {
      this.map.addLayer({
        id: circleId,
        type: 'circle',
        source: sourceId,
        'source-layer': sourceLayer,
        paint: {
          'circle-color': (layer.default_style_json['circleColor'] as string) || '#14532d',
          'circle-opacity': this.layerState(layer).opacity,
          'circle-radius': Number(layer.default_style_json['circleRadius'] ?? 4)
        }
      });
    }
  }

  private applyLayerOpacity(layer: SpatialLayer): void {
    if (!this.map) {
      return;
    }
    const opacity = this.layerState(layer).opacity;
    const fillId = `lyr-fill-${layer.layer_code}`;
    const circleId = `lyr-circle-${layer.layer_code}`;
    const wmsLayerId = `lyr-wms-${layer.layer_code}`;
    if (this.map.getLayer(fillId)) {
      this.map.setPaintProperty(fillId, 'fill-opacity', opacity);
    }
    if (this.map.getLayer(circleId)) {
      this.map.setPaintProperty(circleId, 'circle-opacity', opacity);
    }
    if (this.map.getLayer(wmsLayerId)) {
      this.map.setPaintProperty(wmsLayerId, 'raster-opacity', opacity);
    }
  }

  private removeVectorLayer(layer: SpatialLayer): void {
    if (!this.map) {
      return;
    }
    const sourceId = `src-${layer.layer_code}`;
    const fillId = `lyr-fill-${layer.layer_code}`;
    const lineId = `lyr-line-${layer.layer_code}`;
    const circleId = `lyr-circle-${layer.layer_code}`;
    if (this.map.getLayer(fillId)) {
      this.map.removeLayer(fillId);
    }
    if (this.map.getLayer(lineId)) {
      this.map.removeLayer(lineId);
    }
    if (this.map.getLayer(circleId)) {
      this.map.removeLayer(circleId);
    }
    if (this.map.getSource(sourceId)) {
      this.map.removeSource(sourceId);
    }
  }

  private removeLayer(layer: SpatialLayer): void {
    this.removeVectorLayer(layer);
    this.removeWmsLayer(layer);
  }

  private wmsTileTemplate(layer: SpatialLayer): string {
    const workspace = 'nbms';
    const geoserverLayer = layer.geoserver_layer_name || `nbms_gs_${layer.layer_code.toLowerCase()}`;
    const params = new URLSearchParams({
      service: 'WMS',
      request: 'GetMap',
      layers: `${workspace}:${geoserverLayer}`,
      styles: '',
      format: 'image/png',
      transparent: 'true',
      version: '1.1.1',
      width: '256',
      height: '256',
      srs: 'EPSG:3857',
      bbox: '{bbox-epsg-3857}'
    });
    return `/geoserver/${workspace}/wms?${params.toString()}`;
  }

  private addOrRefreshWmsLayer(layer: SpatialLayer, forceReload: boolean): void {
    if (!this.map) {
      return;
    }
    const sourceId = `src-wms-${layer.layer_code}`;
    const layerId = `lyr-wms-${layer.layer_code}`;
    if (forceReload) {
      this.removeWmsLayer(layer);
    }
    this.removeVectorLayer(layer);
    if (!this.map.getSource(sourceId)) {
      this.map.addSource(sourceId, {
        type: 'raster',
        tiles: [this.wmsTileTemplate(layer)],
        tileSize: 256
      });
    }
    if (!this.map.getLayer(layerId)) {
      this.map.addLayer({
        id: layerId,
        type: 'raster',
        source: sourceId,
        paint: {
          'raster-opacity': this.layerState(layer).opacity
        }
      });
    }
  }

  private removeWmsLayer(layer: SpatialLayer): void {
    if (!this.map) {
      return;
    }
    const sourceId = `src-wms-${layer.layer_code}`;
    const layerId = `lyr-wms-${layer.layer_code}`;
    if (this.map.getLayer(layerId)) {
      this.map.removeLayer(layerId);
    }
    if (this.map.getSource(sourceId)) {
      this.map.removeSource(sourceId);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.removeAoiOverlay();
    this.map?.remove();
  }
}
