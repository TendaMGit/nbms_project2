from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.cache import cache

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures_seed.json"


class BirdieClient:
    def __init__(self):
        self.base_url = (getattr(settings, "BIRDIE_BASE_URL", "") or "").rstrip("/")
        self.token = getattr(settings, "BIRDIE_API_TOKEN", "") or ""
        self.timeout = int(getattr(settings, "BIRDIE_TIMEOUT_SECONDS", 20) or 20)
        self.use_fixture = bool(getattr(settings, "BIRDIE_USE_FIXTURE", True))

    def _cache_key(self, endpoint: str, params: dict[str, Any] | None):
        blob = json.dumps({"endpoint": endpoint, "params": params or {}}, sort_keys=True)
        return f"birdie:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"

    def _request_json(self, endpoint: str, params: dict[str, Any] | None = None):
        cache_key = self._cache_key(endpoint, params)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        if self.base_url and requests:
            headers = {"Accept": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            errors = []
            for _ in range(3):
                try:
                    response = requests.get(
                        f"{self.base_url}/{endpoint.lstrip('/')}",
                        params=params or {},
                        headers=headers,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    cache.set(cache_key, payload, timeout=900)
                    return payload
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))
            if not self.use_fixture:
                raise RuntimeError("; ".join(errors))

        fixture = self.fixture_payload()
        if endpoint in fixture:
            payload = fixture[endpoint]
            cache.set(cache_key, payload, timeout=900)
            return payload
        return []

    def fixture_payload(self):
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def fetch_species_list(self):
        return self._request_json("species")

    def fetch_site_list(self):
        return self._request_json("sites")

    def fetch_abundance_trends(self):
        return self._request_json("abundance_trends")

    def fetch_occupancy_predictions(self):
        return self._request_json("occupancy_predictions")

    def fetch_wcv_scores(self):
        return self._request_json("wcv_scores")
