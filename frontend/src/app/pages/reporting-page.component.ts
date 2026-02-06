import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-reporting-page',
  standalone: true,
  imports: [MatCardModule, MatButtonModule, MatIconModule],
  template: `
    <section class="reporting-grid">
      <mat-card>
        <mat-card-title>Reporting Instances</mat-card-title>
        <mat-card-content>
          <p>
            Manage cycles, section workflows, approvals, and review dashboards in the existing Django reporting
            workspace.
          </p>
        </mat-card-content>
        <mat-card-actions>
          <a mat-flat-button color="primary" href="/reporting/cycles/">Open reporting cycles</a>
          <a mat-button href="/reporting/instances/new/">Create instance</a>
        </mat-card-actions>
      </mat-card>

      <mat-card>
        <mat-card-title>Review and Export</mat-card-title>
        <mat-card-content>
          <p>Use review dashboard, snapshots, and ORT exports from the reporting workspace.</p>
        </mat-card-content>
        <mat-card-actions>
          <a mat-flat-button color="primary" href="/reporting/cycles/">Go to workflow</a>
        </mat-card-actions>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .reporting-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }

      @media (max-width: 860px) {
        .reporting-grid {
          grid-template-columns: 1fr;
        }
      }
    `
  ]
})
export class ReportingPageComponent {}
