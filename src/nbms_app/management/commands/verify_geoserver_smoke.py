from __future__ import annotations

import base64
import os
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from nbms_app.models import SpatialLayer


def _auth_header(user: str, password: str):
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _request(url: str, headers: dict[str, str], timeout=30):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.getcode(), response.read(), response.headers.get("Content-Type", "")


class Command(BaseCommand):
    help = "Smoke-check GeoServer REST/WMS endpoints and published NBMS layer visibility."

    def add_arguments(self, parser):
        parser.add_argument("--layer-code", action="append", dest="layer_codes", default=[])

    def handle(self, *args, **options):
        geoserver_url = os.environ.get("GEOSERVER_URL", "http://localhost:8080/geoserver").rstrip("/")
        geoserver_user = os.environ.get("GEOSERVER_USER", "admin")
        geoserver_password = os.environ.get("GEOSERVER_PASSWORD", "")
        workspace = os.environ.get("GEOSERVER_WORKSPACE", "nbms")
        if not geoserver_password:
            self.stderr.write(self.style.ERROR("GEOSERVER_PASSWORD is required."))
            raise SystemExit(1)

        headers = _auth_header(geoserver_user, geoserver_password)

        try:
            code, _body, _content_type = _request(f"{geoserver_url}/rest/about/version.xml", headers)
        except urllib.error.URLError as exc:
            self.stderr.write(self.style.ERROR(f"GeoServer unavailable: {exc}"))
            raise SystemExit(1)
        if code != 200:
            self.stderr.write(self.style.ERROR(f"GeoServer REST probe returned HTTP {code}."))
            raise SystemExit(1)

        requested_codes = options.get("layer_codes") or []
        layers = SpatialLayer.objects.filter(is_active=True, publish_to_geoserver=True).order_by("layer_code")
        if requested_codes:
            layers = layers.filter(layer_code__in=requested_codes)
        layers = list(layers[:10])
        if not layers:
            self.stdout.write("No publish_to_geoserver layers found; GeoServer smoke completed with no layer checks.")
            return

        cap_url = f"{geoserver_url}/{workspace}/wms?service=WMS&request=GetCapabilities&version=1.1.1"
        code, cap_body, _content_type = _request(cap_url, headers)
        if code != 200:
            self.stderr.write(self.style.ERROR(f"WMS GetCapabilities returned HTTP {code}."))
            raise SystemExit(1)
        cap_text = cap_body.decode("utf-8", errors="ignore")

        expected_layer_names = []
        for layer in layers:
            expected_name = layer.geoserver_layer_name or f"nbms_gs_{layer.layer_code.lower()}"
            expected_layer_names.append(expected_name)
            if f"<Name>{workspace}:{expected_name}</Name>" not in cap_text and f"<Name>{expected_name}</Name>" not in cap_text:
                self.stderr.write(self.style.ERROR(f"Layer missing from capabilities: {workspace}:{expected_name}"))
                raise SystemExit(1)

        first_layer = expected_layer_names[0]
        query = urllib.parse.urlencode(
            {
                "service": "WMS",
                "version": "1.1.1",
                "request": "GetMap",
                "layers": f"{workspace}:{first_layer}",
                "styles": "",
                "bbox": "16,-35,33,-21",
                "width": "512",
                "height": "512",
                "srs": "EPSG:4326",
                "format": "image/png",
                "transparent": "true",
            }
        )
        map_url = f"{geoserver_url}/{workspace}/wms?{query}"
        code, _map_body, map_content_type = _request(map_url, headers)
        if code != 200:
            self.stderr.write(self.style.ERROR(f"WMS GetMap returned HTTP {code} for {workspace}:{first_layer}."))
            raise SystemExit(1)
        if "image/png" not in (map_content_type or "").lower():
            self.stderr.write(
                self.style.ERROR(f"WMS GetMap content type is not image/png: '{map_content_type}' for {workspace}:{first_layer}.")
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"GeoServer smoke succeeded. checked_layers={len(expected_layer_names)}, "
                f"map_layer={workspace}:{first_layer}."
            )
        )
