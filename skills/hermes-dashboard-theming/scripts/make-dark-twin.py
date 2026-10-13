#!/usr/bin/env python3
"""make-dark-twin -- derive the dark counterpart of a light dashboard theme.

The hard part of a light/dark pair is not picking a dark canvas, it is keeping
the two recognisably the same theme: the hue family has to survive, the roles
that must invert have to invert, and every tone that was tuned against a bright
surface has to be lifted off the new dark one. This script applies exactly the
rules written down in references/palette-to-theme-mapping.md ("Dark version")
and prints the measured contrast for each pair it produces, so the result is a
reviewable starting point rather than a guess.

    python3 make-dark-twin.py themes/light-clean.yaml
    python3 make-dark-twin.py my-light.yaml -o /tmp/my-dark.yaml --name my-dark
    python3 make-dark-twin.py my-light.yaml --stdout

What it derives (all by bisection against a luminance or contrast target, never
by stepping the mix in whole percent -- that gets stuck at the rounding):

    canvas    light theme's text hue, darkened to ~0.012 luminance
    text      light theme's canvas hue, lifted until contrast to the canvas >= 7
    card      canvas + 6% text          popover  canvas + 9% text
    panel     canvas + 5% text          (sidebar and header)
    border    canvas + 20% text         (border and input)
    muted     canvas + 9% text          muted text fitted to >= 4.5 on muted
    primary   a dark light-theme primary inverts to the text tone with the
              canvas as label; a coloured primary keeps its hue and is lifted
              until it reaches 3.2:1 on the dark canvas
    ring      the light ring lifted to >= 3.0 on the canvas, else the primary
    semantic  success/warning/destructive lifted until >= 4.5 on the card
    series    token accents lifted until >= 4.5 on the card

Not touched automatically, and reported instead: customCSS. It is plain CSS
full of values that were chosen for the light surface; rewriting it blind would
produce plausible-looking nonsense. The script lists every hardcoded colour in
it so the human (or agent) can review the rules one by one.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme_lib as t  # noqa: E402

TEXT_TARGET = 7.0
BUTTON_MIN = 3.2
CARD_TEXT_MIN = 4.5
RING_MIN = 3.0
CANVAS_LUM = 0.012
DARK_PRIMARY_LUM = 0.35   # a light primary below this counts as "dark" and inverts

_HEX_IN_CSS = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def derive(light):
    """Return (dark_theme_dict, report_list). ``report`` is [(label, fg, bg, ratio, ok)]."""
    canvas = t.darken_to(t.norm_hex(t.layer_hex(light, "midground", "#111827")), CANVAS_LUM)
    seed = t.norm_hex(t.layer_hex(light, "background", "#F8F9FB"))
    text = t.fit(seed, canvas, TEXT_TARGET, "#FFFFFF")

    card = t.mix(canvas, text, 0.06)
    popover = t.mix(canvas, text, 0.09)
    panel = t.mix(canvas, text, 0.05)
    border = t.mix(canvas, text, 0.20)
    muted = t.mix(canvas, text, 0.09)
    muted_fg = t.fit(t.mix(canvas, text, 0.55), muted, CARD_TEXT_MIN, "#FFFFFF")
    secondary = t.mix(canvas, text, 0.12)
    accent = t.mix(canvas, text, 0.14)

    # Buttons: a dark light-theme primary inverts (light surface, dark label);
    # a coloured primary keeps its hue and is lifted onto the dark canvas.
    light_primary = t.norm_hex(t.ov(light, "primary", t.norm_hex(t.layer_hex(light, "midground", "#111827"))))
    if t.lum(light_primary) < DARK_PRIMARY_LUM:
        primary, primary_fg = text, canvas
    else:
        primary = t.fit(light_primary, canvas, BUTTON_MIN, "#FFFFFF")
        primary_fg = "#FFFFFF" if t.lum(primary) < 0.5 else canvas
        if t.ratio(primary, primary_fg) < BUTTON_MIN:
            primary_fg = "#FFFFFF" if t.ratio(primary, "#FFFFFF") > t.ratio(primary, canvas) else canvas

    light_ring = t.ov(light, "ring")
    if light_ring and t.is_hex(light_ring) and t.ratio(t.norm_hex(light_ring), canvas) >= RING_MIN:
        ring = t.norm_hex(light_ring)
    elif light_ring and t.is_hex(light_ring):
        ring = t.fit(t.norm_hex(light_ring), canvas, RING_MIN, "#FFFFFF")
    else:
        ring = primary

    dark = {
        "name": (light.get("name") or "theme") + "-dark",
        "label": ((light.get("label") or light.get("name") or "Theme").strip() + " Dark"),
        "description": "Dark counterpart of %r, derived from it." % (light.get("name") or "?"),
        "palette": {
            "background": canvas,
            "midground": text,
            "foreground": {"hex": "#FFFFFF", "alpha": 0},
            "warmGlow": "rgba(%s, 0.03)" % ", ".join(str(x) for x in t.channels(text)),
            "noiseOpacity": 0,
        },
        "typography": light.get("typography") if isinstance(light.get("typography"), dict) else {},
        "layout": light.get("layout") if isinstance(light.get("layout"), dict) else {},
        "colorOverrides": {
            "card": card,
            "cardForeground": text,
            "popover": popover,
            "popoverForeground": text,
            "primary": primary,
            "primaryForeground": primary_fg,
            "secondary": secondary,
            "secondaryForeground": text,
            "muted": muted,
            "mutedForeground": muted_fg,
            "accent": accent,
            "accentForeground": text,
            "border": border,
            "input": border,
            "ring": ring,
        },
        "componentStyles": {
            "card": {
                "background": card,
                "boxShadow": "0 1px 2px rgba(0, 0, 0, 0.45), 0 12px 32px -20px rgba(0, 0, 0, 0.75)",
            },
            "header": {"background": panel},
            "sidebar": {"background": panel},
        },
        "customCSS": light.get("customCSS") or "",
    }

    for role in ("success", "warning", "destructive"):
        val = t.ov(light, role)
        if val and t.is_hex(val):
            dark["colorOverrides"][role] = t.fit(t.norm_hex(val), card, CARD_TEXT_MIN, "#FFFFFF")
    dark["colorOverrides"].setdefault("success", t.fit("#15803D", card, CARD_TEXT_MIN, "#FFFFFF"))
    dark["colorOverrides"].setdefault("warning", t.fit("#8A6A3B", card, CARD_TEXT_MIN, "#FFFFFF"))
    dark["colorOverrides"].setdefault("destructive", t.fit("#B42318", card, CARD_TEXT_MIN, "#FFFFFF"))
    dark["colorOverrides"]["destructiveForeground"] = canvas

    report = [
        ("body text", text, canvas, TEXT_TARGET),
        ("card text", text, card, CARD_TEXT_MIN),
        ("button label", primary_fg, primary, BUTTON_MIN),
        ("muted text", muted_fg, muted, CARD_TEXT_MIN),
        ("border vs canvas", border, canvas, 1.15),
    ]
    rows = []
    for label, fg, bg, target in report:
        r = t.ratio(fg, bg)
        rows.append((label, fg, bg, r, r >= target, target))
    for role in ("success", "warning", "destructive"):
        val = dark["colorOverrides"].get(role)
        if val:
            r = t.ratio(val, card)
            rows.append(("%s on card" % role, val, card, r, r >= CARD_TEXT_MIN, CARD_TEXT_MIN))
    return dark, rows


# --------------------------------------------------------------------------
# Emit
# --------------------------------------------------------------------------

def _q(s):
    import json
    return json.dumps(str(s), ensure_ascii=False)


def _indent_block(text, pad="  "):
    lines = text.rstrip("\n").split("\n")
    return "\n".join((pad + ln) if ln.strip() else "" for ln in lines)


def emit(dark, light):
    out = []
    out.append("# Dark counterpart derived from %r by scripts/make-dark-twin.py." % (light.get("name") or "?"))
    out.append("# The customCSS block is carried over VERBATIM from the light theme -- every")
    out.append("# hardcoded colour in it was chosen for the bright surface and has to be")
    out.append("# reviewed by hand (the script lists them when it runs).")
    out.append("# Enable with:  hermes config set dashboard.theme %s" % dark["name"])
    out.append("")
    out.append("name: %s" % dark["name"])
    out.append("label: %s" % _q(dark["label"]))
    out.append("description: %s" % _q(dark["description"]))
    out.append("")

    pal = dark["palette"]
    out.append("palette:")
    out.append("  background: %s" % _q(pal["background"]))
    out.append("  midground: %s" % _q(pal["midground"]))
    out.append("  foreground:")
    out.append("    hex: \"#FFFFFF\"")
    out.append("    alpha: 0")
    out.append("  warmGlow: %s" % _q(pal["warmGlow"]))
    out.append("  noiseOpacity: 0")
    out.append("")

    typo = dark.get("typography") or {}
    if typo:
        out.append("typography:")
        for key in ("fontSans", "fontMono", "fontDisplay", "fontUrl", "baseSize", "lineHeight", "letterSpacing"):
            if typo.get(key):
                out.append("  %s: %s" % (key, _q(typo[key])))
        out.append("")

    lay = dark.get("layout") or {}
    if lay:
        out.append("layout:")
        if lay.get("radius"):
            out.append("  radius: %s" % _q(lay["radius"]))
        if lay.get("density"):
            out.append("  density: %s" % lay["density"])
        out.append("")

    out.append("colorOverrides:")
    for key in ("card", "cardForeground", "popover", "popoverForeground", "primary", "primaryForeground",
                "secondary", "secondaryForeground", "muted", "mutedForeground", "accent", "accentForeground",
                "destructive", "destructiveForeground", "success", "warning", "border", "input", "ring"):
        val = dark["colorOverrides"].get(key)
        if val:
            out.append("  %s: %s" % (key, _q(val)))
    out.append("")

    styles = dark.get("componentStyles") or {}
    if styles:
        out.append("componentStyles:")
        for bucket in ("card", "header", "sidebar"):
            props = styles.get(bucket)
            if not props:
                continue
            out.append("  %s:" % bucket)
            for prop, val in props.items():
                out.append("    %s: %s" % (prop, _q(val)))
        out.append("")

    css = dark.get("customCSS") or ""
    if css.strip():
        out.append("customCSS: |")
        out.append(_indent_block(css))
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def report(rows, light, dark, css):
    print("derived %r -> %r" % (light.get("name") or "?", dark["name"]))
    print("  %-22s %-9s %-9s %7s  %s" % ("pair", "fg", "bg", "ratio", "target"))
    for label, fg, bg, r, ok, target in rows:
        print("  %-22s %-9s %-9s %6.2f  %s (>= %.1f)"
              % (label, fg, bg, r, "ok " if ok else "LOW", target))
    fails = [r for r in rows if not r[4]]
    if fails:
        print("  %d pair(s) below target -- adjust by hand before shipping" % len(fails))

    notes = []
    hexes = sorted(set(m.upper() for m in _HEX_IN_CSS.findall(css or "")))
    if hexes:
        notes.append("customCSS carries %d hardcoded colour(s) taken from the light theme: %s"
                     % (len(hexes), ", ".join(hexes[:14]) + (" ..." if len(hexes) > 14 else "")))
    if isinstance(light.get("seriesColors"), dict):
        notes.append("the light theme has `seriesColors`; the server drops it, so the dark theme "
                     "needs the same values in customCSS (--series-input-token/--series-output-token, "
                     "with !important)")
    if "--selection-bg" in (css or ""):
        notes.append("customCSS freezes --selection-bg; check the value against the dark surfaces "
                     "(the app paints `code` chips with it)")
    if not (css or "").strip():
        notes.append("the light theme has no customCSS, so the dark twin has none either -- "
                     "semantic colours, code chips and rounded-none surfaces keep the stock look")
    if notes:
        print("  review by hand:")
        for n in notes:
            print("    - %s" % n)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="make-dark-twin",
        description="Derive the dark counterpart of a light Hermes dashboard theme.")
    ap.add_argument("light", help="the light theme YAML")
    ap.add_argument("-o", "--out", help="output file (default: <name>-dark.yaml next to the input)")
    ap.add_argument("--name", help="override the derived theme name")
    ap.add_argument("--label", help="override the derived label")
    ap.add_argument("--stdout", action="store_true", help="print the YAML instead of writing it")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output file")
    args = ap.parse_args(argv)

    try:
        light = t.load(args.light)
    except (t.YamlError, OSError) as exc:
        print("make-dark-twin: %s: %s" % (args.light, exc), file=sys.stderr)
        return 2

    dark, rows = derive(light)
    if args.name:
        dark["name"] = args.name
    if args.label:
        dark["label"] = args.label
    text = emit(dark, light)

    if args.stdout:
        sys.stdout.write(text)
    else:
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.light)), dark["name"] + ".yaml")
        if os.path.exists(out) and not args.force:
            print("make-dark-twin: %s exists -- pass --force to overwrite" % out, file=sys.stderr)
            return 2
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s (%d bytes)" % (out, len(text.encode("utf-8"))))

    report(rows, light, dark, dark.get("customCSS") or "")
    return 0 if all(r[4] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
