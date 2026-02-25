import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { Router } from '@angular/router';

import { ReportingInstanceSummary, ReportProductPreviewResponse, ReportProductSummary } from '../models/api.models';
import { DownloadRecordService } from '../services/download-record.service';
import { Nr7BuilderService } from '../services/nr7-builder.service';
import { ReportProductService } from '../services/report-product.service';
import { UserPreferencesService } from '../services/user-preferences.service';

@Component({
  selector: 'app-report-products-page',
  standalone: true,
  imports: [NgFor, NgIf, FormsModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatIconModule, MatSelectModule],
  template: `
    <div class="page">
      <mat-card>
        <mat-card-title>One Biodiversity Report Products</mat-card-title>
        <mat-card-subtitle>Generate NBA, GMO, and invasive report outputs from approved periodic releases.</mat-card-subtitle>
        <div class="controls">
          <mat-form-field appearance="outline">
            <mat-label>Report product</mat-label>
            <mat-select [(ngModel)]="selectedProductCode">
              <mat-option *ngFor="let product of products" [value]="product.code">
                {{ product.title }}
              </mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Reporting instance</mat-label>
            <mat-select [(ngModel)]="selectedInstanceUuid">
              <mat-option [value]="''">Global (no instance)</mat-option>
              <mat-option *ngFor="let instance of instances" [value]="instance.uuid">
                {{ instance.cycle_code }} / {{ instance.version_label }}
              </mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-flat-button color="primary" (click)="generatePreview()">Generate preview</button>
          <button mat-stroked-button type="button" (click)="saveCurrentView()">Save view</button>
        </div>
      </mat-card>

      <mat-card *ngIf="preview">
        <mat-card-title>{{ preview.template.title }} ({{ preview.template.code }})</mat-card-title>
        <mat-card-subtitle>Run {{ preview.run_uuid }}</mat-card-subtitle>
        <div class="actions">
          <button mat-stroked-button type="button" (click)="createProductExport('report_product_html')">
            Export HTML
          </button>
          <button mat-stroked-button type="button" (click)="createProductExport('report_product_pdf')">
            Export PDF
          </button>
        </div>
        <mat-card-content>
          <h3>Outline</h3>
          <ul>
            <li *ngFor="let section of payloadSections()">{{ section.title }}</li>
          </ul>
          <h3>QA</h3>
          <div *ngIf="payloadQaItems().length; else qaOk">
            <div *ngFor="let item of payloadQaItems()">
              [{{ item.severity }}] {{ item.message }}
            </div>
          </div>
          <ng-template #qaOk>
            <div>No QA findings.</div>
          </ng-template>
          <h3>Indicators in table</h3>
          <div>{{ payloadIndicatorCount() }}</div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: `
    .page {
      display: grid;
      gap: 1rem;
    }
    .controls {
      margin-top: 0.8rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 0.8rem;
      align-items: end;
    }
    .actions {
      display: flex;
      gap: 0.6rem;
      margin-bottom: 0.8rem;
    }
  `
})
export class ReportProductsPageComponent implements OnInit {
  readonly reportProductService = inject(ReportProductService);
  private readonly downloadRecords = inject(DownloadRecordService);
  private readonly nr7BuilderService = inject(Nr7BuilderService);
  private readonly preferences = inject(UserPreferencesService);
  private readonly router = inject(Router);

  products: ReportProductSummary[] = [];
  instances: ReportingInstanceSummary[] = [];
  selectedProductCode = '';
  selectedInstanceUuid = '';
  preview: ReportProductPreviewResponse | null = null;

  ngOnInit(): void {
    this.reportProductService.list().subscribe((payload) => {
      this.products = payload.report_products;
      if (!this.selectedProductCode && this.products.length) {
        this.selectedProductCode = this.products[0].code;
      }
    });
    this.nr7BuilderService.listInstances().subscribe((rows) => {
      this.instances = rows.instances;
    });
  }

  generatePreview(): void {
    if (!this.selectedProductCode) {
      return;
    }
    this.reportProductService
      .preview(this.selectedProductCode, this.selectedInstanceUuid || undefined)
      .subscribe((payload) => {
        this.preview = payload;
      });
  }

  payloadSections(): Array<{ title: string }> {
    return ((this.preview?.payload?.['sections'] as Array<{ title: string }>) || []).slice();
  }

  payloadQaItems(): Array<{ severity: string; message: string }> {
    const qa = this.preview?.payload?.['qa'] as { items?: Array<{ severity: string; message: string }> } | undefined;
    return qa?.items || [];
  }

  payloadIndicatorCount(): number {
    return ((this.preview?.payload?.['indicator_table'] as unknown[]) || []).length;
  }

  saveCurrentView(): void {
    const name = typeof window !== 'undefined' ? window.prompt('Name this downloads view', 'Downloads view') : 'Downloads view';
    if (!name || !name.trim()) {
      return;
    }
    this.preferences
      .saveFilter(
        'downloads',
        name.trim(),
        {
          product_code: this.selectedProductCode || undefined,
          instance_uuid: this.selectedInstanceUuid || undefined
        },
        true
      )
      .subscribe();
  }

  createProductExport(kind: 'report_product_html' | 'report_product_pdf'): void {
    if (!this.selectedProductCode) {
      return;
    }
    this.downloadRecords
      .create({
        record_type: 'custom_bundle',
        object_type: 'report_product',
        query_snapshot: {
          kind,
          product_code: this.selectedProductCode,
          instance_uuid: this.selectedInstanceUuid || undefined
        }
      })
      .subscribe((payload) => {
        this.router.navigate(['/downloads', payload.uuid]);
      });
  }
}
