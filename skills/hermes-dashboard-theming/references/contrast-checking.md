# Checking contrast: three traps that produce false alarms

A contrast audit is only as good as the background it compares against. Every mistake below looks
like a theme bug and is really a measurement bug — all three happened in a row while verifying the
`dark-clean` theme.

## 1. A transparent element has no background of its own

The chat page host is `background: rgba(0, 0, 0, 0)`. Reading the theme variable instead
(`--background: #F8F9FB`) suggests white text on a light surface and a 1.4:1 disaster. The real
backdrop is painted by an ancestor: the chat panel is `rgb(0, 0, 0)`, and gold/white ANSI output on
it measures 14.9:1 and 21:1 — perfectly fine.

**Rule: walk up the ancestor chain to the first painted background and measure there.** Also check
whether a *child* paints the surface (the button ring pattern does this) — an ancestor-only walk
reports an invisible label that is in fact dark-on-light.

## 2. Three colour notations, one parser

`getComputedStyle()` returns the colour in whatever notation it was written in:

- `rgb(15, 17, 21)` / `rgba(…)` — the common case
- `color(srgb 0.901961 0.909804 0.92549)` — from `color-mix()` and CSS colour functions
- `oklab(0.930605 -0.00051114 -0.00576353 / 0.9)` — from modern colour spaces

A parser that only knows `rgb(…)` silently falls through to the ancestor and invents violations.
Each of the three formats produced exactly one false alarm: light buttons read as invisible
(`color(srgb …)`), status chips read as text-on-itself (`alpha` ignored), the selected tab read as
canvas-on-canvas (`oklab(…)`).

**Rule: handle all three, and assert that the parser saw the element's own background before
reporting.** An unknown notation must produce "unknown", never a fallback colour.

## 3. Translucency has to be composited

`color-mix(in srgb, #96CEB4 18%, transparent)` computes to `rgb(150, 206, 180)` with alpha `0.18`.
Taking the RGB and ignoring the alpha claims a mint chip surface under mint text — 1:1. Composited
over the dark card it is about `rgb(45, 55, 50)`, and the text sits at roughly 7:1.

**Rule: composite the whole stack from the furthest ancestor forward**
(`result = c*a + result*(1-a)`), and treat an opaque background as the end of the chain.

## What to check, and what to expect

- Run the audit over every page, not just the one you were working on. Two of the three traps only
  appeared on `skills`, `sessions` and `cron`.
- Pixel-count the result as a second opinion: light theme > 90 % light pixels, dark theme > 90 % dark
  pixels. A leftover surface from the other theme shows up as a jump in that number long before it is
  visible in a zoomed screenshot.
- Compare both themes at the phone width (390 px) as well — page furniture such as the session list
  moves off-screen there, so "blur it for the screenshot" resolves itself.
