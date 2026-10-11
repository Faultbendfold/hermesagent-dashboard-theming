# Roundness and customCSS

Why the interface looks angular, which elements can actually be made round, and how to prove it in the
browser. Applies to the shipped dashboard bundle (the order of the rules in this file is the order in
which to proceed).

## 1. The default state is angular

- The preflight sets `button, input, select, optgroup, textarea { border-radius: 0 }`.
- The layout consists of 1px hairlines (`.g` with cells `.gc`, plus many `border-t`/`border-b`),
  not rounded cards.
- In the DOM, rounding utilities barely occur: on the skills page (2266 elements) there is
  exactly one `rounded-full` and one `focus-visible:rounded-sm`.

Consequence: "everything still angular" is **not** a sign of a theme that was not applied. Colors and
type come via CSS variables, roundness via classes — the two paths can take effect independently.

## 2. Element map (measured in the browser, skills page)

| What | Selector from the DOM | Count |
|---|---|---|
| Status markers active/inactive | `span[class*="pointer-events-none"][class*="w-3.5"]` | 156 |
| Highlight of sidebar entries | `span[class*="inset-y-0.5"][class*="bg-midground"]` | 21 |
| Buttons | `button` | 338 |
| Outlined areas/cards | `div[class*="border-border"]`, `div[class*="border-midground"]` | many |
| Hairline grid (tables) | `.g` (cells `.gc`) | few |
| Input fields | `input:not([type="checkbox"]):not([type="radio"])`, `select`, `textarea` | few |
| Hard-wired angular | `[class*="rounded-none"]` | page-dependent |
| Tags / hub chips | `span[class*="font-compressed"]` | 67-68 |
| Wrapping border around buttons | `.arc-border` | 58 (models page) |
| Bezel inner edge (inner shadow) | `[class*="shadow-[inset"]` | many buttons |

The status markers are **not form elements** — the interface paints them itself. That is why
searching for `input[type="checkbox"]` in the skills list is a dead end: there is only a search box
there. Real checkboxes live in the cron menu and for webhooks.

## 3. Verified CSS block (customCSS)

Always use the radius tokens (`var(--radius-md)`, `var(--radius-lg)`) so that a change to
`layout.radius` propagates everywhere — no fixed pixel values.

```css
/* hard-wired corners */
[class*="rounded-none"] { border-radius: var(--radius-md) !important; }

/* buttons with a visible surface */
button[class*="bg-"] { border-radius: var(--radius-md) !important; }

/* cards and outlined areas */
div[class*="border-border"],
div[class*="border-midground"] { border-radius: var(--radius-lg) !important; }

/* input fields */
input:not([type="checkbox"]):not([type="radio"]),
select, textarea { border-radius: var(--radius-md) !important; }

/* grid tables as a whole, overflow prevents cells poking out */
.g { border-radius: var(--radius-lg) !important; overflow: hidden; }

/* status markers in lists: circle (50%) or rounded box (4-5px) */
span[class*="pointer-events-none"][class*="w-3.5"] { border-radius: 50% !important; }

/* sidebar highlight instead of an angular bar */
span[class*="inset-y-0.5"][class*="bg-midground"] { border-radius: 8px !important; }

/* progress bars */
progress, meter, [role="progressbar"] { border-radius: 999px !important; overflow: hidden; }
```

Effect of this block: **523 of 2266** elements rounded (before: 1), all 156 status markers round,
337 of 338 buttons rounded.

## 4. Checkboxes: `appearance: none` is mandatory

`input[type="checkbox"] { border-radius: 6px }` alone changes **nothing** — the browser paints native
widgets itself. The box has to be drawn completely by hand:

```css
input[type="checkbox"] {
  -webkit-appearance: none; appearance: none;
  width: 15px; height: 15px;
  border: 1.5px solid #C7CDD6;
  border-radius: 5px;
  background: #FFFFFF;
  display: inline-grid; place-content: center;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
input[type="checkbox"]:checked { background: #1F2937; border-color: #1F2937; }
input[type="checkbox"]:checked::after {
  content: "";
  width: 7px; height: 3px;
  border-left: 2px solid #FFFFFF; border-bottom: 2px solid #FFFFFF;
  transform: rotate(-45deg) translateY(-1px);
}
input[type="checkbox"]:focus-visible { outline: 2px solid #94A3B8; outline-offset: 1px; }
```

## 5. Measure instead of claiming

The dashboard is reachable in the browser without a token (only the API requires auth). Measure before
and after every change — the difference in the number of rounded elements is the evidence:

```python
new_tab("http://127.0.0.1:18789/skills"); wait_for_load(); time.sleep(3)
print(js("""(() => {
  const alle = [...document.querySelectorAll('*')];
  return JSON.stringify({
    css_zeichen: (document.getElementById('hermes-theme-custom-css')||{}).textContent?.length||0,
    gerundet: alle.filter(e => getComputedStyle(e).borderTopLeftRadius !== '0px').length,
    gesamt: alle.length
  });
})()"""))
```

Then `js("location.reload()")` and measure again. The SPA can be addressed directly via its paths
(`/skills`, `/cron`, `/config`). `capture_screenshot()` provides an evidence image for the chat
window. **For fine questions of shape, however, it is not the image that decides, but the computed
value.** An image description is unreliable for millimetre questions: in the same state it reported
"round" once and "angular" once, where the radius was measurably 0 or 15 px, and called an equally
wide ring "even" once and "uneven" once. What is reliable are counts and `getComputedStyle` in the
DOM; the image shows the result to a human, it does not measure it. Always judge shape details with
**frozen** decoration (`element.style.animationPlayState = 'paused'`), otherwise two animation frames
are compared.

Scrollbars are the exception: their rounding (`::-webkit-scrollbar-thumb` with `border-radius: 999px`
and a transparent border for the pill shape) is only mastered by WebKit. **Firefox ignores it** — there
only `scrollbar-width`/`scrollbar-color` exist, and angular ends are a browser matter, not a theme
matter. Say this openly instead of trying to fix it.

### 5a. Compute contrast in layers

The obvious approximation — for each text node take the first ancestor with an opaque surface
color — overestimates the contrast: semi-transparent labels (`bg-…/10`) and tinted dialogs then
fall back to white, and precisely the weak spots disappear from the finding (one run reported "no
weak contrast" while the label was really at 3.8:1). Instead, blend all ancestor colors from the root
downwards:

```python
print(js("""(() => {
  const hexOf = c => { const n = (c.match(/-?[\\d.]+(?:e-?\\d+)?/g) || []).map(Number);
    if (c.startsWith('color(srgb')) return { r: n[0]*255, g: n[1]*255, b: n[2]*255, a: n.length > 3 ? n[n.length-1] : 1 };
    return { r: n[0], g: n[1], b: n[2], a: n.length > 3 ? n[n.length-1] : 1 }; };
  const mischen = (o, u) => ({ r: o.r*o.a + u.r*(1-o.a), g: o.g*o.a + u.g*(1-o.a), b: o.b*o.a + u.b*(1-o.a), a: 1 });
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
    return 0.2126*f(c.r) + 0.7152*f(c.g) + 0.0722*f(c.b); };
  const grund = e => { const kette = [];
    for (let x = e; x; x = x.parentElement) { const c = hexOf(getComputedStyle(x).backgroundColor); if (c.a > 0.001) kette.push(c); }
    let r = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = kette.length - 1; i >= 0; i--) r = mischen(kette[i], r);
    return r; };
  const schwach = {};
  document.querySelectorAll('*').forEach(e => {
    if (e.children.length || !/\\S/.test(e.innerText || '')) return;
    const q = e.getBoundingClientRect(); if (q.width < 2 || Number(getComputedStyle(e).opacity) < 0.4) return;
    const s = getComputedStyle(e), vg = grund(e);
    const la = lum(hexOf(s.color)), lb = lum(vg);
    const k = (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
    if (k < 3.2) schwach[e.innerText.trim().slice(0, 30) + ' ' + s.color + ' ' + (Math.round(k*100)/100)] = 1;
  });
  return JSON.stringify(Object.keys(schwach).slice(0, 8)); })()"""))
```

Thresholds for the finding: 4.5:1 for small type (12-13 px is the normal case in the dashboard), 3:1
for pure graphics (status dots, chart lines).

Do not drive to **states that are not worth provoking** (scan result in the skill dialog, empty
lists): instead hang the component's color classes into the page as a probe element and read its
computed color. That proves the rule without the state and without triggering an action.

```python
print(js("""(() => {
  const proben = ['bg-emerald-500/5 text-emerald-400', 'bg-amber-500/10 text-amber-400', 'bg-red-500/10 text-red-400'];
  const topf = document.createElement('div');
  topf.style.position = 'fixed'; topf.style.left = '-9999px';
  topf.innerHTML = proben.map(c => '<span class="' + c + '">x</span>').join('');
  document.body.appendChild(topf);
  const r = proben.map((c, i) => c + ' -> ' + getComputedStyle(topf.children[i]).color);
  topf.remove(); return JSON.stringify(r, null, 1); })()"""))
```

### 5b. Mobile width and the blame question

Mobile is a primary use case. Layout bugs that get reported often arise only at narrow widths and are
invisible on the desktop — so reproduce them at mobile width rather than disproving them on the
desktop:

```python
cdp('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=3, mobile=True)
# … measure … and at the end of the session cdp('Emulation.clearDeviceMetricsOverride')
```

Whether the **own** CSS causes an overlap or a shift is clarified by a test in the page — without
switching theme or config: find the injected `<style>` with the custom CSS, briefly disable it,
measure again, re-enable it. That settles the answer before an explanation or a fix is given.

```python
print(js("""(() => {
  const styleTag = [...document.querySelectorAll('style')].find(s => (s.textContent || '').includes('#4E7C99'));
  const messen = () => [...document.querySelectorAll('span')]
    .filter(e => /^FILES:?$/.test((e.innerText || '').trim()))
    .map(e => { const q = e.parentElement.getBoundingClientRect(); return Math.round(q.top); });
  const withCss = messen(); let withoutCss = null;
  if (styleTag) { styleTag.disabled = true; withoutCss = messen(); styleTag.disabled = false; }
  return JSON.stringify({ withCss, withoutCss }); })()"""))
```

Overlaps are found by a rectangle intersection across all text nodes (intersection area > 25% of the
smaller rectangle). If the finding stays the same with and without the own CSS, it is app behavior —
then report it as such, with the measured value, instead of booking it as fixed.

For the follow-up check on an image supplied by a user (mobile screenshot), the Hermes Python has no
image module; a run with `uv run --quiet --with pillow --with numpy python …` works, but is only
sensible for locating the region. The reliable answer comes from the DOM: a blurry mobile screenshot
is useless for detail questions, and so is a model report about it.

## 6. The wrapping border around buttons (`arc-border`) and the focus border

- `.arc-border` carries **no border**: `border-width: 0`, no `border-image` anywhere in the document.
  What is visible is an absolutely positioned pseudo content whose gradient is reduced by a mask
  (`mask-composite: exclude`) to an equally wide ring area. Key values:
  `inset: -2px` (2 px larger than the button), `padding: var(--arc-width)` = **stroke width**
  (default 1.25 px), `--arc-angle: 160deg`, `--arc-duration: 2.23s`, animation `gradient-stroke`
  on `background-position`.
- **The gradient starts at `transparent`** (or at `foreground` with `alpha: 0`). A section of the
  ring is therefore invisible; the animation moves this gap around the element. It reads as "the
  border is not uniformly even, the bottom-left and top-right corners are thinner" — and a snapshot
  then shows a different pair of corners than the observation. Not a bug of the own theme: the same
  gap is in the bundled skins.
- Fix — opaque instead of transparent, animation stays:

```css
.arc-border {
  border-radius: calc(var(--radius-md) + 2px) !important; /* outside = inside + offset */
  --arc-gradient: linear-gradient(var(--arc-angle), var(--midground) 0%, var(--midground) 100%);
}
```

  Calm version (a single hue, no motion) additionally with `--arc-duration: 0s`.
  Present both as numbered options — the animated variant and the deliberately calm one.
- `--arc-width` also controls **the computed padding** (`padding` follows the variable), so an increase
  really takes effect: `--arc-width: 1.6px` against edge smoothing. A 1.25-px stroke is smoothed more
  strongly on curves than on straight stretches and reads paler there — that is appearance, not
  geometry. Do not answer it with new geometry, but with a little more width.
- The ring always lies **on the side surface** (2 px outside the button), not on the button fill;
  a dark tone therefore stays visible even on dark-filled buttons.
- Focus border and this ring are **two different things**:
  `.focus-visible\:border-midground\/25:focus-visible { border-color: var(--midground) }` (and
  relatives) stand as utility classes in the source of the buttons. What stays stuck after tapping is
  app behavior — grep the bundle before blaming any theme.
- **The most common cause of "strange borders", however, is two hard inner shadows (bezel).**
  Many buttons carry arbitrary shadow utilities of the form
  `.shadow-[inset_-1px_-1px_0_0_#00000080,inset_1px_1px_0_0_#ffffff80]` (three variants in the bundle):
  a 1-px inner stroke dark at bottom right and one light at top left, both hard and **without**
  blur. Because inner shadows follow the rounding, the eye reads it as a border:
  - on the **dark** button the light part becomes the "grey stripe at the top that follows the rounding";
  - on the **light** button the light part is invisible, while the dark part emphasizes two
    **opposite** corners — exactly the observation "top left and bottom right fit, bottom left and
    top right do not".

  **Replace, do not delete** — and via the variable, **not** via `box-shadow: none` (otherwise the
  focus ring goes away too, because it is set as a separate part of the same shorthand `--tw-ring-shadow`):

  ```css
  [class*="shadow-[inset"] { --tw-shadow: inset 0 0 0 1px var(--midground) !important; }
  ```

  The reason for the replacement: the **light** buttons have `border-width: 0` — the bezel is their
  only edge. With `0 0 #0000` they are borderless on a light background ("the borders of the white
  buttons are gone"). A full `--midground` color is the recommended default; on dark buttons the line
  then disappears by itself.

  Check: `getComputedStyle(btn).getPropertyValue('--tw-shadow')` returns the `inset` ring, and
  `boxShadow` contains exactly one `inset` part (the bezel had two, with an offset). The earlier
  version noted here, `0 0 #0000`, was that bug.

  What else is hard-wired (semantic colors, title classes) and how to find it in the bundle:
  `references/hardcoded-build-styles.md`. Check this edge **first**: it survives every change to
  `layout.radius` and to the ring, and has repeatedly steered troubleshooting down the wrong track.

## 7. Producing heavily magnified evidence

For an evidence image, CDP zooms itself instead of scaling the image afterwards (8-16x turns a
1.6-px stroke into 13-26 px, which the eye can judge):

```python
res = cdp('Page.captureScreenshot', format='png', captureBeyondViewport=True,
          clip={'x': x - 5, 'y': y - 8, 'width': 14, 'height': 14, 'scale': 16})
open('$HERMES_HOME/cache/ecke.png', 'wb').write(base64.b64decode(res['data']))
```

Read the rect (`getBoundingClientRect()`) **in the same call** that produces the image, and set
`window.scrollTo(0,0)` beforehand — otherwise the image coordinates no longer match (crops move with
the scroll position).

## 8. Tags as pills

The tags inherit size and spacing from the list (`letter-spacing` ~0.2em) and carry the retro display
font via the same class:

```css
span[class*="font-compressed"] {
  border-radius: 999px !important;
  font-family: var(--theme-font-sans) !important;
  font-size: 10px;
  letter-spacing: 1.4px;
}
```

Counter-check in the DOM: the number of `span[class*="font-compressed"]` and their `borderTopLeftRadius`.
