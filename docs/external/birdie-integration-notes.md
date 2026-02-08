# BIRDIE Integration Notes

## Source

- BIRDIE project overview and repository
- https://birdiemodel.org/
- https://github.com/birdiemonitoring/birdie

## Key Requirements Extracted

- Keep external model outputs integrated first (do not re-implement all modeling logic immediately).
- Preserve provenance and versioning for downstream indicator/report trust.
- Enable map- and site-level interpretation of model outputs.

## NBMS Mapping

- Existing BIRDIE connector remains API-first with bronze/silver/gold persistence.
- Spatial features from BIRDIE occupancy outputs are now served via NBMS spatial registry and tile APIs.
- Programme operations and map workspace expose provenance-ready BIRDIE layers for report use.
