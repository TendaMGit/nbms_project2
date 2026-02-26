import { NgIf } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import * as maplibregl from 'maplibre-gl';

import { IndicatorMapResponse } from '../models/api.models';

@Component({
  selector: 'app-indicator-map-panel',
  standalone: true,
  imports: [NgIf],
  template: `
    <div class="map-wrapper">
      <div #mapHost class="map-host"></div>
      <div class="empty" *ngIf="!featureCollection?.features?.length">No map features available.</div>
    </div>
  `,
  styles: [
    `
      .map-wrapper {
        position: relative;
        min-height: 320px;
        border: 1px solid rgba(18, 48, 39, 0.2);
        border-radius: 12px;
        overflow: hidden;
      }
      .map-host {
        min-height: 320px;
      }
      .empty {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        background: rgba(255, 255, 255, 0.72);
        color: #244;
        font-size: 0.9rem;
      }
    `
  ]
})
export class IndicatorMapPanelComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() featureCollection: IndicatorMapResponse | null = null;
  @ViewChild('mapHost', { static: true }) mapHost!: ElementRef<HTMLDivElement>;

  private map?: maplibregl.Map;
  private popup?: maplibregl.Popup;

  ngAfterViewInit(): void {
    this.map = new maplibregl.Map({
      container: this.mapHost.nativeElement,
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
    this.map.on('load', () => {
      this.applyGeoJson();
      this.map?.on('click', 'indicator-fill', (event) => {
        const feature = event.features?.[0];
        const props = feature?.properties as Record<string, string> | undefined;
        if (!props) {
          return;
        }
        const label = props['name'] || props['province_code'] || props['feature_key'] || 'Feature';
        const value = props['indicator_value'] || 'n/a';
        if (this.popup) {
          this.popup.remove();
        }
        this.popup = new maplibregl.Popup({ closeButton: true, maxWidth: '260px' })
          .setLngLat(event.lngLat)
          .setHTML(`<strong>${label}</strong><br/>Indicator value: ${value}`)
          .addTo(this.map as maplibregl.Map);
      });
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['featureCollection']) {
      this.applyGeoJson();
    }
  }

  private applyGeoJson(): void {
    if (!this.map || !this.map.isStyleLoaded()) {
      return;
    }
    const payload = this.featureCollection ?? {
      type: 'FeatureCollection',
      features: []
    };
    const sourceId = 'indicator-geojson';
    if (!this.map.getSource(sourceId)) {
      this.map.addSource(sourceId, {
        type: 'geojson',
        data: payload as GeoJSON.FeatureCollection
      });
      this.map.addLayer({
        id: 'indicator-fill',
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': [
            'interpolate',
            ['linear'],
            ['coalesce', ['to-number', ['get', 'indicator_value']], 0],
            0,
            '#edf8e9',
            10,
            '#bae4b3',
            20,
            '#74c476',
            30,
            '#31a354',
            40,
            '#006d2c'
          ],
          'fill-opacity': 0.6
        }
      });
      this.map.addLayer({
        id: 'indicator-line',
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#1b4332',
          'line-width': 1
        }
      });
    } else {
      const source = this.map.getSource(sourceId) as maplibregl.GeoJSONSource;
      source.setData(payload as GeoJSON.FeatureCollection);
    }

    const features = (payload as IndicatorMapResponse).features || [];
    if (!features.length) {
      return;
    }
    const bounds = new maplibregl.LngLatBounds();
    for (const feature of features) {
      const coordinates = (feature.geometry as any)?.coordinates;
      this.extendBounds(bounds, coordinates);
    }
    if (!bounds.isEmpty()) {
      this.map.fitBounds(bounds, { padding: 28, duration: 0, maxZoom: 7.5 });
    }
  }

  private extendBounds(bounds: maplibregl.LngLatBounds, node: any): void {
    if (!Array.isArray(node)) {
      return;
    }
    if (node.length >= 2 && typeof node[0] === 'number' && typeof node[1] === 'number') {
      bounds.extend([node[0], node[1]]);
      return;
    }
    for (const child of node) {
      this.extendBounds(bounds, child);
    }
  }

  ngOnDestroy(): void {
    this.popup?.remove();
    this.map?.remove();
  }
}
