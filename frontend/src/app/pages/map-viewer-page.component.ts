import { AsyncPipe, KeyValuePipe, NgFor, NgIf } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, debounceTime, map, startWith, Subject, switchMap, takeUntil, tap } from 'rxjs';
import * as maplibregl from 'maplibre-gl';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { SpatialLayer } from '../models/api.models';
import { SpatialService } from '../services/spatial.service';

@Component({
  selector: 'app-map-viewer-page',
  standalone: true,
  imports: [
    AsyncPipe,
    KeyValuePipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule
  ],
  template: `
    <section class="map-layout">
      <mat-card class="controls">
        <mat-card-title>Layer Controls</mat-card-title>
        <mat-card-content *ngIf="layers$ | async as layerPayload">
          <div class="layer-row" *ngFor="let layer of layerPayload.layers">
            <mat-checkbox [formControl]="layerControl(layer.slug)">
              {{ layer.name }}
            </mat-checkbox>
          </div>

          <mat-form-field appearance="outline">
            <mat-label>Province filter</mat-label>
            <input matInput [formControl]="province" placeholder="WC, EC, KZN..." />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Indicator code</mat-label>
            <input matInput [formControl]="indicator" placeholder="NBMS-GBF-..." />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Year</mat-label>
            <input matInput type="number" [formControl]="year" />
          </mat-form-field>

          <section class="legend">
            <h3>Legend</h3>
            <div class="legend-row" *ngFor="let layer of layerPayload.layers">
              <span
                class="legend-swatch"
                [style.background]="layer.default_style_json['fillColor'] || '#2f855a'"
              ></span>
              <span>{{ layer.name }}</span>
            </div>
          </section>

          <section class="feature-info" *ngIf="selectedFeature">
            <h3>Selected Feature</h3>
            <div class="feature-row" *ngFor="let entry of selectedFeature | keyvalue">
              <strong>{{ entry.key }}:</strong> {{ entry.value }}
            </div>
          </section>
        </mat-card-content>
      </mat-card>

      <section class="map-pane">
        <div #mapContainer class="map-canvas"></div>
      </section>
    </section>
  `,
  styles: [
    `
      .map-layout {
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: 1rem;
      }

      .controls {
        max-height: 78vh;
        overflow: auto;
      }

      .map-pane {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(27, 67, 50, 0.2);
      }

      .map-canvas {
        min-height: 78vh;
      }

      .layer-row {
        margin-bottom: 0.4rem;
      }

      .legend,
      .feature-info {
        margin-top: 1rem;
      }

      .legend-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.3rem;
        font-size: 0.9rem;
      }

      .legend-swatch {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        border: 1px solid rgba(0, 0, 0, 0.18);
      }

      .feature-row {
        margin-bottom: 0.35rem;
      }

      @media (max-width: 980px) {
        .map-layout {
          grid-template-columns: 1fr;
        }
        .map-canvas {
          min-height: 60vh;
        }
      }
    `
  ]
})
export class MapViewerPageComponent implements AfterViewInit, OnDestroy {
  private readonly spatialService = inject(SpatialService);

  @ViewChild('mapContainer', { static: true }) mapContainer!: ElementRef<HTMLDivElement>;
  private map?: maplibregl.Map;
  private readonly destroy$ = new Subject<void>();
  private readonly layerControls = new Map<string, FormControl<boolean>>();
  private activeLayerIds: string[] = [];
  selectedFeature: Record<string, unknown> | null = null;

  readonly province = new FormControl<string>('');
  readonly indicator = new FormControl<string>('');
  readonly year = new FormControl<number | null>(null);
  readonly layers$ = this.spatialService.layers();

  layerControl(slug: string): FormControl<boolean> {
    if (!this.layerControls.has(slug)) {
      this.layerControls.set(slug, new FormControl<boolean>(true, { nonNullable: true }));
    }
    return this.layerControls.get(slug)!;
  }

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
      zoom: 4.6
    });

    this.map.on('load', () => {
      this.layers$
        .pipe(
          tap((payload) => {
            payload.layers.forEach((layer) => this.layerControl(layer.slug));
          }),
          switchMap((payload) =>
            combineLatest([
              ...payload.layers.map((layer) =>
                this.layerControl(layer.slug).valueChanges.pipe(startWith(this.layerControl(layer.slug).value))
              ),
              this.province.valueChanges.pipe(startWith(this.province.value)),
              this.indicator.valueChanges.pipe(startWith(this.indicator.value)),
              this.year.valueChanges.pipe(startWith(this.year.value))
            ]).pipe(
              debounceTime(250),
              switchMap((state) => {
                const visibility = state.slice(0, payload.layers.length) as boolean[];
                const province = (state[payload.layers.length] as string) ?? '';
                const indicator = (state[payload.layers.length + 1] as string) ?? '';
                const year = state[payload.layers.length + 2] as number | null;

                return combineLatest(
                  payload.layers.map((layer, index) => {
                    if (!visibility[index]) {
                      return [layer, null] as const;
                    }
                    const bounds = this.map!.getBounds();
                    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
                    return this.spatialService
                      .features(layer.slug, {
                        bbox,
                        province: province || undefined,
                        indicator: indicator || undefined,
                        year: year ?? undefined,
                        limit: 1500
                      })
                      .pipe(map((fc) => [layer, fc] as const));
                  })
                );
              })
            )
          ),
          takeUntil(this.destroy$)
        )
        .subscribe((entries) => this.renderLayers(entries as Array<readonly [SpatialLayer, any]>));

      const mapInstance = this.map;
      if (!mapInstance) {
        return;
      }
      mapInstance.on('click', (event) => {
        if (!this.map || !this.activeLayerIds.length) {
          this.selectedFeature = null;
          return;
        }
        const features = this.map.queryRenderedFeatures(event.point, { layers: this.activeLayerIds });
        if (!features.length) {
          this.selectedFeature = null;
          return;
        }
        this.selectedFeature = { ...(features[0].properties ?? {}) };
      });
    });
  }

  private renderLayers(entries: Array<readonly [SpatialLayer, any]>) {
    if (!this.map) {
      return;
    }
    this.activeLayerIds = [];
    for (const [layer, featureCollection] of entries) {
      const sourceId = `layer-${layer.slug}`;
      const fillId = `fill-${layer.slug}`;
      const lineId = `line-${layer.slug}`;

      if (this.map.getLayer(fillId)) {
        this.map.removeLayer(fillId);
      }
      if (this.map.getLayer(lineId)) {
        this.map.removeLayer(lineId);
      }
      if (this.map.getSource(sourceId)) {
        this.map.removeSource(sourceId);
      }

      if (!featureCollection) {
        continue;
      }
      this.map.addSource(sourceId, {
        type: 'geojson',
        data: featureCollection
      });
      this.map.addLayer({
        id: fillId,
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': '#2f855a',
          'fill-opacity': 0.3
        }
      });
      this.map.addLayer({
        id: lineId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#1b4332',
          'line-width': 1.2
        }
      });
      this.activeLayerIds.push(fillId);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.map?.remove();
  }
}
