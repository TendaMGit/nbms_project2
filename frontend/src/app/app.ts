import { AsyncPipe, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { catchError, combineLatest, filter, map, of, startWith, switchMap } from 'rxjs';

import { AuthService } from './services/auth.service';
import { HelpService } from './services/help.service';
import { AuthMeResponse } from './models/api.models';
import { NbmsAppShellComponent } from './ui/nbms-app-shell.component';
import { NbmsCommand } from './ui/nbms-command-palette.component';
import { NbmsNavGroup, NbmsNavItem } from './ui/nbms-app-shell.types';

type NavGroup = NbmsNavGroup;
type NavItem = NbmsNavItem;

@Component({
  selector: 'app-root',
  imports: [
    AsyncPipe,
    NgIf,
    RouterOutlet,
    NbmsAppShellComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  private readonly authService = inject(AuthService);
  private readonly helpService = inject(HelpService);
  private readonly router = inject(Router);

  readonly navGroups: NavGroup[] = [
    {
      label: 'Core',
      items: [
        { route: '/dashboard', label: 'Dashboard', icon: 'dashboard', capability: 'can_view_dashboard' },
        { route: '/work', label: 'My Work', icon: 'task', public: true },
        { route: '/indicators', label: 'Indicators', icon: 'insights', public: true }
      ]
    },
    {
      label: 'Publishing',
      items: [
        { route: '/reporting', label: 'Reporting', icon: 'description', capability: 'can_view_reporting_builder' },
        { route: '/template-packs', label: 'Template Packs', icon: 'account_tree', capability: 'can_view_template_packs' },
        { route: '/downloads', label: 'Downloads', icon: 'download', public: true }
      ]
    },
    {
      label: 'Biodiversity',
      items: [
        { route: '/registries', label: 'Registries', icon: 'biotech', capability: 'can_view_registries' },
        { route: '/spatial/map', label: 'Spatial Viewer', icon: 'map', capability: 'can_view_spatial' },
        { route: '/spatial/layers', label: 'Spatial Layers', icon: 'layers', capability: 'can_view_spatial' }
      ]
    },
    {
      label: 'Operations',
      items: [
        { route: '/programmes', label: 'Programmes', icon: 'lan', capability: 'can_view_programmes' },
        { route: '/integrations', label: 'Integrations', icon: 'sync', capability: 'can_view_birdie' },
        { route: '/admin', label: 'Admin', icon: 'admin_panel_settings', capability: 'can_view_system_health' },
        { route: '/system/health', label: 'System Health', icon: 'monitor_heart', capability: 'can_view_system_health' }
      ]
    }
  ];

  readonly me$ = this.authService.getMe().pipe(startWith(null));
  readonly visibleNavGroups$ = this.me$.pipe(
    map((me) =>
      this.navGroups
        .map((group) => ({
          ...group,
          items: group.items.filter((item) => this.canShowNavItem(item, me))
        }))
        .filter((group) => group.items.length > 0)
    )
  );

  readonly commandItems$ = this.visibleNavGroups$.pipe(
    map((groups) =>
      groups.flatMap((group) =>
        group.items.map<NbmsCommand>((item) => ({
          id: `${group.label}-${item.route}`,
          label: `${group.label}: ${item.label}`,
          icon: item.icon,
          route: item.route
        }))
      )
    )
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
        .pipe(
          map((payload) => payload.sections[sectionKey] ?? payload.sections['section_i'] ?? {}),
          catchError(() => of({}))
        )
    ),
    startWith({})
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

  readonly shellVm$ = combineLatest([this.me$, this.sectionHelp$, this.title$, this.visibleNavGroups$, this.commandItems$]).pipe(
    map(([me, help, title, navGroups, commandItems]) => ({
      me,
      help,
      title,
      navGroups,
      commandItems
    }))
  );

  readonly environmentBadge =
    typeof window !== 'undefined' && window.location.hostname.includes('localhost') ? 'DEV' : 'PROD';

  onGlobalSearch(search: string): void {
    if (!search.trim()) {
      return;
    }
    void this.router.navigate(['/indicators'], { queryParams: { search } });
  }

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
