import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatListModule } from '@angular/material/list';

import { TemplatePackService } from '../services/template-pack.service';

@Component({
  selector: 'app-template-packs-page',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf, MatCardModule, MatChipsModule, MatListModule],
  template: `
    <mat-card>
      <mat-card-title>Multi-MEA Template Packs</mat-card-title>
      <mat-card-subtitle>CBD is first-class; Ramsar/CITES/CMS scaffolds are active.</mat-card-subtitle>
      <mat-card-content>
        <mat-list *ngIf="packs$ | async as payload">
          <mat-list-item *ngFor="let pack of payload.packs">
            <div matListItemTitle>{{ pack.title }} ({{ pack.code }})</div>
            <div matListItemLine>{{ pack.description }}</div>
            <mat-chip-set>
              <mat-chip>{{ pack.mea_code }}</mat-chip>
              <mat-chip>{{ pack.version }}</mat-chip>
              <mat-chip>{{ pack.section_count }} sections</mat-chip>
            </mat-chip-set>
          </mat-list-item>
        </mat-list>
      </mat-card-content>
    </mat-card>
  `
})
export class TemplatePacksPageComponent {
  private readonly templatePackService = inject(TemplatePackService);
  readonly packs$ = this.templatePackService.list();
}
