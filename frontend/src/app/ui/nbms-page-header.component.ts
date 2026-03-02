import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { NbmsStatusPillComponent } from './nbms-status-pill.component';

type PageHeaderBreadcrumb = string | { label: string; route?: string | any[] };
type PageHeaderBadge = { label: string; tone: 'neutral' | 'success' | 'warn' | 'error' | 'info' };
type PageHeaderAction = {
  id: string;
  label: string;
  icon?: string;
  variant?: 'flat' | 'stroked' | 'text';
  route?: string | any[];
  disabled?: boolean;
  ariaLabel?: string;
};

@Component({
  selector: 'nbms-page-header',
  standalone: true,
  imports: [NgFor, NgIf, RouterLink, MatButtonModule, MatIconModule, NbmsStatusPillComponent],
  template: `
    <header class="page-header">
      <div class="header-main">
        <div class="breadcrumbs" *ngIf="breadcrumbs.length">
          <span *ngFor="let crumb of breadcrumbs; let last = last; trackBy: trackByValue">
            <ng-container *ngIf="isSimpleCrumb(crumb); else linkedCrumb">{{ crumb }}</ng-container>
            <ng-template #linkedCrumb>
              <a *ngIf="breadcrumbRoute(crumb); else crumbLabel" [routerLink]="breadcrumbRoute(crumb)">{{ breadcrumbLabel(crumb) }}</a>
              <ng-template #crumbLabel>{{ breadcrumbLabel(crumb) }}</ng-template>
            </ng-template>
            <span *ngIf="!last"> / </span>
          </span>
        </div>
        <h1>{{ title }}</h1>
        <p *ngIf="subtitle">{{ subtitle }}</p>
        <div class="badge-row" *ngIf="badges.length">
          <nbms-status-pill *ngFor="let badge of badges; trackBy: trackByBadge" [label]="badge.label" [tone]="badge.tone"></nbms-status-pill>
        </div>
      </div>
      <div class="header-actions">
        <nbms-status-pill
          *ngIf="statusLabel"
          [label]="statusLabel"
          [tone]="statusTone"
        ></nbms-status-pill>
        <button mat-flat-button color="primary" *ngIf="primaryActionLabel">{{ primaryActionLabel }}</button>
        <ng-container *ngFor="let action of actions; trackBy: trackByAction">
          <a
            *ngIf="action.route; else actionButton"
            [routerLink]="action.route"
            [attr.aria-label]="action.ariaLabel || action.label"
            [class.button-stroked]="(action.variant || 'stroked') === 'stroked'"
            [class.button-flat]="(action.variant || 'stroked') === 'flat'"
            class="header-action"
          >
            <mat-icon *ngIf="action.icon" aria-hidden="true">{{ action.icon }}</mat-icon>
            {{ action.label }}
          </a>
          <ng-template #actionButton>
            <button
              type="button"
              class="header-action"
              [class.button-stroked]="(action.variant || 'stroked') === 'stroked'"
              [class.button-flat]="(action.variant || 'stroked') === 'flat'"
              [disabled]="action.disabled"
              [attr.aria-label]="action.ariaLabel || action.label"
              (click)="actionSelected.emit(action.id)"
            >
              <mat-icon *ngIf="action.icon" aria-hidden="true">{{ action.icon }}</mat-icon>
              {{ action.label }}
            </button>
          </ng-template>
        </ng-container>
      </div>
    </header>
  `,
  styles: [
    `
      .page-header {
        display: flex;
        justify-content: space-between;
        gap: var(--nbms-space-4);
        align-items: flex-start;
        margin-bottom: var(--nbms-space-4);
      }

      .header-main h1 {
        font-size: var(--nbms-font-size-h2);
        margin-bottom: var(--nbms-space-1);
      }

      .header-main p {
        margin: 0;
        color: var(--nbms-text-secondary);
      }

      .breadcrumbs {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        margin-bottom: var(--nbms-space-1);
      }

      .breadcrumbs a {
        color: inherit;
        text-decoration: none;
      }

      .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: var(--nbms-space-2);
        margin-top: var(--nbms-space-2);
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: var(--nbms-space-2);
        flex-wrap: wrap;
      }

      .header-action {
        display: inline-flex;
        align-items: center;
        gap: var(--nbms-space-1);
        border-radius: var(--nbms-radius-pill);
        border: 1px solid var(--nbms-border);
        background: var(--nbms-surface);
        color: var(--nbms-text-primary);
        cursor: pointer;
        font: inherit;
        font-weight: 700;
        padding: var(--nbms-space-2) var(--nbms-space-3);
        text-decoration: none;
      }

      .header-action.button-flat {
        background: var(--nbms-color-primary-500);
        border-color: var(--nbms-color-primary-500);
        color: var(--nbms-surface);
      }

      .header-action:not(.button-flat):hover {
        background: var(--nbms-surface-muted);
      }

      @media (max-width: 900px) {
        .page-header {
          flex-direction: column;
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsPageHeaderComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() breadcrumbs: PageHeaderBreadcrumb[] = [];
  @Input() badges: PageHeaderBadge[] = [];
  @Input() actions: PageHeaderAction[] = [];
  @Input() statusLabel = '';
  @Input() statusTone: 'neutral' | 'success' | 'warn' | 'error' | 'info' = 'neutral';
  @Input() primaryActionLabel = '';

  @Output() actionSelected = new EventEmitter<string>();

  isSimpleCrumb(value: PageHeaderBreadcrumb): value is string {
    return typeof value === 'string';
  }

  breadcrumbLabel(value: PageHeaderBreadcrumb): string {
    return typeof value === 'string' ? value : value.label;
  }

  breadcrumbRoute(value: PageHeaderBreadcrumb): string | any[] | undefined {
    return typeof value === 'string' ? undefined : value.route;
  }

  trackByValue(_: number, value: PageHeaderBreadcrumb): string {
    return typeof value === 'string' ? value : value.label;
  }

  trackByBadge(_: number, value: PageHeaderBadge): string {
    return value.label;
  }

  trackByAction(_: number, value: PageHeaderAction): string {
    return value.id;
  }
}
