import { AsyncPipe, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import {
  BehaviorSubject,
  catchError,
  combineLatest,
  debounceTime,
  distinctUntilChanged,
  filter,
  map,
  of,
  startWith,
  switchMap
} from 'rxjs';

import { AuthService } from './services/auth.service';
import { HelpService } from './services/help.service';
import { AuthMeResponse, DashboardSummary, IndicatorListResponse } from './models/api.models';
import { NbmsAppShellComponent } from './ui/nbms-app-shell.component';
import { NbmsCommand } from './ui/nbms-command-palette.component';
import { NbmsNavGroup, NbmsNavItem } from './ui/nbms-app-shell.types';
import { NbmsSearchResult } from './ui/nbms-search-bar.component';
import { DashboardService } from './services/dashboard.service';
import { IndicatorService } from './services/indicator.service';
import { UserPreferencesService } from './services/user-preferences.service';

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
  private readonly dashboard = inject(DashboardService);
  private readonly indicators = inject(IndicatorService);
  private readonly userPreferences = inject(UserPreferencesService);
  private readonly searchQuerySubject = new BehaviorSubject<string>('');

  readonly navGroups: NavGroup[] = [
    {
      label: 'Database surfaces',
      items: [
        { route: '/dashboard', label: 'Dashboard', icon: 'dashboard', capability: 'can_view_dashboard' },
        { route: '/frameworks', label: 'Frameworks', icon: 'account_tree', public: true },
        { route: '/indicators', label: 'Indicators', icon: 'insights', public: true }
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
  readonly searchResults$ = combineLatest([
    this.searchQuerySubject.pipe(
      map((value) => value.trim()),
      debounceTime(120),
      distinctUntilChanged()
    ),
    this.dashboard.getSummary().pipe(catchError(() => of(emptyDashboardSummary())))
  ]).pipe(
    switchMap(([query, summary]) => {
      if (query.length < 2) {
        return of([] as NbmsSearchResult[]);
      }
      return this.indicators
        .list({ q: query, page_size: 6, sort: 'last_updated_desc' })
        .pipe(
          catchError(() => of(emptyIndicatorList())),
          map((payload) => buildSearchResults(summary, payload, query))
        );
    }),
    startWith([] as NbmsSearchResult[])
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

  readonly shellVm$ = combineLatest([
    this.me$,
    this.sectionHelp$,
    this.title$,
    this.visibleNavGroups$,
    this.commandItems$,
    this.searchResults$,
    this.userPreferences.preferences$
  ]).pipe(
    map(([me, help, title, navGroups, commandItems, searchResults, preferences]) => ({
      me,
      help,
      title,
      navGroups,
      commandItems,
      searchResults,
      preferences,
      pinnedViews: this.userPreferences.pinnedViews()
    }))
  );

  constructor() {
    this.userPreferences.bootstrap();
  }

  readonly environmentBadge =
    typeof window !== 'undefined' && window.location.hostname.includes('localhost') ? 'DEV' : 'PROD';
  readonly uiBuildMarker = this.detectUiBuildMarker();

  onGlobalSearch(search: string): void {
    this.searchQuerySubject.next(search);
  }

  onGlobalSearchSubmit(search: string): void {
    const query = search.trim();
    if (!query) {
      return;
    }
    void this.router.navigate(['/dashboard'], {
      queryParams: { tab: 'overview', q: query },
      queryParamsHandling: ''
    });
  }

  onGlobalSearchSelected(result: NbmsSearchResult): void {
    this.searchQuerySubject.next('');
    if (Array.isArray(result.route)) {
      void this.router.navigate(result.route);
      return;
    }
    void this.router.navigateByUrl(result.route);
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

  private detectUiBuildMarker(): string {
    if (typeof document === 'undefined') {
      return 'unknown';
    }
    const marker = document.querySelector('meta[name="nbms-ui-build"]')?.getAttribute('content')?.trim() ?? '';
    if (!marker || marker.includes('__NBMS_UI_BUILD__')) {
      return 'dev-local';
    }
    return marker;
  }
}

function buildSearchResults(
  summary: DashboardSummary,
  payload: IndicatorListResponse,
  query: string
): NbmsSearchResult[] {
  const frameworkRows = Array.from(
    summary.published_by_framework_target.reduce((acc, row) => {
      const code = row.framework_indicator__framework_target__framework__code || 'UNMAPPED';
      const current = acc.get(code) ?? { targetCount: 0, indicatorCount: 0 };
      current.targetCount += 1;
      current.indicatorCount += row.total;
      acc.set(code, current);
      return acc;
    }, new Map<string, { targetCount: number; indicatorCount: number }>())
  )
    .map(([code, metrics]) => ({
      id: `framework-${code}`,
      title: frameworkTitle(code),
      subtitle: `${code} • ${metrics.targetCount} targets • ${metrics.indicatorCount} indicator links`,
      kind: 'framework' as const,
      route: ['/frameworks', code],
      score: searchScore(query, code, frameworkTitle(code))
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title))
    .slice(0, 4);

  const targetFrameworkByCode = new Map<string, string>();
  for (const row of summary.published_by_framework_target) {
    if (!targetFrameworkByCode.has(row.framework_indicator__framework_target__code)) {
      targetFrameworkByCode.set(
        row.framework_indicator__framework_target__code,
        row.framework_indicator__framework_target__framework__code
      );
    }
  }

  const targetRows = summary.indicator_readiness.by_target
    .map((row) => {
      const frameworkId = targetFrameworkByCode.get(row.target_code) || 'GBF';
      return {
        id: `target-${frameworkId}-${row.target_code}`,
        title: `${row.target_code} • ${row.target_title || 'Target'}`,
        subtitle: `${frameworkId} • ${row.indicator_count} indicators • readiness ${Math.round(row.readiness_score_avg)}`,
        kind: 'target' as const,
        route: ['/frameworks', frameworkId, 'targets', row.target_code],
        score: searchScore(query, frameworkId, row.target_code, row.target_title)
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title))
    .slice(0, 5);

  const indicatorRows = payload.results
    .map((row) => ({
      id: `indicator-${row.uuid}`,
      title: `${row.code} • ${row.title}`,
      subtitle: `${row.status} • ${row.national_target.code || 'Unmapped'} • readiness ${row.readiness_score}`,
      kind: 'indicator' as const,
      route: ['/indicators', row.uuid],
      score: searchScore(query, row.code, row.title, row.national_target.title)
    }))
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title))
    .slice(0, 6);

  return [...frameworkRows, ...targetRows, ...indicatorRows].slice(0, 10);
}

function searchScore(query: string, ...fields: Array<string | null | undefined>): number {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return 0;
  }
  return fields.reduce((score, field) => {
    const haystack = (field || '').toLowerCase();
    if (!haystack) {
      return score;
    }
    if (haystack === needle) {
      return score + 100;
    }
    if (haystack.startsWith(needle)) {
      return score + 60;
    }
    if (haystack.includes(needle)) {
      return score + 25;
    }
    return score;
  }, 0);
}

function frameworkTitle(code: string): string {
  const titles: Record<string, string> = {
    GBF: 'Global Biodiversity Framework',
    NBSAP: 'National Biodiversity Strategy and Action Plan',
    SDG: 'Sustainable Development Goals',
    RAMSAR: 'Ramsar Convention',
    CITES: 'CITES',
    CMS: 'Convention on Migratory Species'
  };
  return titles[code] || code;
}

function emptyDashboardSummary(): DashboardSummary {
  return {
    counts: {},
    approvals_queue: 0,
    latest_published_updates: [],
    data_quality_alerts: [],
    published_by_framework_target: [],
    approvals_over_time: [],
    trend_signals: [],
    indicator_readiness: {
      totals: { ready: 0, warning: 0, blocked: 0 },
      by_target: []
    }
  };
}

function emptyIndicatorList(): IndicatorListResponse {
  return {
    count: 0,
    page: 1,
    page_size: 0,
    results: [],
    facets: {}
  };
}
