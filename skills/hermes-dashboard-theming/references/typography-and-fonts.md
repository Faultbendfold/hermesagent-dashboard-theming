# Typography in the dashboard theme

## What the shipped build actually reads

| Key | Effect |
|---|---|
| `typography.fontSans` | sets `--theme-font-sans`; `html`/`body` read it -> body text, inputs, button labels |
| `typography.fontMono` | `--theme-font-mono` (code, logs) |
| `typography.fontDisplay` | sets `--theme-font-display`, **read by nobody** -> has no effect |
| `typography.fontUrl` | is injected into the page as `<link rel="stylesheet">` (external fonts) |
| `baseSize`, `lineHeight`, `letterSpacing` | global typography |

Proof in the bundle (a pattern starting with `--` needs the double hyphen as protection, otherwise
the search tool reads it as an option):

```bash
cd /opt/hermes/hermes_cli/web_dist/assets
for f in *.css *.js; do n=$(grep -o -- 'theme-font-display' "$f" | wc -l); [ "$n" -gt 0 ] && echo "$f: $n"; done
grep -o -- '.\{80\}theme-font-display.\{80\}' index-*.css   # only the definition, no rule
```

## Headings: only via customCSS

Titles carry fixed classes in the source — `font-mondwest` (Mondwest, the pixel font) and
`font-expanded` (Rules Expanded). No theme field reaches them. Check:

```bash
grep -rn "<h1\|<h2\|<h3" /opt/hermes/web/src --include=*.tsx | head
grep -rno "font-mondwest\|font-expanded" /opt/hermes/web/src --include=*.tsx | wc -l
```

Override in the theme — put the titles on the **same** font as the surface. The intent is
explicitly a single font everywhere, and `fontDisplay` alone does not reach these classes:

```css
.font-mondwest, .font-expanded, h1, h2, h3 {
  font-family: var(--theme-font-sans) !important;
  letter-spacing: normal !important;   /* titles carry tracking-wider */
}
```

Only add a separate display stack here if that is explicitly wanted.

## Font choice

- **UI: a modern sans with intermediate weights** (Inter or a system stack). Reading and ebook fonts
  (Libron, the Readerly/Newsreader class) are unsuitable as a UI font: they lack 500/600, and
  intermediate weights are ubiquitous in buttons, tabs and tables — the browser computes them
  synthetically and that looks washed out.
- **One font for everything: Inter** (UI **and** titles). Serifs in the headings (Newsreader) have
  been tried and rejected — "only one font". Do not suggest it again.
- **Newsreader** (variable 400-700 plus italic) would be the Google Fonts counterpart of a book font
  like Libron, should one ever be needed. Other serifs in the picker: Spectral, Fraunces,
  Source Serif 4.
  The normal case here is a **single** family: `?family=Inter:wght@400;500;600;700&display=swap`.
  If two are needed after all, bundle them in one `<link>` request (two families, one request):

```
https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400..700;1,6..72,400..700&display=swap
```

  Before entering it, check that the address returns `@font-face`. Variable fonts need
  the axes in alphabetical order (`ital,opsz,wght`).

## Limits

- **The font picker in the menu only overrides `--theme-font-sans`/`--theme-font-display`** and
  writes `dashboard.font`. It does **not** reach the hard-coded classes of the headings.
- **Self-hosted fonts need a reachable address.** The dashboard only serves its
  own bundle (`web_dist`), there is no user static path. So place WOFF2 files on your own
  infrastructure (any web server you control) and point `fontUrl` at them. OFL
  permits embedding; use reserved names only unchanged.
- Always end the sans **and** display stack with system and generic families
  (`..., sans-serif`) so that a usable fallback applies without a network.
