# Palette -> Dashboard Theme: Roles, Target Values, Pitfalls

How a complete Hermes theme is derived from a color-hex palette (typically 5 colors).
The basics of the theme mechanism are in SKILL.md; this sheet is the computation recipe.
Generate with: `scripts/gen_dashboard_themes.py`.

## Role Mapping

| Role | Source | Derivation | Limit |
|---|---|---|---|
| Canvas `palette.background` | lightest palette tone | lighten toward white until ~0.93 relative luminance; if already >= 0.90, take unchanged | do not take the darkest tone just because it is the darkest |
| Cards `card`, `popover` | canvas | white when the canvas is tinted (luminance < 0.965); otherwise canvas 5% toward text | cards need separation from the canvas, otherwise they disappear |
| Text `palette.midground`, `*Foreground` | darkest palette tone | darken toward black until contrast >= 7 against the canvas | check against the canvas, not against white |
| Buttons `primary`, `ring` | most saturated palette tone | first tone with contrast >= 3.2 against white or black; label then white or black respectively | if contrast falls below 3.0, fall back to the text tone |
| Hover / `muted` / `secondary` / `accent` | canvas + text | 6-7% text in the canvas | keep neutral when a white canvas is wanted |
| `mutedForeground` | text + canvas | 38-40% canvas in the text | |
| Border `border`, `input` | canvas + text | 15-17% text | |
| Text selection `::selection` | `primary` | `rgba(primary, 0.25)` | |
| Scrollbar | border / canvas | `scrollbar-color: <border> <background>` | |

Dark version (name suffix `-dark`, only for palettes without a usable light tone):
canvas = darkest tone, cards = 7% of the lightest tone mixed in, text = lightest tone
lightened until contrast >= 7, hover 10%, border 24%.

## Target Values

- Text on canvas: contrast **>= 7** — WCAG-AA is 4.5; the buffer prevents individual
  derived tones from slipping through.
- Button label: **>= 3.2**, below 3.0 fall back to the text tone.
- Canvas luminance: **~0.93** — light enough as a surface, dark enough that the hue is still
  recognizable.
- From a canvas luminance of 0.965 (practically white) cards must become somewhat darker than
  the canvas, otherwise no edge is visible.

## Verification Table

The script outputs name, mode, canvas, text, contrast and button color per variant and
sorts by contrast. This table belongs in the reported result: it shows at a glance which variants
are readable and which palette had to be darkened heavily (a high darkening fraction means: the
palette had no usable dark tone and is a candidate for discarding).

## Querying color-hex.com

Fetch palette pages with `web_extract` (`https://www.color-hex.com/color-palette/<id>`), not with
`curl` — the page responds to curl with a Cloudflare 403. The color values sit between two
markers in the extracted text:

```python
seg = content.split("Colors in Palette", 1)[-1].split("PNG Image", 1)[0]
hexes = list(dict.fromkeys(re.findall(r'#([0-9a-fA-F]{6})', seg)))[:6]
```

The overview `color-palettes/popular.php` provides only palette names and IDs, no color values —
the values come from the respective detail page. Five colors are sufficient for a theme:
two of them are actually used (darkest and most saturated tone), the light surfaces are
computed from the hue.

## Pitfalls

- **Iterative mixing in integer percentage steps gets stuck at rounding.** The
  increment eventually becomes 0, the loop runs into its limit and permanently yields a too
  pale value (instead of a warm `#FFF8E3`, e.g. `#FFF3F3`, because G and B
  snap to the same integer value). Solve the mix factor by bisection against the luminance or
  contrast target and round once.
- **Mid-tone palettes need a computed canvas.** Their darkest tones as surfaces
  yield contrasts of 1.5-3.3 and are unreadable; their own light tones as surfaces appear
  superficially the same — which is why lightening is done instead of forcing a palette-tone
  mapping.
- **The contrast target depends on the canvas.** Continuing to compute against
  `#FFFFFF` after switching to tinted surfaces is the mistake that marks variants as readable
  that are not.
- **Observe the write gate when batch-generating:** an existing theme file requires a
  complete `read_file` beforehand, otherwise `write_file` fails with `ok=None`. Per
  `execute_code` call, process only as many files as fit the call limit (each file = 1 read +
  1 write).
