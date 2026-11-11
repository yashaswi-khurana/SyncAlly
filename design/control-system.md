# Form Control System

The frontend has one control surface. Every text input, textarea and select in the app renders
with the same frame, height, radius, type size, placeholder colour and focus ring, no matter
which page or panel it lives on. This note records the rules so future components extend the
system instead of adding a fifth variant of "a box you type in".

## 1. The base layer

`frontend/src/styles.css` defines the base control once, at zero specificity:

```css
:where(input, textarea, select):where(:not([type="checkbox"], [type="radio"], [type="range"], …)) { … }
```

- Zero specificity (`:where()`) means any component class can refine a control and still win —
  the base layer never needs `!important` and never fights a feature rule.
- The base layer deliberately excludes checkboxes, radios, ranges, files and buttons, so native
  controls stay native.
- Selects drop the platform chrome and draw one shared chevron (inline SVG data URI), because the
  three previous native arrows rendered at different sizes on every page.

## 2. Field anatomy

`.field` is the one wrapper for a labelled control:

```html
<div class="field">
  <label for="…">Label</label>
  <input id="…" />
  <p class="hint">Optional help</p>
  <p class="field-error" role="alert">Optional error</p>
</div>
```

- Order is always label → control → hint/error, with a 7px rhythm.
- `.field` sets `min-width: 0` and `align-content: start` so it never stretches a grid row or
  pushes its label away from its box.
- Labels are `0.82rem / 600 / var(--ink-soft)`. The previous uppercase Sourcing Hub labels were
  the only place that broke this, and now match.

## 3. States

| State | Treatment |
| --- | --- |
| Default | `1px solid var(--line-strong)` frame on `var(--surface)` paper |
| Hover | Frame lifts to the component's hover colour (auth card lifts its light frame) |
| Focus | `border-color: var(--accent)` plus a `3px var(--accent-soft)` ring, `outline: none` |
| Invalid | `aria-invalid="true"` gives a `var(--danger)` frame and soft danger ring |
| Disabled | `var(--surface-2)` fill, soft text, `not-allowed` cursor, `0.75` opacity |
| Read-only | Paper-subtle fill until focused, so it never looks editable |
| Placeholder | `var(--muted)` at full opacity — no more browser-default grey |

## 4. Surfaces with their own tint

Two surfaces intentionally re-tint the same geometry instead of re-defining controls:

- **Auth card** (dark green panel): light-on-dark inputs, 48px tall, warm focus ring (`#ef9a78`).
- **Sourcing Hub / modals**: slightly larger type (`0.9375rem`) and brighter `var(--surface)`
  fill, but the same 44px minimum height, frame and focus ring.

Both are implemented as refinements of the base layer, not replacements.

## 5. Choice controls

- `.control-rows` — a grid of checkbox/radio rows (permission bundles, approvers, deal access).
  Rows are 36px minimum, hover-tinted, with a 17px accent-tinted box aligned to the first line.
- `.check-row` — a single acknowledgement checkbox with a long label (proposal replacement,
  import confirmation). Same geometry as one `.control-rows` row.
- Bare `<fieldset>` groups (deal role, counterparty mode, case type) render as inline segmented
  chips: 44px tall, accent border and soft fill when the option is checked.
- `.message-composer__visibility` stays a hidden-input segmented control with an explicit
  `:focus-within` ring.

## 6. Rules for new components

1. Wrap labelled controls in `.field`; do not hand-roll block labels and margins.
2. Never re-declare `border`, `background`, `padding` or `border-radius` for a control to change
   its *shape* — only to change its *tint* on a dark surface.
3. Use `.input` when a control is not inside `.field` (compact rows, modal forms).
4. Use `.control-rows` for groups of checkboxes or radios; never inline `style={{ display:
   "block", margin: "6px 0" }}` on each label.
5. Keep copy in tests intact: placeholders, labels and button names are covered by the test suite.

## 7. Verification

- `npm test` — 544 frontend tests, including the deal case modal, invite modal and sourcing flows.
- `npm run lint:check` — ESLint plus `tsc --noEmit`.
- `npm run build` — production bundle.
- The stylesheets are parse-checked with `css-tree` (no parse errors, no duplicated declarations
  inside a rule, no `url()` outside a background shorthand).
