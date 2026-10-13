# A theme in ten minutes

This walks through building a working theme from nothing, using the tools in this repository.
Nothing here needs an install until the last step.

## 1. Write a skeleton that is already correct

```bash
python3 tools/new-theme.py aurora --accent "#7C5CFF"
```

That writes `themes/aurora.yaml`: every supported key, commented, with colours derived so that the
contrast targets are met from the start. Add `--mode dark` for the dark half. The scaffold is a
starting point, not a design -- it is deliberately neutral.

## 2. Look at it without installing anything

```bash
python3 tools/preview.py themes/aurora.yaml --open
```

A standalone HTML page opens: sidebar, cards, buttons, status chips, chart bars -- all painted from
your tokens. Nothing is installed, no server runs. This is the loop you iterate in.

For a single colour question (a new accent, a hover tone, a border), open `tools/color-board.html`
instead: type a hex value and it prints the swatch, the derived mixes, the WCAG contrast and a
ready-to-paste snippet.

## 3. Check it, then trust it

```bash
python3 skills/hermes-dashboard-theming/scripts/theme-check.py themes/aurora.yaml
python3 tools/contrast-report.py themes/aurora.yaml
```

`theme-check` is the one that matters: a theme fails *silently*, and this is where the silence is
broken. It reports keys the server would drop, buckets nothing reads, `customCSS` over the size cap,
and any pair whose contrast is below target. Exit code 1 means something is wrong.

If you have Hermes installed, add the live check -- it runs the theme through that version's own
normaliser and tells you whether the schema moved:

```bash
python3 skills/hermes-dashboard-theming/scripts/theme-check.py --live --hermes /path/to/hermes themes/aurora.yaml
```

## 4. Install it

```bash
./install.sh --activate aurora          # or: ./install.sh --dry-run first
```

Then reload the dashboard page completely -- the theme list is read once per page load. If it does
not show up, `./install.sh --status` says which directory is being read and which theme is active.

Revert any time with `hermes config set dashboard.theme default`.

## 5. Add the dark half

```bash
python3 skills/hermes-dashboard-theming/scripts/make-dark-twin.py themes/aurora.yaml
```

That derives the dark counterpart by the documented rules and prints the contrast table. It carries
your `customCSS` over unchanged and lists the hardcoded colours inside it -- those are the ones you
have to decide about by hand, because no rule can tell whether a hex value means "the light surface"
or "a deliberate accent".

## Three things that swallow a theme silently

1. **`seriesColors` never arrives.** The chart series colours must be set in `customCSS` as
   `--series-input-token` / `--series-output-token` **with `!important`** -- the client writes them
   inline on `<html>`.
2. **Five `componentStyles` buckets are dead.** `badge`, `page`, `progress`, `backdrop` and `footer`
   are accepted, emitted as variables, and read by nothing. Colours there fake a change.
3. **`fontDisplay` does nothing.** Headings need a `customCSS` rule.

Full detail, including which of the 19 `colorOverrides` keys exist and what each surface reads:
[`schema.md`](schema.md). The reasoning and the probes behind every claim:
`skills/hermes-dashboard-theming/` -- in particular `references/theme-token-inventory.md`,
`references/contrast-checking.md` and `references/palette-to-theme-mapping.md`.

## Where the pieces are

| I want to... | Use |
|---|---|
| start a theme | `tools/new-theme.py` |
| see a theme | `tools/preview.py`, `tools/color-board.html` |
| find one colour | `tools/color-board.html` |
| prove a theme is sound | `skills/.../scripts/theme-check.py`, `tools/contrast-report.py` |
| build the dark half | `skills/.../scripts/make-dark-twin.py` |
| know what the schema accepts | `docs/schema.md` |
| install it | `install.sh` |
| check everything before a PR | `./tools/verify.sh` |
