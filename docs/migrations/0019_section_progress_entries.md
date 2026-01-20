# Migration 0019: Section III/IV progress entries

## Summary

Adds structured progress entry models for NR7:

- `SectionIIINationalTargetProgress`
- `SectionIVFrameworkTargetProgress`

Each model includes narrative fields plus M2M links to indicator data series,
binary indicator responses, evidence, and dataset releases.

## Why

Section III/IV require per-target/per-goal progress records that can be
queried, governed, and exported without relying solely on narrative blobs.

## Rollback strategy

This migration is additive. To roll back:

1) Create a new migration that removes the two progress models and their M2M
   tables.
2) Apply the rollback migration and verify no downstream tables depend on
   these models.
