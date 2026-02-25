from __future__ import annotations

from threading import Lock

from django.db import connections
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed by Django.",
    labelnames=("method", "route", "status"),
    registry=REGISTRY,
)

HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "http_request_latency_seconds",
    "Request latency in seconds by method and route.",
    labelnames=("method", "route"),
    registry=REGISTRY,
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

EXPORT_REQUESTS_TOTAL = Counter(
    "export_requests_total",
    "Total export/download generation requests.",
    labelnames=("type",),
    registry=REGISTRY,
)

DOWNLOADS_CREATED_TOTAL = Counter(
    "downloads_created_total",
    "Total download records created.",
    labelnames=("record_type",),
    registry=REGISTRY,
)

BACKGROUND_JOBS_TOTAL = Counter(
    "background_jobs_total",
    "Background job events by type and status.",
    labelnames=("job_type", "status"),
    registry=REGISTRY,
)

TILE_REQUESTS_TOTAL = Counter(
    "tile_requests_total",
    "Total vector tile requests by layer.",
    labelnames=("layer",),
    registry=REGISTRY,
)

DB_POOL_CONNECTIONS = Gauge(
    "db_pool_connections",
    "Current database connection wrappers tracked by Django.",
    labelnames=("alias",),
    registry=REGISTRY,
)

_DYNAMIC_COUNTERS: dict[tuple[str, tuple[str, ...]], Counter] = {}
_LOCK = Lock()


def _sanitize_label_value(value: object, default: str = "unknown") -> str:
    text = str(value or "").strip()
    return text or default


def _dynamic_counter(name: str, label_keys: tuple[str, ...]) -> Counter:
    key = (name, label_keys)
    counter = _DYNAMIC_COUNTERS.get(key)
    if counter is not None:
        return counter
    with _LOCK:
        counter = _DYNAMIC_COUNTERS.get(key)
        if counter is None:
            counter = Counter(name, f"Dynamically registered counter: {name}", labelnames=label_keys, registry=REGISTRY)
            _DYNAMIC_COUNTERS[key] = counter
    return counter


def inc_counter(name: str, labels: dict[str, object] | None = None, value: int = 1) -> None:
    """
    Backward-compatible dynamic counter helper for existing call sites.
    """
    label_values = labels or {}
    label_keys = tuple(sorted(label_values.keys()))
    counter = _dynamic_counter(name=name, label_keys=label_keys)
    if label_keys:
        counter.labels(*[_sanitize_label_value(label_values[key]) for key in label_keys]).inc(value)
    else:
        counter.inc(value)


def observe_http_request(*, method: str, route: str, status_code: int, duration_seconds: float) -> None:
    method_value = _sanitize_label_value(method, default="UNKNOWN").upper()
    route_value = _sanitize_label_value(route, default="unresolved")
    status_value = str(int(status_code))
    HTTP_REQUESTS_TOTAL.labels(method=method_value, route=route_value, status=status_value).inc()
    HTTP_REQUEST_LATENCY_SECONDS.labels(method=method_value, route=route_value).observe(max(float(duration_seconds), 0.0))


def observe_export_request(export_type: str) -> None:
    EXPORT_REQUESTS_TOTAL.labels(type=_sanitize_label_value(export_type)).inc()


def observe_download_created(record_type: str) -> None:
    DOWNLOADS_CREATED_TOTAL.labels(record_type=_sanitize_label_value(record_type)).inc()


def observe_background_job(job_type: str, status: str) -> None:
    BACKGROUND_JOBS_TOTAL.labels(
        job_type=_sanitize_label_value(job_type),
        status=_sanitize_label_value(status),
    ).inc()


def observe_tile_request(layer_code: str) -> None:
    TILE_REQUESTS_TOTAL.labels(layer=_sanitize_label_value(layer_code)).inc()


def update_db_pool_metrics() -> None:
    aliases = sorted(connections)
    for alias in aliases:
        conn = connections[alias]
        active = 1 if conn.connection is not None else 0
        DB_POOL_CONNECTIONS.labels(alias=alias).set(active)


def render_prometheus() -> str:
    return generate_latest(REGISTRY).decode("utf-8")
