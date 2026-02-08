import { AsyncPipe, KeyValuePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { AuthService } from './services/auth.service';
import { HelpService } from './services/help.service';
import { AuthMeResponse } from './models/api.models';

type NavItem = {
  route: string;
  label: string;
  icon: string;
  public?: boolean;
  capability?: string;
};

@Component({
  selector: 'app-root',
  imports: [
    AsyncPipe,
    KeyValuePipe,
    NgFor,
    NgIf,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatSidenavModule,
    MatToolbarModule,
    MatDividerModule,
    MatProgressBarModule
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  private readonly authService = inject(AuthService);
  private readonly helpService = inject(HelpService);
  private readonly router = inject(Router);

  readonly navItems: NavItem[] = [
    { route: '/dashboard', label: 'Dashboard', icon: 'dashboard', capability: 'can_view_dashboard' },
    { route: '/indicators', label: 'Indicator Explorer', icon: 'insights', public: true },
    { route: '/map', label: 'Spatial Viewer', icon: 'map', capability: 'can_view_spatial' },
    { route: '/programmes', label: 'Programme Ops', icon: 'lan', capability: 'can_view_programmes' },
    { route: '/programmes/templates', label: 'Programme Templates', icon: 'schema', capability: 'can_manage_programme_templates' },
    { route: '/programmes/birdie', label: 'BIRDIE', icon: 'water', capability: 'can_view_birdie' },
    { route: '/registries/ecosystems', label: 'Ecosystem Registry', icon: 'terrain', capability: 'can_view_registries' },
    { route: '/registries/taxa', label: 'Taxon Registry', icon: 'pets', capability: 'can_view_registries' },
    { route: '/registries/ias', label: 'IAS Registry', icon: 'bug_report', capability: 'can_view_registries' },
    { route: '/nr7-builder', label: 'NR7 Builder', icon: 'assignment', capability: 'can_view_reporting_builder' },
    { route: '/template-packs', label: 'MEA Packs', icon: 'account_tree', capability: 'can_view_template_packs' },
    { route: '/report-products', label: 'Report Products', icon: 'auto_stories', capability: 'can_view_report_products' },
    { route: '/system-health', label: 'System Health', icon: 'monitor_heart', capability: 'can_view_system_health' }
  ];

  readonly me$ = this.authService.getMe();
  readonly visibleNavItems$ = this.me$.pipe(
    map((me) => this.navItems.filter((item) => this.canShowNavItem(item, me)))
  );
  readonly sectionHelp$ = this.router.events.pipe(
    filter((event) => event instanceof NavigationEnd),
    startWith(null),
    map(() => this.router.routerState.snapshot.root),
    map((root) => {
      let active = root;
      while (active.firstChild) {
        active = active.firstChild;
      }
      return (active.data?.['sectionKey'] as string) || 'section_i';
    }),
    switchMap((sectionKey) =>
      this.helpService
        .getSections()
        .pipe(map((payload) => payload.sections[sectionKey] ?? payload.sections['section_i'] ?? {}))
    )
  );

  readonly title$ = this.router.events.pipe(
    filter((event) => event instanceof NavigationEnd),
    startWith(null),
    map(() => this.router.routerState.snapshot.root),
    map((root) => {
      let active = root;
      while (active.firstChild) {
        active = active.firstChild;
      }
      return (active.data?.['title'] as string) || 'NBMS Workspace';
    })
  );

  private canShowNavItem(item: NavItem, me: AuthMeResponse | null): boolean {
    if (item.public) {
      return true;
    }
    if (!me) {
      return false;
    }
    if (!item.capability) {
      return true;
    }
    return Boolean(me.capabilities?.[item.capability]);
  }
}
