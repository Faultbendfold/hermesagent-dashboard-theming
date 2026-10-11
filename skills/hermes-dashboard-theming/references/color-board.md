# Walking through colors: color list, color chart, interactive board

Colors should be **checkable directly** rather than taken from suggestions. Three forms have
emerged for this and are used in this order:

1. measured **color list** of a page, grouped by roles and with meaning (question: "list all
   colors for me and what they stand for")
2. **color chart** as PNG, when an image in chat is to carry the assignment
3. **interactive board** (`tools/color-board.html`, shipped with this skill), when you want to enter your own hex values

## 1. Color list: group by ROLES, not by hex

Measurement in the running dashboard (`browser_exec`, page `/models`):

```python
print(js("""(() => {
  const hexOf = c => { const n = (c.match(/[\\d.]+/g) || []).map(Number);
    if (!n.length) return c;
    if (/^oklab/.test(c)) return c;                       // rough; do not convert oklab yourself
    if (n.length >= 3 && !/%| /.test(c.replace(/[\\d.]+%?/g,'')) && n[0] <= 1.001) return c;
    return '#' + n.slice(0,3).map(v => Math.round(v).toString(16).padStart(2,'0')).join('').toUpperCase() +
           (n.length > 3 ? '@' + n[3] : ''); })();
  const out = {};
  document.querySelectorAll('*').forEach(e => {
    const s = getComputedStyle(e);
    [[s.color, 'text'], [s.backgroundColor, 'surface'], [s.borderTopColor, 'border']].forEach(([c, art]) => {
      const h = hexOf(c);
      if (h.indexOf('#') !== 0) return;
      (out[h] = out[h] || { n: 0, kinds: {}, role: '' }).n++;
      out[h].kinds[art] = (out[h].kinds[art] || 0) + 1;
      if (!out[h].role) { const t = (e.innerText || '').trim().slice(0, 30);
        if (t) out[h].role = t; }
    });
  });
  return JSON.stringify(Object.entries(out).sort((a,b) => b[1].n - a[1].n).slice(0, 20), null, 1);
})()"""))
```

Evaluation: the frequency shows which color is structural, the first occurrence gives the role
(label text, legend dot, bar segment). **State the opacity too** — the same text color
occurs as 100 / 80 / 65 % and means primary / secondary / meta text. In the end, address
which colors **no longer** occur (the replaced glaring tones): that shows that the change has
landed.

## 2. Color chart as PNG (illustration, not proof)

One line per color: color swatch, hex, name, meaning; group headings in between; for text
additionally a proof strip in the respective opacity on light and on dark. With
`uv run --with pillow` and `ImageFont.truetype` on a DejaVu Sans (Debian:
`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`) — the PIL default font is unreadably small.
The numbers come from the measurement, the image is only the representation.

## 3. Interactive board (`tools/color-board.html`, shipped with this skill)

Single HTML file, no server — structure and pitfalls of this file type:
`single-file-html-prototype` (classic script at the end of the body, no `type=module`,
`localStorage` in try/catch).

- **Structure:** six groups (surfaces, text, border, abilities, consumption, state), 20 values.
  Each line: color picker + hex field. The matching inputs are added per role type — labels:
  palette color **and** text color **and** surface share in percent; text lines: opacity;
  series: dot full and bar at 70 %.
- **Behavior:** recompute while typing (`input` event), plus a button "Redraw
  everything", a button "Reset to defaults", values in browser storage (try/catch —
  not guaranteed on `file://`, hence the output block as a backup).
- **Output block at the bottom** = ready-made theme snippets (raw values, `seriesColors`, the `customCSS` lines)
  with "Copy output". Above it, values are sent back that go 1:1 into the theme — without retyping.
- **The defaults mirror the active theme.** After every theme change, pull the defaults along,
  otherwise the board shows an old state and the decision is made on a wrong basis.

### Pitfalls during construction (all actually occurred)

- **An opacity field without a default computes with 0 %.** `Number('') === 0`, and a mix with
  a share of 0 yields white. Symptom: the board reports "on white: 1.00:1 · effective
  #FFFFFF" for dark text and appears broken. The cause was a default taken from the wrong data field (`anteil`
  instead of `alpha`). When building, set every numeric value explicitly and store the default in the field itself,
  so that "Reset" finds it again.
- **Evaluate text lines only against the LIGHT surface.** The dark sample strip is only for
  viewing; if it is included in the evaluation, every dark text reports 1.00:1 "too low".
- **Border lines need their own measure.** A card border sits at 1.18:1 against the canvas and
  is still correct — here what counts is visibility against the canvas (threshold ~1.15), not 4.5.
  Without a dedicated rule the board classifies its own borders as errors.
- **Three tiers instead of two:** >= 4.5 "good", 3.0-4.5 "sufficient for large text only", < 3.0
  "too low". With two tiers the board raises the alarm on the theme's meta tones (65 % opacity sits
  at 3.2:1) and thereby becomes implausible.

### Proof that the board works

Open it in a real browser and **exercise behavior**, not just load it: `new_tab("file://.../tools/color-board.html")`,
set the hex field, trigger the `input` event, read the computed surface, cross-check the output block.
Before checking the defaults, clear the storage (`localStorage.clear()` + reload), otherwise you
test the state of the last run. Recipe: `single-file-html-prototype`, section Verification.

## Always report weak spots with the number

The board computes the contrasts itself and shows them immediately. This list is therefore **not a state,
but a finding** — it changes with every decision and is not kept up to date in the skill;
the current state is in the board and in the theme.

- **Contrast is a consequence of the surface strength, not of the text color alone.** If only the
  share is increased (reasoning 14 % -> 35 %), the contrast of the text on its own surface
  falls (4.67 -> 3.42:1) — the text stayed, the surface became stronger. After every share change,
  measure again and name the number.
- **With too-low contrast, do not secretly turn the surface back down** — the choice stands. Instead
  offer two to three darker tiers **of the same** hue with their computed values, so that a
  selection is all that is needed.
- **Graphics and text have different thresholds:** 3.0 for legend dots and bars, 4.5 for
  small text. A series dot below 3.0 is not an error, but worth mentioning.
- When demonstrating, name them, do not hide them: the numbers are the proof that something was computed and not
  decided by taste.

## Board and dashboard must show the same number

After every theme change, pull the defaults in the board along and **cross-check**: measure the same role in the board
and in the running dashboard. Two identical numbers (e.g. 3.42:1 for reasoning) prove in one
go that the theme change has landed and that the board is not deciding on an old state.
If they diverge, the board was not pulled along — not the theme.
