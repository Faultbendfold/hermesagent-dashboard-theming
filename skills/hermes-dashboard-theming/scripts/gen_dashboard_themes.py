#!/usr/bin/env python3
"""Generate Hermes dashboard themes from color-hex palettes.

Each palette carries the complete UI: canvas (a lightened palette tone),
cards, text, borders, hover surfaces, buttons and the panel surfaces of the
sidebar and header. Only what a palette does not provide is derived by mixing.
Roles and target values: references/palette-to-theme-mapping.md.

Output:   <HERMES_HOME>/dashboard-themes/<name>.yaml
Activate: hermes config set dashboard.theme <name>

The mixes run via bisection in floating point and only round at the very end --
iterative mixing in integer steps gets stuck at the rounding and keeps
returning the same too-pale value.

In componentStyles, ONLY the props the shipped build reads are set
(sidebar/header/card: background, border-image, clip-path; card additionally
box-shadow). Everything else would be dead configuration -- see
references/theme-token-inventory.md.
"""

import os
import re

OUT = os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
                   "dashboard-themes")

# Contrast targets -- see references/palette-to-theme-mapping.md
TEXT_TARGET = 7.0     # Text against the canvas
BUTTON_MIN = 3.2      # Button label against the fill
CANVAS_LUM = 0.93     # Brightness target of the canvas

# Palette name -> color values. Add further palettes following the same pattern;
# fetch values via web_extract from https://www.color-hex.com/color-palette/<id>
# (curl gets a Cloudflare 403).
PALETTES = {
    "Cappuccino":          ["#4B3832", "#854442", "#FFF4E6", "#3C2F2F", "#BE9B7B"],
    "Beach":               ["#96CEB4", "#FFEEAD", "#FF6F69", "#FFCC5C", "#88D8B0"],
    "Beautiful Blues":     ["#011F4B", "#03396C", "#005B96", "#6497B1", "#B3CDE0"],
    "Shades of Teal":      ["#B2D8D8", "#66B2B2", "#008080", "#006666", "#004C4C"],
    "Faded Rose":          ["#DFDFDE", "#A2798F", "#D7C6CF", "#8CABA8", "#EBDADA"],
    "aesthetic":           ["#66545E", "#A39193", "#AA6F73", "#EEA990", "#F6E0B5"],
    "Retro":               ["#666547", "#FB2E01", "#6FCB9F", "#FFE28A", "#FFFEB3"],
    "Shades of Turquoise": ["#B3ECEC", "#89ECDA", "#43E8D8", "#40E0D0", "#3BD6C6"],
    "Pastels":             ["#FFD4E5", "#D4FFEA", "#EECBFF", "#FEFFA3", "#DBDCFF"],
    "Ice cream":           ["#6B3E26", "#FFC5D9", "#C2F2D0", "#FDF5C9", "#FFCB85"],
    "s+b teal":            ["#007777", "#006666", "#005555", "#004444", "#003333"],
    "Seafoam":             ["#A3C1AD", "#A0D6B4", "#5F9EA0", "#317873", "#49796B"],
    "Down Town":           ["#373854", "#493267", "#9E379F", "#E86AF0", "#7BB3FF"],
    "24K GOLD":            ["#A67C00", "#BF9B30", "#FFBF00", "#FFCF40", "#FFDC73"],
    "space-gray like":     ["#343D46", "#4F5B66", "#65737E", "#A7ADBA", "#C0C5CE"],
    "Shades of Gray":      ["#999999", "#777777", "#555555", "#333333", "#111111"],
    "Sage Green":          ["#8F9779", "#78866B", "#738276", "#738678", "#4D5D53"],
    "Shades of White":     ["#FAF0E6", "#FFF5EE", "#FDF5E6", "#FAEBD7"],
    "Cream Coffee":        ["#ECE0D1", "#DBC1AC", "#967259", "#634832", "#38220F"],
    "Summertime 3":        ["#FFBE4F", "#6BD2DB", "#0EA7B5", "#0C457D", "#E8702A"],
    "City Sunset":         ["#EEAF61", "#FB9062", "#EE5D6C", "#CE4993", "#6A0D83"],
    "Metro UI Colors":     ["#D11141", "#00B159", "#00AEDB", "#F37735", "#FFC425"],
    "Soft Black":          ["#414A4C", "#3B444B", "#353839", "#232B2B", "#0E1111"],
    "Grey-Lavender Colors":["#D2D4DC", "#AFAFAF", "#F8F8FA", "#E5E6EB", "#C0C2CE"],
    "Pastel Palette":      ["#B8DBD3", "#F7E7B4", "#68C4AF", "#96EAD7", "#F2F6C3"],
    "Shades of Lavender":  ["#997A8D", "#AA98A9", "#B39EB5", "#777696", "#796878"],
    "blues":               ["#77AAFF", "#99CCFF", "#BBEEFF", "#5588FF", "#3366FF"],
    "millennial pink":     ["#FB958B", "#F7A583", "#F7BAA1", "#FB9FA4", "#FF9E99"],
    "off white":           ["#FFFFF2", "#F9F9F9", "#FFFFF4", "#FBF7F5", "#F9F1F1"],
    "Violet":              ["#FFFFFF", "#E5D0FF", "#DABCFF", "#CCA3FF", "#BF8BFF"],
    "Purple-Grey":         ["#8B8589", "#989898", "#838996", "#979AAA", "#4C516D"],
    "Shades of Pink":      ["#FF00A9", "#FB9F9F", "#FF0065", "#FFBFD3", "#FB5858"],
    "muted colors":        ["#2E4045", "#83ADB5", "#C7BBC9", "#5E3C58", "#BFB5B2"],
    "Dusty Sage":          ["#F8D3C5", "#FCEEE9", "#DDE6D5", "#A3B899", "#667B68"],
    "Blue-Grey":           ["#6E7F80", "#536872", "#708090", "#536878", "#36454F"],
    "cool blue":           ["#005073", "#107DAC", "#189AD3", "#1EBBD7", "#71C7EC"],
}

# Palettes without a usable light tone additionally get a dark variant
# (see slugify for the name suffix).
DARK_TOO = ["Cream Coffee", "Beautiful Blues", "s+b teal", "Soft Black", "muted colors"]

TEMPLATE = '''# Hermes dashboard theme -- color-hex palette "__SRC__" throughout the UI (__MODE__).
# Palette: __HEXES__
# Activate:  hermes config set dashboard.theme __NAME__
# Revert:    hermes config set dashboard.theme default

name: __NAME__
label: Clear · __LABEL__
description: Palette «__SRC__» throughout the UI -- __MODE__

palette:
  background: "__BG__"
  midground: "__TEXT__"
  foreground:
    hex: "#FFFFFF"
    alpha: 0
  warmGlow: "rgba(16, 24, 40, 0.02)"
  noiseOpacity: 0

typography:
  fontSans: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
  fontMono: 'ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas, monospace'
  baseSize: "15px"
  lineHeight: "1.55"
  letterSpacing: "-0.005em"

layout:
  radius: "1rem"
  density: comfortable

colorOverrides:
  card: "__CARD__"
  cardForeground: "__TEXT__"
  popover: "__CARD__"
  popoverForeground: "__TEXT__"
  primary: "__PRIMARY__"
  primaryForeground: "__PRIMARYFG__"
  secondary: "__HOVER__"
  secondaryForeground: "__TEXT__"
  muted: "__HOVER__"
  mutedForeground: "__MUTED__"
  accent: "__HOVER__"
  accentForeground: "__PRIMARY__"
  border: "__BORDER__"
  input: "__BORDER__"
  ring: "__PRIMARY__"
  destructive: "#B4433A"
  destructiveForeground: "#FFFFFF"
  success: "#15803D"
  warning: "#8A6A3B"

componentStyles:
  # The shipped build really reads only these props:
  # sidebar/header/card know background, border-image, clip-path; card additionally
  # box-shadow. badge/page/progress/backdrop/footer would be dead configuration.
  card:
    background: "__CARD__"
    boxShadow: "0 1px 2px rgba(16, 24, 40, 0.06), 0 10px 28px -18px rgba(16, 24, 40, 0.22)"
  header:
    background: "__PANEL__"
  sidebar:
    background: "__PANEL__"

customCSS: |
  html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
  }
  [class~="rounded-none"] {
    border-radius: var(--radius-md) !important;
  }
  ::selection {
    background: rgba(__SEL__, 0.25);
  }
  * {
    scrollbar-color: __BORDER__ __BG__;
  }
'''


def channels(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def hexs(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x))) for x in c)


def lum(h):
    v = [x / 255 for x in channels(h)]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, f):
    ca, cb = channels(a), channels(b)
    return hexs([ca[i] * (1 - f) + cb[i] * f for i in range(3)])


def chroma(h):
    r, g, b = [x / 255 for x in channels(h)]
    return max(r, g, b) - min(r, g, b)


def lighten_to(col, target):
    """Push col toward white until the luminance reaches `target`."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if lum(mix(col, "#FFFFFF", mid)) >= target:
            hi = mid
        else:
            lo = mid
    return mix(col, "#FFFFFF", hi)


def fit(col, base, target, toward):
    """Push col toward `toward` until the contrast to `base` reaches `target`."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if ratio(mix(col, toward, mid), base) >= target:
            hi = mid
        else:
            lo = mid
    return mix(col, toward, hi)


def slugify(name, dark=False):
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return s + "-dark" if dark else s


def build(src, hexes, dark=False):
    tones = sorted(hexes, key=lum)
    darkest, lightest = tones[0], tones[-1]
    if dark:
        bg = darkest
        card = mix(bg, lightest, 0.07)
        text = fit(lightest, bg, TEXT_TARGET, "#FFFFFF")
        muted = mix(text, bg, 0.42)
        hover = mix(bg, text, 0.10)
        border = mix(bg, text, 0.24)
        mode = "dark"
    else:
        bg = lightest if lum(lightest) >= 0.90 else lighten_to(lightest, CANVAS_LUM)
        card = "#FFFFFF" if lum(bg) < 0.965 else mix(bg, darkest, 0.05)
        text = fit(darkest, bg, TEXT_TARGET, "#000000")
        muted = mix(text, bg, 0.40)
        hover = mix(bg, text, 0.07)
        border = mix(bg, text, 0.17)
        mode = "light"

    primary = text
    for c in sorted(hexes, key=chroma, reverse=True):
        if max(ratio(c, "#FFFFFF"), ratio(c, "#000000")) >= BUTTON_MIN:
            primary = c
            break
    pfg = "#FFFFFF" if ratio(primary, "#FFFFFF") >= ratio(primary, "#000000") else "#000000"
    if ratio(primary, pfg) < 3.0:
        primary, pfg = text, ("#FFFFFF" if not dark else bg)

    # Panel surfaces: own palette tone, so the palette also carries the sidebar and
    # the header -- but only far enough that the structure stays visible.
    if dark:
        panel = mix(bg, lightest, 0.15)
    elif lum(primary) > lum(bg):
        panel = mix(bg, text, 0.05)
    else:
        panel = mix(bg, primary, 0.09)

    name = slugify(src, dark)
    vals = {
        "__SRC__": src, "__NAME__": name,
        "__LABEL__": src + (" (dark)" if dark else ""),
        "__HEXES__": " ".join(hexes), "__MODE__": mode, "__BG__": bg,
        "__CARD__": card, "__TEXT__": text, "__MUTED__": muted, "__HOVER__": hover,
        "__BORDER__": border, "__PRIMARY__": primary, "__PRIMARYFG__": pfg,
        "__PANEL__": panel,
        "__SEL__": ", ".join(str(x) for x in channels(primary)),
    }
    body = TEMPLATE
    for k, v in vals.items():
        body = body.replace(k, v)
    with open(os.path.join(OUT, name + ".yaml"), "w") as fh:
        fh.write(body)
    return (name, mode, bg, text, round(ratio(bg, text), 2), primary, pfg, panel)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for src, hexes in PALETTES.items():
        rows.append(build(src, hexes))
        if src in DARK_TOO:
            rows.append(build(src, hexes, dark=True))
    rows.sort(key=lambda r: (r[1], -r[4]))
    print(f"{'Theme':30} {'Mode':7} {'Surface':8} {'Text':8} Contrast  Buttons"
          f"            Panel")
    for r in rows:
        print(f"{r[0]:30} {r[1]:7} {r[2]:8} {r[3]:8} {r[4]:6}  {r[5]} on {r[6]}  {r[7]}")
    print(f"\nWrote: {len(rows)} themes to {OUT}")
