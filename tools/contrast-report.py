#!/usr/bin/env python3
"""contrast-report -- every text/surface pair of a theme, measured and labelled.

`theme-check.py` reports the pairs that are *wrong*; this prints the whole
matrix, which is what a pull request wants to see:

    python3 tools/contrast-report.py themes/*.yaml
    python3 tools/contrast-report.py --format markdown themes/light-clean.yaml
    python3 tools/contrast-report.py --format json themes/*.yaml

Each pair names the surface the colour really sits on, so a theme that leans on
translucent chips is reported honestly rather than flattered. A value that is
not set is derived the way the dashboard derives it, and marked `(derived)`.

Targets: body text 4.5 (WCAG AA), large text/graphics 3.0, AAA 7.0 for text.

Exit code: 0 if every pair meets its target, 1 otherwise (use --no-fail to
report without failing).
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "hermes-dashboard-theming", "scripts"))

import theme_lib as t  # noqa: E402

TEXT = 4.5
GRAPHIC = 3.0
AAA = 7.0


def surfaces(theme):
    """Resolve every surface the way the dashboard resolves it."""
    canvas = t.layer_hex(theme, "background", "#FFFFFF")
    ink = t.layer_hex(theme, "midground", "#111827")
    card = t.ov(theme, "card", canvas)
    return {
        "canvas": canvas, "ink": ink,
        "card": card,
        "cardFg": t.ov(theme, "cardForeground", ink),
        "popover": t.ov(theme, "popover", card),
        "popoverFg": t.ov(theme, "popoverForeground", t.ov(theme, "cardForeground", ink)),
        "primary": t.ov(theme, "primary", ink),
        "primaryFg": t.ov(theme, "primaryForeground", "#FFFFFF"),
        "secondary": t.ov(theme, "secondary", t.mix(canvas, ink, 0.07)),
        "secondaryFg": t.ov(theme, "secondaryForeground", ink),
        "muted": t.ov(theme, "muted", t.mix(canvas, ink, 0.07)),
        "mutedFg": t.ov(theme, "mutedForeground", t.mix(ink, canvas, 0.4)),
        "accent": t.ov(theme, "accent", t.mix(canvas, ink, 0.07)),
        "accentFg": t.ov(theme, "accentForeground", ink),
        "destructive": t.ov(theme, "destructive", "#B42318"),
        "destructiveFg": t.ov(theme, "destructiveForeground", "#FFFFFF"),
        "success": t.ov(theme, "success", "#15803D"),
        "warning": t.ov(theme, "warning", "#B54708"),
        "border": t.ov(theme, "border", t.mix(canvas, ink, 0.15)),
        "ring": t.ov(theme, "ring", t.ov(theme, "primary", ink)),
    }


def pairs(theme):
    s = surfaces(theme)
    given = lambda k: t.ov(theme, k) is not None  # noqa: E731
    out = [
        ("body text on canvas", s["ink"], s["canvas"], TEXT, given("card")),
        ("text on card", s["cardFg"], s["card"], TEXT, given("cardForeground")),
        ("text on popover", s["popoverFg"], s["popover"], TEXT, given("popoverForeground")),
        ("text on secondary", s["secondaryFg"], s["secondary"], TEXT, given("secondaryForeground")),
        ("muted text on muted", s["mutedFg"], s["muted"], TEXT, given("mutedForeground")),
        ("text on accent", s["accentFg"], s["accent"], TEXT, given("accentForeground")),
        ("button label on primary", s["primaryFg"], s["primary"], GRAPHIC, given("primaryForeground")),
        ("label on destructive", s["destructiveFg"], s["destructive"], TEXT, given("destructiveForeground")),
        ("success on card", s["success"], s["card"], TEXT, given("success")),
        ("warning on card", s["warning"], s["card"], TEXT, given("warning")),
        ("destructive on card", s["destructive"], s["card"], TEXT, given("destructive")),
        ("border on canvas", s["border"], s["canvas"], 1.1, given("border")),
        ("focus ring on canvas", s["ring"], s["canvas"], GRAPHIC, given("ring")),
    ]
    return [(label, fg, bg, need, "set" if explicit else "derived")
            for label, fg, bg, need, explicit in out]


def measure(theme):
    name = theme.get("name") or "?"
    rows = []
    for label, fg, bg, need, src in pairs(theme):
        if t.is_hex(fg) and t.is_hex(bg):
            r = t.ratio(t.norm_hex(fg), t.norm_hex(bg))
            ok = r >= need
            rows.append({"pair": label, "fg": fg, "bg": bg, "ratio": round(r, 2),
                         "need": need, "ok": ok, "source": src})
        else:
            rows.append({"pair": label, "fg": fg, "bg": bg, "ratio": None,
                         "need": need, "ok": None, "source": src})
    canvas = t.layer_hex(theme, "background", "#FFFFFF")
    mode = "dark" if t.lum(canvas) <= 0.5 else "light"
    return {"name": name, "mode": mode, "canvas": canvas, "rows": rows}


def label_of(ratio, need):
    """WCAG-ish label, read against the target the pair actually has."""
    if ratio is None:
        return "-"
    if ratio < need:
        return "fail"
    if need >= TEXT:
        return "AAA" if ratio >= AAA else "AA"
    if need >= GRAPHIC:
        return "AA-large"
    return "separation"


def as_text(reports):
    L = []
    for path, rep in reports:
        fails = [r for r in rep["rows"] if r["ok"] is False]
        L.append("%s   mode %s   canvas %s   (%s)"
                 % (rep["name"], rep["mode"], rep["canvas"], os.path.basename(path)))
        L.append("  %-24s %-9s %-10s %6s %6s  %s" % ("pair", "fg", "surface", "ratio", "need", "wcag"))
        for r in rep["rows"]:
            L.append("  %-24s %-9s %-10s %6s %6s  %s%s"
                     % (r["pair"], r["fg"], r["bg"],
                        "-" if r["ratio"] is None else "%.2f" % r["ratio"],
                        "%.1f" % r["need"], label_of(r["ratio"], r["need"]),
                        "" if r["ok"] is not False else "   <-- below target"))
        L.append("  %d pairs, %d below target" % (len(rep["rows"]), len(fails)))
        L.append("")
    return "\n".join(L)


def as_markdown(reports):
    L = []
    for path, rep in reports:
        L.append("### `%s` -- %s, canvas `%s`" % (rep["name"], rep["mode"], rep["canvas"]))
        L.append("")
        L.append("| pair | foreground | surface | ratio | need | WCAG | |")
        L.append("|---|---|---|---|---|---|---|")
        for r in rep["rows"]:
            L.append("| %s | `%s` | `%s` | %s | %.1f | %s | %s |"
                     % (r["pair"], r["fg"], r["bg"],
                        "-" if r["ratio"] is None else "%.2f" % r["ratio"],
                        r["need"], label_of(r["ratio"], r["need"]),
                        "" if r["ok"] is not False else "**below target**"))
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measured contrast matrix for dashboard themes.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    ap.add_argument("--no-fail", action="store_true", help="report without a failing exit code")
    args = ap.parse_args(argv)

    reports = []
    for path in args.files:
        try:
            with open(path, encoding="utf-8") as fh:
                theme = t.parse_yaml(fh.read())
        except (OSError, t.YamlError) as exc:
            print("contrast-report: %s: %s" % (path, exc), file=sys.stderr)
            return 2
        reports.append((path, measure(theme)))

    if args.format == "json":
        print(json.dumps({"themes": [dict(rep, path=p) for p, rep in reports]}, indent=2))
    elif args.format == "markdown":
        print(as_markdown(reports))
    else:
        print(as_text(reports))

    failing = [p for p, rep in reports if any(r["ok"] is False for r in rep["rows"])]
    if failing and not args.no_fail:
        print("contrast-report: %d theme(s) with a pair below target: %s"
              % (len(failing), ", ".join(os.path.basename(p) for p in failing)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
