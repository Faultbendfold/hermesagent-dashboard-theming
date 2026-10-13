# Changelog

## 2026-10-13 -- tooling

Everything below is additive: the themes and their look are unchanged except for the one
contrast fix noted at the end.

### Added

- `skills/hermes-dashboard-theming/scripts/theme_lib.py` -- shared YAML-subset reader (no PyYAML),
  colour maths and a mirror of the schema the installed Hermes accepts.
- `skills/hermes-dashboard-theming/scripts/theme-check.py` -- lints a theme for everything that
  fails silently: unknown `colorOverrides` keys, style buckets nothing reads, `seriesColors` and
  other fields that never reach the surface, `customCSS` over the 32 KiB cap, series variables
  without `!important`, unbalanced braces, stray `</style>`, and the contrast of every pair.
  `--live --hermes <dir>` reports drift against the installed Hermes, exit code 1 gates CI.
- `skills/hermes-dashboard-theming/scripts/make-dark-twin.py` -- derives a dark counterpart from a
  light theme and prints the measured contrast table.
- `install.sh` -- copy and activate the themes; `--list`, `--status`, `--dry-run`, `--force`
  (which keeps a timestamped `.bak`), never deletes anything.
- `tools/new-theme.py` -- writes a commented skeleton that already passes `--strict`.
- `tools/gen-schema-doc.py` and `docs/schema.md` -- the schema reference, generated from the mirror
  so it cannot drift.
- `tools/contrast-report.py` -- the full contrast matrix per theme, as text, Markdown or JSON.
- `tools/preview.py` -- a theme as a standalone offline HTML page, without installing Hermes.
- `tools/build-gallery.py`, `docs/index.html`, `docs/color-board.html` -- a browsable gallery with
  swatches, a mock of each theme and its WCAG summary.
- `docs/preview-<name>.html` -- one full-size preview page per theme, published by the gallery
  builder with the same renderer `tools/preview.py` uses, and linked from each gallery card.
- `tools/verify.sh` -- every check in one command; `.github/workflows/validate.yml` runs it.
- `tests/` -- unit tests for the maths and the reader, black-box tests for the tools.
- `templates/minimal-light.yaml`, `templates/minimal-dark.yaml`.
- `CONTRIBUTING.md`, issue and pull request templates.

### Changed

- `light-clean`: `mutedForeground` `#64748B` -> `#5F6C7F`. `#64748B` on `muted` `#F1F3F6` measured
  4.28:1, below the 4.5:1 target for body text; the new value measures 4.80:1 and leaves the canvas
  and card ratios at 5.06:1 and 5.33:1.

### Fixed

- `theme_lib.fit()` returned the opposite end of the scale when the colour already met the target,
  which turned an already-readable green into white in light themes. It now returns the colour
  unchanged when the target is met.
- `theme-check.py` no longer warns about `seriesColors` when `customCSS` already carries
  `--series-input-token`/`--series-output-token` with `!important`; it says so instead.

### Known

- The dashboard screenshots in `screenshots/` were captured before the two light-theme tone changes
  above. The difference is a slightly darker muted text and focus ring; the composited pairs have not
  been re-shot yet.
