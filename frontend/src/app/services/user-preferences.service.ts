import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import {
  DensityMode,
  GeographyType,
  SavedFilterEntry,
  SavedFilterNamespace,
  ThemeMode,
  ThemePackId,
  UserPreferenceResponse,
  WatchlistNamespace
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

type PinnedView = {
  id: string;
  name: string;
  namespace: SavedFilterNamespace;
  route: string;
  queryParams: Record<string, string>;
};

const LOCAL_STORAGE_KEY = 'nbms.preferences.local';
const THEME_PACKS: ThemePackId[] = ['fynbos', 'gbif_clean', 'high_contrast', 'dark_pro'];
const THEME_MODES: ThemeMode[] = ['light', 'dark'];
const DENSITIES: DensityMode[] = ['comfortable', 'compact'];
const GEOGRAPHY_TYPES: GeographyType[] = ['national', 'province', 'district', 'municipality'];
const FILTER_NAMESPACES: SavedFilterNamespace[] = ['indicators', 'registries', 'downloads'];
const WATCHLIST_NAMESPACES: WatchlistNamespace[] = ['indicators', 'registries', 'reports'];

const DEFAULT_PREFERENCES: UserPreferenceResponse = {
  theme_id: 'fynbos',
  theme_mode: 'light',
  density: 'comfortable',
  default_geography: {
    type: 'national',
    code: null
  },
  saved_filters: {
    indicators: [],
    registries: [],
    downloads: []
  },
  watchlist: {
    indicators: [],
    registries: [],
    reports: []
  },
  dashboard_layout: {},
  updated_at: null
};

@Injectable({ providedIn: 'root' })
export class UserPreferencesService {
  private bootstrapped = false;
  private readonly stateSubject = new BehaviorSubject<UserPreferenceResponse>(this.readLocalPreferences());
  readonly preferences$ = this.stateSubject.asObservable();

  constructor(private readonly api: ApiClientService) {
    this.applyToDocument(this.stateSubject.value);
  }

  bootstrap(): void {
    if (this.bootstrapped) {
      return;
    }
    this.bootstrapped = true;
    this.api
      .get<UserPreferenceResponse>('me/preferences')
      .pipe(catchError(() => of(this.stateSubject.value)))
      .subscribe((payload) => {
        const normalized = this.normalize(payload);
        this.commit(normalized);
      });
  }

  get snapshot(): UserPreferenceResponse {
    return this.stateSubject.value;
  }

  update(payload: Partial<UserPreferenceResponse>): Observable<UserPreferenceResponse> {
    return this.api.put<UserPreferenceResponse>('me/preferences', payload).pipe(
      map((response) => this.normalize(response)),
      tap((next) => this.commit(next)),
      catchError(() => {
        const next = this.applyLocalPartial(payload);
        return of(next);
      })
    );
  }

  setThemePack(themeId: ThemePackId): Observable<UserPreferenceResponse> {
    return this.update({ theme_id: themeId });
  }

  setThemeMode(themeMode: ThemeMode): Observable<UserPreferenceResponse> {
    return this.update({ theme_mode: themeMode });
  }

  setDensity(density: DensityMode): Observable<UserPreferenceResponse> {
    return this.update({ density });
  }

  setDefaultGeography(type: GeographyType, code: string | null): Observable<UserPreferenceResponse> {
    return this.update({ default_geography: { type, code } });
  }

  addWatchlist(namespace: WatchlistNamespace, itemId: string): Observable<UserPreferenceResponse> {
    return this.api
      .post<{ watchlist: UserPreferenceResponse['watchlist'] }>('me/preferences/watchlist/add', {
        namespace,
        uuid: itemId
      })
      .pipe(
        map((payload) => {
          const next: UserPreferenceResponse = {
            ...this.snapshot,
            watchlist: this.normalizeWatchlist(payload.watchlist),
            updated_at: new Date().toISOString()
          };
          this.commit(next);
          return next;
        }),
        catchError(() => {
          const watchlist = this.normalizeWatchlist(this.snapshot.watchlist);
          if (!watchlist[namespace].includes(itemId)) {
            watchlist[namespace] = [...watchlist[namespace], itemId];
          }
          const next = {
            ...this.snapshot,
            watchlist,
            updated_at: new Date().toISOString()
          };
          this.commit(next);
          return of(next);
        })
      );
  }

  removeWatchlist(namespace: WatchlistNamespace, itemId: string): Observable<UserPreferenceResponse> {
    return this.api
      .post<{ watchlist: UserPreferenceResponse['watchlist'] }>('me/preferences/watchlist/remove', {
        namespace,
        uuid: itemId
      })
      .pipe(
        map((payload) => {
          const next: UserPreferenceResponse = {
            ...this.snapshot,
            watchlist: this.normalizeWatchlist(payload.watchlist),
            updated_at: new Date().toISOString()
          };
          this.commit(next);
          return next;
        }),
        catchError(() => {
          const watchlist = this.normalizeWatchlist(this.snapshot.watchlist);
          watchlist[namespace] = watchlist[namespace].filter((value) => value !== itemId);
          const next = {
            ...this.snapshot,
            watchlist,
            updated_at: new Date().toISOString()
          };
          this.commit(next);
          return of(next);
        })
      );
  }

  saveFilter(
    namespace: SavedFilterNamespace,
    name: string,
    params: Record<string, unknown>,
    pinned = true
  ): Observable<UserPreferenceResponse> {
    return this.api
      .post<{ saved_filters: UserPreferenceResponse['saved_filters']; entry: SavedFilterEntry }>(
        'me/preferences/saved-filters',
        {
          namespace,
          name,
          params,
          pinned
        }
      )
      .pipe(
        map((payload) => {
          const next: UserPreferenceResponse = {
            ...this.snapshot,
            saved_filters: this.normalizeSavedFilters(payload.saved_filters),
            updated_at: payload.entry.updated_at
          };
          this.commit(next);
          return next;
        }),
        catchError(() => {
          const next = this.snapshotFromLocalFilterSave(namespace, name, params, pinned);
          this.commit(next);
          return of(next);
        })
      );
  }

  deleteSavedFilter(filterId: string, namespace?: SavedFilterNamespace): Observable<UserPreferenceResponse> {
    const params = namespace ? { namespace } : undefined;
    return this.api
      .delete<{ saved_filters: UserPreferenceResponse['saved_filters'] }>(
        `me/preferences/saved-filters/${encodeURIComponent(filterId)}`,
        params
      )
      .pipe(
        map((payload) => {
          const next: UserPreferenceResponse = {
            ...this.snapshot,
            saved_filters: this.normalizeSavedFilters(payload.saved_filters),
            updated_at: new Date().toISOString()
          };
          this.commit(next);
          return next;
        }),
        catchError(() => {
          const savedFilters = this.normalizeSavedFilters(this.snapshot.saved_filters);
          for (const key of FILTER_NAMESPACES) {
            if (!namespace || namespace === key) {
              savedFilters[key] = savedFilters[key].filter((entry) => entry.id !== filterId);
            }
          }
          const next = {
            ...this.snapshot,
            saved_filters: savedFilters,
            updated_at: new Date().toISOString()
          };
          this.commit(next);
          return of(next);
        })
      );
  }

  isWatched(namespace: WatchlistNamespace, itemId: string): boolean {
    return this.snapshot.watchlist[namespace].includes(itemId);
  }

  pinnedViews(): PinnedView[] {
    const views: PinnedView[] = [];
    for (const namespace of FILTER_NAMESPACES) {
      for (const entry of this.snapshot.saved_filters[namespace]) {
        if (!entry.pinned) {
          continue;
        }
        views.push({
          id: entry.id,
          name: entry.name,
          namespace,
          route: this.routeForNamespace(namespace),
          queryParams: this.stringifyParams(entry.params)
        });
      }
    }
    return views;
  }

  readonly themeOptions = [
    { id: 'fynbos' as ThemePackId, label: 'Fynbos', subtitle: 'Biodiversity green + ocean blue' },
    { id: 'gbif_clean' as ThemePackId, label: 'GBIF Clean', subtitle: 'Neutral and airy' },
    { id: 'high_contrast' as ThemePackId, label: 'High Contrast', subtitle: 'Accessibility-first contrast' },
    { id: 'dark_pro' as ThemePackId, label: 'Dark Pro', subtitle: 'Deep dark with vivid accents' }
  ];

  private commit(next: UserPreferenceResponse): void {
    this.stateSubject.next(next);
    this.persistLocal(next);
    this.applyToDocument(next);
  }

  private normalize(value: Partial<UserPreferenceResponse> | null | undefined): UserPreferenceResponse {
    const payload = value ?? {};
    const theme_id = THEME_PACKS.includes(payload.theme_id as ThemePackId)
      ? (payload.theme_id as ThemePackId)
      : DEFAULT_PREFERENCES.theme_id;
    const theme_mode = THEME_MODES.includes(payload.theme_mode as ThemeMode)
      ? (payload.theme_mode as ThemeMode)
      : DEFAULT_PREFERENCES.theme_mode;
    const density = DENSITIES.includes(payload.density as DensityMode)
      ? (payload.density as DensityMode)
      : DEFAULT_PREFERENCES.density;
    const defaultType = GEOGRAPHY_TYPES.includes(payload.default_geography?.type as GeographyType)
      ? (payload.default_geography?.type as GeographyType)
      : DEFAULT_PREFERENCES.default_geography.type;
    const codeRaw = payload.default_geography?.code;
    const geographyCode = typeof codeRaw === 'string' && codeRaw.trim() ? codeRaw.trim() : null;
    return {
      theme_id,
      theme_mode,
      density,
      default_geography: {
        type: defaultType,
        code: geographyCode
      },
      saved_filters: this.normalizeSavedFilters(payload.saved_filters),
      watchlist: this.normalizeWatchlist(payload.watchlist),
      dashboard_layout:
        payload.dashboard_layout && typeof payload.dashboard_layout === 'object'
          ? payload.dashboard_layout
          : {},
      updated_at: payload.updated_at ?? null
    };
  }

  private normalizeSavedFilters(value: unknown): UserPreferenceResponse['saved_filters'] {
    const normalized: UserPreferenceResponse['saved_filters'] = {
      indicators: [],
      registries: [],
      downloads: []
    };
    if (!value || typeof value !== 'object') {
      return normalized;
    }
    for (const namespace of FILTER_NAMESPACES) {
      const rows = (value as Record<string, unknown>)[namespace];
      if (!Array.isArray(rows)) {
        continue;
      }
      normalized[namespace] = rows
        .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
        .map((row) => {
          const idRaw = typeof row['id'] === 'string' && row['id'].trim() ? row['id'] : crypto.randomUUID();
          const nameRaw = typeof row['name'] === 'string' && row['name'].trim() ? row['name'] : 'Saved view';
          return {
            id: idRaw,
            name: nameRaw,
            params:
              row['params'] && typeof row['params'] === 'object'
                ? (row['params'] as Record<string, unknown>)
                : {},
            pinned: Boolean(row['pinned']),
            updated_at: typeof row['updated_at'] === 'string' ? row['updated_at'] : null
          };
        });
    }
    return normalized;
  }

  private normalizeWatchlist(value: unknown): UserPreferenceResponse['watchlist'] {
    const normalized: UserPreferenceResponse['watchlist'] = {
      indicators: [],
      registries: [],
      reports: []
    };
    if (!value || typeof value !== 'object') {
      return normalized;
    }
    for (const namespace of WATCHLIST_NAMESPACES) {
      const rows = (value as Record<string, unknown>)[namespace];
      if (!Array.isArray(rows)) {
        continue;
      }
      normalized[namespace] = Array.from(
        new Set(
          rows
            .map((entry) => String(entry ?? '').trim())
            .filter((entry) => entry.length > 0)
        )
      );
    }
    return normalized;
  }

  private applyLocalPartial(payload: Partial<UserPreferenceResponse>): UserPreferenceResponse {
    const current = this.snapshot;
    const next: UserPreferenceResponse = {
      ...current,
      ...payload,
      default_geography: payload.default_geography
        ? {
            type: payload.default_geography.type,
            code: payload.default_geography.code ?? null
          }
        : current.default_geography,
      saved_filters: payload.saved_filters ? this.normalizeSavedFilters(payload.saved_filters) : current.saved_filters,
      watchlist: payload.watchlist ? this.normalizeWatchlist(payload.watchlist) : current.watchlist,
      dashboard_layout: payload.dashboard_layout ?? current.dashboard_layout,
      updated_at: new Date().toISOString()
    };
    this.commit(next);
    return next;
  }

  private snapshotFromLocalFilterSave(
    namespace: SavedFilterNamespace,
    name: string,
    params: Record<string, unknown>,
    pinned: boolean
  ): UserPreferenceResponse {
    const savedFilters = this.normalizeSavedFilters(this.snapshot.saved_filters);
    const entry: SavedFilterEntry = {
      id: crypto.randomUUID(),
      name,
      params,
      pinned,
      updated_at: new Date().toISOString()
    };
    savedFilters[namespace] = [entry, ...savedFilters[namespace]];
    return {
      ...this.snapshot,
      saved_filters: savedFilters,
      updated_at: entry.updated_at
    };
  }

  private routeForNamespace(namespace: SavedFilterNamespace): string {
    if (namespace === 'downloads') {
      return '/downloads';
    }
    if (namespace === 'registries') {
      return '/registries/taxa';
    }
    return '/indicators';
  }

  private stringifyParams(params: Record<string, unknown>): Record<string, string> {
    const output: Record<string, string> = {};
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined) {
        continue;
      }
      output[key] = String(value);
    }
    return output;
  }

  private readLocalPreferences(): UserPreferenceResponse {
    if (typeof window === 'undefined') {
      return this.normalize(DEFAULT_PREFERENCES);
    }
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) {
      return this.normalize(DEFAULT_PREFERENCES);
    }
    try {
      const parsed = JSON.parse(raw) as Partial<UserPreferenceResponse>;
      return this.normalize(parsed);
    } catch {
      return this.normalize(DEFAULT_PREFERENCES);
    }
  }

  private persistLocal(preferences: UserPreferenceResponse): void {
    if (typeof window === 'undefined') {
      return;
    }
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(preferences));
  }

  private applyToDocument(preferences: UserPreferenceResponse): void {
    if (typeof document === 'undefined') {
      return;
    }
    document.documentElement.setAttribute('data-theme', preferences.theme_mode);
    document.documentElement.setAttribute('data-theme-pack', preferences.theme_id);
    document.documentElement.setAttribute('data-density', preferences.density);
  }
}

