# Repo Sync Note

Date: 2026-02-25  
Branch: `chore/align-blueprint-2026Q1`

## Findings

- `origin` remote is `https://github.com/TendaMGit/nbms_project2`.
- Before sync, this branch was local-only (not present in `origin` heads).
- `origin/main..HEAD` shows a large delta that includes Angular SPA and API expansion, indicating `origin/main` is behind this working branch.
- Local `main` is also behind `origin/main` by 2 commits on this machine (`main [origin/main: behind 2]`), but this does not affect the branch push/PR.

## Actions Taken

1. Fetched remotes and verified branch status:
   - `git fetch --all`
   - `git branch -vv`
   - `git diff --stat origin/main..HEAD`
2. Pushed branch to origin:
   - `git push -u origin chore/align-blueprint-2026Q1`
3. Opened PR against `main`:
   - PR: `https://github.com/TendaMGit/nbms_project2/pull/30`
   - Title: `Angular UI foundation + user preferences (Phase 1 MVP)`
4. Confirmed branch is now visible on origin:
   - `git ls-remote --heads origin | rg "chore/align-blueprint-2026Q1"`
5. Updated top-level `README.md` to reflect current architecture reality:
   - Angular frontend + Django backend
   - session+CSRF auth model
   - API locations and local run commands

## Compliance Confirmation

- Internal source documents are ignored and not tracked:
  - `NBMS_Draft Design & Scope.docx`
  - `Instructions v2.docx`

## Status

Remote alignment prerequisites are now satisfied (branch pushed + PR open), so feature work can proceed safely from this branch.
