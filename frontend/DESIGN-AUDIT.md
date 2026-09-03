# FraudLens frontend — design audit

Manual audit (no `unslop:audit` skill available in this environment — see PR
description) of `frontend/` against the design principles carried over from
this project's design guidance: plain-language summary before technical
evidence, monospace reserved for identifiers/numeric evidence, red/amber/
green reserved strictly for risk states, panel radii ≤8px, no nested cards.
Every claim below points at the file/line it comes from.

## 1. No typographic hierarchy — everything is Tailwind's default scale

`app/feed/page.tsx:14` (`text-lg font-semibold`) and every `Panel` title
(`components/Panel.tsx:13`, `text-xs font-semibold uppercase`) are the only
two type "styles" in the whole app. Body text, data values, and captions all
collapse to `text-sm`/`text-xs` with no considered scale, weight ladder, or
letter-spacing beyond the one uppercase panel label. Nothing visually
distinguishes "this is the primary recommendation" from "this is a caption"
except font-size steps borrowed straight from a Tailwind starter — there is
no product-specific type system.

## 2. Every surface gets identical treatment — no elevation, no priority

`Panel.tsx:9-11` applies the exact same `rounded-lg border px-5 py-4` to
every panel regardless of importance. On `/case` (`app/case/page.tsx`), the
Recommendation panel (the plain-language decision an analyst reads first)
is styled identically to the Fraud DNA match panel and the decision-submission
form at the bottom — same border weight, same radius, same padding, no
elevation or accent to anchor the eye. A console whose entire job is
triage has no visual hierarchy for what to look at first.

## 3. Generic Bootstrap-blue accent with no distinct identity

`globals.css:13` — `--cobalt: #2954e0` is a stock primary-blue with no
relationship to the rest of the palette; it reads as "whatever the
Tailwind starter shipped," not a considered brand color for a
fraud-investigation tool.

## 4. NavRail is an unstyled list, not a product shell

`components/NavRail.tsx` — a single link ("Alert Feed"), no icon, no visual
weight beyond a color swap on the active item, and the wordmark
(`FraudLens`, line 16-18) is plain white text with no mark or visual anchor.
It reads as scaffolding left over from bootstrapping the app, not a
finished shell for a professional console.

## 5. Feed table has no risk-scanning affordance

`app/feed/page.tsx:41-78` — every row gets identical borders/padding
regardless of severity. The only color signal live on the page is inside
`DecisionBadge`'s small pill (`components/DecisionBadge.tsx:7-9`); an
analyst scanning 25 rows has to read each badge individually rather than
pattern-match rows by position/color, which is exactly the kind of
triage affordance a fraud console should offer first.

## 6. DecisionForm's selection state ignores the risk-color language it already owns

`components/DecisionForm.tsx:46-51` — every option (`clear`/`review`/
`block`/`block_and_report`) highlights identically in `--cobalt` when
selected, even though these four options are literally the same four
decision/risk states `DecisionBadge` already colors via `DECISION_TONE`
(`lib/risk.ts:10-18`). The form doesn't reuse the risk-color vocabulary
it has right next to it, so selecting "Block & Report" looks exactly like
selecting "Clear."

## 7. No dark theme at all

`globals.css` defines exactly one `:root` palette with no
`prefers-color-scheme` handling. Every professional analyst/SOC tool
ships a dark theme; its total absence here is one of the more visible
"basic" tells.

## 8. Focus states are whatever the browser defaults to

No component defines an explicit `:focus-visible` treatment anywhere in
`frontend/`. That's a real WCAG 2.2 AA risk (2.4.11 Focus Not Obscured,
2.4.7 Focus Visible) resting entirely on browser/UA defaults rather than
a deliberate, on-brand, guaranteed-visible focus ring.

## What's already right (preserve, don't rebuild)

- Monospace is already applied correctly and only to identifiers/numeric
  evidence (`txn_id`, `account_id`, amounts, scores, timestamps) — see
  `app/feed/page.tsx:50-66` and `app/case/page.tsx:71-91`. Keep this
  discipline exactly as-is when introducing new typography.
- Risk colors (`--risk-low/medium/high/critical` + their `-bg` pairs,
  `globals.css:16-23`) are used correctly today — only on `DecisionBadge`,
  the suspicious-cluster flag (`app/case/page.tsx:153-159`), the Fraud DNA
  recommendation, and form success/error text. None of it is decorative.
  Preserve this scoping; do not introduce new decorative uses.
- No nested cards exist today (`dl` grids inside `Panel` carry no
  border/background of their own) — keep it that way.
- `SampleBanner` is already always-rendered from `app/layout.tsx:31`,
  above `<main>`, on every route. Keep it non-dismissible.

## Plan

1. Introduce a real type scale and a single `--radius` token (≤8px) used
   everywhere, instead of ad hoc Tailwind size classes per component.
2. Replace the generic cobalt accent with a more distinct, still
   professional accent; keep every risk-color hex value untouched.
3. Give `Panel` an optional elevation/priority variant so the
   Recommendation panel on `/case` reads as primary, not equal to every
   other panel.
4. Redesign `NavRail` with a real wordmark treatment and icon, keep it to
   the one existing route (do not add `/insights` — out of scope, not yet
   on this branch).
5. Add a risk-tone left-edge accent to feed rows and tie `DecisionForm`'s
   selected-option color to that option's own `DECISION_TONE` — reusing
   existing risk-color semantics, not adding new decorative color.
6. Add a `prefers-color-scheme: dark` palette, including dark-safe
   variants of the risk background colors (same hues, adjusted for
   contrast — meaning doesn't change).
7. Add explicit, on-brand `:focus-visible` styling globally.
