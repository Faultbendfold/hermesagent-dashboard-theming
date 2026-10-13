#!/usr/bin/env python3
"""preview -- render a theme as a standalone HTML page you can open offline.

    python3 tools/preview.py themes/light-clean.yaml
    python3 tools/preview.py themes/*.yaml --out /tmp/preview.html --open

No install, no server, no Hermes: the markup is fixed and only the theme's own
tokens are substituted, so what you see is what the dashboard paints for those
variables. That makes it the fast loop for building a theme, before anything
lands in `$HERMES_HOME/dashboard-themes/`.

Every colour is resolved the way the dashboard resolves it (an override wins, a
missing one falls back to the palette), and the page ends with the measured
contrast summary -- the same maths `theme-check.py` uses, so a preview cannot
flatter a theme the linter would reject.
"""

import argparse
import os
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "hermes-dashboard-theming", "scripts"))

import theme_lib as t  # noqa: E402

BODY = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { __VARS__ }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.6 "__FONT__", system-ui, sans-serif; }
.shell { display: flex; min-height: 100vh; }
.side { width: 210px; background: var(--panel); border-right: 1px solid var(--border); padding: 18px 14px; }
.side .brand { font-weight: 600; margin-bottom: 18px; }
.side a { display: block; color: var(--mutedFg); text-decoration: none; padding: 6px 8px; border-radius: 8px; font-size: 14px; }
.side a.on { background: var(--muted); color: var(--ink); }
.main { flex: 1; padding: 22px 26px; }
.top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
h1 { font-size: 21px; margin: 0; }
.grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
.card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
.card h2 { font-size: 15px; margin: 0 0 4px; }
.card p { margin: 0 0 12px; color: var(--mutedFg); font-size: 13px; }
button { font: inherit; font-size: 13px; padding: 7px 15px; border: 0; border-radius: 10px;
         background: var(--primary); color: var(--primaryFg); }
.ghost { background: var(--muted); color: var(--ink); border: 1px solid var(--border); }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.badge { font-size: 12px; padding: 2px 10px; border-radius: 999px; background: var(--muted); color: var(--ink); }
.badge.ok { background: var(--success); color: var(--bg); }
.badge.warn { background: var(--warning); color: var(--bg); }
.badge.bad { background: var(--destructive); color: var(--card); }
.bars { display: flex; gap: 6px; align-items: flex-end; height: 64px; margin-top: 6px; }
.bars i { flex: 1; border-radius: 6px 6px 0 0; background: var(--ring); }
.term { margin-top: 16px; background: #0B0D10; color: #E6E8EC; border-radius: var(--radius);
        padding: 12px 14px; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px; }
.term b { color: #7FC9C9; font-weight: 500; }
table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
th { color: var(--mutedFg); font-weight: 500; }
.sum { margin-top: 14px; font-size: 13px; color: var(--mutedFg); }
.sum b { color: var(--ink); }
</style>
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand">__LABEL__</div>
    <a class="on" href="#">Chat</a><a href="#">Models</a><a href="#">Skills</a>
    <a href="#">Analytics</a><a href="#">Config</a>
  </aside>
  <main class="main">
    <div class="top">
      <h1>Models</h1>
      <div class="row"><span class="badge">__MODE__</span><button>New session</button></div>
    </div>
    <div class="grid">
      <section class="card">
        <h2>Active model</h2>
        <p>Card surface, muted text, primary action.</p>
        <div class="row"><button>Run</button><button class="ghost">Cancel</button></div>
      </section>
      <section class="card">
        <h2>Status</h2>
        <p>Semantic colours as chips.</p>
        <div class="row"><span class="badge ok">ok</span><span class="badge warn">warning</span>
        <span class="badge bad">failed</span></div>
      </section>
      <section class="card">
        <h2>Usage</h2>
        <p>Chart bars follow the ring colour.</p>
        <div class="bars">
          <i style="height:32%"></i><i style="height:58%"></i><i style="height:44%"></i>
          <i style="height:76%"></i><i style="height:61%"></i><i style="height:90%"></i>
        </div>
      </section>
    </div>
    <div class="term">$ <b>hermes</b> config get dashboard.theme<br>__NAME__</div>
    <table><thead><tr><th>pair</th><th>foreground</th><th>surface</th><th>ratio</th><th>need</th></tr></thead>
    <tbody>__ROWS__</tbody></table>
    <p class="sum">__SUMMARY__</p>
  </main>
</div>
</body>
</html>
"""


def resolve(theme):
    """Every token the mock uses, resolved like the dashboard resolves it."""
    canvas = t.layer_hex(theme, "background", "#FFFFFF")
    ink = t.layer_hex(theme, "midground", "#111827")
    card = t.ov(theme, "card", canvas)
    return {
        "bg": canvas, "ink": ink, "card": card,
        "panel": t.mix(canvas, ink, 0.035),
        "muted": t.ov(theme, "muted", t.mix(canvas, ink, 0.07)),
        "mutedFg": t.ov(theme, "mutedForeground", t.mix(ink, canvas, 0.4)),
        "primary": t.ov(theme, "primary", ink),
        "primaryFg": t.ov(theme, "primaryForeground", "#FFFFFF"),
        "border": t.ov(theme, "border", t.mix(canvas, ink, 0.15)),
        "ring": t.ov(theme, "ring", ink),
        "success": t.ov(theme, "success", "#15803D"),
        "warning": t.ov(theme, "warning", "#B54708"),
        "destructive": t.ov(theme, "destructive", "#B42318"),
    }


CHECKS = (
    ("body text on canvas", "ink", "bg", 4.5),
    ("text on card", "ink", "card", 4.5),
    ("muted text on muted", "mutedFg", "muted", 4.5),
    ("button label on primary", "primaryFg", "primary", 3.2),
    ("border on canvas", "border", "bg", 1.1),
)


def rows_html(c):
    out, ratios = [], []
    for label, fg_key, bg_key, need in CHECKS:
        fg, bg = c[fg_key], c[bg_key]
        r = t.ratio(fg, bg) if t.is_hex(fg) and t.is_hex(bg) else None
        ratios.append((label, r, need))
        mark = "" if r is None else ("ok" if r >= need else "LOW")
        out.append("<tr><td>%s</td><td><code>%s</code></td><td><code>%s</code></td>"
                   "<td>%s</td><td>%.1f %s</td></tr>"
                   % (label, fg, bg, "-" if r is None else "%.2f" % r, need, mark))
    return "\n".join(out), ratios


def render(theme):
    c = resolve(theme)
    name = theme.get("name") or "theme"
    label = theme.get("label") or name
    vars_css = " ".join("--%s: %s;" % (k, v) for k, v in c.items())
    vars_css += " --radius: %s;" % ((theme.get("layout") or {}).get("radius") or "1rem")
    rows, ratios = rows_html(c)
    need_all = [x for x in ratios if x[1] is not None]
    worst = min(need_all, key=lambda x: x[1] / x[2] - 1.0, default=None)
    failing = [x[0] for x in need_all if x[1] < x[2]]
    summary = ("All %d measured pairs meet their target." % len(need_all) if not failing
               else "Below target: %s." % ", ".join(failing))
    if worst:
        summary += " Tightest pair: %s at %.2f:1 (target %.1f)." % (worst[0], worst[1], worst[2])
    font = ((theme.get("typography") or {}).get("fontSans") or "system-ui").split(",")[0].strip("'\" ")
    mode = "dark" if t.lum(c["bg"]) <= 0.5 else "light"
    return (BODY
            .replace("__VARS__", vars_css)
            .replace("__TITLE__", "Preview -- %s" % label)
            .replace("__LABEL__", label)
            .replace("__NAME__", name)
            .replace("__MODE__", mode)
            .replace("__FONT__", font)
            .replace("__ROWS__", rows)
            .replace("__SUMMARY__", summary))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a theme as a standalone HTML preview.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", help="output file (default: preview-<first theme>.html)")
    ap.add_argument("--open", action="store_true", help="open the result in the browser")
    args = ap.parse_args(argv)

    pages = []
    for path in args.files:
        try:
            with open(path, encoding="utf-8") as fh:
                theme = t.parse_yaml(fh.read())
        except (OSError, t.YamlError) as exc:
            print("preview: %s: %s" % (path, exc), file=sys.stderr)
            return 2
        pages.append(render(theme))

    if len(pages) > 1:
        # one file per theme so each preview stays self-contained
        written = []
        for path, page, theme_name in zip(args.files, pages, [p.split("/")[-1][:-5] for p in args.files]):
            out = os.path.join(os.path.dirname(args.out) if args.out else os.getcwd(),
                               "preview-%s.html" % theme_name)
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(page)
            written.append(out)
    else:
        out = args.out or os.path.join(os.getcwd(), "preview-%s.html" % os.path.basename(args.files[0])[:-5])
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(pages[0])
        written = [out]

    for out in written:
        print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    if args.open and written:
        webbrowser.open("file://" + os.path.abspath(written[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
