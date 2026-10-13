#!/usr/bin/env python3
"""theme-check -- lint a Hermes dashboard theme before you trust it.

A theme YAML fails in ways that never produce an error message: the server
silently drops what it does not know, the built bundle ignores several fields
the schema still accepts, and a colour that is fine on paper can be unreadable
on the surface it actually sits on. This tool turns all of that into a list.

    python3 theme-check.py themes/light-clean.yaml
    python3 theme-check.py --live --hermes /opt/hermes themes/*.yaml
    python3 theme-check.py --json my-theme.yaml

What it checks (E = error, W = warning, I = note)
    E  name missing            the theme is dropped entirely
    E  unknown colorOverrides  silently discarded by the server
    E  unknown style bucket    silently discarded by the server
    E  customCSS over 32 KiB   clipped (``_THEME_CUSTOM_CSS_MAX``)
    W  seriesColors            accepted but never reaches the surface
    W  dead style buckets      badge/page/progress/backdrop/footer: nothing reads them
    W  dead style properties   e.g. a colour on ``tab`` (only clip-path is read)
    W  contrast below target   text < 4.5, button label < 3.2, muted text < 4.5
    W  builtin name reuse      a user theme cannot shadow a builtin theme
    I  hardcoded hex in CSS    must be reviewed by hand for the other mode
    I  fontDisplay set         no effect in the shipped build
    I  --live drift            mirror vs installed Hermes constants

Exit code: 0 = clean, 1 = findings (with --strict: any warning counts),
2 = the file could not be parsed. Findings are printed grouped by level; the
JSON form (``--json``) is stable enough to gate a CI job on it.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme_lib as t  # noqa: E402

# The two series variables the client reads; the theme has no other way to set them.
_SERIES_VARS = {"--series-input-token", "--series-output-token"}

LEVELS = ("error", "warn", "info")
LEVEL_TAG = {"error": "ERROR", "warn": "WARN", "info": "NOTE"}

# Text and graphics targets used by this repository (see references/).
TEXT_MIN = 4.5        # WCAG AA for body text; the skill aims at 7
TEXT_TARGET = 7.0
BUTTON_MIN = 3.2
MUTED_MIN = 4.5
CSS_WARN_AT = 24 * 1024

_HEX_IN_CSS = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_SERIES_VARS = ("--series-input-token", "--series-output-token")


class Findings:
    """Collects findings and renders them."""

    def __init__(self):
        self.items = []

    def add(self, level, code, message):
        self.items.append({"level": level, "code": code, "message": message})

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)

    def worst(self):
        for level in LEVELS:
            if self.count(level):
                return level
        return None

    def has_errors(self):
        return self.count("error") > 0


# --------------------------------------------------------------------------
# Structure: name, palette, overrides, styles, typography, layout
# --------------------------------------------------------------------------

def check_structure(theme, f):
    name = theme.get("name")
    if not isinstance(name, str) or not name.strip():
        f.add("error", "name-missing",
              "no usable `name:` -- the server skips the file entirely "
              "(the theme never appears in the picker)")
    else:
        if name in t.BUILTIN_THEME_NAMES:
            f.add("warn", "name-builtin",
                  "name %r equals a builtin theme; a user theme cannot shadow a builtin, "
                  "so `hermes config set dashboard.theme %s` still shows the stock look" % (name, name))
        if name != name.strip() or " " in name or name.lower() != name:
            f.add("info", "name-shape",
                  "name %r is unusual; use a lower-case slug (the theme directory is keyed by it)" % name)
    for key in ("label", "description"):
        if not (isinstance(theme.get(key), str) and theme[key].strip()):
            f.add("info", "meta-%s" % key,
                  "no `%s:` -- the picker falls back to the name" % key)

    known = t.KNOWN_TOP_LEVEL
    for key in theme:
        if key not in known:
            f.add("warn", "unknown-top-level",
                  "unknown top-level key %r -- the server ignores it" % key)
        elif key in t.DROPPED_TOP_LEVEL:
            css = theme.get("customCSS") if isinstance(theme.get("customCSS"), str) else ""
            handled = (key == "seriesColors"
                       and "--series-input-token" in css and "--series-output-token" in css)
            if handled:
                f.add("info", "dropped-%s" % key,
                      "`%s` does not reach the surface, but customCSS already carries "
                      "`--series-input-token`/`--series-output-token` -- keep the two in sync" % key)
            else:
                f.add("warn", "dropped-%s" % key,
                      "`%s` is accepted but dropped before it reaches the surface: %s"
                      % (key, t.DROPPED_TOP_LEVEL[key]))

    pal = theme.get("palette") if isinstance(theme.get("palette"), dict) else {}
    if not pal and not isinstance(theme.get("colors"), dict):
        f.add("error", "palette-missing", "no `palette:` block -- the whole first frame is uncontrolled")
    if not t.is_hex(t.layer_hex(theme, "background")):
        f.add("warn", "palette-background",
              "`palette.background` missing or not a hex colour -- falls back to the builtin "
              "dark teal (#041c1c); a light theme will flash dark on load")
    if not t.is_hex(t.layer_hex(theme, "midground")):
        f.add("warn", "palette-midground",
              "`palette.midground` missing or not a hex colour -- falls back to #ffe6cb")
    if t.layer_alpha(theme, "foreground", 0.0) not in (0, 0.0):
        f.add("info", "palette-foreground-alpha",
              "`palette.foreground.alpha` is not 0 -- that layer is an overlay, a non-zero "
              "alpha tints the whole surface")
    for extra, note in (("noiseOpacity", "grain/noise overlay"), ("warmGlow", "warm glow overlay")):
        val = pal.get(extra, theme.get(extra))
        if val in (None, "", "0", 0, "0.0", 0.0):
            continue
        if extra == "warmGlow":
            m = re.search(r"([0-9]*\.?[0-9]+)\s*\)\s*$", str(val))
            if m and float(m.group(1)) <= 0.05:  # a 3% glow is not a visible retro element
                continue
        f.add("info", "retro-%s" % extra, "`%s` is active (%r) -- the %s is a retro element" % (extra, val, note))

    check_overrides(theme, f)
    check_styles(theme, f)
    check_typography(theme, f)
    check_layout(theme, f)


def check_overrides(theme, f):
    src = theme.get("colorOverrides")
    if src is None:
        f.add("info", "overrides-none",
              "no `colorOverrides:` -- every colour is derived from the three palette layers")
        return
    if not isinstance(src, dict):
        f.add("error", "overrides-type", "`colorOverrides:` is not a mapping")
        return
    for key, val in src.items():
        if key not in t.OVERRIDE_KEYS:
            f.add("error", "override-unknown",
                  "`colorOverrides.%s` is not one of the 19 permitted keys -- the server "
                  "discards it silently (permitted: %s)" % (key, ", ".join(sorted(t.OVERRIDE_KEYS))))
            continue
        if not (isinstance(val, str) and val.strip()):
            f.add("error", "override-empty", "`colorOverrides.%s` is empty/not a string -- dropped" % key)
        elif not t.is_hex(val):
            f.add("warn", "override-not-hex",
                  "`colorOverrides.%s: %r` is not #rrggbb -- accepted verbatim, but only "
                  "plain hex is guaranteed to render everywhere" % (key, val))
    missing = t.OVERRIDE_KEYS - set(src)
    if len(src) >= 8 and missing:
        f.add("info", "override-partial",
              "%d of 19 overrides set; the rest derive from the palette (%s)"
              % (len(src), ", ".join(sorted(missing)[:6]) + ("..." if len(missing) > 6 else "")))


def check_styles(theme, f):
    src = theme.get("componentStyles")
    if src is None:
        return
    if not isinstance(src, dict):
        f.add("error", "styles-type", "`componentStyles:` is not a mapping")
        return
    for bucket, props in src.items():
        if bucket not in t.COMPONENT_BUCKETS:
            f.add("error", "style-bucket-unknown",
                  "`componentStyles.%s` is not a permitted bucket -- dropped "
                  "(permitted: %s)" % (bucket, ", ".join(sorted(t.COMPONENT_BUCKETS))))
            continue
        if not isinstance(props, dict):
            f.add("error", "style-bucket-type", "`componentStyles.%s` is not a mapping -- dropped" % bucket)
            continue
        readable = t.COMPONENT_READ.get(bucket)
        if readable is None:
            f.add("warn", "style-bucket-dead",
                  "`componentStyles.%s` is accepted but nothing in the build reads it -- "
                  "dead configuration" % bucket)
            continue
        for prop in props:
            kebab = _kebab(prop)
            if kebab not in readable:
                f.add("warn", "style-prop-dead",
                      "`componentStyles.%s.%s` is emitted as `--component-%s-%s` but never read; "
                      "`%s` reads only: %s" % (bucket, prop, bucket, kebab, bucket, ", ".join(sorted(readable))))


def _kebab(prop):
    """camelCase -> kebab-case, the spelling the server emits the variable in."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", str(prop)).lower()


def check_typography(theme, f):
    typo = theme.get("typography")
    if not isinstance(typo, dict):
        return
    allowed = {"fontSans", "fontMono", "fontDisplay", "fontUrl", "baseSize", "lineHeight", "letterSpacing"}
    for key in typo:
        if key not in allowed:
            f.add("warn", "typo-unknown", "`typography.%s` is not a known field -- ignored" % key)
    if typo.get("fontDisplay"):
        f.add("info", "typo-fontDisplay",
              "`fontDisplay` is stored but the shipped build does not use it; headings and "
              "the retro fonts need a customCSS rule (see references/typography-and-fonts.md)")


def check_layout(theme, f):
    lay = theme.get("layout")
    if isinstance(lay, dict):
        radius = lay.get("radius")
        if radius is not None and not re.match(r"^\d*\.?\d+(px|rem|em|%)$", str(radius).strip()):
            f.add("warn", "layout-radius",
                  "`layout.radius: %r` is not a CSS length (px/rem/em/%%) -- the variable "
                  "lands in CSS as-is" % radius)
        density = lay.get("density")
        if density is not None and density not in t.DENSITIES:
            f.add("warn", "layout-density",
                  "`layout.density: %r` is not one of %s -- falls back to comfortable"
                  % (density, ", ".join(sorted(t.DENSITIES))))
    variant = theme.get("layoutVariant")
    if variant is not None and variant not in t.LAYOUT_VARIANTS:
        f.add("warn", "layout-variant",
              "`layoutVariant: %r` is not one of %s -- falls back to standard"
              % (variant, ", ".join(sorted(t.LAYOUT_VARIANTS))))


# --------------------------------------------------------------------------
# customCSS
# --------------------------------------------------------------------------

def check_custom_css(theme, f):
    css = theme.get("customCSS")
    if css is None:
        f.add("info", "css-none",
              "no `customCSS` -- everything that has no token (semantic colours, code chips, "
              "::selection, rounded-none surfaces) keeps the stock look")
        return
    if not isinstance(css, str):
        f.add("error", "css-type", "`customCSS:` is not a string -- dropped")
        return

    size = len(css.encode("utf-8"))
    if size > t.CUSTOM_CSS_MAX:
        f.add("error", "css-size",
              "customCSS is %d bytes, above the %d byte cap -- it is silently clipped"
              % (size, t.CUSTOM_CSS_MAX))
    elif size > CSS_WARN_AT:
        f.add("warn", "css-size-near",
              "customCSS is %d bytes, close to the %d byte cap" % (size, t.CUSTOM_CSS_MAX))

    hexes = sorted(set(m.upper() for m in _HEX_IN_CSS.findall(css)))
    if hexes:
        shown = ", ".join(hexes[:12]) + (" ..." if len(hexes) > 12 else "")
        f.add("info", "css-hardcoded-hex",
              "customCSS carries %d hardcoded colour(s): %s -- a rule cannot tell the light "
              "theme from the dark one, so each value has to be reviewed for both modes" % (len(hexes), shown))

    for var in _SERIES_VARS:
        for m in re.finditer(re.escape(var) + r"\s*:[^;]*;", css):
            if "!important" not in m.group(0):
                f.add("warn", "css-series-important",
                      "`%s` is set without `!important`; the client writes it inline on <html>, "
                      "and inline style wins" % var)
                break

    if re.search(r"</?\s*(script|style)", css, re.I):
        f.add("error", "css-tag",
              "customCSS contains a `</style>`/`<script` sequence; it is injected into a "
              "<style> tag, so this breaks the whole page")

    if css.count("{") != css.count("}"):
        f.add("warn", "css-braces",
              "customCSS has %d `{` and %d `}` -- one rule swallows the next"
              % (css.count("{"), css.count("}")))

    for name in sorted(set(re.findall(r"--series-[a-z-]*", css))):
        if name not in _SERIES_VARS:
            f.add("warn", "css-series-typo",
                  "`%s` looks like a typo of `--series-input-token`/`--series-output-token`; "
                  "the client only reads the two exact names" % name)

    bangs = css.count("!important")
    if bangs > 40:
        f.add("info", "css-important",
              "customCSS uses `!important` %d times -- fine for the inline-set tokens, worth a "
              "look everywhere else" % bangs)

    if (t.ov(theme, "success") or t.ov(theme, "warning") or t.ov(theme, "destructive")):
        if not re.search(r"text-(success|warning|destructive)", css):
            f.add("info", "css-semantic-unreached",
                  "`colorOverrides.success/warning/destructive` are set, but the app hardwires "
                  "those colours in the stylesheet -- without a `[class*=\"text-success\"]` style "
                  "rule the override does not show on status chips")


# --------------------------------------------------------------------------
# Contrast
# --------------------------------------------------------------------------

def _pair(label, fg, bg, f, min_ratio, level="warn", hint=""):
    if not (t.is_hex(fg) and t.is_hex(bg)):
        return None
    r = t.ratio(t.norm_hex(fg), t.norm_hex(bg))
    if r < min_ratio:
        f.add(level, "contrast",
              "%s: %.2f:1 (%s on %s), below %.1f:1%s"
              % (label, r, fg, bg, min_ratio, (" -- " + hint) if hint else ""))
    return r


def check_contrast(theme, f):
    canvas = t.layer_hex(theme, "background")
    mid = t.layer_hex(theme, "midground")
    card = t.ov(theme, "card") or canvas
    card_fg = t.ov(theme, "cardForeground") or mid
    popover = t.ov(theme, "popover") or card
    popover_fg = t.ov(theme, "popoverForeground") or mid
    primary, primary_fg = t.ov(theme, "primary"), t.ov(theme, "primaryForeground")
    muted, muted_fg = t.ov(theme, "muted") or canvas, t.ov(theme, "mutedForeground")
    secondary, secondary_fg = t.ov(theme, "secondary") or canvas, t.ov(theme, "secondaryForeground")
    accent, accent_fg = t.ov(theme, "accent") or canvas, t.ov(theme, "accentForeground")
    border = t.ov(theme, "border") or canvas

    _pair("body text", mid, canvas, f, TEXT_MIN, "warn",
          "the palette's text tone on the canvas")
    _pair("card text", card_fg, card, f, TEXT_MIN, "warn", "cardForeground on card")
    _pair("popover text", popover_fg, popover, f, TEXT_MIN, "warn", "popoverForeground on popover")
    if primary and primary_fg:
        _pair("button label", primary_fg, primary, f, BUTTON_MIN, "warn", "primaryForeground on primary")
    _pair("muted text", muted_fg, muted, f, MUTED_MIN, "warn", "mutedForeground on muted")
    _pair("secondary text", secondary_fg, secondary, f, MUTED_MIN, "warn", "secondaryForeground on secondary")
    _pair("accent text", accent_fg, accent, f, MUTED_MIN, "warn", "accentForeground on accent")

    if t.is_hex(border) and t.is_hex(canvas):
        r = t.ratio(t.norm_hex(border), t.norm_hex(canvas))
        if r < 1.15:
            f.add("info", "contrast-border",
                  "border vs canvas is %.2f:1 -- the edge is invisible, cards and inputs blur "
                  "into the surface" % r)

    for role in ("success", "warning", "destructive"):
        val = t.ov(theme, role)
        if val and t.is_hex(card):
            r = t.ratio(t.norm_hex(val), t.norm_hex(card))
            f.add("info", "contrast-%s" % role,
                  "%s %s on the card surface: %.2f:1 (tinted chips composite further; measure "
                  "the real page, see references/contrast-checking.md)" % (role, val, r))


# --------------------------------------------------------------------------
# Live cross-check against an installed Hermes
# --------------------------------------------------------------------------

def check_live(theme, f, live):
    mirror = {
        "override keys": (t.OVERRIDE_KEYS, live["override_keys"]),
        "style buckets": (t.COMPONENT_BUCKETS, live["buckets"]),
        "builtin names": (t.BUILTIN_THEME_NAMES, live["builtins"]),
    }
    for label, (mine, theirs) in mirror.items():
        if not theirs:
            f.add("info", "live-constant-missing",
                  "the installed Hermes exposes no %s -- cannot cross-check" % label)
            continue
        extra = mine - theirs
        missing = theirs - mine
        if extra:
            f.add("warn", "live-drift-extra",
                  "%s: this tool knows %s, the installed Hermes does not -- update theme_lib.py"
                  % (label, ", ".join(sorted(extra))))
        if missing:
            f.add("warn", "live-drift-missing",
                  "%s: the installed Hermes has %s that this tool does not know -- the mirror "
                  "in theme_lib.py is stale" % (label, ", ".join(sorted(missing))))
    cap = live.get("custom_css_max")
    if cap and cap != t.CUSTOM_CSS_MAX:
        f.add("warn", "live-drift-css-cap",
              "customCSS cap is %s here and %s in theme_lib.py" % (cap, t.CUSTOM_CSS_MAX))

    normalise = live.get("normalise")
    if callable(normalise):
        try:
            kept = normalise(theme)
        except Exception as exc:
            f.add("warn", "live-normalise-failed", "the live normaliser raised: %s" % exc)
            return
        if kept is None:
            f.add("error", "live-rejected",
                  "the installed Hermes rejects this file outright (normaliser returned None)")
            return
        dropped = [k for k in theme if k not in kept]
        if dropped:
            f.add("warn", "live-dropped",
                  "the installed Hermes drops these top-level keys: %s" % ", ".join(dropped))
        kept_css = kept.get("customCSS") or ""
        if len(kept_css) < len((theme.get("customCSS") or "")):
            f.add("error", "live-css-clipped",
                  "the installed Hermes clips customCSS (%d -> %d bytes)"
                  % (len(theme.get("customCSS") or ""), len(kept_css)))
        f.add("info", "live-ok",
              "live check against %s: %d top-level key(s) kept, name %r"
              % (live["file"], len(kept), kept.get("name")))


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def check_file(path, live=None, contrast=True):
    theme = t.load(path)
    if not isinstance(theme, dict):
        raise t.YamlError("top level is not a mapping")
    f = Findings()
    check_structure(theme, f)
    check_custom_css(theme, f)
    if contrast:
        check_contrast(theme, f)
    if live:
        check_live(theme, f, live)
    return theme, f


def render(path, theme, f, quiet=False):
    name = theme.get("name") or "?"
    css = theme.get("customCSS") or ""
    mode = "dark" if (t.is_hex(t.layer_hex(theme, "background"))
                      and t.lum(t.norm_hex(t.layer_hex(theme, "background"))) < 0.35) else "light"
    print("%s" % path)
    print("  name %r   mode %s   canvas %s   customCSS %.1f KiB"
          % (name, mode, t.layer_hex(theme, "background") or "?", len(css.encode()) / 1024.0))
    order = ("error", "warn", "info")
    for level in order:
        items = [i for i in f.items if i["level"] == level]
        if not items or (quiet and level == "info"):
            continue
        print("  %s (%d)" % (LEVEL_TAG[level] + "S" if level != "info" else "NOTES", len(items)))
        for i in items:
            print("    [%s] %s" % (i["code"], i["message"]))
    worst = f.worst()
    if worst is None:
        print("  clean: no findings")
    else:
        print("  %d error(s), %d warning(s), %d note(s)"
              % (f.count("error"), f.count("warn"), f.count("info")))


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="theme-check",
        description="Lint a Hermes dashboard theme YAML (structure, dead config, contrast).")
    ap.add_argument("files", nargs="+", help="theme YAML file(s)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="any warning also fails (exit 1)")
    ap.add_argument("--quiet", action="store_true", help="hide notes")
    ap.add_argument("--no-contrast", action="store_true", help="skip the contrast section")
    ap.add_argument("--live", action="store_true",
                    help="cross-check against an installed Hermes (import hermes_cli.web_server_dashboard)")
    ap.add_argument("--hermes", metavar="DIR",
                    help="directory that contains hermes_cli/ (implies --live)")
    args = ap.parse_args(argv)

    live = None
    if args.live or args.hermes:
        live, reason = t.load_live_schema(args.hermes)
        if live is None:
            print("theme-check: live check unavailable (%s)" % reason, file=sys.stderr)
            if args.hermes:
                return 2

    results, failed = [], False
    for path in args.files:
        try:
            theme, f = check_file(path, live=live, contrast=not args.no_contrast)
        except (t.YamlError, OSError) as exc:
            print("theme-check: %s: %s" % (path, exc), file=sys.stderr)
            return 2
        results.append((path, theme, f))
        if f.has_errors() or (args.strict and f.count("warn")):
            failed = True

    if args.json:
        print(json.dumps({
            "files": [{
                "path": p,
                "name": th.get("name"),
                "findings": f.items,
                "summary": {lv: f.count(lv) for lv in LEVELS},
            } for p, th, f in results],
            "summary": {
                "files": len(results),
                "errors": sum(f.count("error") for _, _, f in results),
                "warnings": sum(f.count("warn") for _, _, f in results),
                "notes": sum(f.count("info") for _, _, f in results),
            },
        }, indent=2, ensure_ascii=False))
    else:
        for i, (path, theme, f) in enumerate(results):
            if i:
                print()
            render(path, theme, f, quiet=args.quiet)
        if len(results) > 1:
            print()
            print("total: %d file(s), %d error(s), %d warning(s), %d note(s)"
                  % (len(results),
                     sum(f.count("error") for _, _, f in results),
                     sum(f.count("warn") for _, _, f in results),
                     sum(f.count("info") for _, _, f in results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
