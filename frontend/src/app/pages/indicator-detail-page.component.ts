import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { map, switchMap } from 'rxjs';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData } from 'chart.js';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';

import { IndicatorService } from '../services/indicator.service';

@Component({
  selector: 'app-indicator-detail-page',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf, MatCardModule, MatListModule, MatChipsModule, BaseChartDirective],
  template: `
    <section *ngIf="detail$ | async as detail" class="detail-layout">
      <mat-card>
        <mat-card-title>{{ detail.indicator.code }} - {{ detail.indicator.title }}</mat-card-title>
        <mat-card-subtitle>{{ detail.indicator.coverage.geography || 'Coverage not specified' }}</mat-card-subtitle>
        <mat-card-content>
          <p>{{ detail.indicator.description || 'No summary currently available.' }}</p>
          <mat-chip-listbox>
            <mat-chip-option>{{ detail.indicator.status }}</mat-chip-option>
            <mat-chip-option>{{ detail.indicator.sensitivity }}</mat-chip-option>
            <mat-chip-option>{{ detail.indicator.qa_status }}</mat-chip-option>
          </mat-chip-listbox>
        </mat-card-content>
      </mat-card>

      <mat-card *ngIf="seriesChart$ | async as chartData">
        <mat-card-title>Trend Chart</mat-card-title>
        <mat-card-content>
          <canvas baseChart [type]="'line'" [data]="chartData"></canvas>
        </mat-card-content>
      </mat-card>

      <mat-card *ngIf="datasets$ | async as datasets">
        <mat-card-title>Linked datasets</mat-card-title>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let row of datasets.datasets">
              {{ row.title }} ({{ row.status }})
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
        gap: 1rem;
      }
    `
  ]
})
export class IndicatorDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly indicatorService = inject(IndicatorService);

  private readonly indicatorUuid$ = this.route.paramMap.pipe(
    map((params) => params.get('uuid') ?? '')
  );

  readonly detail$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.detail(uuid))
  );

  readonly datasets$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.datasets(uuid))
  );

  readonly seriesChart$ = this.indicatorUuid$.pipe(
    switchMap((uuid) => this.indicatorService.series(uuid, { agg: 'year' })),
    map((series) => {
      const labels = series.results.map((item) => String(item.bucket));
      const data = series.results.map((item) => item.numeric_mean ?? 0);
      return {
        labels,
        datasets: [
          {
            label: 'Mean value',
            data,
            borderColor: '#2f855a',
            backgroundColor: 'rgba(47, 133, 90, 0.2)',
            tension: 0.3
          }
        ]
      } as ChartData<'line'>;
    })
  );
}
