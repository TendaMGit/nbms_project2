import json
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError

from nbms_app.services.export_contracts import (
    validate_ort_indicator_tabular_rows,
    validate_ort_nr7_v2_payload_shape,
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_validate_ort_nr7_v2_payload_shape_accepts_minimal_fixture():
    payload = _load_json("src/nbms_app/tests/golden/ort_nr7_v2_minimal.json")
    assert validate_ort_nr7_v2_payload_shape(payload) == payload


def test_validate_ort_nr7_v2_payload_shape_rejects_missing_sections():
    payload = _load_json("src/nbms_app/tests/golden/ort_nr7_v2_minimal.json")
    payload.pop("sections", None)
    with pytest.raises(ValidationError):
        validate_ort_nr7_v2_payload_shape(payload)


def test_validate_ort_indicator_tabular_rows_accepts_fixture():
    rows = _load_json("src/nbms_app/tests/fixtures/exports/ort_indicator_tabular_submission_minimal.json")
    assert validate_ort_indicator_tabular_rows(rows) == rows


def test_validate_ort_indicator_tabular_rows_rejects_missing_indicator_code():
    rows = _load_json("src/nbms_app/tests/fixtures/exports/ort_indicator_tabular_submission_minimal.json")
    rows[0]["indicator_code"] = ""
    with pytest.raises(ValidationError):
        validate_ort_indicator_tabular_rows(rows)

