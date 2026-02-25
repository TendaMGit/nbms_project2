import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { WatchlistNamespace } from '../models/api.models';
import { UserPreferencesService } from '../services/user-preferences.service';

@Component({
  selector: 'app-work-page',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf, RouterLink, MatButtonModule, MatCardModule, MatIconModule],
  template: `
    <section class="work-page" *ngIf="vm$ | async as vm">
      <mat-card>
        <mat-card-title>My Work Queue</mat-card-title>
        <mat-card-subtitle>Watchlist updates and quick return views.</mat-card-subtitle>
        <div class="kpi-grid">
          <article>
            <strong>{{ vm.watchlist.indicators.length }}</strong>
            <span>Watched indicators</span>
          </article>
          <article>
            <strong>{{ vm.watchlist.registries.length }}</strong>
            <span>Watched registries</span>
          </article>
          <article>
            <strong>{{ vm.watchlist.reports.length }}</strong>
            <span>Watched reports</span>
          </article>
          <article>
            <strong>{{ vm.pinnedViews.length }}</strong>
            <span>Pinned views</span>
          </article>
        </div>
      </mat-card>

      <mat-card>
        <mat-card-title>My Watchlist</mat-card-title>
        <div class="watchlist-group" *ngFor="let namespace of watchlistNamespaces; trackBy: trackByNamespace">
          <h3>{{ namespace }}</h3>
          <div class="empty" *ngIf="!vm.watchlist[namespace].length">No items yet.</div>
          <div class="watch-row" *ngFor="let itemId of vm.watchlist[namespace]; trackBy: trackByItem">
            <code>{{ itemId }}</code>
            <div class="actions">
              <a mat-button color="primary" [routerLink]="routeFor(namespace, itemId)">Open</a>
              <button mat-button type="button" (click)="remove(namespace, itemId)">Remove</button>
            </div>
          </div>
        </div>
      </mat-card>

      <mat-card>
        <mat-card-title>Pinned Views</mat-card-title>
        <div class="empty" *ngIf="!vm.pinnedViews.length">Pin a saved filter from Indicator Explorer, Registries, or Downloads.</div>
        <div class="watch-row" *ngFor="let view of vm.pinnedViews; trackBy: trackByView">
          <div>
            <strong>{{ view.name }}</strong>
            <div class="meta">{{ view.namespace }}</div>
          </div>
          <a mat-button color="primary" [routerLink]="view.route" [queryParams]="view.queryParams">Open</a>
        </div>
      </mat-card>
    </section>
  `,
  styles: [
    `
      .work-page {
        display: grid;
        gap: 1rem;
      }

      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.6rem;
      }

      .kpi-grid article {
        border: 1px solid var(--nbms-border);
        border-radius: var(--nbms-radius-sm);
        padding: 0.65rem;
        display: grid;
        gap: 0.2rem;
      }

      .kpi-grid strong {
        font-size: 1.3rem;
      }

      .kpi-grid span {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      .watchlist-group {
        display: grid;
        gap: 0.45rem;
        margin-top: 0.75rem;
      }

      .watch-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid var(--nbms-border);
        border-radius: var(--nbms-radius-sm);
        padding: 0.45rem 0.65rem;
        gap: 0.5rem;
      }

      .actions {
        display: flex;
        align-items: center;
        gap: 0.35rem;
      }

      .meta,
      .empty {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class WorkPageComponent {
  private readonly preferences = inject(UserPreferencesService);
  readonly watchlistNamespaces: WatchlistNamespace[] = ['indicators', 'registries', 'reports'];

  readonly vm$ = this.preferences.preferences$.pipe(
    map((state) => ({
      watchlist: state.watchlist,
      pinnedViews: this.preferences.pinnedViews()
    }))
  );

  remove(namespace: WatchlistNamespace, itemId: string): void {
    this.preferences.removeWatchlist(namespace, itemId).subscribe();
  }

  routeFor(namespace: WatchlistNamespace, itemId: string): string[] {
    if (namespace === 'indicators') {
      return ['/indicators', itemId];
    }
    if (namespace === 'reports') {
      return ['/reports', itemId];
    }
    return ['/registries/taxa'];
  }

  trackByNamespace(_: number, namespace: string): string {
    return namespace;
  }

  trackByItem(_: number, itemId: string): string {
    return itemId;
  }

  trackByView(_: number, view: { id: string }): string {
    return view.id;
  }
}

