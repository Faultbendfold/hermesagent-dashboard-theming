# Contributing

Themes, fixes and new pitfalls are welcome — this repository is meant to be
copied from. Three things to know before you open a pull request.

## Add or change a theme

1. Put the file in `themes/<name>.yaml`. The `name:` inside must match the file
   name (lower-case slug) — the dashboard keys themes by it.
2. Run `./tools/verify.sh`. It lints every theme with warnings treated as errors,
   so a silently dropped key or a contrast miss fails before a reviewer sees it.
3. Regenerate the gallery: `python3 tools/build-gallery.py`. CI fails if `docs/`
   is stale.
4. For a light/dark pair, keep both files in the same family and put the
   measured contrast table in the pull request.

## Add a pitfall to the skill

The skill under `skills/hermes-dashboard-theming/` is written for an agent, so it
earns its length: every claim needs the probe that proves it. Add the probe, not
just the rule.

## What the checks are

`tools/verify.sh` runs `py_compile` over every script, `sh -n` over the shell
scripts, `theme-check.py --strict` over `themes/*.yaml`, the two `--check` modes
that keep `docs/` and `docs/schema.md` in step with their generators, and the
`unittest` suites in `tests/`. Nothing needs installing: standard library only.

## The tools, in one line each

| Tool | Use |
|---|---|
| `tools/new-theme.py` | scaffold a theme that already passes the linter |
| `tools/preview.py` | see a theme as a standalone offline page |
| `tools/color-board.html` | find one colour, with its derived mixes and WCAG contrast |
| `skills/.../scripts/theme-check.py` | find what the dashboard would silently drop |
| `tools/contrast-report.py` | the full contrast matrix, for a pull request |
| `skills/.../scripts/make-dark-twin.py` | derive the dark half of a light theme |
| `docs/schema.md` | what the schema accepts, generated from the mirror |
| `install.sh` | copy and activate the themes |

## Conventions

- `#rrggbb` for colours, no short forms.
- Keep `customCSS` under the 32 KiB cap the server enforces.
- Screenshots are composited from two captures of the same page by
  `scripts/pair_screenshots.py` — light left, dark right.
- This repository was built with an AI agent. Say so if that is how you produced
  your change, and state what you verified by hand.
