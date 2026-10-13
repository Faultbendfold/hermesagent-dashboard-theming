#!/usr/bin/env python3
"""build-gallery -- render the themes in this repository into a static page.

Writes ``docs/index.html``: one self-contained page showing every theme in
``themes/`` with its swatches, a mock of its surfaces and the measured
contrast, so the repository can be browsed without installing Hermes. Also
copies ``tools/color-board.html`` to ``docs/color-board.html`` (GitHub Pages
serves only ``docs/``).

The theme data is embedded at build time: a page that fetched the YAML would
work over HTTP but not from ``file://``. Regenerate after touching a theme:

    python3 tools/build-gallery.py            # write docs/
    python3 tools/build-gallery.py --check    # exit 1 if docs/ is stale
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "hermes-dashboard-theming", "scripts"))

import theme_lib as t  # noqa: E402

sys.path.insert(0, HERE)
import preview  # noqa: E402  (the single-theme offline page, reused verbatim)

REPO = "https://github.com/Faultbendfold/hermesagent-dashboard-theming"


def load_themes():
    """Every themes/*.yaml, parsed. customCSS is replaced by its size: the page
    does not need 11 KiB of CSS per theme and the embedded JSON stays small."""
    out = []
    tdir = os.path.join(ROOT, "themes")
    for fname in sorted(os.listdir(tdir)):
        if not fname.endswith(".yaml"):
            continue
        with open(os.path.join(tdir, fname), encoding="utf-8") as fh:
            theme = t.parse_yaml(fh.read())
        css = theme.pop("customCSS", None) or ""
        theme["_file"] = fname
        theme["_cssBytes"] = len(css.encode("utf-8"))
        theme["_cssSeries"] = "--series-input-token" in css
        out.append(theme)
    return out


CSS = """
:root {
  --page: #0F1115; --panel: #171A21; --panel-2: #1F2430; --line: #2A2F3A;
  --ink: #E6E8EC; --ink-2: #9BA3AF; --accent: #7FC9C9;
  --ok: #5FA98A; --bad: #E0736B;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 20px 60px; background: var(--page); color: var(--ink);
  font: 15px/1.6 "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); }
header { max-width: 1100px; margin: 0 auto; padding: 44px 0 26px; }
h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: -0.02em; }
header p { margin: 0 0 6px; color: var(--ink-2); max-width: 74ch; }
main { max-width: 1100px; margin: 0 auto; display: grid; gap: 22px;
       grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); }
"""

CSS += """
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
        padding: 20px 20px 16px; }
.card h2 { margin: 0; font-size: 19px; }
.card .meta { color: var(--ink-2); font-size: 13px; margin: 2px 0 12px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 14px; }
.chip { font-size: 12px; padding: 3px 9px; border-radius: 999px;
        border: 1px solid var(--line); color: var(--ink-2); }
.chip.mode-light { color: #111827; background: #E6E8EC; border-color: #E6E8EC; }
.chip.mode-dark  { color: #E6E8EC; background: #111827; border-color: #2A2F3A; }
.chip.wcag-ok    { color: #0F1115; background: #5FA98A; border-color: #5FA98A; }
.chip.wcag-bad   { color: #0F1115; background: #E0736B; border-color: #E0736B; }
.plink { display: inline-block; margin-top: 10px; font-size: 13px; }
.mock { border-radius: 12px; padding: 14px; margin-bottom: 14px; }
.mock h3 { margin: 0 0 4px; font-size: 15px; }
.mock p { margin: 0 0 10px; font-size: 13px; }
.mock .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.mock button { font: inherit; font-size: 13px; padding: 6px 14px; border-radius: 10px;
               border: 0; cursor: default; }
.mock .badge { font-size: 12px; padding: 2px 9px; border-radius: 999px; }
.swatches { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 14px; }
.sw { width: 76px; }
.sw .box { height: 34px; border-radius: 8px; border: 1px solid var(--line); }
.sw .lbl { font-size: 10px; color: var(--ink-2); margin-top: 4px; word-break: break-all; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 5px 6px; border-bottom: 1px solid var(--line); }
th { color: var(--ink-2); font-weight: 500; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.pass { color: var(--ok); } .fail { color: var(--bad); }
code, pre { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; }
pre { background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px;
      padding: 10px 12px; overflow-x: auto; }
footer { max-width: 1100px; margin: 34px auto 0; color: var(--ink-2); font-size: 13px; }
"""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hermes dashboard themes</title>
<style>__CSS__</style>
</head>
<body>
<header>
  <h1>Hermes dashboard themes</h1>
  <p>Every theme in this repository, rendered from its YAML with the measured contrast. The values
     below are read out of <code>themes/*.yaml</code> by <code>tools/build-gallery.py</code> &mdash;
     nothing here is typed in by hand.</p>
  <p><a href="__REPO__">Repository</a> &middot; <a href="color-board.html">Colour board</a>
     &middot; <a href="__REPO__#readme">Install instructions</a></p>
</header>
<main id="themes"></main>
<footer>
  <p>Contrast is measured against the surface the colour actually sits on: text against the card,
  the button label against its fill, muted text against <code>muted</code>. Targets: 4.5:1 for text,
  3.2:1 for a button label. Tinted chips composite further &mdash; measure the real page for
  those (<code>references/contrast-checking.md</code> in the skill).</p>
</footer>
<script id="theme-data" type="application/json">__DATA__</script>
<script>
__JS__
</script>
</body>
</html>
"""


JS = r"""
const THEMES = JSON.parse(document.getElementById('theme-data').textContent);

function isHex(v) { return typeof v === 'string' && /^#[0-9a-fA-F]{6}$/.test(v.trim()); }
function rgb(h) { h = h.trim().slice(1); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); }
function lum(h) {
  const c = rgb(h).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function ratio(a, b) {
  if (!isHex(a) || !isHex(b)) return null;
  const la = lum(a), lb = lum(b), hi = Math.max(la, lb), lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}
function ov(th, k, dflt) {
  const v = (th.colorOverrides || {})[k];
  return isHex(v) ? v.trim() : dflt;
}
function layer(th, k, dflt) {
  const p = (th.palette || {})[k];
  if (typeof p === 'string') return isHex(p) ? p.trim() : dflt;
  if (p && typeof p === 'object') return isHex(p.hex) ? p.hex.trim() : dflt;
  return dflt;
}
"""

JS += r"""
function mock(canvas, card, ink, muted, mutedInk, primary, primaryInk, border) {
  return `<div class="mock" style="background:${canvas};border:1px solid ${border}">
    <div style="background:${card};border:1px solid ${border};border-radius:10px;padding:12px">
      <h3 style="color:${ink}">Models</h3>
      <p style="color:${mutedInk}">Secondary text on the card surface.</p>
      <div class="row">
        <button style="background:${primary};color:${primaryInk}">Run</button>
        <span class="badge" style="background:${muted};color:${ink}">badge</span>
        <span class="badge" style="background:${card};color:${mutedInk};border:1px solid ${border}">bordered</span>
      </div>
    </div>
  </div>`;
}

function swatches(th) {
  const items = [];
  for (const k of ['background', 'midground', 'foreground']) {
    const v = layer(th, k, null);
    if (v) items.push([k, v]);
  }
  for (const [k, v] of Object.entries(th.colorOverrides || {})) {
    if (isHex(v)) items.push([k, v.trim()]);
  }
  return items.map(([k, v]) =>
    `<div class="sw"><div class="box" style="background:${v}"></div>` +
    `<div class="lbl">${esc(k.replace(/([a-z])([A-Z])/g, '$1\u200b$2'))}<br>${esc(v)}</div></div>`).join('');
}
"""

JS += r"""
function row(label, fg, bg, target) {
  const r = ratio(fg, bg);
  const txt = r === null ? '&mdash;' : r.toFixed(2) + ':1';
  const cls = r === null ? '' : (r >= target ? 'pass' : 'fail');
  return `<tr><td>${esc(label)}</td><td><code>${esc(fg || '')}</code></td>` +
         `<td><code>${esc(bg || '')}</code></td>` +
         `<td class="num ${cls}">${txt}</td><td class="num">${target}</td></tr>`;
}

function pairsOf(th) {
  const canvas = layer(th, 'background', '#FFFFFF');
  const card = ov(th, 'card', canvas);
  const ink = ov(th, 'cardForeground', layer(th, 'midground', '#111827'));
  const muted = ov(th, 'muted', canvas);
  return [
    ['body text on canvas', layer(th, 'midground', ink), canvas, 4.5],
    ['text on card', ink, card, 4.5],
    ['button label on primary', ov(th, 'primaryForeground', '#FFFFFF'), ov(th, 'primary', ink), 3.2],
    ['muted text on muted', ov(th, 'mutedForeground', ink), muted, 4.5],
    ['border on canvas', ov(th, 'border', canvas), canvas, 1.1],
  ];
}

function wcagBadge(th) {
  const measured = pairsOf(th)
    .map(p => ({ r: ratio(p[1], p[2]), need: p[3] }))
    .filter(x => x.r !== null);
  if (!measured.length) return '';
  const text = measured.filter(x => x.need >= 4.5);
  const graphic = measured.filter(x => x.need < 4.5);
  if (text.some(x => x.r < x.need) || graphic.some(x => x.r < x.need)) {
    const below = measured.filter(x => x.r < x.need).length;
    return `<span class="chip wcag-bad">${below} pair(s) below target</span>`;
  }
  const worstText = text.length ? Math.min(...text.map(x => x.r)) : null;
  const level = worstText === null ? null : (worstText >= 7 ? 'AAA' : (worstText >= 4.5 ? 'AA' : 'AA-large'));
  return (level ? `<span class="chip wcag-ok">text contrast ${level}</span>` : '')
       + `<span class="chip wcag-ok">all pairs pass</span>`;
}

function contrastTable(th) {
  return `<table><thead><tr><th>pair</th><th>foreground</th><th>surface</th>` +
    `<th class="num">ratio</th><th class="num">target</th></tr></thead><tbody>` +
    pairsOf(th).map(p => row(p[0], p[1], p[2], p[3])).join('') +
    `</tbody></table>`;
}
"""

JS += r"""
function render() {
  document.getElementById('themes').innerHTML = THEMES.map(th => {
    const canvas = layer(th, 'background', '#FFFFFF');
    const card = ov(th, 'card', canvas);
    const ink = ov(th, 'cardForeground', layer(th, 'midground', '#111827'));
    const muted = ov(th, 'muted', canvas);
    const mutedInk = ov(th, 'mutedForeground', ink);
    const primary = ov(th, 'primary', ink);
    const primaryInk = ov(th, 'primaryForeground', '#FFFFFF');
    const border = ov(th, 'border', canvas);
    const mode = lum(canvas) > 0.5 ? 'light' : 'dark';
    const kib = (th._cssBytes / 1024).toFixed(1);
    return `<section class="card">
      <h2>${esc(th.label || th.name)}</h2>
      <div class="meta"><code>${esc(th.name)}</code> &middot; ${esc(th._file)}</div>
      <p>${esc(th.description || '')}</p>
      <div class="chips">
        <span class="chip mode-${mode}">${mode}</span>
        <span class="chip">canvas ${esc(canvas)}</span>
        <span class="chip">customCSS ${kib} KiB</span>
        ${th._cssSeries ? '<span class="chip">series via customCSS</span>' : ''}
        ${wcagBadge(th)}
      </div>
      ${mock(canvas, card, ink, muted, mutedInk, primary, primaryInk, border)}
      <div class="swatches">${swatches(th)}</div>
      ${contrastTable(th)}
      <pre>hermes config set dashboard.theme ${esc(th.name)}</pre>
      <a class="plink" href="preview-${esc(th.name)}.html">open the full-size preview &rarr;</a>
    </section>`;
  }).join('');
}

render();
"""


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def build():
    themes = load_themes()
    data = json.dumps(themes, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (PAGE.replace("__CSS__", CSS)
                .replace("__REPO__", REPO)
                .replace("__DATA__", data)
                .replace("__JS__", JS))
    with open(os.path.join(ROOT, "tools", "color-board.html"), encoding="utf-8") as fh:
        board = fh.read()
    files = {"index.html": html, "color-board.html": board}
    # one standalone preview page per theme, written by the same renderer the
    # command line tool uses -- so the gallery and `preview.py` cannot drift
    for theme in themes:
        name = theme.get("name")
        if name:
            files["preview-%s.html" % name] = preview.render(theme)
    return files


def main():
    ap = argparse.ArgumentParser(description="Render themes/ into a static gallery page.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if docs/ differs from what would be generated (for CI)")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"),
                    help="output directory (default: <repo>/docs)")
    args = ap.parse_args()

    files = build()
    if args.check:
        stale = [n for n, c in files.items() if read(os.path.join(args.out, n)) != c]
        if stale:
            print("docs/ is stale: %s" % ", ".join(sorted(stale)))
            print("run: python3 tools/build-gallery.py")
            return 1
        print("docs/ is up to date")
        return 0

    os.makedirs(args.out, exist_ok=True)
    for name, content in files.items():
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print("wrote %s (%d bytes)" % (path, len(content.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
