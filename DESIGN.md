# HSS Study Voice — Design Guide (built on the HSS Music design system)

## Source of truth

HSS Study Voice does not define its own visual language. It consumes the **HSS Music** design system.

- Tokens: `frontend/src/hss/tokens.css` (compiled from HSS Music `tokens.json`).
- Components: `frontend/src/hss/bundle.css` (classes prefixed `hss-`).
- Reference docs: `frontend/src/hss/README.md` and `frontend/src/hss/components/<Component>/README.md` (each has a `preview.html` with copy-ready markup).
- `frontend/src/styles.css` only imports the two files above and holds Study Voice layout rules. It must not declare colors, fonts, radii or shadows of its own.

Import order, once, at the app root:

```css
@import "./hss/tokens.css";
@import "./hss/bundle.css";
```

Load the fonts (Figtree 400/700/800 and DM Mono 400) and set `<html lang="pt-BR" data-theme="dark">`. Wrap the app in an element with class `hss-surface`.

If a token or component you need does not exist, do not invent a color or style. Compose from existing tokens and flag the gap in your summary.

## Direction

The product keeps its structure: the **creation desk** is the primary surface and the **local archive** comes second, as a compact program index. Visually it follows HSS Music: dark-first, flat layered panels, pill controls, one accent used sparingly. Keep one clear action path per screen.

## Color

Use tokens only. Never hardcode hex values and never use `transparent`, `white` or `black` in place of a token.

| Role | Token |
| --- | --- |
| Window background, gaps between panels | `--bg-canvas` |
| Main panels (creation desk, archive) | `--bg-panel` |
| Inputs, chips, raised cards | `--bg-raised` |
| Hover and pressed rows | `--bg-hover` |
| Menus, popovers, dialogs | `--bg-overlay` + `--shadow-menu` |
| Primary text / secondary / metadata | `--text-primary` / `--text-secondary` / `--text-muted` |
| Disabled controls only | `--text-disabled` |
| Principal action, active indicator | `--accent` (hover `--accent-hover`, pressed `--accent-press`) |
| Text on the accent | `--on-accent` (never white) |
| Accent as text or icon | `--accent-text` |
| Dividers, input borders | `--border-subtle` / `--border-strong` |
| Focus | `--focus-ring` |
| Validation and operational failures | `--danger` (also `--warning`, `--info`) |

Rules:

- **At most one accent point per screen**: the principal action (for example "Criar áudio") or the playing item. Two `primary` buttons means one should be `secondary`.
- Text always uses one of the three text levels.
- Status (`danger`, `warning`, `info`) always comes with a word or an icon, never color alone.

### Themes

- `dark` is the default.
- `light` is the editorial theme: panels are white and separated by `--border-subtle` lines (class `hss-panel`), without gray layers. It is the closest match to the original editorial public-radio direction. Switch with `document.documentElement.dataset.theme = "light" | "dark"`.
- Test every new surface in both themes.

## Typography

- Family: `--font-sans` (Figtree) at weights 400, 700 and 800. Use `--font-mono` (DM Mono) only for durations, positions and counters, with tabular figures.
- Styles: `display` for large page heads, `headline` for the product name and feature callouts, `title` for section titles, `subtitle` for entry names, `body` and `body-sm` for reading and support text, `label` for buttons and chips, `caption` and `time` for metadata.
- Hierarchy comes from weight and color, not size. Keep body at 14–16px and headings compact.
- Sentence case everywhere. **No ALL CAPS and no tracked uppercase labels**, including section titles, buttons and metadata.
- Product name "HSS Study Voice" is set in `headline` at weight 800 until a logo exists.

## Layout and shape

- Spacing uses the 4px scale (`--space-1` to `--space-8`). Content gutter is `--space-4`, panel gap is `--space-2`.
- The app is a stack of flat panels (`--bg-panel`, `--radius-lg`) over `--bg-canvas`. No borders and no shadows on panels in the dark theme. Shadows exist only on floating elements (`--shadow-menu`).
- Desktop: creation desk panel first, archive panel second, asymmetric widths. Mobile: one reading sequence, nothing hidden or clipped horizontally.
- Anything clickable on its own is a pill (`--radius-pill`): buttons, chips, search. Thumbnails use `--radius-sm` or `--radius-md`. Panels use `--radius-lg`.
- Control heights: `--size-control-sm` (32px), `--size-control-md` (48px), `--size-control-lg` (56px, main play button).
- No gradients. No decorative card grids: use cards (`hss-card`, `hss-shelf-*`) only when the content is a browsable set.

## Components

Use the HSS Music classes on top of `hss-surface`. Do not restyle them.

| Study Voice need | HSS Music component |
| --- | --- |
| Primary action ("Criar áudio") | `hss-btn hss-btn-primary` (one per screen) |
| Secondary actions | `hss-btn-secondary`, `hss-btn-tertiary`; compact: `hss-btn-sm` |
| Icon-only actions | `hss-iconbtn` (needs `aria-label`) |
| Text entry and search | `hss-search` for search; inputs and textareas use `--bg-raised`, an explicit visible label and the focus ring |
| Archive entries | `hss-row` (TrackRow) or `hss-libitem`: label, creation time, duration, progress. Playing entry gets `is-playing` and keeps the play glyph, not color alone |
| Playback | `hss-player` (PlayerBar) with the main play button `hss-iconbtn-play` |
| Filters (for example by status) | `hss-chip` with `aria-pressed` |
| Context actions (rename, delete) | `hss-menu` |

- Archive entries must not load study assets just to render the list.
- Status messages stay close to the action that produced them and use `aria-live` when updated dynamically.
- Empty and failure states explain the condition in plain language without replacing the whole page.

## Content and copy

Text is in Brazilian Portuguese, direct, with "você".

- Imperative verbs, one action per button: `Criar áudio`, `Buscar`, `Tentar de novo`.
- Metadata uses type, middle dot and owner: `Áudio • Harry Sousa`.
- No emoji. No exclamation marks.
- Empty state: say what will appear and how to start. Example: `Seus áudios aparecem aqui. Crie o primeiro acima.`
- Error: say what happened and what to do. Example: `Não foi possível salvar este áudio. Você ainda pode ouvi-lo agora.`

## Icons

HSS Music ships no icon files. Use 16px (inline) and 24px (navigation and player) SVG glyphs with `fill="currentColor"`, solid for the active state and outline for inactive, inheriting `--text-secondary` or `--text-primary`. Never use emoji as icons.

## Interaction

- Hover lightens the surface to `--bg-hover`; buttons grow 4% and return on press. Motion is brief and functional, never required to understand state.
- Respect `prefers-reduced-motion`: no scale or translate for those users.
- Focus is a solid 2px `--focus-ring` outline and is never removed. Verify it stays prominent on every surface, in both themes.
- A failed local save must not block immediate playback when valid audio is already available.

## Accessibility

- Preserve semantic labels and native controls.
- Maintain WCAG AA contrast for text and interactive states. Use `--accent-text` (not `--accent`) for accent-colored text, and `--on-accent` on accent fills.
- Do not communicate status through color alone.
- Test at desktop and narrow mobile widths, in dark and light, before shipping a new surface.

## Do / Don't

- Do compose from `hss-*` classes and tokens.
- Do keep one accent per screen.
- Don't add new colors, fonts, radii or shadows.
- Don't use amber, Archivo Narrow, Atkinson Hyperlegible, uppercase tracked labels or rectangular buttons from the previous Study Voice direction. They are retired.
