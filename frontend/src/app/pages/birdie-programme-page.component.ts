import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';

import { BirdieService } from '../services/birdie.service';

@Component({
  selector: 'app-birdie-programme-page',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf, MatCardModule, MatChipsModule, MatIconModule, MatTableModule],
  template: `
    <div class="grid" *ngIf="dashboard$ | async as dashboard">
      <mat-card>
        <mat-card-title>BIRDIE Programme Dashboard</mat-card-title>
        <mat-card-subtitle>{{ dashboard.programme.title }}</mat-card-subtitle>
        <mat-card-content>
          <mat-chip-set>
            <mat-chip>Code: {{ dashboard.programme.programme_code }}</mat-chip>
            <mat-chip>Cadence: {{ dashboard.programme.refresh_cadence }}</mat-chip>
            <mat-chip>Latest run: {{ dashboard.programme.latest_run_status || 'n/a' }}</mat-chip>
            <mat-chip>Open alerts: {{ dashboard.programme.open_alert_count }}</mat-chip>
          </mat-chip-set>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Site Reports</mat-card-title>
        <mat-card-content>
          <table mat-table [dataSource]="dashboard.site_reports" class="table">
            <ng-container matColumnDef="site">
              <th mat-header-cell *matHeaderCellDef>Site</th>
              <td mat-cell *matCellDef="let row">{{ row.site_name }} ({{ row.site_code }})</td>
            </ng-container>
            <ng-container matColumnDef="province">
              <th mat-header-cell *matHeaderCellDef>Province</th>
              <td mat-cell *matCellDef="let row">{{ row.province_code }}</td>
            </ng-container>
            <ng-container matColumnDef="abundance">
              <th mat-header-cell *matHeaderCellDef>Abundance</th>
              <td mat-cell *matCellDef="let row">{{ row.abundance_index ?? 'n/a' }}</td>
            </ng-container>
            <ng-container matColumnDef="richness">
              <th mat-header-cell *matHeaderCellDef>Richness</th>
              <td mat-cell *matCellDef="let row">{{ row.richness ?? 'n/a' }}</td>
            </ng-container>
            <ng-container matColumnDef="trend">
              <th mat-header-cell *matHeaderCellDef>Trend</th>
              <td mat-cell *matCellDef="let row">{{ row.trend }}</td>
            </ng-container>
            <tr mat-header-row *matHeaderRowDef="siteColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: siteColumns"></tr>
          </table>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Species Reports</mat-card-title>
        <mat-card-content>
          <table mat-table [dataSource]="dashboard.species_reports" class="table">
            <ng-container matColumnDef="species">
              <th mat-header-cell *matHeaderCellDef>Species</th>
              <td mat-cell *matCellDef="let row">{{ row.common_name }} ({{ row.species_code }})</td>
            </ng-container>
            <ng-container matColumnDef="guild">
              <th mat-header-cell *matHeaderCellDef>Guild</th>
              <td mat-cell *matCellDef="let row">{{ row.guild }}</td>
            </ng-container>
            <ng-container matColumnDef="value">
              <th mat-header-cell *matHeaderCellDef>Latest</th>
              <td mat-cell *matCellDef="let row">{{ row.last_value ?? 'n/a' }}</td>
            </ng-container>
            <ng-container matColumnDef="trend">
              <th mat-header-cell *matHeaderCellDef>Trend</th>
              <td mat-cell *matCellDef="let row">{{ row.trend }}</td>
            </ng-container>
            <tr mat-header-row *matHeaderRowDef="speciesColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: speciesColumns"></tr>
          </table>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-title>Map Layers and Provenance</mat-card-title>
        <mat-card-content>
          <div class="provenance-block">
            <h4>Map layer toggles</h4>
            <mat-chip-set>
              <mat-chip *ngFor="let layer of dashboard.map_layers">{{ layer.name }} ({{ layer.slug }})</mat-chip>
            </mat-chip-set>
          </div>
          <div class="provenance-block">
            <h4>Evidence and provenance</h4>
            <ul>
              <li *ngFor="let row of dashboard.provenance">
                {{ row.dataset_key }} - {{ row.captured_at }} - {{ row.source_endpoint }}
              </li>
            </ul>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: `
    .grid {
      display: grid;
      gap: 1rem;
    }
    .table {
      width: 100%;
    }
    .provenance-block {
      margin-bottom: 0.8rem;
    }
  `
})
export class BirdieProgrammePageComponent {
  private readonly birdieService = inject(BirdieService);
  readonly dashboard$ = this.birdieService.dashboard();

  readonly siteColumns = ['site', 'province', 'abundance', 'richness', 'trend'];
  readonly speciesColumns = ['species', 'guild', 'value', 'trend'];
}
