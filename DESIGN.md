# HSS Study Voice Design System

## Direction

HSS Study Voice uses an editorial public-radio language: focused, calm, and tactile rather than dashboard-like. The creation desk is the primary surface; the local archive reads as a compact program index. Interfaces should preserve one clear action path and avoid decorative card grids.

## Color

Core tokens live in `frontend/src/styles.css`.

- Ink (`--ink`): primary text and dark structural surfaces.
- Paper (`--paper`): main reading and working surface.
- Amber (`--amber`): primary action and active emphasis.
- Amber dark (`--amber-dark`): hover and pressed action state.
- Muted ink (`--muted`): secondary copy and metadata.
- Rule (`--rule`): dividers, input borders, and quiet structure.
- Error (`--error`): validation and operational failures.

Use amber selectively. It identifies the principal action, not general decoration.

## Typography

- Display: `Archivo Narrow`, condensed and assertive for mastheads and section titles.
- Body: `Atkinson Hyperlegible`, optimized for sustained reading and accessible controls.
- Metadata: uppercase, tracked labels with restrained sizing.

Keep headings compact and avoid oversized marketing-style copy. Numeric values use tabular figures where alignment matters.

## Layout

- Desktop uses an asymmetric editorial grid: creation desk first, archive second.
- Mobile becomes one reading sequence without hidden or horizontally clipped controls.
- Rules and whitespace establish groups; use containers only when they clarify structure.
- Controls remain full-width where text entry or playback benefits from available space.

## Components

- Buttons are rectangular, high-contrast, and visibly interactive. The primary button uses amber with ink text.
- Inputs and textareas use paper-toned surfaces, explicit labels, and strong focus outlines.
- Status messages remain close to the action that produced them and use `aria-live` when updated dynamically.
- Archive entries prioritize label, creation time, duration, and progress without loading study assets.
- Empty and failure states explain the condition in plain language without replacing the whole page.

## Interaction

- Motion is brief and functional, never required to understand state.
- Respect `prefers-reduced-motion`.
- Keyboard focus must remain prominent against both ink and paper surfaces.
- A failed local save must not block immediate playback when valid audio is already available.

## Accessibility

- Preserve semantic labels and native controls.
- Maintain WCAG AA contrast for text and interactive states.
- Do not communicate status through color alone.
- Test at desktop and narrow mobile widths before shipping a new surface.
