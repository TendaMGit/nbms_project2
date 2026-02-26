import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import {
  GeographyType,
  SavedFilterNamespace,
  ThemeMode,
  ThemePackId,
  WatchlistNamespace
} from '../models/api.models';
import { UserPreferencesService } from '../services/user-preferences.service';

@Component({
  selector: 'app-account-preferences-page',
  standalone: true,
  imports: [
    AsyncPipe,
    NgFor,
    NgIf,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule
  ],
  template: `
    <section class="preferences-page" *ngIf="vm$ | async as vm">
      <mat-card>
        <mat-card-title>Profile & Preferences</mat-card-title>
        <mat-card-subtitle>Personalize layout, theme, default geography, saved views, and watchlists.</mat-card-subtitle>
        <div class="theme-grid">
          <button
            type="button"
            *ngFor="let option of themeOptions; trackBy: trackTheme"
            class="theme-option"
            [class.selected]="form.controls.theme_id.value === option.id"
            (click)="selectTheme(option.id)"
          >
            <div class="theme-swatch" [class]="'theme-' + option.id"></div>
            <strong>{{ option.label }}</strong>
            <span>{{ option.subtitle }}</span>
          </button>
        </div>

        <div class="form-grid">
          <mat-form-field appearance="outline">
            <mat-label>Theme mode</mat-label>
            <mat-select [formControl]="form.controls.theme_mode" (selectionChange)="saveThemeMode()">
              <mat-option value="light">Light</mat-option>
              <mat-option value="dark">Dark</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Density</mat-label>
            <mat-select [formControl]="form.controls.density" (selectionChange)="saveDensity()">
              <mat-option value="comfortable">Comfortable</mat-option>
              <mat-option value="compact">Compact</mat-option>
            </mat-select>
          </mat-form-field>
        </div>

        <div class="form-grid">
          <mat-form-field appearance="outline">
            <mat-label>Default geography level</mat-label>
            <mat-select [formControl]="form.controls.default_geography_type">
              <mat-option value="national">National</mat-option>
              <mat-option value="province">Province</mat-option>
              <mat-option value="district">District</mat-option>
              <mat-option value="municipality">Municipality</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Default geography code</mat-label>
            <input matInput [formControl]="form.controls.default_geography_code" placeholder="Optional code" />
          </mat-form-field>
        </div>

        <div class="actions">
          <button mat-flat-button color="primary" (click)="saveGeography()">Save default geography</button>
        </div>
      </mat-card>

      <mat-card>
        <mat-card-title>Saved Filters</mat-card-title>
        <mat-card-subtitle>Pinned views appear in the sidebar for quick return.</mat-card-subtitle>
        <div class="saved-filters" *ngFor="let namespace of filterNamespaces; trackBy: trackNamespace">
          <h3>{{ namespace }}</h3>
          <div class="empty" *ngIf="!vm.savedFilters[namespace].length">No saved views yet.</div>
          <div class="saved-row" *ngFor="let entry of vm.savedFilters[namespace]; trackBy: trackSavedFilter">
            <div>
              <strong>{{ entry.name }}</strong>
              <div class="meta">{{ entry.updated_at || 'n/a' }}</div>
            </div>
            <button mat-icon-button type="button" (click)="deleteSavedFilter(entry.id, namespace)" aria-label="Delete saved filter">
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </div>
      </mat-card>

      <mat-card>
        <mat-card-title>Watchlist</mat-card-title>
        <mat-card-subtitle>Watched items feed My Work and updates workflow.</mat-card-subtitle>
        <div class="watchlist-namespace" *ngFor="let namespace of watchlistNamespaces; trackBy: trackNamespace">
          <h3>{{ namespace }}</h3>
          <div class="empty" *ngIf="!vm.watchlist[namespace].length">No watched items.</div>
          <div class="watch-item" *ngFor="let itemId of vm.watchlist[namespace]; trackBy: trackWatch">
            <code>{{ itemId }}</code>
            <button mat-button color="primary" type="button" (click)="removeWatch(namespace, itemId)">Remove</button>
          </div>
        </div>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .preferences-page {
        display: grid;
        gap: 1rem;
      }

      .theme-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.75rem;
        margin-top: 0.75rem;
      }

      .theme-option {
        border: 1px solid var(--nbms-border);
        border-radius: var(--nbms-radius-md);
        background: var(--nbms-surface);
        color: var(--nbms-text-primary);
        text-align: left;
        padding: 0.7rem;
        display: grid;
        gap: 0.35rem;
        cursor: pointer;
      }

      .theme-option.selected {
        border-color: var(--nbms-color-primary-500);
        box-shadow: var(--nbms-shadow-sm);
      }

      .theme-option span {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      .theme-swatch {
        height: 0.75rem;
        border-radius: 999px;
      }

      .theme-fynbos {
        background: linear-gradient(90deg, #1e8b64, #318cc2);
      }

      .theme-gbif_clean {
        background: linear-gradient(90deg, #2e5f84, #a8bbc8);
      }

      .theme-high_contrast {
        background: linear-gradient(90deg, #000000, #ffd000);
      }

      .theme-dark_pro {
        background: linear-gradient(90deg, #0f1720, #1d6fd0);
      }

      .form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 0.75rem;
        margin-top: 0.9rem;
      }

      .actions {
        margin-top: 0.5rem;
      }

      .saved-filters,
      .watchlist-namespace {
        display: grid;
        gap: 0.4rem;
        margin-top: 0.75rem;
      }

      .saved-row,
      .watch-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.45rem 0.65rem;
        border-radius: var(--nbms-radius-sm);
        border: 1px solid var(--nbms-border);
      }

      .meta {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      .empty {
        color: var(--nbms-text-muted);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccountPreferencesPageComponent {
  private readonly preferences = inject(UserPreferencesService);
  private readonly destroyRef = inject(DestroyRef);

  readonly themeOptions = this.preferences.themeOptions;
  readonly filterNamespaces: SavedFilterNamespace[] = ['indicators', 'registries', 'downloads'];
  readonly watchlistNamespaces: WatchlistNamespace[] = ['indicators', 'registries', 'reports'];

  readonly form = new FormGroup({
    theme_id: new FormControl<ThemePackId>('fynbos', { nonNullable: true }),
    theme_mode: new FormControl<ThemeMode>('light', { nonNullable: true }),
    density: new FormControl<'comfortable' | 'compact'>('comfortable', { nonNullable: true }),
    default_geography_type: new FormControl<GeographyType>('national', { nonNullable: true }),
    default_geography_code: new FormControl<string>('', { nonNullable: true })
  });

  readonly vm$ = this.preferences.preferences$.pipe(
    map((state) => ({
      savedFilters: state.saved_filters,
      watchlist: state.watchlist
    }))
  );

  constructor() {
    this.preferences.preferences$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => {
        this.form.patchValue(
          {
            theme_id: state.theme_id,
            theme_mode: state.theme_mode,
            density: state.density,
            default_geography_type: state.default_geography.type,
            default_geography_code: state.default_geography.code || ''
          },
          { emitEvent: false }
        );
      });
  }

  selectTheme(themeId: ThemePackId): void {
    this.form.controls.theme_id.setValue(themeId, { emitEvent: false });
    this.preferences.setThemePack(themeId).subscribe();
  }

  saveThemeMode(): void {
    this.preferences.setThemeMode(this.form.controls.theme_mode.value).subscribe();
  }

  saveDensity(): void {
    this.preferences.setDensity(this.form.controls.density.value).subscribe();
  }

  saveGeography(): void {
    const code = this.form.controls.default_geography_code.value.trim();
    this.preferences
      .setDefaultGeography(
        this.form.controls.default_geography_type.value,
        code.length ? code : null
      )
      .subscribe();
  }

  deleteSavedFilter(filterId: string, namespace: SavedFilterNamespace): void {
    this.preferences.deleteSavedFilter(filterId, namespace).subscribe();
  }

  removeWatch(namespace: WatchlistNamespace, itemId: string): void {
    this.preferences.removeWatchlist(namespace, itemId).subscribe();
  }

  trackTheme(_: number, item: { id: ThemePackId }): string {
    return item.id;
  }

  trackNamespace(_: number, value: string): string {
    return value;
  }

  trackSavedFilter(_: number, entry: { id: string }): string {
    return entry.id;
  }

  trackWatch(_: number, itemId: string): string {
    return itemId;
  }
}
