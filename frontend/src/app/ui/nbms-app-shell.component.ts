import { NgFor, NgIf } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  EventEmitter,
  HostListener,
  Input,
  Output,
  inject
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NbmsHelpDrawerComponent } from './nbms-help-drawer.component';
import { NbmsSearchBarComponent, type NbmsSearchResult } from './nbms-search-bar.component';
import { NbmsCommand, NbmsCommandPaletteComponent } from './nbms-command-palette.component';
import { NbmsNavGroup, NbmsNavItem, NbmsPinnedView } from './nbms-app-shell.types';
import { UserPreferencesService } from '../services/user-preferences.service';

@Component({
  selector: 'nbms-app-shell',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    RouterLink,
    RouterLinkActive,
    MatBadgeModule,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    MatListModule,
    MatMenuModule,
    MatSidenavModule,
    MatToolbarModule,
    MatTooltipModule,
    NbmsHelpDrawerComponent,
    NbmsSearchBarComponent,
    NbmsCommandPaletteComponent
  ],
  template: `
    <mat-sidenav-container class="shell-container">
      <mat-sidenav
        #mainNav
        class="side-nav"
        [mode]="isMobile ? 'over' : 'side'"
        [opened]="!isMobile || navOpen"
        [fixedInViewport]="isMobile"
      >
        <div class="brand">
          <p class="brand-kicker">National Biodiversity Monitoring System</p>
          <div class="brand-head">
            <h1>NBMS</h1>
            <span class="env-badge">{{ environment }}</span>
          </div>
          <p>Indicator database, narratives, and auditable reporting drilldowns.</p>
        </div>

        <mat-divider></mat-divider>

        <ng-container *ngFor="let group of navGroups; trackBy: trackByGroup">
          <section class="nav-group">
            <h3>{{ group.label }}</h3>
            <mat-nav-list>
              <a
                mat-list-item
                *ngFor="let item of group.items; trackBy: trackByItem"
                [routerLink]="item.route"
                routerLinkActive="active-link"
                (click)="onNavClick()"
              >
                <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
                <span matListItemTitle>{{ item.label }}</span>
                <span matListItemMeta class="item-badge" *ngIf="item.badge">{{ item.badge }}</span>
              </a>
            </mat-nav-list>
          </section>
        </ng-container>

        <section class="nav-group" *ngIf="pinnedViews.length">
          <h3>Pinned Views</h3>
          <mat-nav-list>
            <a
              mat-list-item
              *ngFor="let view of pinnedViews; trackBy: trackByPinnedView"
              [routerLink]="view.route"
              [queryParams]="view.queryParams"
              routerLinkActive="active-link"
              (click)="onNavClick()"
            >
              <mat-icon matListItemIcon>push_pin</mat-icon>
              <span matListItemTitle>{{ view.name }}</span>
              <span matListItemMeta class="item-badge">{{ view.namespace }}</span>
            </a>
          </mat-nav-list>
        </section>
      </mat-sidenav>

      <mat-sidenav-content>
        <mat-toolbar class="topbar">
          <div class="topbar-start">
            <button
              mat-icon-button
              class="mobile-toggle"
              aria-label="Toggle navigation"
              (click)="toggleNav()"
            >
              <mat-icon>menu</mat-icon>
            </button>
            <div class="title-wrap">
              <h2>{{ title }}</h2>
              <span class="subtitle">Periodic releases and approved publications</span>
            </div>
          </div>

          <div class="topbar-search">
            <nbms-search-bar
              [results]="searchResults"
              (queryChange)="search.emit($event)"
              (submitted)="searchSubmitted.emit($event)"
              (resultSelected)="searchResultSelected.emit($event)"
            ></nbms-search-bar>
          </div>

          <div class="topbar-actions">
            <button mat-icon-button aria-label="Command palette" (click)="openCommandPalette()" matTooltip="Command palette (Ctrl/Cmd+K)">
              <mat-icon>keyboard_command_key</mat-icon>
            </button>
            <button mat-icon-button aria-label="Toggle theme" (click)="toggleTheme()">
              <mat-icon>{{ themeMode === 'light' ? 'dark_mode' : 'light_mode' }}</mat-icon>
            </button>
            <button mat-icon-button aria-label="Notifications" [matBadge]="notificationsCount" matBadgeColor="warn" [matBadgeHidden]="!notificationsCount">
              <mat-icon>notifications</mat-icon>
            </button>
            <button mat-icon-button aria-label="Help drawer" (click)="toggleHelp()">
              <mat-icon>help</mat-icon>
            </button>
            <button mat-icon-button [matMenuTriggerFor]="userMenu" aria-label="User menu">
              <mat-icon>account_circle</mat-icon>
            </button>
            <mat-menu #userMenu="matMenu">
              <div class="user-summary">
                <strong>{{ username || 'Anonymous' }}</strong>
                <small>{{ orgName || 'No organisation' }}</small>
                <small>{{ themeId }} / {{ themeMode }} / {{ density }}</small>
              </div>
              <mat-divider></mat-divider>
              <a mat-menu-item [routerLink]="'/account/preferences'">
                <mat-icon>tune</mat-icon>
                Preferences
              </a>
              <a mat-menu-item *ngIf="username; else loginItem" [href]="logoutUrl">
                <mat-icon>logout</mat-icon>
                Logout
              </a>
              <ng-template #loginItem>
                <a mat-menu-item [href]="loginUrl">
                  <mat-icon>login</mat-icon>
                  Login / MFA
                </a>
              </ng-template>
            </mat-menu>
          </div>
        </mat-toolbar>

        <section class="content">
          <ng-content></ng-content>
        </section>
      </mat-sidenav-content>

      <mat-sidenav
        class="help-nav"
        position="end"
        mode="over"
        [opened]="helpOpen"
        (closedStart)="helpOpen = false"
      >
        <nbms-help-drawer [entries]="helpEntries"></nbms-help-drawer>
      </mat-sidenav>
    </mat-sidenav-container>

    <nbms-command-palette
      *ngIf="commandPaletteOpen"
      [commands]="commandItems"
      (closed)="commandPaletteOpen = false"
      (selected)="onCommandSelected($event)"
    ></nbms-command-palette>
  `,
  styles: [
    `
      .shell-container {
        min-height: 100vh;
        background: transparent;
      }

      .side-nav {
        width: var(--nbms-sidebar-width);
        border-right: 1px solid var(--nbms-border);
        background:
          linear-gradient(
            180deg,
            color-mix(in srgb, var(--nbms-surface-2) 84%, var(--nbms-surface-1)) 0%,
            var(--nbms-surface-1) 38%,
            color-mix(in srgb, var(--nbms-accent-100) 20%, var(--nbms-surface-1)) 100%
          );
        color: var(--nbms-text-primary);
        padding-bottom: var(--nbms-space-4);
      }

      .brand {
        padding: var(--nbms-space-5) var(--nbms-space-4) var(--nbms-space-4);
        display: grid;
        gap: var(--nbms-space-2);
      }

      .brand-kicker {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .brand-head {
        display: flex;
        align-items: center;
        gap: var(--nbms-space-2);
      }

      .brand h1 {
        margin: 0;
        font-size: 1.45rem;
        color: var(--nbms-text-primary);
      }

      .brand p {
        margin: 0;
        font-size: var(--nbms-font-size-label);
        color: var(--nbms-text-secondary);
      }

      .env-badge {
        font-size: var(--nbms-font-size-label-sm);
        border-radius: var(--nbms-radius-pill);
        border: 1px solid var(--nbms-border-strong);
        background: color-mix(in srgb, var(--nbms-accent-100) 72%, var(--nbms-surface));
        color: var(--nbms-text-primary);
        padding: 0.1rem 0.55rem;
      }

      .nav-group {
        padding: var(--nbms-space-2) var(--nbms-space-2) 0;
      }

      .nav-group h3 {
        margin: 0;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
        text-transform: uppercase;
        letter-spacing: 0.07em;
        padding: var(--nbms-space-2) var(--nbms-space-3);
      }

      .active-link {
        background: color-mix(in srgb, var(--nbms-accent-100) 76%, var(--nbms-surface));
        color: var(--nbms-text-primary);
        position: relative;
      }

      .active-link::before {
        content: '';
        position: absolute;
        left: 0.35rem;
        top: 50%;
        width: 0.45rem;
        height: 0.45rem;
        border-radius: 50%;
        background: var(--nbms-accent-500);
        transform: translateY(-50%);
      }

      .side-nav .mdc-list-item {
        margin: 0.15rem 0;
        border-radius: var(--nbms-radius-md);
      }

      .side-nav .mdc-list-item__primary-text,
      .side-nav mat-icon {
        color: inherit;
      }

      .item-badge {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      .topbar {
        position: sticky;
        top: 0;
        z-index: 50;
        height: auto;
        min-height: 4.6rem;
        padding: var(--nbms-space-3) var(--nbms-space-5);
        border-bottom: 1px solid var(--nbms-divider);
        background: color-mix(in srgb, var(--nbms-surface) 94%, transparent);
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: var(--nbms-space-3);
        backdrop-filter: blur(14px);
      }

      .topbar-start {
        display: flex;
        align-items: center;
        gap: var(--nbms-space-2);
      }

      .mobile-toggle {
        display: none;
      }

      .title-wrap {
        display: grid;
      }

      .title-wrap h2 {
        font-size: var(--nbms-font-size-h3);
        margin: 0;
        color: var(--nbms-text-primary);
      }

      .subtitle {
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label-sm);
      }

      .topbar-search {
        align-self: center;
      }

      .topbar-actions {
        display: flex;
        align-items: center;
        gap: var(--nbms-space-1);
      }

      .content {
        padding: var(--nbms-space-5);
      }

      .content > * {
        max-width: var(--nbms-app-max-width);
        margin: 0 auto;
        width: 100%;
      }

      .help-nav {
        width: min(26rem, calc(100vw - 1rem));
        padding: var(--nbms-space-4);
      }

      .user-summary {
        display: grid;
        padding: var(--nbms-space-2) var(--nbms-space-4);
      }

      .user-summary small {
        color: var(--nbms-text-muted);
      }

      @media (max-width: 960px) {
        .topbar {
          grid-template-columns: 1fr;
          align-items: stretch;
          gap: var(--nbms-space-2);
        }

        .mobile-toggle {
          display: inline-flex;
        }

        .content {
          padding: var(--nbms-space-3);
        }
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsAppShellComponent {
  private readonly navPreferenceKey = 'nbms.shell.navOpen';
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly userPreferences = inject(UserPreferencesService);

  @Input() navGroups: NbmsNavGroup[] = [];
  @Input() pinnedViews: NbmsPinnedView[] = [];
  @Input() title = 'NBMS Workspace';
  @Input() environment = 'DEV';
  @Input() notificationsCount = 0;
  @Input() username = '';
  @Input() orgName = '';
  @Input() themeId: 'mono_clean' | 'fynbos' | 'gbif_clean' | 'high_contrast' | 'dark_pro' = 'mono_clean';
  @Input() themeMode: 'light' | 'dark' = 'light';
  @Input() density: 'comfortable' | 'compact' = 'comfortable';
  @Input() loginUrl = '/account/login/';
  @Input() logoutUrl = '/accounts/logout/';
  @Input() helpEntries: Record<string, string> | null = null;
  @Input() commandItems: NbmsCommand[] = [];
  @Input() searchResults: NbmsSearchResult[] = [];
  @Output() search = new EventEmitter<string>();
  @Output() searchSubmitted = new EventEmitter<string>();
  @Output() searchResultSelected = new EventEmitter<NbmsSearchResult>();

  navOpen = true;
  helpOpen = false;
  commandPaletteOpen = false;
  isMobile = false;

  constructor() {
    this.isMobile = this.detectMobile();
    this.navOpen = this.readNavPreference();
    this.router.events
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => {
        if (event instanceof NavigationEnd && this.isMobile) {
          this.navOpen = false;
        }
      });
  }

  @HostListener('window:resize')
  onResize(): void {
    this.isMobile = this.detectMobile();
    if (!this.isMobile) {
      this.navOpen = this.readNavPreference();
    }
  }

  @HostListener('window:keydown', ['$event'])
  onWindowKeydown(event: KeyboardEvent): void {
    const pressed = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && pressed === 'k') {
      event.preventDefault();
      this.openCommandPalette();
    }
    if (pressed === 'escape') {
      this.commandPaletteOpen = false;
      if (this.isMobile && this.navOpen) {
        this.navOpen = false;
        this.writeNavPreference();
      }
      if (this.helpOpen) {
        this.helpOpen = false;
      }
    }
  }

  toggleNav(): void {
    this.navOpen = !this.navOpen;
    this.writeNavPreference();
  }

  onNavClick(): void {
    if (this.isMobile) {
      this.navOpen = false;
    }
  }

  toggleHelp(): void {
    this.helpOpen = !this.helpOpen;
  }

  openCommandPalette(): void {
    this.commandPaletteOpen = true;
  }

  onCommandSelected(command: NbmsCommand): void {
    this.commandPaletteOpen = false;
    if (command.route) {
      void this.router.navigateByUrl(command.route);
    }
  }

  toggleTheme(): void {
    const nextMode = this.themeMode === 'light' ? 'dark' : 'light';
    this.userPreferences.setThemeMode(nextMode).subscribe();
  }

  trackByGroup(_: number, group: NbmsNavGroup): string {
    return group.label;
  }

  trackByItem(_: number, item: NbmsNavItem): string {
    return item.route;
  }

  trackByPinnedView(_: number, item: NbmsPinnedView): string {
    return item.id;
  }

  private detectMobile(): boolean {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return false;
    }
    return window.matchMedia('(max-width: 960px)').matches;
  }

  private readNavPreference(): boolean {
    if (typeof localStorage === 'undefined') {
      return !this.isMobile;
    }
    const stored = localStorage.getItem(this.navPreferenceKey);
    if (stored === null) {
      return !this.isMobile;
    }
    return stored === '1';
  }

  private writeNavPreference(): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(this.navPreferenceKey, this.navOpen ? '1' : '0');
  }
}
