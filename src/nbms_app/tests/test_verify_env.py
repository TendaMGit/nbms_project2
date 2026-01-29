import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.verify_env import extract_required_vars


def test_extract_required_vars_from_compose():
    compose_text = (
        "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}\n"
        "NBMS_DB_PASSWORD: ${NBMS_DB_PASSWORD:?NBMS_DB_PASSWORD is required}\n"
        "MINIO_ROOT_USER: ${S3_ACCESS_KEY:?S3_ACCESS_KEY is required}\n"
        "MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:?S3_SECRET_KEY is required}\n"
        "GEOSERVER_ADMIN_PASSWORD: ${GEOSERVER_PASSWORD:?GEOSERVER_PASSWORD is required}\n"
    )

    required = extract_required_vars(compose_text)
    assert set(required) == {
        "POSTGRES_PASSWORD",
        "NBMS_DB_PASSWORD",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "GEOSERVER_PASSWORD",
    }
