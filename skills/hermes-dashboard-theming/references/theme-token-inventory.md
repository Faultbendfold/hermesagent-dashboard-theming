# Theme color tokens: how many exist and which ones actually take effect

Evidenced from three places in the shipped build (Hermes v2026.9.24):

- `web/src/themes/types.ts` — the data model (`ThemePalette`, `ThemeColorOverrides`,
  `ThemeComponentStyles`, `ThemeSeriesColors`)
- `hermes_cli/web_server_dashboard.py` — `_THEME_OVERRIDE_KEYS`, `_THEME_COMPONENT_BUCKETS`,
  `_THEME_NAMED_ASSET_KEYS`, `_THEME_CUSTOM_CSS_MAX`, `_normalise_theme_definition()`
- `hermes_cli/web_dist/assets/*.js|*.css` — what the shipped build actually reads

## Structured color fields: 29

| Field | Count | Content |
|---|---|---|
| `palette` | 3 | `background`, `midground`, `foreground` (each `hex` + `alpha`) |
| `colorOverrides` | 19 | see below |
| `seriesColors` | 2 | `inputTokenAccent`, `outputTokenAccent` (charts on Analytics/Models) |
| `terminalBackground`, `terminalForeground` | 2 | xterm |
| `swatchColors` | 3 | only the preview swatches in the picker |

The 19 permitted `colorOverrides` keys (only these; everything else the server silently discards):
`card`, `cardForeground`, `popover`, `popoverForeground`, `primary`, `primaryForeground`,
`secondary`, `secondaryForeground`, `muted`, `mutedForeground`, `accent`, `accentForeground`,
`destructive`, `destructiveForeground`, `success`, `warning`, `border`, `input`, `ring`.

`palette.warmGlow` and `palette.noiseOpacity` are still accepted (compatibility with old
themes). Whether the respective build still reads them should be checked in the bundle beforehand
rather than assumed:
`grep -rl "noise\|warmGlow" hermes_cli/web_dist/assets/`.

## What shapes the visible picture

Eight values decide almost everything: `background`, `midground`, `card`, `primary`, `border`,
`muted`/`accent`, `ring`. The interface derives the rest from the three `palette` levels when
they are not overridden. A theme can stay small; a theme **without** `background` makes
the first frame uncontrolled.

## componentStyles: 9 buckets allowed, 4 read

The server accepts `card`, `header`, `footer`, `sidebar`, `tab`, `progress`, `badge`,
`backdrop`, `page` and passes the values through raw as `--component-<bucket>-<kebab-prop>`. Of
these, the shipped build consumes only:

| Bucket | Read properties |
|---|---|
| `sidebar` | `background`, `border-image`, `clip-path` |
| `header` | `background`, `border-image`, `clip-path` |
| `card` | `background`, `box-shadow`, `border-image`, `clip-path` |
| `tab` | `clip-path` (only — no color) |

`badge`, `page`, `progress`, `backdrop` and `footer` are **dead configuration**: the server accepts
them, no place in the build reads them. Colors set there fake a change that does
not happen — check before setting, not after the effect fails to appear.

Probe (always against the running build, not against the docs):

```bash
cd <install>/hermes_cli/web_dist && \
  grep -oh -- "--component-[a-z]*-[a-z-]*" assets/*.css assets/*.js | sort | uniq -c | sort -rn
```

The double hyphen before the pattern is mandatory: `rg`/`grep` otherwise read a pattern that
starts with `--` as an option ("unrecognized flag") and return zero matches even though matches exist.
Anyone using the search tool instead of the shell should use a pattern without leading hyphens, e.g.
`component-sidebar`.

The consumption site in the source (counter-check without the bundle): `web/src/App.tsx` and
`web/src/pages/ChatPage.tsx` read the variables via `var(--component-…, <fallback>)`. The right
panel of the chat page hangs off the same `--component-sidebar-background`.

## customCSS

Raw CSS in an injected `<style>` tag, limit **32 KiB** (`_THEME_CUSTOM_CSS_MAX`), deliberately
not sanitized — user YAML has the same trust level as `config.yaml`. Here colors
per selector are unlimited: the only lever for everything that has no token (speech bubbles,
code blocks, table rows, scrollbars, `::selection`).
