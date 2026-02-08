import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { combineLatest, map, shareReplay, startWith, switchMap, tap } from 'rxjs';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { IndicatorMapPanelComponent } from '../components/indicator-map-panel.component';
import { IndicatorService } from '../services/indicator.service';

@Component({
  selector: 'app-indicator-detail-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatCardModule,
    MatListModule,
    MatChipsModule,
    MatFormFieldModule,
    MatSelectModule,
    BaseChartDirective,
    IndicatorMapPanelComponent
  ],
  template: `
    <section *ngIf="detail$ | async as detail" class="detail-layout">
      <mat-card class="summary-card">
        <mat-card-title>{{ detail.indicator.code }} - {{ detail.indicator.title }}</mat-card-title>
        <mat-card-subtitle>{{ detail.indicator.coverage.geography || 'Coverage not specified' }}</mat-card-subtitle>
        <mat-card-content>
          <p>{{ detail.narrative?.summary || detail.indicator.description || 'No summary currently available.' }}</p>
          <div class="narrative-grid">
            <div>
              <strong>Limitations</strong>
              <p>{{ detail.narrative?.limitations || 'Not documented.' }}</p>
            </div>
            <div>
              <strong>Spatial coverage</strong>
              <p>{{ detail.narrative?.spatial_coverage || 'Not documented.' }}</p>
            </div>
            <div>
              <strong>Temporal coverage</strong>
              <p>{{ detail.narrative?.temporal_coverage || 'Not documented.' }}</p>
            </div>
          </div>
          <mat-chip-listbox>
            <mat-chip-option>{{ detail.indicator.status }}</mat-chip-option>
            <mat-chip-option>{{ detail.indicator.sensitivity }}</mat-chip-option>
            <mat-chip-option>{{ detail.indicator.qa_status }}</mat-chip-option>
            <mat-chip-option>{{ detail.indicator.method_readiness_state }}</mat-chip-option>
          </mat-chip-listbox>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>National Trend</mat-card-title>
        <mat-card-content *ngIf="lineChart$ | async as chartData">
          <canvas baseChart [type]="'line'" [data]="chartData"></canvas>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Province Comparison</mat-card-title>
        <mat-card-content>
          <mat-form-field appearance="outline" class="year-picker">
            <mat-label>Year</mat-label>
            <mat-select [formControl]="selectedYearControl">
              <mat-option *ngFor="let year of (yearOptions$ | async) ?? []" [value]="year">{{ year }}</mat-option>
            </mat-select>
          </mat-form-field>
          <canvas *ngIf="barChart$ | async as barData" baseChart [type]="'bar'" [data]="barData"></canvas>
        </mat-card-content>
      </mat-card>

      <mat-card class="map-card">
        <mat-card-title>Spatial Disaggregation Map</mat-card-title>
        <mat-card-content>
          <app-indicator-map-panel [featureCollection]="mapData$ | async"></app-indicator-map-panel>
        </mat-card-content>
      </mat-card>

      <mat-card class="pipeline-card" *ngIf="detail.pipeline as pipeline">
        <mat-card-title>Data Refresh and Provenance</mat-card-title>
        <mat-card-content>
          <p><strong>Data last refreshed:</strong> {{ pipeline.data_last_refreshed_at || 'n/a' }}</p>
          <p><strong>Latest year:</strong> {{ pipeline.latest_year || 'n/a' }}</p>
          <p><strong>Pipeline run:</strong> {{ pipeline.latest_pipeline_run_uuid || 'n/a' }}</p>
          <p><strong>Pipeline status:</strong> {{ pipeline.latest_pipeline_run_status || 'n/a' }}</p>
        </mat-card-content>
      </mat-card>

      <mat-card *ngIf="datasets$ | async as datasets">
        <mat-card-title>Linked Datasets</mat-card-title>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let row of datasets.datasets">
              {{ row.title }} ({{ row.status }}) - {{ row.organisation || 'No organisation' }}
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Methodologies</mat-card-title>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let item of detail.methodologies">
              {{ item.methodology_code }} v{{ item.version }} - {{ item.methodology_title }}
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Method Readiness</mat-card-title>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let profile of detail.method_profiles">
              {{ profile.method_type }} ({{ profile.implementation_key }}) - {{ profile.readiness_state }}
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>

      <mat-card *ngIf="detail.spatial_readiness as readiness">
        <mat-card-title>Spatial Input Readiness</mat-card-title>
        <mat-card-content>
          <p>
            Overall readiness:
            <strong>{{ readiness.overall_ready ? 'ready' : 'blocked/partial' }}</strong>
          </p>
          <h4>Required layers</h4>
          <mat-list>
            <mat-list-item *ngFor="let layer of readiness.layer_requirements">
              {{ layer.layer_code }} - {{ layer.title }} ({{ layer.available ? 'available' : 'not visible' }})
            </mat-list-item>
          </mat-list>
          <h4>Required sources</h4>
          <mat-list>
            <mat-list-item *ngFor="let source of readiness.source_requirements">
              {{ source.code }} - {{ source.status }} (last sync: {{ source.last_sync_at || 'n/a' }})
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Evidence</mat-card-title>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let item of detail.evidence">
              <a [href]="item.source_url" target="_blank" rel="noreferrer">{{ item.title }}</a>
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .detail-layout {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .summary-card,
      .map-card,
      .pipeline-card {
        grid-column: span 2;
      }
      .narrative-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
      }
      .narrative-grid p {
        margin: 0.35rem 0 0;
      }
      .year-picker {
        width: 180px;
      }
      @media (max-width: 1080px) {
        .detail-layout {
          grid-template-columns: 1fr;
        }
        .summary-card,
        .map-card,
        .pipeline-card {
          grid-column: span 1;
        }
        .narrative-grid {
          grid-template-columns: 1fr;
        }
      }
    `
  ]
})
export class IndicatorDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly indicatorService = inject(IndicatorService);

  readonly selectedYearControl = new FormControl<number | null>(null);

  private readonly indicatorUuid$ = this.route.paramMap.pipe(
    map((params) => params.get('uuid') ?? ''),
    shareReplay(1)
  );

  readonly detail$ = this.indicatorUuid$.pipe(switchMap((uuid) => this.indicatorService.detail(uuid)));

  readonly datasets$ = this.indicatorUuid$.pipe(switchMap((uuid) => this.indicatorService.datasets(uuid)));

  private readonly yearSeriesResponse$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.series(uuid, { agg: 'year' })),
    shareReplay(1)
  );

  readonly yearOptions$ = this.yearSeriesResponse$.pipe(
    map((series) => series.results.map((item) => Number(item.bucket)).filter((value) => Number.isFinite(value)).sort((a, b) => a - b)),
    shareReplay(1)
  );

  readonly selectedYear$ = combineLatest([
    this.yearOptions$,
    this.selectedYearControl.valueChanges.pipe(startWith(this.selectedYearControl.value))
  ]).pipe(
    map(([years, selected]) => {
      if (!years.length) {
        return null;
      }
      if (typeof selected === 'number' && years.includes(selected)) {
        return selected;
      }
      return years[years.length - 1];
    }),
    tap((year) => {
      if (year !== this.selectedYearControl.value) {
        this.selectedYearControl.setValue(year, { emitEvent: false });
      }
    }),
    shareReplay(1)
  );

  readonly lineChart$ = this.yearSeriesResponse$.pipe(
    map((series) => {
      const labels = series.results.map((item) => String(item.bucket));
      const data = series.results.map((item) => item.numeric_mean ?? 0);
      return {
        labels,
        datasets: [
          {
            label: 'National trend',
            data,
            borderColor: '#2f855a',
            backgroundColor: 'rgba(47, 133, 90, 0.2)',
            tension: 0.3
          }
        ]
      } as ChartData<'line'>;
    })
  );

  readonly barChart$ = combineLatest([this.indicatorUuid$, this.selectedYear$]).pipe(
    switchMap(([uuid, year]) => this.indicatorService.series(uuid, { agg: 'province', year: year ?? undefined })),
    map((series) => {
      const labels = series.results.map((item) => String(item.bucket));
      const data = series.results.map((item) => item.numeric_mean ?? 0);
      return {
        labels,
        datasets: [
          {
            label: 'Province value',
            data,
            backgroundColor: 'rgba(28, 99, 76, 0.7)',
            borderColor: '#14523d',
            borderWidth: 1
          }
        ]
      } as ChartData<'bar'>;
    })
  );

  readonly mapData$ = combineLatest([this.indicatorUuid$, this.selectedYear$]).pipe(
    switchMap(([uuid, year]) => this.indicatorService.map(uuid, { year: year ?? undefined }))
  );
}
