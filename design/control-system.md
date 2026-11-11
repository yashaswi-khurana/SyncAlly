# Form Control System

The frontend has one control surface. Every text input, textarea and select in the app renders
with the same frame, height, radius, type size, placeholder colour and focus ring, no matter
which page or panel it lives on. This note records the rules so future components extend the
system instead of adding a fifth variant of "a box you type in".

## 1. The base layer

`frontend/src/styles/base.css` defines the base control once, on the elements themselves:

```css
input:not([type="checkbox"], [type="radio"], [type="range"], [type="file"], [type="color"]),
select,
textarea { … }
```

- The rule has the specificity of one element plus one attribute. A refinement therefore needs a
  class *and* the element (`.sector-filter-controls select`, `.requirement-input-panel textarea`); a lone class on the
  control does not win. No refinement needs `!important`.
- Component stylesheets load after the shared layer (`src/main.tsx` imports `styles.css` before
  `App`), so a refinement of equal specificity wins too.
- The base layer deliberately excludes checkboxes, radios, ranges, files and colour inputs, so
  native controls stay native.
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
- Labels are `var(--text-sm)` (0.8125rem) / 560 / `var(--ink-2)`. The one exception is the
  sourcing hub's sector filter, whose label reads as a mono caption beside its select.
- A `<label>` that wraps its control directly (marketplace, delivery, proposal editor) gets the
  same 7px rhythm without a `.field` wrapper.

## 3. States

| State | Treatment |
| --- | --- |
| Default | `1px solid var(--line-control)` frame on `var(--surface)`, 46px tall, `var(--r-sm)` radius |
| Hover | The frame darkens |
| Focus | `border-color: var(--accent)` plus the shared `var(--ring)` (4px `var(--accent-soft)`), `outline: none` |
| Invalid | `aria-invalid="true"` gives a `var(--danger)` frame, and a soft danger ring on focus |
| Disabled | `var(--surface-2)` fill, `var(--ink-3)` text, `not-allowed` cursor |
| Read-only | `var(--surface-2)` fill and mono type, so it never looks editable |
| Placeholder | `var(--ink-4)` at full opacity, not the browser-default grey |

## 4. Surfaces

Every surface uses the base control unchanged: the glass sign-in card, workspace cards, the
sourcing hub and dialogs. Where a control differs it is a refinement of the base layer, not a
replacement:

- The sourcing hub's sector filter is a pill-shaped select sized to its content.
- Rows of short fields (marketplace quantity, unit, price, currency) sit in a fixed column grid so
  a date input can never push its neighbours out of the card.

## 5. Choice controls

- `.control-rows` — a grid of checkbox/radio rows (permission bundles, approvers, deal access).
  Rows are 38px minimum, hover-tinted, with a 17px accent-tinted box aligned to the first line.
- `.check-row` — a single acknowledgement checkbox with a long label (proposal replacement,
  import confirmation). Same geometry as one `.control-rows` row.
- Bare `<fieldset>` groups (deal role, counterparty mode, case type) render as inline segmented
  pills: 44px tall, accent border and soft fill when the option is checked. These rules are
  written with `:where()` at zero specificity, so any component class overrides them.
- `.message-composer__visibility` stays a hidden-input segmented control with an explicit
  `:focus-within` ring.

## 6. Rules for new components

1. Wrap labelled controls in `.field`; do not hand-roll block labels and margins.
2. Never re-declare `border`, `background`, `padding` or `border-radius` for a control to change
   its *shape* — only to change its *tint* on a dark surface.
3. A control outside `.field` (compact rows, modal forms) needs no class: the base layer styles
   the element. Existing `className="input"` attributes are harmless and carry no rules.
4. Use `.control-rows` for groups of checkboxes or radios; never inline `style={{ display:
   "block", margin: "6px 0" }}` on each label.
5. Keep copy in tests intact: placeholders, labels and button names are covered by the test suite.

## 7. Verification

- `npm test` — 555 frontend tests, including the deal case modal, invite modal and sourcing flows.
- `npx eslint src` — lint.
- `npx vite build` — production bundle.
- `npm run lint:check` and `npm run build` also run `tsc --noEmit`, which currently stops on a type
  error in `src/deals/AISuggestionReview.tsx` (line 279, `.size` read on an array). That error is
  in application logic and predates the control system.
