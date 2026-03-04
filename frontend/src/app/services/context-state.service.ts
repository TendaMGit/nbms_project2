import { Injectable } from '@angular/core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { Observable, distinctUntilChanged, map, startWith } from 'rxjs';

import {
  DEFAULT_NBMS_CONTEXT,
  type NbmsContextPatch,
  type NbmsContextQueryParams,
  type NbmsGeoType,
  type NbmsModeKey,
  type NbmsPublishedOnly
} from '../models/context.models';

type ContextBindConfig = {
  defaults?: Partial<NbmsContextQueryParams>;
  aliases?: Partial<Record<keyof NbmsContextQueryParams, string[]>>;
};

@Injectable({ providedIn: 'root' })
export class ContextStateService {
  constructor(private readonly router: Router) {}

  connect(route: ActivatedRoute, config: ContextBindConfig = {}): Observable<NbmsContextQueryParams> {
    return route.queryParamMap.pipe(
      startWith(route.snapshot.queryParamMap),
      map((params) => this.parseQueryParams(params, config.defaults ?? {}, config.aliases ?? {})),
      distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b))
    );
  }

  update(route: ActivatedRoute, patch: NbmsContextPatch, extras: Record<string, string | number | boolean | null> = {}): void {
    const current = this.parseQueryParams(route.snapshot.queryParamMap);
    const merged = { ...current, ...patch };
    const queryParams = {
      ...this.serialize(merged),
      ...extras
    };
    void this.router.navigate([], {
      relativeTo: route,
      queryParams,
      queryParamsHandling: '',
      replaceUrl: true
    });
  }

  serialize(state: NbmsContextQueryParams): Record<string, string | null> {
    return {
      tab: state.tab || null,
      mode: state.mode || null,
      report_cycle: state.report_cycle || null,
      release: state.release || null,
      method: state.method || null,
      geo_type: state.geo_type || null,
      geo_code: state.geo_code || null,
      start_year: state.start_year ? String(state.start_year) : null,
      end_year: state.end_year ? String(state.end_year) : null,
      agg: state.agg || null,
      metric: state.metric || null,
      published_only: String(state.published_only),
      q: state.q || null,
      sort: state.sort || null,
      view: state.view || null,
      compare: state.compare || null,
      left: state.left || null,
      right: state.right || null
    };
  }

  parseQueryParams(
    params: ParamMap,
    defaults: Partial<NbmsContextQueryParams> = {},
    aliases: Partial<Record<keyof NbmsContextQueryParams, string[]>> = {}
  ): NbmsContextQueryParams {
    const read = <K extends keyof NbmsContextQueryParams>(key: K): string | null => {
      const direct = params.get(key);
      if (direct !== null) {
        return direct;
      }
      for (const alias of aliases[key] ?? []) {
        const value = params.get(alias);
        if (value !== null) {
          return value;
        }
      }
      return null;
    };

    const state: NbmsContextQueryParams = {
      ...DEFAULT_NBMS_CONTEXT,
      ...defaults,
      tab: read('tab') ?? defaults.tab ?? DEFAULT_NBMS_CONTEXT.tab,
      mode: toMode(read('mode') ?? defaults.mode ?? DEFAULT_NBMS_CONTEXT.mode),
      report_cycle: read('report_cycle') ?? defaults.report_cycle ?? DEFAULT_NBMS_CONTEXT.report_cycle,
      release: read('release') ?? defaults.release ?? DEFAULT_NBMS_CONTEXT.release,
      method: read('method') ?? defaults.method ?? DEFAULT_NBMS_CONTEXT.method,
      geo_type: toGeoType(read('geo_type') ?? defaults.geo_type ?? DEFAULT_NBMS_CONTEXT.geo_type),
      geo_code: read('geo_code') ?? defaults.geo_code ?? DEFAULT_NBMS_CONTEXT.geo_code,
      start_year: toNullableNumber(read('start_year') ?? defaults.start_year ?? DEFAULT_NBMS_CONTEXT.start_year),
      end_year: toNullableNumber(read('end_year') ?? defaults.end_year ?? DEFAULT_NBMS_CONTEXT.end_year),
      agg: read('agg') ?? defaults.agg ?? DEFAULT_NBMS_CONTEXT.agg,
      metric: read('metric') ?? defaults.metric ?? DEFAULT_NBMS_CONTEXT.metric,
      published_only: toPublishedOnly(
        read('published_only') ?? defaults.published_only ?? DEFAULT_NBMS_CONTEXT.published_only
      ),
      q: read('q') ?? defaults.q ?? DEFAULT_NBMS_CONTEXT.q,
      sort: read('sort') ?? defaults.sort ?? DEFAULT_NBMS_CONTEXT.sort,
      view: read('view') ?? defaults.view ?? DEFAULT_NBMS_CONTEXT.view,
      compare: read('compare') ?? defaults.compare ?? DEFAULT_NBMS_CONTEXT.compare,
      left: read('left') ?? defaults.left ?? DEFAULT_NBMS_CONTEXT.left,
      right: read('right') ?? defaults.right ?? DEFAULT_NBMS_CONTEXT.right
    };

    if (state.start_year && state.end_year && state.start_year > state.end_year) {
      [state.start_year, state.end_year] = [state.end_year, state.start_year];
    }
    return state;
  }
}

function toMode(value: unknown): NbmsModeKey {
  return value === 'cards' || value === 'map' ? value : 'table';
}

function toGeoType(value: unknown): NbmsGeoType {
  if (
    value === 'province' ||
    value === 'biome' ||
    value === 'ecoregion' ||
    value === 'municipality' ||
    value === 'custom'
  ) {
    return value;
  }
  return 'national';
}

function toNullableNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function toPublishedOnly(value: unknown): NbmsPublishedOnly {
  return ['0', 'false', 'no', 'off'].includes(String(value ?? '').toLowerCase()) ? 0 : 1;
}
