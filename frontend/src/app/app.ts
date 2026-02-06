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

  readonly navItems = [
    { route: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
    { route: '/indicators', label: 'Indicator Explorer', icon: 'insights' },
    { route: '/map', label: 'Spatial Viewer', icon: 'map' },
    { route: '/reporting', label: 'Reporting', icon: 'assignment' },
    { route: '/template-packs', label: 'MEA Packs', icon: 'account_tree' }
  ];

  readonly me$ = this.authService.getMe();
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
}
