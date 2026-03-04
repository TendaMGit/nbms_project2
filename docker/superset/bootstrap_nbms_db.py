import json
import os

from superset.app import create_app
from superset.extensions import db


def build_uri() -> str:
    password = os.getenv("SUPERSET_NBMS_RO_PASSWORD", "").strip()
    if not password:
        raise RuntimeError("SUPERSET_NBMS_RO_PASSWORD must be set before bootstrapping the NBMS analytics database.")
    db_name = os.getenv("NBMS_DB_NAME", "nbms_project_db2").strip()
    db_host = os.getenv("NBMS_DB_HOST", "postgis").strip() or "postgis"
    db_port = os.getenv("NBMS_DB_PORT", "5432").strip() or "5432"
    return f"postgresql+psycopg2://superset_ro:{password}@{db_host}:{db_port}/{db_name}"


def main() -> None:
    app = create_app()
    with app.app_context():
        from superset.models.core import Database

        database_name = os.getenv("SUPERSET_NBMS_DATABASE_NAME", "NBMS Analytics").strip() or "NBMS Analytics"
        uri = build_uri()
        extra = json.dumps(
            {
                "engine_params": {},
                "metadata_params": {},
                "schemas_allowed_for_csv_upload": [],
                "schemas_allowed_for_file_upload": [],
            }
        )

        database = db.session.query(Database).filter_by(database_name=database_name).one_or_none()
        if database is None:
            database = Database(database_name=database_name)
            db.session.add(database)

        database.configuration_method = "sqlalchemy_form"
        database.set_sqlalchemy_uri(uri)
        database.expose_in_sqllab = True
        database.allow_run_async = True
        database.allow_ctas = False
        database.allow_cvas = False
        database.allow_dml = False
        database.allow_file_upload = False
        database.force_ctas_schema = ""
        database.extra = extra
        db.session.commit()
        print(f"Ensured Superset database '{database_name}' points at analytics schema in {os.getenv('NBMS_DB_NAME', 'nbms_project_db2')}.")


if __name__ == "__main__":
    main()
