# Migration 0017: Alignment Mappings

Applies migration:
- `src/nbms_app/migrations/0017_framework_frameworkindicator_frameworktarget_and_more.py`

## Changes

- Adds framework registries:
  - `Framework`
  - `FrameworkTarget`
  - `FrameworkIndicator`
- Adds alignment link tables:
  - `NationalTargetFrameworkTargetLink`
  - `IndicatorFrameworkIndicatorLink`

## Apply

```
python manage.py migrate
```

## Rollback

To rollback, run:

```
python manage.py migrate nbms_app 0016
```

This removes the new alignment tables and framework registry tables.
