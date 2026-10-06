# HSS Study Voice — Design Guide (Process Academy)

## Source of truth

The visual language is **Process Academy**, in two themes (light and a derived dark).

- Tokens: `frontend/src/hss/tokens.css` — the only place colors, fonts, sizes, radii and shadows are defined.
- Components: `frontend/src/hss/bundle.css` (`hss-` classes: button, chip, icon button, panel, study row, player, progress bar).
- Layout: `frontend/src/styles.css`. It reads tokens only; no raw colors or sizes.
- `frontend/src/hss/components/*` and `tokens.json` are legacy HSS Music reference docs and no longer describe the live styles.

Theme switching only swaps token values (`:root[data-theme="light" | "dark"]`, plus `prefers-color-scheme` when no attribute is set). Never write per-theme color rules in components.

## Tokens

| Role | Token |
| --- | --- |
| Page / cards / fields (dark: raised) | `--surface-primary` / `--surface-muted` / `--field-bg` |
| Inverted chip (selected chip, "Ouvir") | `--surface-inverted` + `--ink-on-inverted` |
| Text / secondary text | `--ink-primary` / `--ink-secondary` |
| Primary action (one per section) | `--accent-coral` + `--ink-on-accent` |
| Links, focus, progress | `--accent-blue` |
| Decorative blob only | `--accent-orange`, `--accent-gold` |
| Field and chip borders | `--border-input` |
| Success / error (always icon + text) | `--state-success` / `--state-error` |
| Shadows | `--shadow-float` (one floating element per section), `--shadow-button` (primary CTA only) |

Type: Onest only. Scales are `--type-*` (display 80/88, headline 55/61, subhead 32/40, body-large 24/36, body 18/28, body-small 15/22, label 16/20, caption 13/18). Below 640px, headline, subhead and body-large shrink. Spacing `--space-*`, radii `--radius-small|medium|large|full`; no square corners.

## Rules

- Coral is the only primary action. The card's featured action ("Ouvir") is `--surface-inverted`; other actions are 2px outline pills; "Remover" is `--state-error` with a trash icon.
- Focus: 3px `--accent-blue` ring on every control; field focus also turns the border blue.
- Hover: `translateY(-2px)` in 150ms, disabled under `prefers-reduced-motion`.
- Touch targets are at least 44px.
- Status icons (check, alert, trash) are CSS masks, so no markup was added.

## Documented deviations

- Light `--ink-secondary` uses 0.75 alpha (0.65 gave ~4.1:1).
- Light `--state-success` is `#075a37` and `--state-error` is `#b82418`; the specified values fail 4.5:1 on cream.
- The CTA label is 19px/700 so white on coral qualifies as large text (3:1).
