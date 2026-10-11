> **Note: this repository was created with the help of AI.**
> The themes, the skill and the tooling were built in a collaboration between a human author
> (direction, design decisions, review) and **Hermes Agent** (implementation, measurements, text).
> Every claim here was checked against a running dashboard, but read the code before you rely on it.

# hermes-dashboard-theming

Light and dark, clean, rounded themes for the **Hermes web dashboard** — plus the skill and the
tooling that an agent needs to build themes like them on its own.

Three things live in this repository:

| What | Where | What it is |
|---|---|---|
| The themes | `themes/light-clean.yaml`, `themes/dark-clean.yaml` | Two YAML files. Drop them in, pick them in the dashboard. |
| The skill | `skills/hermes-dashboard-theming/` | Instructions an agent loads to restyle a dashboard: schema, procedures, pitfalls, verification recipes. |
| The color board | `tools/color-board.html` | A single-file page for trying out hex values live: swatch, example badge, derived fills, WCAG contrast, ready-to-paste snippet. |

Every screenshot below shows the same view twice: **light on the left, dark on the right.**

## The themes

![Dashboard — models](screenshots/models-light-dark.png)

Both themes are one shape with two surfaces. Light: canvas `#F8F9FB`, cards white. Dark: canvas
`#0F1115`, cards `#171A21`. Everything else is shared — one modern sans-serif (Inter) for the whole
UI, rounded corners everywhere, `1rem` radius, the noise/grain overlay switched off, and colour used
only as an accent on buttons, badges and status marks. The roles invert where they must: the light
theme's near-black buttons become light buttons with dark labels in the dark theme.

**Switching is a selection in the dashboard itself:** open the theme control at the bottom of the
sidebar and pick *Light Clean* or *Dark Clean* — every entry shows its description, next to the
stock themes. The theme directory is read once per page load, so anything dropped into
`$HERMES_HOME/dashboard-themes/` appears in that list.

![Theme picker](screenshots/theme-picker-light-dark.png)

![Skills page](screenshots/skills-light-dark.png)

![Chat](screenshots/chat-light-dark.png)

The chat page keeps its terminal dark in both themes — the dashboard paints that panel itself. The
session list on the right is blurred in these screenshots; it shows real session titles.

![On a phone](screenshots/phone-models-light-dark.png)

**Install**

```bash
mkdir -p "$HERMES_HOME/dashboard-themes"          # default: ~/.hermes/dashboard-themes
cp themes/light-clean.yaml themes/dark-clean.yaml "$HERMES_HOME/dashboard-themes/"
hermes config set dashboard.theme light-clean      # or: dark-clean
```

Then reload the dashboard page completely (a plain reload is enough; the theme list is fetched once
per page load) — or simply pick the theme in the UI as described above. Revert any time with
`hermes config set dashboard.theme default`.

Requires a Hermes version whose web dashboard reads user themes from
`$HERMES_HOME/dashboard-themes/` (verified against v2026.9.24).

## The skill

Install it as a **skill tap** — a plain GitHub repository of `SKILL.md` files, no registry, no
server:

```bash
hermes skills tap add Faultbendfold/hermesagent-dashboard-theming
```

Or copy the directory into your own skill tree:

```bash
cp -r skills/hermes-dashboard-theming "$HERMES_HOME/skills/devops/"
```

The skill is written for an agent, not for a human reading it top to bottom. It covers:

- the theme schema (palette, typography, layout, `colorOverrides`, `componentStyles`, `customCSS`)
  and which of those fields the shipped build actually reads;
- the three-layer palette and how every derived token cascades from it;
- the light recipe, and how to derive the **dark counterpart** from it — which roles invert, which
  surfaces stay, which tones have to be lifted;
- how to reach the things a theme *cannot* reach — hard-coded Tailwind colours, inline styles,
  the button bezel, the animated button ring, `rounded-none` surfaces;
- measuring instead of guessing: reading computed styles in a real browser, counting rounded
  elements, stacking translucent backgrounds before computing contrast;
- pitfalls that cost hours otherwise, each with the probe that proves it.

Supporting material lives next to it: `references/*.md` (deep dives per topic, including
`contrast-checking.md` with its three classic false alarms), `templates/light-clean-theme.yaml`
(a starting point), `scripts/gen_dashboard_themes.py` (builds a whole family of themes from a palette
list).

## The color board

Open `tools/color-board.html` in any browser — no server, no build, no network. Type a hex value or
use the colour picker on the left; the panel on the right updates live with the resulting swatch, an
example badge, the derived surface and border mixes, and the WCAG contrast against the surfaces the
colour actually sits on. The text area at the bottom prints the values and the ready-to-paste theme
snippet.

![Color board](screenshots/color-board.png)

## Notes

- **Dashboard themes are not CLI skins.** The terminal look is themed by `display.skin` and files in
  `$HERMES_HOME/skins/`; the web dashboard is themed by `dashboard.theme` and files in
  `$HERMES_HOME/dashboard-themes/`. Two systems, two directories.
- A theme is a runtime drop-in: no rebuild, no fork, no patching of the dashboard source. It
  survives application updates because it lives in the persistent Hermes home, not in the app.
- Colour values are plain `#rrggbb`. Contrast targets: text against its real background ≥ 4.5:1,
  large graphics ≥ 3:1, button label against its fill ≥ 3.2:1.
- The screenshots are composited from two captures of the same page — same viewport, same state,
  only the theme changed. `scripts/pair_screenshots.py` does that composition.

## License

MIT — see [LICENSE](LICENSE).
