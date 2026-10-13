#!/usr/bin/env python3
"""theme_lib -- shared helpers for the Hermes dashboard theming tools.

Deliberately free of third-party imports. Hermes itself ships a venv with
PyYAML, but these tools are meant to run under whatever ``python3`` a user
happens to have, so the reader below covers only the YAML subset that theme
files actually use -- nested maps, quoted and plain scalars, block literals --
and raises on anything else instead of guessing. Sequences are refused on
purpose: a theme file that needs them is not a theme file this repo supports.

Contents
--------
* ``parse_yaml``                -- the YAML subset reader
* colour maths                  -- channels/hexs/lum/ratio/mix/chroma/fit/lighten_to
* ``SCHEMA`` constants           -- mirror of what the shipped server accepts and
                                   what the built bundle actually reads
                                   (hermes_cli/web_server_dashboard.py, v2026.9.24)
* theme accessors               -- layer_hex/ov/norm_hex

The mirror can go stale when Hermes changes. ``theme-check.py --live`` re-reads
the constants from an installed Hermes and reports the drift, so the mirror
never has to be trusted blindly.
"""

import json
import os
import re

__all__ = [
    "YamlError", "parse_yaml", "load",
    "channels", "hexs", "lum", "ratio", "mix", "chroma", "lighten_to", "darken_to", "fit",
    "norm_hex", "is_hex", "layer_hex", "ov", "layer_alpha",
    "BUILTIN_THEME_NAMES", "OVERRIDE_KEYS", "COMPONENT_BUCKETS", "COMPONENT_READ",
    "CUSTOM_CSS_MAX", "NAMED_ASSET_KEYS", "LAYOUT_VARIANTS", "DENSITIES",
    "DROPPED_TOP_LEVEL", "KNOWN_TOP_LEVEL", "load_live_schema",
]


# --------------------------------------------------------------------------
# YAML subset reader
# --------------------------------------------------------------------------

_BLOCK_MARKERS = {"|", "|-", "|+", ">", ">-", ">+"}


class YamlError(ValueError):
    """Raised when a file leaves the YAML subset this reader understands."""


def _split_key(line, lineno):
    """Split ``key: value`` on the first colon that sits outside quotes."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == ":":
            return line[:i].rstrip(), line[i + 1:]
    raise YamlError("line %d: expected 'key: value', got %r" % (lineno, line))


def _scalar(raw, lineno):
    s = raw.strip()
    if s == "":
        return None
    if s[0] in "'\"":
        quote, out, i = s[0], [], 1
        while i < len(s):
            ch = s[i]
            if quote == "'" and ch == "'":
                if i + 1 < len(s) and s[i + 1] == "'":  # '' is an escaped quote
                    out.append("'")
                    i += 2
                    continue
                break
            if quote == '"' and ch == "\\" and i + 1 < len(s):
                out.append(ch)
                out.append(s[i + 1])
                i += 2
                continue
            if quote == '"' and ch == '"':
                break
            out.append(ch)
            i += 1
        else:
            raise YamlError("line %d: unterminated quoted string" % lineno)
        tail = s[i + 1:].strip()
        if tail and not tail.startswith("#"):
            raise YamlError("line %d: text after a quoted value: %r" % (lineno, tail))
        body = "".join(out)
        if quote == '"':
            try:
                return json.loads('"' + body + '"')
            except ValueError:
                return body
        return body
    s = re.split(r"\s+#", s, maxsplit=1)[0].strip()  # trailing inline comment
    if s == "":
        return None
    if s in ("null", "Null", "NULL", "~"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    return s


def _next_content_indent(lines, start):
    """Indent of the next non-blank, non-comment line at or after ``start``."""
    for j in range(start, len(lines)):
        ln = lines[j]
        if ln.strip() and not ln.lstrip().startswith("#"):
            return len(ln) - len(ln.lstrip(" "))
    return None


def parse_yaml(text):
    """Parse the YAML subset used by Hermes dashboard theme files into a dict.

    Plain scalars stay strings -- callers convert (``float(theme[...])``); only
    ``true``/``false``/``null`` become Python values. Block scalars are returned
    as text, always with the trailing newline the clip chomping implies.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    root = {}
    stack = [(-1, root)]  # (indent of the key that owns this mapping, mapping)
    i, n = 0, len(lines)

    while i < n:
        raw = lines[i]
        lineno = i + 1
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent]:
            raise YamlError("line %d: tab in indentation (use spaces)" % lineno)
        content = raw[indent:]
        if content.startswith("- ") or content == "-":
            raise YamlError("line %d: sequences are not part of a theme file" % lineno)

        key, rest = _split_key(content, lineno)
        if not key:
            raise YamlError("line %d: empty key" % lineno)

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        if indent <= stack[-1][0]:
            raise YamlError("line %d: unexpected indentation" % lineno)
        parent = stack[-1][1]

        marker = rest.strip()
        if marker in _BLOCK_MARKERS:
            block, block_indent, j = [], None, i
            while j < n:
                ln = lines[j]
                if ln.strip() == "":
                    block.append("")
                    j += 1
                    continue
                ind = len(ln) - len(ln.lstrip(" "))
                if ind <= indent:
                    break
                if block_indent is None:
                    block_indent = ind
                block.append(ln[block_indent:])
                j += 1
            i = j
            while block and block[-1] == "":
                block.pop()
            if marker.startswith(">"):
                body = " ".join(x.strip() for x in block)
            else:
                body = "\n".join(block)
            parent[key] = body if marker.endswith("-") else body + "\n"
        elif marker == "":
            if _next_content_indent(lines, i) is not None and _next_content_indent(lines, i) > indent:
                child = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                parent[key] = None
        else:
            parent[key] = _scalar(rest, lineno)

    return root


def load(path):
    """Read and parse a theme file from disk."""
    with open(path, "r", encoding="utf-8") as fh:
        return parse_yaml(fh.read())


# --------------------------------------------------------------------------
# Colour maths
# --------------------------------------------------------------------------

def channels(h):
    """'#rrggbb' -> [r, g, b]."""
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def hexs(c):
    """[r, g, b] (floats allowed) -> '#RRGGBB'."""
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x))) for x in c)


def lum(h):
    """WCAG relative luminance of a hex colour."""
    v = [x / 255 for x in channels(h)]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def ratio(a, b):
    """WCAG contrast ratio between two hex colours (1.0 .. 21.0)."""
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, f):
    """Mix ``a`` toward ``b`` by the fraction ``f`` in 0..1."""
    ca, cb = channels(a), channels(b)
    return hexs([ca[i] * (1 - f) + cb[i] * f for i in range(3)])


def chroma(h):
    """Saturation proxy: max channel minus min channel, in 0..1."""
    r, g, b = [x / 255 for x in channels(h)]
    return max(r, g, b) - min(r, g, b)


def lighten_to(col, target):
    """Push ``col`` toward white until its luminance reaches ``target``."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if lum(mix(col, "#FFFFFF", mid)) >= target:
            hi = mid
        else:
            lo = mid
    return mix(col, "#FFFFFF", hi)


def darken_to(col, target):
    """Push ``col`` toward black until its luminance drops to ``target``."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if lum(mix(col, "#000000", mid)) <= target:
            hi = mid
        else:
            lo = mid
    return mix(col, "#000000", hi)


def fit(col, base, target, toward):
    """Push ``col`` toward ``toward`` until contrast to ``base`` reaches ``target``.

    Returns ``col`` unchanged when it already meets the target -- otherwise the
    bisection walks the wrong way (the predicate is then already true at the
    first step and converges to ``toward`` instead of to the threshold).

    Bisection, not an integer-percent loop: stepping the mix in whole percent
    gets stuck at the rounding and returns a permanently too-pale value.
    """
    if ratio(col, base) >= target:
        return col
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if ratio(mix(col, toward, mid), base) >= target:
            hi = mid
        else:
            lo = mid
    return mix(col, toward, hi)


_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_hex(v):
    return isinstance(v, str) and bool(_HEX_RE.match(v.strip()))


def norm_hex(v, default="#000000"):
    """Uppercase '#rrggbb', or ``default`` when the value is not a hex colour."""
    if not is_hex(v):
        return default
    h = v.strip().upper()
    if len(h) == 4:  # #abc -> #AABBCC
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


# --------------------------------------------------------------------------
# Schema mirror -- Hermes v2026.9.24 (see references/theme-token-inventory.md)
# --------------------------------------------------------------------------

BUILTIN_THEME_NAMES = {
    "default", "default-large", "nous-blue", "midnight",
    "ember", "mono", "cyberpunk", "rose",
}

OVERRIDE_KEYS = {
    "card", "cardForeground", "popover", "popoverForeground",
    "primary", "primaryForeground", "secondary", "secondaryForeground",
    "muted", "mutedForeground", "accent", "accentForeground",
    "destructive", "destructiveForeground", "success", "warning",
    "border", "input", "ring",
}

COMPONENT_BUCKETS = {
    "card", "header", "footer", "sidebar", "tab", "progress", "badge", "backdrop", "page",
}

# What the shipped bundle actually consumes out of each bucket.
COMPONENT_READ = {
    "sidebar": {"background", "border-image", "clip-path"},
    "header": {"background", "border-image", "clip-path"},
    "card": {"background", "box-shadow", "border-image", "clip-path"},
    "tab": {"clip-path"},
}

CUSTOM_CSS_MAX = 32 * 1024

NAMED_ASSET_KEYS = {"bg", "hero", "logo", "crest", "sidebar", "header"}

LAYOUT_VARIANTS = {"standard", "cockpit", "tiled"}
DENSITIES = {"compact", "comfortable", "spacious"}

# Accepted by the file but dropped before it reaches the surface.
DROPPED_TOP_LEVEL = {
    "seriesColors": "use customCSS with --series-input-token/--series-output-token and !important",
    "terminalBackground": "the xterm panel is painted by the app, not by the theme",
    "terminalForeground": "the xterm panel is painted by the app, not by the theme",
    "swatchColors": "only the picker preview; has no effect on the dashboard",
}

KNOWN_TOP_LEVEL = {
    "name", "label", "description", "palette", "colors", "typography", "layout",
    "layoutVariant", "colorOverrides", "componentStyles", "customCSS", "assets",
    "noiseOpacity", "warmGlow",
} | set(DROPPED_TOP_LEVEL)


# --------------------------------------------------------------------------
# Theme accessors
# --------------------------------------------------------------------------

def layer_hex(theme, name, default=None):
    """Hex of a palette layer, accepting both the bare and the {hex, alpha} form."""
    pal = theme.get("palette")
    val = pal.get(name) if isinstance(pal, dict) else None
    if isinstance(val, dict):
        val = val.get("hex")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return default


def layer_alpha(theme, name, default=None):
    pal = theme.get("palette")
    val = pal.get(name) if isinstance(pal, dict) else None
    if isinstance(val, dict) and "alpha" in val:
        try:
            return float(val["alpha"])
        except (TypeError, ValueError):
            return default
    return default


def ov(theme, key, default=None):
    """A colorOverrides value if it is a usable string, else ``default``."""
    src = theme.get("colorOverrides")
    val = src.get(key) if isinstance(src, dict) else None
    if isinstance(val, str) and val.strip():
        return val.strip()
    return default


# --------------------------------------------------------------------------
# Live schema (optional cross-check against an installed Hermes)
# --------------------------------------------------------------------------

def load_live_schema(hermes_path=None):
    """Import the installed Hermes theme normaliser.

    Returns ``(info, None)`` on success, ``(None, reason)`` otherwise. ``info``
    carries the live constants plus the normaliser itself, so a caller can see
    exactly what a running Hermes would keep of a given file.
    """
    import importlib

    added = False
    if hermes_path:
        hermes_path = os.path.abspath(os.path.expanduser(hermes_path))
        if hermes_path not in os.sys.path:
            os.sys.path.insert(0, hermes_path)
            added = True
    try:
        mod = importlib.import_module("hermes_cli.web_server_dashboard")
    except Exception as exc:  # ImportError, or the module's own deps missing
        if added:
            os.sys.path.remove(hermes_path)
        return None, "%s: %s" % (type(exc).__name__, exc)
    return {
        "module": mod,
        "file": getattr(mod, "__file__", "?"),
        "override_keys": set(getattr(mod, "_THEME_OVERRIDE_KEYS", ())),
        "buckets": set(getattr(mod, "_THEME_COMPONENT_BUCKETS", ())),
        "custom_css_max": getattr(mod, "_THEME_CUSTOM_CSS_MAX", None),
        "builtins": {t.get("name") for t in getattr(mod, "_BUILTIN_DASHBOARD_THEMES", [])},
        "normalise": getattr(mod, "_normalise_theme_definition", None),
        "discover": getattr(mod, "_discover_user_themes", None),
    }, None
