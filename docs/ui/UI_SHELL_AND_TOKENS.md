# UI Shell And Tokens

## Scope

This note describes where the current NBMS frontend shell and design tokens are implemented, and how to extend them safely.

## Files

- `frontend/src/app/ui/nbms-app-shell.component.ts`
- `frontend/src/app/ui/nbms-app-shell.types.ts`
- `frontend/src/app/services/user-preferences.service.ts`
- `frontend/src/styles/_tokens.scss`
- `frontend/src/styles/_theme.scss`
- `frontend/src/styles.scss`

## Shell Responsibilities

- Global layout: topbar + sidebar + content frame.
- Role-aware navigation groups and quick actions.
- Global search trigger and command palette entry point.
- Theme mode toggle and environment badge rendering.
- Help drawer host and shared notification/toast anchor points.

## Token Structure

`_tokens.scss` contains primitive and semantic tokens:

- Palette tokens (primary/secondary/accent/semantic states)
- Neutral scale
- Spacing scale (8pt rhythm)
- Radius/elevation
- Typography scale
- Focus ring variables

`_theme.scss` maps tokens into runtime theme classes:

- `:root` and light defaults
- dark-mode overrides
- component surface/text/border variables

Runtime preference attributes are set by `UserPreferencesService`:

- `data-theme` (`light|dark`)
- `data-theme-pack` (`fynbos|gbif_clean|high_contrast|dark_pro`)
- `data-density` (`comfortable|compact`)

## Adding A New Theme Pack

1. Add or reuse palette/semantic values in `_tokens.scss`.
2. Add theme-pack selectors in `_tokens.scss` (for example `:root[data-theme-pack='fynbos']`).
3. Ensure contrast remains WCAG AA for body text and interactive controls.
4. Ensure the root `data-theme-pack` attribute is set from preferences so all pages inherit.
5. Validate in desktop + mobile breakpoints.

## Rules

- Do not hardcode hex colors in feature components when a token exists.
- Keep all major spacing/radius decisions token-driven.
- Avoid introducing additional heavy UI libraries; keep Angular Material/CDK as the base.
