---
name: FraudLens
description: AI fraud intelligence and regulatory case-ops console
colors:
  canvas: "#050807"
  panel-solid: "#101a15"
  foreground: "#f2f5f3"
  muted: "#a5b0aa"
  border: "#b4dcc824"
  emerald: "#16a36a"
  amber: "#d88a45"
  risk-low: "#12b76a"
  risk-medium: "#f79009"
  risk-high: "#f04438"
  risk-critical: "#f04438"
typography:
  display:
    fontFamily: "Inter, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(2.25rem, 4vw, 3.375rem)"
    fontWeight: 800
    lineHeight: 1.08
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Inter, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    letterSpacing: "0.05em"
  numeric:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontWeight: 400
rounded:
  control: "8px"
  panel: "14px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
components:
  panel:
    backgroundColor: "{colors.panel-solid}"
    rounded: "{rounded.panel}"
    padding: "20px"
  stat-card:
    backgroundColor: "{colors.panel-solid}"
    rounded: "{rounded.panel}"
    padding: "16px 20px"
  button-primary:
    backgroundColor: "{colors.emerald}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "14px 24px"
  badge-risk:
    rounded: "{rounded.control}"
    padding: "2px 10px"
---

# Design System: FraudLens

## 1. Overview

**Creative North Star: "The Forensic Terminal, Rebuilt for Trust"**

FraudLens is an instrument, not a marketing surface — a near-black operations console an analyst lives inside for their entire shift, where every color, badge, and number carries a real consequence. The system rejects the two easy failure modes of a hackathon build: the generic warm-neutral SaaS template (cream backgrounds, gradient hero text, identical card grids, tiny uppercase eyebrows on every section), and the opposite over-correction into a cosplay "hacker terminal" (all-caps everywhere, one monospace font for all text, no real typographic hierarchy — which is exactly what this system looked like before this pass). The resolution is a near-black, high-density console where a real sans typeface (Inter) carries hierarchy and voice, and monospace (JetBrains Mono) is reserved strictly for the numbers and identifiers an analyst is actually verifying — amounts, scores, transaction IDs, timestamps.

**Key Characteristics:**
- Near-black canvas, translucent glass panels, one emerald brand accent used sparingly
- Risk-tone color (green/amber/red/crimson) is the only place color carries urgency — never decorative
- Sans for reading, mono for verifying — never mixed within the same semantic role
- Density is correct for this register; alignment and consistent spacing keep it legible, not cluttered

## 2. Colors

A near-black operations palette with one warm-emerald brand accent and a strictly-reserved risk-tone system layered on top.

### Primary
- **Signal Emerald** (`#16a36a`): the one brand accent — primary CTAs, active nav state, links, focus rings, the landing page's "live" indicator. Used sparingly; if more than roughly a third of a screen is emerald, something has drifted from the brand's restraint.

### Secondary
- **Ring Amber** (`#d88a45`): reserved for Fraud DNA / fraud-ring / network-intelligence content specifically — deliberately distinct from the risk-medium amber tone so "this is pattern-library intelligence" never reads as "this is a medium-risk warning."

### Neutral
- **Deep Canvas** (`#050807`): the page background, with a faint radial emerald/amber glow — never flat black.
- **Panel Ink** (`#101a15`): solid panel surfaces (cards, dropdowns, the sticky decision bar).
- **Glass Panel** (`rgba(14,29,22,0.55)`): the translucent default panel surface, paired with `backdrop-blur`.
- **Foreground Mist** (`#f2f5f3`): primary text.
- **Muted Sage** (`#a5b0aa`): secondary text, labels, timestamps.
- **Hairline Border** (`rgba(180,220,200,0.14)`): every panel/card border and divider.

### Named Rules
**The Reserved Signal Rule.** Risk-tone colors (`--risk-low` `#12b76a`, `--risk-medium` `#f79009`, `--risk-high` / `--risk-critical` `#f04438`) exist only to represent an actual risk state on an actual case — a decision badge, a score bar, an audit-event dot. They are never repurposed as a decorative accent, a chart color for non-risk data, or a "pop of color." If a color choice can't be traced to a real risk state, it isn't one of these four.

## 3. Typography

**UI Font:** Inter (with `-apple-system, Segoe UI, sans-serif` fallback)
**Numeric/Identifier Font:** JetBrains Mono (with `ui-monospace, monospace` fallback)

**Character:** Inter carries every heading, label, and sentence of prose — it's what gives this system real weight hierarchy after the previous single-mono-font pass silently dropped every bold heading to regular weight. JetBrains Mono is reserved strictly for things an analyst is checking character-by-character: amounts, risk scores, transaction/account/ring IDs, timestamps. The pairing is a deliberate contrast axis (humanist sans for reading, monospace for verifying), not decoration.

### Hierarchy
- **Display** (extrabold 800, `clamp(2.25rem, 4vw, 3.375rem)`, line-height 1.08, letter-spacing -0.02em): landing-page hero headline only.
- **Headline** (semibold 600, 1.25rem, tracking tight): console page `<h1>` titles. One consistent size and weight across all nine console surfaces — this was previously inconsistent (one page ran a full size smaller) and is now fixed at this single value everywhere.
- **Title** (semibold 600, 0.875–1rem): panel section headers, card titles.
- **Body** (regular 400, 0.875rem, line-height 1.6): prose, descriptions, table cells.
- **Label** (semibold 600, 0.6875rem, tracking +0.05em, uppercase): panel eyebrow headers (`Panel`'s own title slot), stat card labels — the one place uppercase-tracked text is earned, because it's a structural section label, not a decorative kicker repeated above every block.
- **Numeric** (JetBrains Mono, regular, tabular-nums): amounts, scores, IDs, timestamps — anywhere precision matters more than voice.

### Named Rules
**The Verify-in-Mono Rule.** If a value is something an analyst double-checks digit-by-digit (₹ amount, risk %, TXN-/ACC-/RING-id, a timestamp), it renders in JetBrains Mono with tabular figures. Everything else — including numbers inside a sentence — stays in Inter.

## 4. Elevation

Flat-by-default translucent glass, not drop-shadow depth. Panels sit on the canvas via `backdrop-blur` plus a soft ambient shadow that reads as "floating slightly," not "casting a hard shadow." A `raised` variant (used for exactly one primary panel per page — the sticky decision bar, the top recommendation panel) gets a stronger ambient shadow to mark it as the page's single most important surface; every other panel stays at the base level so that emphasis stays meaningful.

### Shadow Vocabulary
- **panel** (`inset 0 1px 0 rgba(255,255,255,0.03), 0 8px 20px rgba(0,0,0,0.35)`): default panel/card elevation.
- **panel-raised** (`inset 0 1px 0 rgba(255,255,255,0.04), 0 8px 28px rgba(0,0,0,0.45)`): the one emphasized panel per page.

### Named Rules
**The One Raised Panel Rule.** At most one panel per page uses the raised shadow. If everything is raised, nothing is.

## 5. Components

### Buttons
- **Shape:** 8px radius (`--radius-control`) on every button, no exceptions.
- **Primary:** emerald gradient fill (`linear-gradient(135deg, rgba(31,167,116,0.9), rgba(18,103,70,0.9))`), white text, 14–24px padding depending on context.
- **Decision buttons** (Clear/Review/Block/Block & Report): outlined by default, fill with the matching risk tone when selected — never colored unless selected.
- **Hover / Focus:** `.hover-lift` — 3px upward translate plus a brightened emerald border, 0.25s exponential ease-out. Focus-visible always gets an explicit 2px emerald outline; never rely on the browser default.

### Cards / Panels
- **Corner style:** 14px radius (`--radius-panel`).
- **Background:** translucent glass (`--panel`) by default; solid ink (`--panel-solid`) for surfaces that must stay legible over moving content (sticky bar, dropdowns).
- **Border:** 1px hairline (`--border`) all around; a risk-tone-colored 3px left border is added only when the card represents an actual risk-scored case (`CaseListItem`, the case-summary accent) — this is the one sanctioned use of a colored side border in the system, because it carries real risk-state meaning rather than decoration.
- **Internal padding:** 16–20px.

### Badges
- **Style:** pill or slightly-rounded rectangle, risk-tone background tint (12–16% opacity) with the same tone as text — never a solid risk-tone fill behind white text except the topmost decision banner.
- **Examples:** AUTO-HELD (medium tone), FALSE POSITIVE (emerald solid — a correction, not a risk state), ACCOUNT RESTRICTED (amber tint).

### List Rows / Tables
- **Style:** no card chrome for dense lists (audit trail, reports table) — a hairline row divider and a token-driven hover background (`rgba(22,163,106,0.07)`) instead. This replaced a prior hardcoded `hover:bg-black/5 dark:hover:bg-white/5` that did nothing (the app has no light/dark toggle).

### Navigation
- **Style:** fixed 220px left sidebar, graphite background, active item gets an emerald-tinted background plus a 2px inset left accent bar. Nav labels are the single source of truth for what a page is called — page `<h1>`s and breadcrumbs must match the nav label verbatim (previously drifted: "Alerts" in nav vs. "INVESTIGATION FEED" as the page's own h1).

## 6. Do's and Don'ts

### Do:
- **Do** reserve JetBrains Mono for amounts, scores, IDs, and timestamps only — Inter everywhere else.
- **Do** keep every page `<h1>` at the same size/weight/tracking, and matching its own nav label and breadcrumb exactly.
- **Do** add real hover feedback (`.hover-lift` or `.hoverable-row`) to anything interactive; a static list row or card reads as unfinished.
- **Do** ground every landing-page number in a real API call — no fabricated stat.

### Don't:
- **Don't** use a gradient on text (`background-clip: text`) — solid color only, emphasis via weight/size.
- **Don't** use a colored `border-left`/`border-right` as decoration — the only sanctioned use is the risk-tone accent on an actually-risk-scored case card.
- **Don't** repeat the identical icon-in-circle treatment across a card grid without variation — six agents got six distinct icons for exactly this reason.
- **Don't** put a tiny uppercase tracked eyebrow above every section — earned only as a Panel's structural label, never as a decorative kicker repeated site-wide.
- **Don't** use the cream/sand/warm-neutral background band, anywhere — this system is near-black canvas or nothing.
- **Don't** reuse a risk-tone color (`--risk-low/medium/high/critical`) for anything that isn't an actual risk state.
