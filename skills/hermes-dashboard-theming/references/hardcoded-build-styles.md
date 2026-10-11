# Hardcoded values in the bundle and how to override them

The theme sets CSS variables. But part of the interface does **not** read these variables at all —
the values sit as hex or as arbitrary utility classes directly in the shipped stylesheet.
This failure is invisible from the outside: the variables are set correctly, `_discover_user_themes()`
shows the right values, and the surface still does not change. What is hardcoded, how to find it,
and how to override it cleanly is described here.

## What is hardcoded (measured in the bundle)

| Spot | Utility in the bundle | Follows the theme? |
|---|---|---|
| Headings | classes `font-mondwest`, `font-expanded` | no |
| Tags/hub chips | class `font-compressed` | no |
| Focus borders of the buttons | `.focus-visible\:border-midground\/25:focus-visible { border-color: var(--midground) }` | yes, but as a class |
| Bezel inner edge | `.shadow-[inset_-1px_-1px_0_0_#00000080,inset_1px_1px_0_0_#ffffff80]` (+2 variants) | no |
| Success | `.text-success { color: #4ade80 }`, `.bg-success { background-color: #4ade80 }` | **no** |
| Warning | `.text-warning { color: #ffbd38 }`, `.bg-warning { background-color: #ffbd38 }` | **no** |
| Danger | `.text-destructive { color: #fb2c36 }`, `.bg-destructive { background-color: #fb2c36 }` | **no** |
| Info | does not exist (`grep -c 'text-info'` = 0) | — |

`colorOverrides.success`/`warning`/`destructive` are allowed keys and are set correctly — it is just
that the utility does not read the value. To change a semantic colour, it must be overridden at the
utility.

## How to find a hardcoded appearance

First search the bundle for the value or the appearance, then fetch the selector. Always with a double
hyphen before the pattern, otherwise the search tool reads it as an option and reports zero hits.

```bash
cd $HERMES_HOME/web_dist/assets
# search the value and show the selector for it
 grep -o '[^{}]\{0,150\}{[^{}]\{0,30\}color:#4ade80[^{}]\{0,30\}}' index-*.css
# which utilities and shades exist at all
 grep -o '\.\(bg\|text\|border\)-success[^{]\{0,12\}' index-*.css | sort -u
```

The first command produced `.text-success{color:#4ade80}` — the proof that the variable is bypassed.
Best additionally read back the computed values in the browser (see below): the evidence is the value,
not the assumption.

## Overriding semantic colours

Attribute selectors instead of exact class names, so that all shades of the app come along (`/10`, `/15`,
`/30`, `hover:`):

```css
/* Success — palette tone as the label surface, text/dot as a darker step of the same colour.
   The "Running" status keeps its text colour: only the chip shades are tinted. */
[class*="text-success"]:not([class*="text-success-foreground"]) { color: #2C7A57 !important; }   /* status */
[class*="bg-success/"][class*="text-success"] { color: #4B3832 !important; }                     /* label text */
[class~="bg-success"] { background-color: #2C7A57 !important; }                                  /* status dot */
[class*="bg-success/10"], [class*="bg-success/15"] { background-color: color-mix(in srgb, #BE9B7B 28%, transparent) !important; }
[class*="border-success"] { border-color: color-mix(in srgb, #BE9B7B 59%, transparent) !important; }

/* Warning — sun yellow */
[class*="text-warning"]:not([class*="text-warning-foreground"]) { color: #8A6100 !important; }
[class~="bg-warning"] { background-color: #8A6100 !important; }
[class*="bg-warning/"]:not([class*="bg-warning-foreground"]) { background-color: color-mix(in srgb, #FFCC5C 38%, transparent) !important; }
[class*="border-warning"] { border-color: color-mix(in srgb, #FFCC5C 65%, transparent) !important; }

/* Danger — coral */
[class*="text-destructive"]:not([class*="text-destructive-foreground"]) { color: #B02A24 !important; }
[class~="bg-destructive"] { background-color: #B02A24 !important; }
[class*="bg-destructive/"]:not([class*="bg-destructive-foreground"]) { background-color: color-mix(in srgb, #FF6F69 30%, transparent) !important; }
[class*="border-destructive"] { border-color: color-mix(in srgb, #FF6F69 60%, transparent) !important; }
```

Two details that are otherwise easy to get wrong:

- **`[class~="bg-success"]` for the full surface, `[class*="bg-success/"]` for the tint.**
  `class~=` matches only the exact class name (status dot, line), `class*=` matches the
  slash shades. Using `class*=` for both fades a solid status dot to the
  12-% tint.
- **`:not([class*="-foreground"])` is mandatory.** `.text-destructive-foreground` carries the same
  substring; without the exception the white text on red buttons gets coloured along with it.
- **A label carries surface AND text on the same element** (`bg-success/10 … text-success` in
  one class list). A descendant selector with a space matches nothing there: the text stays
  the bundle colour while the surface is already the new one — the symptom is a brown chip with
  green text. Always write the compound form `[class*="bg-success/"][class*="text-success"]`
  as well; its specificity (0,2,0) beats the text rule above.
- **Do not tint `[class*="bg-success/"]` across the board.** That also matches `bg-success/[0.03]`, an almost
  invisible wash surface that becomes visible as a 28-% tint. List only the shades that
  really are chips (`/10`, `/15`).

## Colour choice: palette tone as surface, text one step darker

The palette tones are correct as a **surface** and unusable as **text**: mint `#96CEB4` on
white gives 1.8:1, while 4.5:1 is required for small text. Hence two values per role — surface from
the palette, text and status dot the same hue darkened. Desaturated bespoke mixes are **wrong** here:
a desaturated green tone was rejected as "too muted" and a palette was named instead.

| Role | Palette tone (surface) | Step for text/dot | Share |
|---|---|---|---|
| Success (status) | `#96CEB4` mint | `#2C7A57` | 28 % |
| Label "Tools" | `#BE9B7B` | `#4B3832` | 28 % |
| Label "Vision" | `#854442` | `#4B3832` | 54 % |
| Label "Reasoning" | `#6E5F94` | `#6E5F94` — at 35 % only 3.42:1, darken the text further | 35 % |
| Warning | `#FFCC5C` sun yellow | `#8A6100` | 38 % |
| Danger | `#FF6F69` coral | `#B02A24` | 30 % |

The share is the adjusting screw: it determines the contrast of the text on its own surface, and
small text needs 4.5:1 there. For mint, 32 % was still 4.1:1 — only 28 % with `#2C7A57` reaches
4.5:1. Calculate rather than estimate (snippet in SKILL.md under "Workflow"); keep the palette tones
as light as possible, "muted" is the rejection.

**The share acts against the text that already stands there.** If only the strength is increased
(Reasoning 14 % -> 35 %), the text colour stays and the contrast falls (4.67 -> 3.42:1). Then do not
secretly turn the surface back — that choice stands — but name the new value and offer two
to three darker steps of the **same** hue with their computed values (`#5F5185`
4.25:1 / `#4A3D6E` 5.84:1 / `#413560` 6.70:1), so that only a choice has to be made. Carry the border
along too (rule of thumb share x 2.1), otherwise surface and border no longer match.

The app instead ships `#4ade80`, `#ffbd38` and `#fb2c36`.

These colours are **semantic**: they apply across the whole dashboard (warning banners, delete buttons,
status texts), not only on the page where they stand out. Say this in advance, otherwise a change is
judged whose scope is unknown.

## Bezel: replace, do not delete

The bezel utilities are the **only** edge of the light buttons (`border-width: 0`). They must
not be covered with `0 0 #0000`, but replaced by a uniform hairline —
otherwise the light buttons are borderless:

```css
[class*="shadow-[inset"] { --tw-shadow: inset 0 0 0 1px var(--midground) !important; }
```

`inset` means: follows the rounding, no layout offset. Full `midground` colour is the recommended
default; on dark buttons the line disappears by itself because it coincides with their surface. Go
through the variable, **not** `box-shadow: none` — otherwise the focus ring is lost.

## Measuring in the browser

```python
goto_url("http://127.0.0.1:18789/models"); wait_for_load(); time.sleep(6)
print(js("""(() => {
  const tag = document.querySelector('[class*="bg-success/"]');
  const dot = document.querySelector('[class~="bg-success"]');
  return JSON.stringify({
    text: getComputedStyle(tag).color,
    surface: getComputedStyle(tag).backgroundColor,
    dot: dot ? getComputedStyle(dot).backgroundColor : '-'
  });
})()"""))
```

Expected: `rgb(44, 122, 87)` (= `#2C7A57`) for text and dot, the surface
`color(srgb 0.588 0.808 0.706 / 0.28)` (= mint `#96CEB4` at 28 %).
The computed value is the evidence; for an evidence image in chat pull an 8x crop via CDP
(`references/roundness-and-custom-css.md`, section 7).

## Where the semantic colours are visible in the UI

For the question "where do I find warning and danger?" there is no need to search: these spots do not
exist in the empty state, so check the page first, then answer. Measured in a running
dashboard:

| Role | Page | Spot |
|---|---|---|
| Warning | Webhooks | card "Webhook receiver disabled" — border in sun yellow at 65 % |
| Warning | System | button **STOP** (halt the gateway), text `#8A6100` |
| Warning | Logs | the `WARNING` lines |
| Danger | Cron | status dot of a job on `error` (coral at 30 %) along with the red state word |
| Danger | System | the buttons **Reset MEMORY.md**, **Reset USER.md**, **Reset all**, text `#B02A24` |

Per state additionally: session icons for cron/tool/webhook and search hits in sessions
(warning), error texts on models/MCP/channels and delete icons in files/profiles (danger).
A walk over the pages with a Hades search for `text-warning|bg-warning|border-warning` or
`-destructive` shows in seconds what currently applies:

```python
for pfad in ("system", "mcp", "webhooks", "models", "files", "profiles", "logs", "chat"):
    goto_url(f"http://127.0.0.1:18789/{pfad}"); wait_for_load(); time.sleep(6)
    print(pfad, js("""(() => { const f = [];
      document.querySelectorAll('*').forEach(e => {
        const c = typeof e.className === 'string' ? e.className : (e.getAttribute && e.getAttribute('class')) || '';
        const t = (e.innerText || '').trim().slice(0, 34);
        if (t && /text-warning|bg-warning|border-warning|text-destructive|bg-destructive|border-destructive/.test(c)) f.push(t);
      }); return JSON.stringify(f.slice(0, 3)); })()"""))
```

For an evidence image in chat, `scrollIntoView({block: 'center'})` works, then read the rect and pull
the CDP crop in the **same** call — the rect is only valid for the scroll position in which it was
read.

## Do not work with a pixel measurement of the screenshot

Measuring a crop image fails on two things and only costs time: the image coordinates
shift with the scroll position (the rect must be read in the same call that produces the image), and
foreign dark content (text, neighbouring buttons) lies in the crop, which falsifies any
count — a ring measurement therefore returned 26 to 128 px for a 1.6-px stroke. For thickness,
colour and presence, `getComputedStyle` and the class list are reliable; the image serves the
presentation in chat.

## Tailwind default palette, fixed hex values and the diagram colours

The semantic colours are only one half: at individual spots the interface additionally reaches into the
**Tailwind default palette** and sets fixed hex values in two components. This too follows
no theme value. What appears in the source and what it is mapped to:

| Occurrence | Classes | Replacement (theme family) |
|---|---|---|
| Vision label | `bg-blue-500/10 text-blue-600 dark:text-blue-400` | text `#4B3832`, surface 54 % of `#854442` |
| Reasoning label | `bg-purple-500/10 text-purple-600 dark:text-purple-400` | grey-violet: text `#6E5F94`, surface 35 % |
| Skill dialog, verdict | `text-emerald-400`, `border-emerald-500/60`, `bg-emerald-500/5` | mint: text `#2C7A57` |
| Skill dialog, hint | `text-amber-300/400/500`, `border-amber-500/40`, `bg-amber-500/10` | sand: text `#8A6100` |
| Skill dialog, warning | `text-red-300/400/500`, `border-red-500/40`, `bg-red-500/10` | coral: text `#B02A24` |

**This is the cause of "some texts are white and barely readable".** The 300/400 tones are
intended for dark surfaces; on white they sit at 1.4-1.7:1 (`#34D399` = 1.7:1, `#fcd34d` =
1.4:1). They do not look white, they *are* washed out. Measure after overriding:
verdict 4.95:1, hint 5.26:1, warning 6.22:1.

```css
[class*="text-blue-"] { color: #4B3832 !important; }
[class*="bg-blue-500/"] { background-color: color-mix(in srgb, #854442 54%, transparent) !important; }
[class*="border-blue-"] { border-color: #854442 !important; }
/* purple (purple/violet/indigo/fuchsia), emerald (emerald/green/teal), amber (amber/orange/yellow)
   and red (red/rose) analogously: text-* = text, bg-*-500/ = tint, border-* = border */
```

Two subtleties:

- **Text and surface need different darkness.** The palette tone itself is too light as
  text on its own label surface: `#854442` on the 54-% surface of its own tone
  is far below the threshold; with `#4B3832` as text it is a measured 4.32:1. For 12-px text
  the value **on the surface** counts; the value on white would have let the weak tone through.
- **The icon strokes move along automatically.** Icons inherit `currentColor`: the 128 purple and 28
  blue strokes in the SVG of the models page came from the badge text carrying that colour. Only fix
  the text class, not the SVGs individually.

The classes are **thinly scattered** (blue and purple ~10 occurrences each in the whole dashboard), so
the scope of the intervention is small — but reach across all families instead of fixing only the
specifically named spots.

### Diagram colours (usage bars) and `seriesColors`

The bar of the models page has four segments; two are theme variables, two sit in the code:

| Series | Source | Reachable via |
|---|---|---|
| Input / Output | `var(--series-input-token)` / `var(--series-output-token)` | theme field `seriesColors` — **is discarded by the server** |
| Cache Read | `#60a5fa` directly in the component | inline style |
| Reasoning | `#c084fc` directly in the component | inline style |

Default measured on a running dashboard: input `#FFE6CB` (orange-100), output `#34D399`
(emerald-400) — both garish, both unreachable via `colorOverrides`. Replacement:

```css
:root { --series-input-token: #FFE28A !important; --series-output-token: #D9A441 !important; }
```

`!important` is mandatory: the client sets these variables **inline on `<html>`**, and inline style
beats any stylesheet declaration without `!important`. Proof that the block takes effect: the two
variables deliver sand and mint, 45+45 legend dots carry them, and the bar segments appear
as `color(srgb … / 0.7)` of the same tones.

The two fixed hex values can only be captured via the style attribute — and **React writes them
serialized**: the attribute holds `background-color: rgb(96, 165, 250)`, not `#60a5fa`. A
selector on the hex string matches **nothing**. Hence both spellings, and dot separated from
bar:

```css
[style*="rgb(96, 165, 250)"].rounded-full, [style*="#60a5fa"].rounded-full { background-color: #66B2B2 !important; }
[style*="rgb(96, 165, 250)"]:not(.rounded-full), [style*="#60a5fa"]:not(.rounded-full) { background-color: color-mix(in srgb, #66B2B2 70%, transparent) !important; }
```

`color-mix` in inline style is also resolved on serialization
(`color-mix(in srgb, rgb(96, 165, 250) 70%, transparent)`), so the `rgb()` string matches bar and
dot together. Without the split by `.rounded-full`, one of the two gets the wrong
opacity (dot full, bar 70 % — the way the app draws it).
