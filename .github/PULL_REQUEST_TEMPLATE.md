## What this changes

<!-- One paragraph. Which theme, which tool, which pitfall. -->

## Checks

- [ ] `./tools/verify.sh` passes locally
- [ ] `docs/` regenerated (`python3 tools/build-gallery.py`) if a theme changed
- [ ] `docs/schema.md` regenerated (`python3 tools/gen-schema-doc.py`) if the schema mirror changed

## For a new or changed theme

Contrast table (paste the output of
`python3 tools/contrast-report.py --format markdown themes/<name>.yaml`):

<!-- table below -->

## Anything a reviewer should not trust

Screenshots? Measurements? Name what you looked at yourself and what you assumed.
