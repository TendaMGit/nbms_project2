# Clean slate reset

Use this when you need to drop and recreate the main and test databases.

```
CONFIRM_DROP=YES scripts/reset_db.sh
```

The script will:
- drop and recreate `NBMS_DB_NAME` and `NBMS_TEST_DB_NAME`
- re-enable PostGIS extensions
- run migrations with `manage.py migrate --noinput`
