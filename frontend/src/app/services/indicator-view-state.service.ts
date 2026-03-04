import { Injectable } from '@angular/core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { Observable, distinctUntilChanged, map, startWith } from 'rxjs';

import { DEFAULT_NBMS_CONTEXT, type NbmsContextQueryParams } from '../models/context.models';
import {
  type IndicatorTopN,
  type IndicatorViewRoutePatch,
  type IndicatorViewRouteState,
} from '../models/indicator-visual.models';
import { ContextStateService } from './context-state.service';

type IndicatorViewBindConfig = {
  defaults?: Partial<IndicatorViewRouteState>;
};

@Injectable({ providedIn: 'root' })
export class IndicatorViewStateService {
  constructor(
    private readonly router: Router,
    private readonly contextState: ContextStateService,
  ) {}

  connect(route: ActivatedRoute, config: IndicatorViewBindConfig = {}): Observable<IndicatorViewRouteState> {
    return route.queryParamMap.pipe(
      startWith(route.snapshot.queryParamMap),
      map((params) => this.parseQueryParams(params, config.defaults ?? {})),
      distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
    );
  }

  parseQueryParams(params: ParamMap, defaults: Partial<IndicatorViewRouteState> = {}): IndicatorViewRouteState {
    const contextDefaults = pickContextDefaults(defaults);
    const context = this.contextState.parseQueryParams(params, contextDefaults);
    return {
      ...context,
      dim: params.get('dim') ?? defaults.dim ?? '',
      dim_value: params.get('dim_value') ?? defaults.dim_value ?? '',
      tax_level: params.get('tax_level') ?? defaults.tax_level ?? '',
      tax_code: params.get('tax_code') ?? defaults.tax_code ?? '',
      top_n: toTopN(params.get('top_n') ?? defaults.top_n ?? 20),
    };
  }

  serialize(state: IndicatorViewRouteState): Record<string, string | null> {
    return {
      ...this.contextState.serialize(state),
      dim: state.dim || null,
      dim_value: state.dim_value || null,
      tax_level: state.tax_level || null,
      tax_code: state.tax_code || null,
      top_n: state.top_n ? String(state.top_n) : null,
    };
  }

  update(route: ActivatedRoute, patch: IndicatorViewRoutePatch): void {
    const current = this.parseQueryParams(route.snapshot.queryParamMap);
    const merged: IndicatorViewRouteState = {
      ...current,
      ...patch,
      top_n: toTopN(patch.top_n ?? current.top_n),
    };
    void this.router.navigate([], {
      relativeTo: route,
      queryParams: this.serialize(merged),
      queryParamsHandling: '',
      replaceUrl: true,
    });
  }

  defaultState(overrides: Partial<IndicatorViewRouteState> = {}): IndicatorViewRouteState {
    return {
      ...DEFAULT_NBMS_CONTEXT,
      dim: '',
      dim_value: '',
      tax_level: '',
      tax_code: '',
      top_n: 20,
      ...overrides,
    };
  }
}

function pickContextDefaults(defaults: Partial<IndicatorViewRouteState>): Partial<NbmsContextQueryParams> {
  return {
    tab: defaults.tab ?? DEFAULT_NBMS_CONTEXT.tab,
    mode: defaults.mode ?? DEFAULT_NBMS_CONTEXT.mode,
    report_cycle: defaults.report_cycle ?? DEFAULT_NBMS_CONTEXT.report_cycle,
    release: defaults.release ?? DEFAULT_NBMS_CONTEXT.release,
    method: defaults.method ?? DEFAULT_NBMS_CONTEXT.method,
    geo_type: defaults.geo_type ?? DEFAULT_NBMS_CONTEXT.geo_type,
    geo_code: defaults.geo_code ?? DEFAULT_NBMS_CONTEXT.geo_code,
    start_year: defaults.start_year ?? DEFAULT_NBMS_CONTEXT.start_year,
    end_year: defaults.end_year ?? DEFAULT_NBMS_CONTEXT.end_year,
    agg: defaults.agg ?? DEFAULT_NBMS_CONTEXT.agg,
    metric: defaults.metric ?? DEFAULT_NBMS_CONTEXT.metric,
    published_only: defaults.published_only ?? DEFAULT_NBMS_CONTEXT.published_only,
    q: defaults.q ?? DEFAULT_NBMS_CONTEXT.q,
    sort: defaults.sort ?? DEFAULT_NBMS_CONTEXT.sort,
    view: defaults.view ?? DEFAULT_NBMS_CONTEXT.view,
    compare: defaults.compare ?? DEFAULT_NBMS_CONTEXT.compare,
    left: defaults.left ?? DEFAULT_NBMS_CONTEXT.left,
    right: defaults.right ?? DEFAULT_NBMS_CONTEXT.right,
  };
}

function toTopN(value: unknown): IndicatorTopN {
  const parsed = Number(value);
  if (parsed === 50 || parsed === 100) {
    return parsed;
  }
  return 20;
}
