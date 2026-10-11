---
name: hermes-dashboard-theming
description: "Reskin the Hermes web dashboard with YAML themes."
version: 1.0.0
author: Faultbendfold, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, dashboard, theme, css, branding]
    related_skills: []
---

# Restyle the Hermes dashboard (themes)

## When to Use

- The web dashboard looks ugly, retro or pixelated and a different look is wanted.
- The dashboard's colors, fonts, density or roundness should change.
- Not covered here: CLI/TUI skins (`display.skin`, `<HERMES_HOME>/skins/`) — a separate system.

## Hard rules

1. **A theme is a YAML file in the persistent home — no rebuild, no fork.** Location:
   `<HERMES_HOME>/dashboard-themes/<name>.yaml`. Never edit `/opt/hermes` — that is the image and
   is gone at the next app update.
2. **Activate only via `hermes config set dashboard.theme <name>`**, never by editing `config.yaml`
   by hand (a single indentation error tears apart the running gateway configuration). The backend
   re-reads user themes on every request — but the **frontend** fetches the list exactly once when
   the page loads and silently swallows errors during it (`api.getThemes().then(…).catch(() => {})`).
   After creating a theme file you therefore need a **full page load**, not just opening the picker:
   a still-open tab keeps showing only the built-in themes — and that looks exactly like a failed
   fetch, namely "no visible difference". On desktop Ctrl+Shift+R. **On mobile there is no hard
   reload** — close and reopen the tab, or use a private tab; a normal reload is already enough,
   because `index.html` is served with `no-store` and the scripts carry content hashes. Do not send
   the user chasing cache tricks: if the choice lives in the config, the bootstrap CSS paints it on
   the first paint anyway.
3. **Watch for name collisions:** a theme with the name of a built-in preset (`default`,
   `default-large`, `mono`, `slate`, `cyberpunk`, `nous`, `nous-blue`, `midnight`, `ember`, `rose`)
   does not override the built-in one. Pick a fresh name.
4. **The palette derivation does not carry a light theme on its own.** The model only has the levels
   `background`/`midground`/`foreground`; `midground` is simultaneously text **and** the primary
   color. With a light canvas and near-black text, the text thereby becomes the button fill color.
   Always set `colorOverrides` because of this: `primary`/`primaryForeground`, `card`/`cardForeground`,
   `popover*`, `secondary*`, `muted`/`mutedForeground`, `accent`/`accentForeground`, `border`,
   `input`, `ring`, `destructive*`, `success`, `warning`.
5. **`palette.noiseOpacity` is the retro knob.** The film-grain overlay creates the
   "pixelated/retro" impression; `0` turns it off. The second retro factor are the bundled display
   fonts: the base font is replaced by a stack in `typography.fontSans` (reaches `body`), but the
   **headings** only by the customCSS override from the Pitfalls — `typography.fontDisplay` alone
   has no effect. Font choice and test: `references/typography-and-fonts.md`.
6. **Color values as `#rrggbb`.** Short forms and CSS function names are not guaranteed on every
   surface; `warmGlow` is the exception (there `rgba(...)` is intentional).
7. **Roundness needs two levers.** `layout.radius` cascades via `--theme-radius` onto
   `--radius-sm/md/lg/xl` (defined in `web/src/index.css`) and thereby reaches buttons, inputs and
   token-based cards. But many surfaces are hard-wired as `rounded-none` — cards, chips and dialogs
   on the skills, plugins and config pages — and stay square no matter what the theme says; that is
   exactly what creates the brutalist or "retro" impression. They can be brought along in
   `customCSS`: `[class~="rounded-none"] { border-radius: var(--radius-md) !important; }`.
   Limit: the selector hits every element marked that way — if a single corner bothers, narrow the
   override to the affected page, do not force the same effect via `radius`.
   **`rounded-none` is only part of the truth:** the preflight sets
   `button,input,select,textarea{border-radius:0}`, almost no `rounded-*` classes occur in the DOM,
   and the active/inactive marks are self-painted 13x13-px `span`s instead of form elements. Class
   list, verified selectors and the `appearance: none` requirement for checkboxes:
   `references/roundness-and-custom-css.md`. Enumerate in the browser first, then round —
   "everything still square" is the normal state of this layout, not a sign of a theme that was not
   applied.
8. **Compute contrast, do not estimate — for text AND button.** The strong accent tone is usually
   too light as a text color and often too flat as a button fill: white button label on `#0D9488`
   gives only 3.74:1 and fails. Rule: set text (`midground`) **and** `primary`/`ring` to a darker
   step of the same hue, check the text tone against the **actual canvas** for >= 7 and the button
   label against the fill for >= 3.2 (WCAG relative luminance, Python snippet under "Procedure").
   The buffer above the AA threshold of 4.5 prevents individual derived tones from slipping through.
   That way variants then differ only in hue, not in legibility.

## Recommended direction: light, clean, modern

**A light, clean, modern UI: light canvas, rounded corners, modern font — and little color.**
This line is stable. The intermediate stages before it are done and not to be picked up again:
white canvas with colored text, "the whole palette in the UI" (canvas, cards, borders, hover
surfaces and panels from one palette) and muted color tones were all built; the verdict was "It
all doesn't look that great. Less is probably better", followed by a complete restart. **Full-area
palette tones are the mistake here, not the goal** — color is an accent on text and buttons, the
surface is light and calm.

- **The palette carries all roles**, not just the accent: canvas, cards, borders,
  hover/`muted`/`secondary`/`accent` surfaces and buttons. The canvas is the lightest tone of the
  palette, lightened up to a brightness that works as a surface (target ~0.93 relative
  luminance) — a palette of mid tones cannot supply its own light canvas.
  Role assignment and target values: `references/palette-to-theme-mapping.md`.
- **Panels carry the palette along** — this step is explicitly wanted (released after the question
  "how many colors can go in parallel?"): set `componentStyles` for `sidebar.background` and
  `header.background`. Light theme: `mix(canvas, primary, 0.09)`; if `primary` is lighter than the
  canvas, instead `mix(canvas, text, 0.05)`. Dark theme: `mix(canvas, lightest_palette_tone, 0.15)`.
  Additionally set `componentStyles.card.background` explicitly, so the card does not fall back to a
  derived value. This also applies to the right panel of the chat page (same sidebar variable).
  Set nothing outside these four props — see Pitfalls.
- Legibility stays mandatory: `midground` **and** `primary`/`ring` on a darker step of the same
  hue, checked against the **real canvas**, not against white.
- Leave one deliberate exception in place: `neutral-accent` (white canvas, neutral text, color only on
  buttons and links) — as a counterpart for direct comparison.
- **Saturation: large surfaces calm, semantic accents fresh — do not confuse them.** For canvas,
  cards and panels: desaturated, mid-dark tones; a fully saturated palette surface (e.g. a complete
  pastel yellow) is sorted out. For the **semantic** colors (success/warning/danger) the opposite
  applies: a muted tone was rejected as "too subdued" and a palette named instead. There the
  palette tone is the **surface**, and only text and status dots get a darkened step of the
  **same** hue. Recipe and locations: `references/hardcoded-build-styles.md`.
- `noiseOpacity: 0`, system font stack, `radius` 1rem, soft low shadows,
  `density: comfortable`, rounded corners for cards and dialogs too.
- **Few, but good drafts.** Two to three variants for comparing are enough; a series of shades was
  rejected. Offer the choice only as a clear directional alternative ("neutral text with one
  accent" versus "palette carries the surfaces"), not as a dozen similarities.
- Variants that differ only in the accent look **the same** on a neutral canvas — that is a reason
  for fewer variants, not for more. That was exactly how it became clear more was wanted; when more
  arrived, it was too colorful.
- **Font: exactly one, and a modern sans (Inter) for everything.** Set `typography.fontSans`
  **and** `fontDisplay` to the same stack and put the retro title classes on
  `var(--theme-font-sans)` via customCSS (`.font-mondwest, .font-expanded, h1, h2, h3 { font-family:
  var(--theme-font-sans) !important; letter-spacing: normal !important; }`) — then the titles follow
  the font picker too. Reading/e-book fonts (Libron) are unsuitable as a UI font (no 500/600
  weights; intermediate weights are ubiquitous in buttons and tabs and would be synthetically
  bolded). Serifs for headings (Newsreader) were tried and **rejected again** ("Only one font") —
  do not propose them again. Details: `references/typography-and-fonts.md`.
- **When cleaning up, move rather than delete.** "All skins out" means: move the YAMLs to
  `<HERMES_HOME>/dashboard-themes-archiv-<timestamp>/` (only `dashboard-themes/*.yaml` is discovered,
  so the archive does not interfere) and reset `dashboard.theme` to `default`. Delete for good only
  after that has been reviewed and confirmed.
- **Colors should be tried out directly, not just judged.** First list a page's color inventory
  ("list all the colors and what they stand for") and then a tool into which own hex values can be
  typed with the result visible immediately. Both belong to the answer: the list grouped by **roles**
  with meaning (surfaces, text with opacity, borders, labels, consumption series, state — plus what
  no longer occurs) and the interactive board `<HERMES_HOME>/farbboard.html`: on the left hex/color
  picker, on the right surface, sample label and contrast, live while typing; at the bottom an
  output block with the finished theme snippets to send back. The board's default values mirror the
  **active** theme — update them after every theme change, otherwise decisions are made on a stale
  state. Structure, measurement recipe and pitfalls: `references/color-board.md`.
- At the end, ask which variant should be set permanently (`hermes config set dashboard.theme ...`).

## Procedure

1. Take stock: does `<HERMES_HOME>/dashboard-themes/` exist, and what is in `dashboard.theme`
   (`hermes config get dashboard.theme`)? The built-in themes live in
   `hermes_cli/web_server_dashboard.py` (`_BUILTIN_DASHBOARD_THEMES`), their colors in
   `web/src/themes/presets.ts` — worth a look, because there is already a light preset whose palette
   is a good template for a custom light theme.
2. Define the schema: palette (3 levels + `warmGlow` + `noiseOpacity`), typography, layout,
   `colorOverrides`, optionally `componentStyles`, `assets`, `customCSS`.
3. Write the YAML (every missing entry falls back to the built-in `default`, so a theme may be
   small). As a starting point copy the template `templates/light-clean-theme.yaml` and adjust only
   the name, label, accent color and the matching hover/selection tones. A comment header with the
   activate and rollback commands saves the user the return question. For **whole palettes** do not
   work by hand: `scripts/gen_dashboard_themes.py` generates complete variants (canvas, cards,
   borders, hover, buttons) from a palette list, along with a check table. Enter the new palette at
   the top of `PALETTES` and run the script; role assignment and target values:
   `references/palette-to-theme-mapping.md`.
4. First prove **without a browser** that the file arrives: import `_discover_user_themes()` from
   `hermes_cli.web_server_dashboard` (Hermes venv, `HERMES_HOME` set) — it normalizes the YAML and
   shows whether the keys arrive. Only then look at it: fully reload the page (on desktop
   Ctrl+Shift+R, on mobile close and reopen the tab), click the palette icon in the header. The
   backend rediscovers themes per request, the frontend only on load — without a full page load the
   list stays old and "no difference" is seen.
5. Second proof without a browser: `_render_active_theme_bootstrap_css()` (same module) shows the
   critical `<style>` block that the server renders for the active theme. If the expected
   `--background-base`/`--midground-base` is there, the chain file -> config -> first paint is
   proven, independent of browser cache and menu.
6. Compute the finished palette's contrast — text tone against the canvas (target >= 7) and button
   label against `primary` (>= 3.2). With a tinted canvas do **not** compute against `#FFFFFF`, but
   against the value in `palette.background`:

   ```python
   def lum(h):
       h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
       c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
       return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

   def ratio(a, b):
       la, lb = lum(a), lum(b); hi, lo = max(la, lb), min(la, lb)
       return round((hi + 0.05) / (lo + 0.05), 2)
   ```

   If a value falls below the target, choose a darker hue and pull text **and** `primary` along
   together — never only one of the two places.
7. Activate and verify: `hermes config set dashboard.theme <name>`, then
   `hermes config get dashboard.theme`. Rollback at any time: `... dashboard.theme default`.

## Knobs (quick reference)

- `palette`: `background`, `midground`, `foreground` (alpha 0 = invisible), `warmGlow`
  (rgba vignette in the backdrop), `noiseOpacity` (0-1.2)
- `typography`: `fontSans`, `fontMono`, `fontDisplay`, `fontUrl` (external stylesheet),
  `baseSize`, `lineHeight`, `letterSpacing`
- `layout`: `radius` (CSS length), `density` (`compact` | `comfortable` | `spacious`)
- `layoutVariant`: `standard` (max 1600px) | `cockpit` (sidebar) | `tiled` (full width)
- `colorOverrides`: **exactly 19 allowed keys** — `card`, `cardForeground`, `popover`,
  `popoverForeground`, `primary`, `primaryForeground`, `secondary`, `secondaryForeground`,
  `muted`, `mutedForeground`, `accent`, `accentForeground`, `destructive`,
  `destructiveForeground`, `success`, `warning`, `border`, `input`, `ring` — map 1:1 to
  `--color-<kebab>`. The server **silently** discards everything else: a typo goes unnoticed,
  the color simply has no effect.
- `seriesColors` (2: `inputTokenAccent`, `outputTokenAccent`) — **the server does not pass the
  block through**: it is missing from the response of `/api/dashboard/themes`, while `customCSS`,
  `colorOverrides`, `componentStyles` and `palette` do arrive there (so the file is read fresh, the
  field is dropped during normalization). Set input/output colors via customCSS instead:
  `--series-input-token` / `--series-output-token`, **with `!important`** — the client sets these
  variables inline on `<html>`, and inline style beats any stylesheet without `!important`.
- `terminalBackground`/`terminalForeground` (2), `swatchColors` (3, picker preview only)
- `componentStyles`: 9 buckets allowed (`card`, `header`, `footer`, `sidebar`, `tab`, `progress`,
  `badge`, `backdrop`, `page`); camelCase properties become `--component-<bucket>-<kebab>`.
  **The shipped build reads only** `sidebar`/`header`/`card` with `background`, `border-image`,
  `clip-path` (card additionally `box-shadow`) as well as `tab` with `clip-path`. Values in the
  remaining buckets have no effect. Inventory and test:
  `references/theme-token-inventory.md`.
- `assets`: `bg` (automatically in the backdrop), `hero`, `logo`, `crest`, `sidebar`, `header`,
  `custom`
- `customCSS`: raw CSS in an injected `<style>` tag, limit 32 KiB
- Additionally independent of the theme: `dashboard.font` (font override, also settable in the
  picker)

## Pitfalls

- Do not mix CLI skins and dashboard themes: `display.skin` + `skins/` theme the terminal,
  `dashboard.theme` + `dashboard-themes/` theme the web. Two systems, two locations.
- **Inline `code` chips and the text selection change color on EVERY click — the app cycles
  `--selection-bg`.** The bundle registers a `selectstart` listener that advances the variable to the
  next of **eleven** pastel hues on every selection start (`oklch(85% 0.12 330)` through
  `oklch(88% 0.10 80)`, once around the color wheel), and
  `code { background: var(--selection-bg, var(--midground)) }` paints the copyable commands with it
  (Keys page = `/env`). Reported as "the texts for direct copying have a colored background and the
  color changes on every click". Freeze it with
  `:root { --selection-bg: <calm tone> !important; }` (this beats the inline value the script sets)
  plus `code { background: … !important; color: #111827 !important; }`; `::selection` additionally
  needs `color: inherit !important`, because the app sets `color: var(--background)` there — near
  white text on a light tint, i.e. an unreadable selection. Evidence: compare two screenshots taken
  before and after a **real** click pixel by pixel; a synthetic `dispatchEvent` click does not fire
  `selectstart` and fakes "no change". The app also dims those commands with `opacity-60`, which
  leaves roughly 3.5:1 against a light surface; to get more, set `opacity: 1 !important` on `code`
  (~14:1), at the cost of making secondary text more prominent.
- **There are no sliders in the dashboard.** `type="range"` and slider components do not occur in
  the source; if a user says "slider", they almost always mean the **scrollbars** or the
  active/inactive marks. Do not guess — ask for a screenshot and have the spot marked.
- **Real checkboxes are native inputs with the single class `accent-foreground`** (cron menu,
  webhooks); `progress` and `meter` are unrounded. Rounding only via `customCSS`, for inputs only
  together with `appearance: none` — native widgets silently ignore `border-radius`.
  Recipes: `references/roundness-and-custom-css.md`.
- **The bundled base fonts are the retro fonts Collapse and Courier Prime**, plus Rules and Mondwest
  for titles and tags. `body` reads `--theme-font-sans`, so a theme `fontSans` takes effect there;
  titles and tag classes do not (their own Pitfalls below).
- **Mechanics state:** discovery, route and bootstrap CSS verified on 2026-10-11 against Hermes
  v2026.9.24. After an app update, re-check `_discover_user_themes()` first before interpreting any
  deviation as a theme bug.
- The picker selection in the browser lives in the browser's localStorage (per device); only the
  config value makes the theme the default for all devices.
- Colors in the picker and the bootstrap CSS at first paint come from the active config: for a user
  theme the backend renders a critical `<style>` with background, text and font, so that no wrong
  theme flashes while loading. A theme without `background` makes the first frame uncontrolled.
- The theme API requires authentication — do not test it via curl against the dashboard port. The
  **page** however needs no token: on "no difference" or "everything still square", read the
  computed values in the real browser via `browser_exec` and compare the number of rounded elements
  before/after a change. That is the only reliable proof that a customCSS block has an effect — and
  it finds the square spots instead of guessing them.
  Recipe: `references/roundness-and-custom-css.md`.
- **`border-radius` on a form element only works together with `appearance: none`.** Native widgets
  (checkbox, radio, select) are painted by the browser itself and silently ignore the rounding: the
  rule sits correctly in the theme and changes nothing. Only turning off the appearance and drawing
  the box yourself (size, border, background, checkmark via `::after`) works.
- **Active/inactive marks are not form elements.** In lists (e.g. skills) they are
  13x13-px `span`s with `pointer-events-none` that the UI paints itself; checkbox CSS does not reach
  them. Round via the utility classes
  (`span[class*="pointer-events-none"][class*="w-3.5"]`), not via `input`.
- Work through "no visible difference" in this order, do not start with the design:
  (1) is the file really in `<HERMES_HOME>/dashboard-themes/` and does `_discover_user_themes()`
  return it? (2) was the page reloaded **completely** (hard on desktop, close and reopen the tab on
  mobile)? (3) did the picker fetch even run in the browser (it fails silently)? (4) only then the
  config. As long as (1)-(3) are open, any statement about the theme is unproven.
- **The picker writes the choice server-side**: a click in the palette menu sets `dashboard.theme`
  in the config (`PUT /api/dashboard/theme`). Before any statement about which theme is active, read
  `hermes config get dashboard.theme` first — the value can change during a session while variants
  are clicked through.
- After activating, actually look at the UI and report the change as proven, not as expected;
  theme changes are purely additive and can be reverted at any time.
- Overwriting an existing theme file requires a full `read_file` beforehand (write gate) —
  otherwise `write_file` fails without an error message in the result (`ok=None`).
  When generating multiple variants, therefore read first, then write, per file in `execute_code`.
- **Palette math in floating point, round only at the end.** Repeated mixing in fixed integer
  percentage steps toward white gets stuck on rounding: the increment becomes 0, the loop runs to
  its limit and permanently returns a pale value instead of the expected hue. Instead of mixing
  iteratively, solve the mix factor by bisection over the luminance or contrast target and round
  once — `lighten_to`/`fit` in `scripts/gen_dashboard_themes.py`.
- **Check contrast against the actual canvas**, not against `#FFFFFF`. With a tinted canvas the
  relevant threshold is text-vs-canvas; the white comparison applies only to the label on filled
  buttons.
- **Never make the darkest palette tone the canvas just because it is the darkest.** With palettes
  of mid tones this produces unreadable themes (contrast 1.5-3.3). Lighten the canvas; a dark
  version only for palettes that have no light tone at all (name suffix `-dark`).
- **Fetch palettes with `web_extract`, not via `curl`.** color-hex.com sits behind Cloudflare and
  answers curl with 403. The color values lie in the extracted text between the markers
  `Colors in Palette` and `PNG Image`; everything outside belongs to the page, not the palette.
- **Set only `componentStyles` props that the build reads.** `badge`, `page`, `progress`,
  `backdrop` and `footer` are accepted by the server, but no place in the shipped build reads them.
  Colors set there are dead configuration and fake a change that does not happen — look in the
  bundle before setting instead of after the effect fails to appear. Test: `grep -oh --
  "--component-[a-z]*-[a-z-]*" hermes_cli/web_dist/assets/*.{css,js} | sort -u` (the double hyphen
  is mandatory, otherwise the search tool reads the pattern as an option and reports zero hits).
- **`typography.fontDisplay` has no effect in the shipped build.** The variable
  `--theme-font-display` is set, but read by no rule; the titles carry their font in the source as a
  class (`font-mondwest` = pixel font, ~20 places; `font-expanded`). Titles can only be reached via
  `customCSS`:
  `.font-mondwest, .font-expanded, h1, h2, h3 { font-family: <stack> !important; letter-spacing:
  normal !important; }` — reset tracking, because the titles carry `tracking-wider` and that tears a
  serif font apart. The font picker in the menu does not reach these classes either.
  Test and font choice: `references/typography-and-fonts.md`.
- **`colorOverrides` knows exactly 19 keys, and unknown ones disappear silently.** When extending a
  theme, check the key list against `_THEME_OVERRIDE_KEYS` in `web_server_dashboard.py`; an invented
  token ("mutedForegroundHover") goes unnoticed everywhere.
- **With panel surfaces the separation must stay visible.** Sidebar, header and canvas must not get
  the same color, otherwise the structure disappears; the panel tone is a mixture of canvas and
  palette, not a palette tone pure.
- **The border around buttons is an animated gradient ring (`.arc-border`), not a border.** The
  element carries neither `border-width` nor `border-image`; a mask (`mask-composite: exclude`) cuts
  out an equally wide ring surface, `--arc-width` **is** the padding (1.25 px), `--arc-duration` the
  runtime (2.23 s). **The gradient starts at `transparent`** — a section of the stroke is therefore
  invisible, and with the animation this gap travels around the element: a user describes this as
  "border not continuous, the corners are thinner" and names different corners depending on the
  moment. That is not the theme's fault, the same gap sits in the bundled skins. The fix is opaque
  ends in the gradient; whether the motion should stay is taste and belongs presented as a numbered
  option, not decided upfront (the animation was first brought back and later the calm version was
  chosen: an opaque tone, `--arc-duration: 0s`, plus `--arc-width: 1.6px` — a 1.25-px stroke is
  smoothed more heavily at curves and reads paler there).
  Outer radius = inner radius + 2 px, otherwise the corners are not concentric. Recipes, selectors
  and options: `references/roundness-and-custom-css.md`.
- **A "sticky border" on buttons is usually app behavior, not the theme.** The focus borders sit as
  utility classes in the button's source
  (`.focus-visible\:border-midground\/25:focus-visible { border-color: var(--midground) }`). Before
  debugging your own CSS, grep the bundle first — otherwise you fix a rule that does not exist.
- **A "strange border" or "gray shadow on top" on buttons are two hard inner shadows (bezel), not
  the ring.** Arbitrary shadow utilities
  (`.shadow-[inset_-1px_-1px_0_0_#00000080,inset_1px_1px_0_0_#ffffff80]` plus two variants) put a
  1-px inner line at the bottom right (dark) and top left (light) on the button. Inner shadows follow
  the rounding: on the dark button the light part becomes the "gray stripe on top", on the light
  button the dark part emphasizes two **opposite** corners. **Replace, do not delete:** the light
  buttons have `border-width: 0` — the bezel is their only edge. Covering it with
  `--tw-shadow: 0 0 #0000` makes them borderless and "the borders of the white buttons are gone" is
  reported; the right thing is
  `[class*="shadow-[inset"] { --tw-shadow: inset 0 0 0 1px var(--midground) !important; }`.
  Go via the variable, **not** via `box-shadow: none`, otherwise the focus ring disappears with it
  (it sits in its own variables of the same shorthand). The replacement line in **full**
  `--midground` color is the recommended default — the muted mix was only the starting value.
  Order for unequal button borders: first check this edge, then `.arc-border`, then
  `layout.radius`. Recipes, selectors and tests: `references/hardcoded-build-styles.md` and
  `references/roundness-and-custom-css.md`.
- **Success/warning/danger are hard-wired in the shipped bundle — `colorOverrides` does not reach
  them.** The utilities carry the hex value directly (`.text-success { color: #4ade80 }`,
  `.bg-success { background-color: #4ade80 }`, likewise `#ffbd38` and `#fb2c36`); `--color-success`
  sits correctly in the theme and is read by no place. This becomes visible as "on the models page
  there are still colors for the capabilities and usages": labels, status dots and hints stay
  garish, while everything else is muted. Override via attribute selectors that take along all
  steps (`/10`, `/15`, `/30`, `hover:`) and exclude `-foreground` (that is the text ON the color):
  `[class*="text-success"]:not([class*="text-success-foreground"])`, `[class~="bg-success"]` for the
  full surface (status dot), `[class*="bg-success/"]` for the tint. An `info` family does not exist
  in the bundle. **Announce beforehand that these colors are semantic and thus apply across the
  whole dashboard** (warning notices, delete buttons) — otherwise a change is judged whose scope is
  unknown. To "where do I find warning and danger?" the locations list in the recipe answers
  (webhooks card, system buttons STOP/Reset, log WARNING lines, cron error dot) — it is not visible
  in the empty state, so check first, then name it. Tones, blocks and grep tests:
  `references/hardcoded-build-styles.md`.
- **For labels the surface and the text sit on THE SAME element — descendant selectors do not reach
  there.** The chip carries `bg-success/10 … text-success` in *one* class list; a selector with a
  space (`[class*="bg-success/"] [class*="text-success"]`) hits nothing, and the text stays in the
  bundle color while the surface is already the new one. Always add the compound form:
  `[class*="bg-success/"][class*="text-success"]`.
- **Label and status share one color family — separate them, do not treat them the same.**
  `success` carries both the capability label and the "Running" status dot. If only the label should
  get the new color, narrow the tint to the chip steps (`[class*="bg-success/10"]`,
  `[class*="bg-success/15"]`) and leave `[class~="bg-success"]` and `text-success` for the dot and
  status text standing. The blanket tint `[class*="bg-success/"]` also visibly colors the almost
  invisible `bg-success/[0.03]` wash surface. Name both roles beforehand — the choice of which is
  meant is theirs.
- **The surface share acts against the legibility of the text on it.** If only the share is raised
  (reasoning 14 % -> 35 %), the text stays the same and the contrast drops (4.67 -> 3.42:1). After
  every share change, measure again, name the number and offer two to three darker steps of the
  **same** hue with their values (`#4A3D6E` = 5.84:1) — do not silently turn the chosen surface value
  back. The border follows the share (rule of thumb share x 2.1), so that surface and frame match.
- **Besides the semantic colors, the Tailwind default palette sits in the source** — blue for
  "Vision", purple for "Reasoning", amber/red for hints in the skill dialog, emerald/orange for
  consumption bars. They follow no theme value and are partly so light that they are reported as
  "some texts are white and barely legible" (`text-emerald-400` = `#34D399` = 1.7:1 on white,
  `text-amber-300` = 1.4:1). **On "please search for other colors" do not only fix the named spots:**
  search the whole source for the color families
  (`grep -rho "\(text\|bg\|border\|stroke\|fill\)-\(red\|orange\|amber\|yellow\|green\|emerald\|teal\|cyan\|sky\|blue\|indigo\|violet\|purple\|fuchsia\|pink\|rose\)-[0-9]\{2,3\}" --include=*.tsx .`) and
  pull all families onto the theme family in one go — the classes are thinly seeded, the scope is
  small. With the **text** classes the icon strokes move along too (the icons inherit
  `currentColor`), so the SVG colors need not be searched individually. Mapping, blocks and measured
  values: `references/hardcoded-build-styles.md`.
- **Fixed hex values in components can only be caught via the style attribute — and React writes
  them serialized.** The consumption bar of the models page carries `#60a5fa` (cache read) and
  `#c084fc` (reasoning) as inline style; `[style*="#60a5fa"]` hits **none** of it, the attribute
  contains `background-color: rgb(96, 165, 250)`. Include both spellings in the selector and separate
  dot (`[style*=…].rounded-full`) from bar (`:not(.rounded-full)`), otherwise one of the two gets the
  wrong opacity.
- **Always compute text contrast with stacked background layers.** The obvious approximation "first
  ancestor with an opaque surface" overestimates the contrast: semi-transparent chips (`bg-…/10`)
  fall onto white there, and exactly the weak spots disappear from the finding. Mix all ancestor
  colors from the root down, then compute. For states that are not intended to be reached (scan
  result, empty lists), hang the component's color classes into the page as a probe element and read
  its `color` — that proves the rule without the state. Recipes:
  `references/roundness-and-custom-css.md`, section 5.
- **Reproduce reported mobile layout errors at mobile width — and measure your own fault first.**
  Mobile work; overlaps only arise at ~390 px (`Emulation.setDeviceMetricsOverride`). Whether your
  own CSS is the cause is clarified by a test **in the page**: find the injected `<style>` with your
  own customCSS, set `disabled = true`, measure again, re-enable — without a theme or config change.
  Overlaps are found by a rectangle intersection over all text nodes. If the finding is the same with
  and without your own CSS, it is app behavior: report it as such instead of as fixed (the `FILES:`
  label of the skill dialog overlaps the file list at 390 px by 11 px in both cases).
- **Tags/hub chips are `span[class*="font-compressed"]`** (67-68 per page) and carry both the retro
  display font and the size and spacing of the list: for a pill shape set all three (CSS in the
  recipe). Keep the font rule for `.font-compressed` separate from the title classes — the class
  hangs only on these tags.
- **Never derive fine shape judgments from an image description.** For millimeter questions the
  computed values and counts in the DOM are the proof (`getComputedStyle`, padding, radius, count);
  the image is only the illustration for the chat window: one description reported the same state
  once as "round" and once as "square", where the radius was measurably 0 or 15 px. Also judge shape
  details only with **frozen** decoration (`animationPlayState = 'paused'`), otherwise two different
  animation frames are compared.
