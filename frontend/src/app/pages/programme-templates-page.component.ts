import { AsyncPipe, JsonPipe, NgFor } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { map, startWith, switchMap } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';

import { HelpTooltipComponent } from '../components/help-tooltip.component';
import { RegistryService } from '../services/registry.service';

@Component({
  selector: 'app-programme-templates-page',
  standalone: true,
  imports: [
    AsyncPipe,
    JsonPipe,
    NgFor,
    RouterLink,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatListModule,
    MatButtonModule,
    MatChipsModule,
    HelpTooltipComponent
  ],
  template: `
    <section class="templates-grid">
      <mat-card>
        <mat-card-title>
          Programme Templates
          <app-help-tooltip text="Programme-driven templates that produce reusable gold outputs for indicators and reports." />
        </mat-card-title>
        <mat-card-content>
          <mat-form-field appearance="outline">
            <mat-label>Domain filter</mat-label>
            <input matInput [formControl]="domainFilter" placeholder="ecosystems / taxa / ias / protected_areas" />
          </mat-form-field>

          <div class="template-row" *ngFor="let row of templates$ | async">
            <div class="template-head">
              <strong>{{ row.template_code }}</strong>
              <mat-chip-set>
                <mat-chip>{{ row.domain }}</mat-chip>
                <mat-chip>{{ row.status }}</mat-chip>
              </mat-chip-set>
            </div>
            <p>{{ row.description }}</p>
            <div class="actions">
              <button
                mat-stroked-button
                color="primary"
                [routerLink]="row.linked_programme_uuid ? ['/programmes'] : ['/programmes/templates']"
                [disabled]="!row.linked_programme_uuid"
              >
                Open Programme Ops
              </button>
            </div>
            <div class="details">
              <h4>Pipeline</h4>
              <pre>{{ row.pipeline_definition_json | json }}</pre>
              <h4>Required outputs</h4>
              <mat-list>
                <mat-list-item *ngFor="let output of row.required_outputs_json">
                  {{ output['code'] }} - {{ output['label'] }}
                </mat-list-item>
              </mat-list>
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .templates-grid {
        display: grid;
        gap: 1rem;
      }
      .template-row {
        border: 1px solid rgba(20, 82, 61, 0.18);
        border-radius: 12px;
        padding: 0.7rem;
        margin-bottom: 0.8rem;
      }
      .template-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.8rem;
      }
      .actions {
        margin: 0.45rem 0 0.8rem;
      }
      .details {
        display: grid;
        gap: 0.3rem;
      }
      pre {
        margin: 0;
        max-height: 220px;
        overflow: auto;
        background: rgba(18, 106, 78, 0.06);
        border-radius: 10px;
        padding: 0.6rem;
      }
    `
  ]
})
export class ProgrammeTemplatesPageComponent {
  private readonly registryService = inject(RegistryService);

  readonly domainFilter = new FormControl<string>('', { nonNullable: true });

  readonly templates$ = this.domainFilter.valueChanges.pipe(
    startWith(this.domainFilter.value),
    switchMap((domain) => this.registryService.programmeTemplates({ domain: domain || undefined })),
    map((payload) => payload.templates)
  );
}
