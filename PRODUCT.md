# Product

## Register

product

## Users

Fraud analysts at a financial institution (bank / NBFC), working an investigation queue under real time pressure — every transaction they leave unreviewed is exposure. Their context: dense case lists, dashboards, and a single investigation view they live in for minutes at a stretch, cross-referencing risk signals against a fraud ring graph and a pattern library. The job to be done on any given screen is triage and decision: is this transaction clear, review, block, or block-and-report — and can they justify that decision to a regulator later. A thin marketing landing page sits in front of the console for evaluators/judges and prospective institutional buyers, but the console is what the product actually is.

## Product Purpose

FraudLens is an AI fraud-detection platform: six independent scoring agents (rule, velocity, behavioral, graph, ML, Fraud DNA) feed a weighted ensemble decision, with bounded, always-human-reversible autonomous action (auto-hold, account-level velocity restriction) on high-confidence cases. Built for a hackathon grand finale, but designed to read as production-grade — the actual fraudsters and regulators it's modeled against don't care that it's a hackathon entry. Success looks like: an analyst can see why a transaction was flagged, trust the recommendation, act on it in one motion, and produce a defensible regulatory-context report afterward.

## Brand Personality

Forensic, precise, composed. A financial-crime operations tool, not a consumer app — it should feel like an instrument an analyst trusts under pressure, not a marketing surface. Confidence without noise; density without clutter.

**Anti-references** — explicitly reject:
- Generic hackathon-demo SaaS: gradient hero text, cream/sand/warm-neutral backgrounds, identical icon-in-circle card grids repeated without variation, tiny uppercase tracked eyebrows above every section, the hero-metric template (big number + label + gradient accent).
- Anything that reads as a template nobody made a decision about — every visual choice should trace to either a real risk-state semantic (the existing risk-tone color system) or a deliberate brand choice, never decoration for its own sake.

## Design Principles

1. **Every color means something.** Risk-tone colors (`--risk-low/medium/high/critical`) are reserved strictly for actual risk states — never reused decoratively. The brand accent (emerald) and Fraud DNA/network accent (amber) are the only other named colors in the system; anything else is a token misuse.
2. **Density with hierarchy, not clutter.** Analysts scan this all day — real information density is correct for this register, but it must be organized (spacing rhythm, alignment, one clear primary action per view), not just packed.
3. **Explainable over impressive.** Every score, badge, and recommendation must be traceable to a real reason string from a real agent — no decorative stat that doesn't correspond to actual backend data. This extends to the landing page: live numbers, not fabricated ones.
4. **Bounded autonomy, always visible.** Anywhere the system acts on its own (auto-hold, account restriction), the UI must make that legible and reversible — never a silent action.
5. **Consistency is the deliverable.** One heading convention, one hover language, one spacing scale, applied identically across all nine console surfaces plus the landing page — inconsistency here reads as "hackathon," which is the single thing this product must not read as.

## Accessibility & Inclusion

WCAG AA as the baseline target (4.5:1 body text contrast, 3:1 for large/bold text) — not yet formally audited. `prefers-reduced-motion` is already respected across existing motion (panel fade-ins, hover lifts, scroll reveals, count-ups) and must stay respected in anything new. No other accessibility requirements have been specified by the team; flag anything found during an audit rather than assuming further constraints.
