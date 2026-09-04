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

---

## Addendum — 2026-09-04: investigation-console redesign

Scope: rebuild the UI as an investigation console (persistent nav rail with
OVERVIEW/CASES/ALERTS/GRAPH/ENTITIES/PATTERNS, a compact feed with per-signal
bars, a restructured `/case` screen, an interactive fraud-ring graph) on
"Share Tech Mono" throughout. Per the brief for this pass, this section is
written *before* any component code — it's the data-availability map, the
layout plan, and a short list of things that need a decision before I build,
not a changelog of work already done.

**Process note, same standard as the first pass**: no `unslop`/`ui-ux-pro-max`/
`impeccable` skill exists in this environment (checked again — none
registered). This addendum is manual work, not the output of a skill run.

### Data-availability map

Read `fraudlens/api/routes/*.py`, `fraudlens/core/privacy.py`,
`fraudlens/models/schemas.py`, and `fraudlens/runtime.py` end to end for this.
Every backend route is listed in `fraudlens/api/main.py`: `/health`,
`/transactions/recent`, `/cases` (list) + `/cases/{txn_id}` (detail),
`/reports/{txn_id}`, `/decisions`, `/copilot/chat`. Nothing else exists.

| UI element needs | Real source | Status |
|---|---|---|
| "SYSTEM OK" top-bar indicator | `GET /health` → `{"status": "ok"}` | ✅ available |
| Product identity / wordmark | Static UI text, not data | ✅ n/a |
| Feed row: amount, decision, final_score, timestamp | `GET /transactions/recent` | ✅ available |
| Feed row: masked account id | `GET /transactions/recent` → `account_id`, **already masked server-side** (`mask_identifier` in `privacy.py`) | ✅ available, see clarification below |
| Feed row: per-signal bars (Device anomaly, Velocity pattern, Graph connection, ...) from `agent_scores` | `GET /transactions/recent` does **not** include `agent_scores` at all (only `top_reason`, one string) | ❌ missing from this endpoint — see Finding A |
| Case summary: risk tier, amount, masked account | `GET /cases/{txn_id}` → `final_score`/`decision`/`transaction.amount`/`transaction.account_id` | ✅ available |
| "Why this was flagged" | `GET /cases/{txn_id}` → `explanation_reasons`, `agent_scores[].reasons` | ✅ available (already used via `plainReason()`) |
| Risk-signal tree, per-agent score/severity | `GET /cases/{txn_id}` → `agent_scores[].score`/`confidence`/`reasons` | ✅ available |
| Risk-signal tree, structured detail (e.g. "which specific device/IP") | `agent_scores[].metadata` | ❌ **stripped server-side** — `public_case()` in `privacy.py` sets `score["metadata"] = {}` for every agent score before it ever reaches the frontend. See Finding B. |
| Fraud ring: node/edge structure | No endpoint returns `FraudGraph` (`nodes`/`edges`) — only the flat `GraphEvidence` summary (`connected_accounts`, `shared_devices`, `shared_ips`, `shared_merchants`, `ring_size`, `ring_id`, `graph_density`, `evidence_summary`) is ever exposed, via `case.graph_evidence` | ❌ missing — see Finding C, the important one |
| Fraud ring: which account is the flagged one | `case.transaction.account_id` (masked), matched against a graph node's label | ✅ available *if* Finding C is resolved |
| Node click detail: device/IP label | Would come from `GraphNode.label` on the new graph endpoint (Finding C) — node identifiers need the same masking `public_case()` already applies to `graph_evidence.shared_devices`/`shared_ips` | ⚠️ available only if Finding C is resolved, and only masked |
| Node click detail: transaction count | Not directly — but `GraphEdge.weight` already accumulates "how many transactions used this account+device/IP pair" (see `GraphBuilder._add_edge` in `fraudlens/core/graph/builder.py`) — summable client-side from real edge weights once exposed | ⚠️ derivable, not direct, only if Finding C is resolved |
| Node click detail: flagged status | `GraphNode.is_suspicious` (real field, already computed) | ⚠️ available only if Finding C is resolved |
| Fraud DNA: typology, similarity, recommendation | `GET /cases/{txn_id}` → `fraud_dna_match.fraud_type`/`similarity_score`/`recommendation`/`description` | ✅ available, already used |
| CASES nav section | `GET /cases` (list) — full, unbounded, every case the engine has computed this session | ✅ available, currently unused |
| ALERTS nav section | `GET /transactions/recent` — the existing `/feed` | ✅ available (this is today's `/feed`) |
| OVERVIEW nav section | No summary/aggregate-metrics endpoint (counts, averages, trend) exists anywhere | ❌ missing |
| GRAPH nav section (as a standalone top-level page, distinct from the per-case ring) | No graph-listing/browse endpoint exists | ❌ missing |
| ENTITIES nav section | No entity-listing endpoint exists | ❌ missing |
| PATTERNS nav section | `FraudDNAStore`'s seeded pattern library exists internally (`fraudlens/core/dna/store.py`) but nothing routes it to the API | ❌ missing |

### Finding A — feed-level signal bars: solvable without a backend change

`GET /transactions/recent` doesn't carry `agent_scores`, but `GET /cases`
(list, no path param) returns full `FraudCase` objects — including real
`agent_scores[].score/confidence/reasons` — for every transaction that's
already been analyzed. And `/transactions/recent`'s own handler calls
`engine.analyze(txn.txn_id)` for every row it returns, which populates that
cache as a side effect. So after the feed has loaded once, `GET /cases`
has real per-agent data for those same rows.

**Plan**: add one new function to `lib/api.ts` — `getCases()`, hitting the
already-existing `GET /cases` — and use its `agent_scores` for the feed's
signal bars, sorting/slicing client-side by `transaction.timestamp`. This
needs **no backend change**, but it does add a new export to `lib/api.ts`,
which is on the "don't touch" list from the original constraints — flagging
before doing it rather than treating "don't touch" as "except for additive
exports."

### Finding B — signal-tree granularity is limited by stripped metadata

Because `agent_scores[].metadata` is always `{}` by the time it reaches the
frontend, I can't read a structured field like "which specific device was
reused." What I *can* do, with zero backend change: derive each tree line's
severity from that agent's real `score` (e.g. ≥0.7 high / ≥0.4 medium /
else low — thresholds open to adjustment) and surface its real `reasons`
strings as the detail text. For "device reuse" vs "IP reuse" specifically —
both currently reported by `graph_agent` under one score — I'd distinguish
them by checking whether `graph_agent`'s `reasons` array contains a
device-shaped vs. IP-shaped sentence (real text the agent already wrote,
just pattern-matched rather than read from a structured field). Calling this
out because it's a heuristic parse of agent-authored text, not a clean
structured signal, and it's a little fragile if an agent's wording changes.

### Finding C — no endpoint exposes actual graph structure (the important one)

`FraudGraph` (`nodes: list[GraphNode]`, `edges: list[GraphEdge]`) is a real,
fully-defined schema in `fraudlens/models/schemas.py` and `GraphBuilder`
already computes it — but `CaseEngine` only ever uses its internal
`GraphBuilder` to derive the flat `GraphEvidence` summary
(`_build_graph_evidence` in `case_engine.py`); the underlying node/edge
graph is never returned by any route. `GraphEvidence`'s lists (e.g.
`shared_devices: ["DEV-...", "DEV-..."]`) tell me *that* two devices are
shared and *how many* accounts touch them in aggregate, but not *which*
account uses *which* specific device — that mapping only exists in
`GraphEdge.source`/`target`.

Building a real force-directed graph (Part 2) needs this. Proposed change,
**not made yet**:

- `fraudlens/core/cases/case_engine.py` — add one public method,
  `get_fraud_graph(txn_id: str) -> FraudGraph | None`, delegating to the
  engine's existing internal `self._graph_builder.get_subgraph(txn_id)`
  (same call `_build_graph_evidence` already makes internally — this adds
  a public accessor, doesn't change existing behavior).
- `fraudlens/core/privacy.py` — add one masking helper, `public_fraud_graph()`,
  mirroring the masking `public_case()` already applies to
  `graph_evidence.shared_devices`/`shared_ips`/`connected_accounts`: mask
  every `GraphNode.label` by `node_type` (`mask_identifier` for
  account/device/merchant, `mask_ip` for ip), pass `node_id`/`node_type`/
  `is_suspicious` through unmasked (they're not identifiers), and edges
  through unchanged (`source`/`target` reference the already-masked
  `node_id`... actually `node_id` itself is an internal key like
  `"account:ACC-00110"`, not the masked label, so I'd mask the **label**
  field only and leave `node_id` as an opaque key the frontend never
  displays directly).
- `fraudlens/api/routes/cases.py` — add one new read-only route,
  `GET /cases/{txn_id}/graph`, returning the masked `FraudGraph`, or `null`
  when there's no ring (mirroring how `graph_evidence` is already `null`
  on a clean case).

This is additive and read-only — no existing route's shape changes, no
existing field changes meaning. **Waiting for a go-ahead before touching
any of these three backend files**, per your instructions.

If this isn't approved, the fallback is a materially weaker graph: nodes
for `connected_accounts`/`shared_devices`/`shared_ips` from `GraphEvidence`
with edges *inferred* as "every connected account touches every shared
device" — which is not what actually happened (a ring's accounts don't all
necessarily share every listed device) and would visually imply
relationships the API never actually confirmed. I don't think that clears
the "no synthetic edges" bar in your brief, so I'd rather wait for Finding C
than ship that.

### Clarification needed — client-side account masking

The brief describes the masked account display as "partial masking applied
client-side to the real account ID" and a utility that "masks a real
account ID string client-side." But per the existing (and, per this
message, still-binding) hard constraint, and confirmed by directly
inspecting `privacy.py` and `transactions.py`/`cases.py`: **the backend
already masks every account/device/IP identifier before it reaches the
frontend.** `GET /transactions/recent` and `GET /cases/{txn_id}` never send
a raw identifier — I verified this live last session (`account_id` arrives
as `"ACC-••0110"` already). There is no raw value for the frontend to mask.

I'll build the requested reusable display utility (consistent monospace
formatting, consistent partial-reveal styling) as a **pass-through
formatter over the already-masked string** — never logic that derives,
reconstructs, or expects an unmasked identifier, since the frontend never
has one and reconstructing one would violate last session's non-negotiable
"never render a raw account_id/device_id/ip_address." Flagging this
because it's a real reinterpretation of the instruction as written, not
because I think there's a live security bug to fix.

### Nav-rail sections: what's real vs. coming-soon

Per "only build out nav sections backed by real API data or real existing
pages":

- **ALERTS** → real, today's `/feed` (`GET /transactions/recent`), redesigned.
- **CASES** → real, but currently unbuilt as its own page — backed by
  `GET /cases` (the full, unbounded case list, a genuinely different query
  than the recent-N feed). Proposing this as a *new* second list page. Flagging
  because it's net-new page count beyond "redesign /feed and /case," not
  just a relabel.
- **OVERVIEW, GRAPH, ENTITIES, PATTERNS** → visually present, disabled/
  "coming soon," per your instruction — no backing endpoint for any of the
  four. (PATTERNS is the closest to feasible later — the DNA library exists
  server-side, just isn't routed — but that's a future call, not this one.)

### Risk-tier labeling

The reference sketch shows three tiers (HIGH/MEDIUM/LOW). The real system
already has **four** real states with four real distinct tokens
(`DECISION_TONE`: clear/review/block/block_and_report →
risk-low/medium/high/critical) — `block_and_report` is a real, more-severe
state than `block`, not a duplicate of it. Collapsing both into one "HIGH"
label would hide a distinction the backend already computed. Plan: keep all
four real tiers, relabeled LOW/MEDIUM/HIGH/CRITICAL to fit the terminal
aesthetic, rather than lossy-collapsing to three. Open to being told to
collapse to three instead — noting the tradeoff rather than deciding
silently.

### Risk-signal tree: real agents, not a fixed 5-label taxonomy

The brief's sketch lists five tree lines (transaction anomaly, device
reuse, IP reuse, behavioral deviation, Fraud DNA match). The real system
has six real agents (`rule_agent`, `velocity_agent`, `graph_agent`,
`behavioral_agent`, `ml_agent`, `fraud_dna_agent`), and velocity doesn't map
cleanly onto any one of the five sketch labels without either dropping it
or misrepresenting what actually fired. Plan: render the tree from the real
`agent_scores` array as-is (one line per real agent that's present, its
real name/score/reasons) rather than force-fitting six real signals into
five fixed labels. This follows your own "match information hierarchy and
density, not literal characters" instruction from the sketch note.

### Font

"Share Tech Mono" via `next/font/google` — no new npm dependency (Next.js
fetches and self-hosts it at build time, same mechanism already used for
Geist Sans/Mono). Wiring it in as `--font-mono`'s replacement (or a new
`--font-terminal` variable, TBD once building) necessarily touches
`app/layout.tsx` — not on the original file-scope list from the first pass,
but required to load any font at all, and low-risk (font loading only, no
structural change to the shell it already renders).

### Open questions, summarized

1. **Finding C (graph endpoint)** — go-ahead needed before touching
   `case_engine.py`, `privacy.py`, `api/routes/cases.py`.
2. **Finding A (`lib/api.ts` addition)** — go-ahead needed to add one new
   `getCases()` export (existing exports unchanged).
3. **Account masking** — confirm the pass-through-formatter interpretation
   above is what you want, given the backend already masks server-side.
4. **CASES as a new page** — confirm building a second list page (backed by
   `GET /cases`) is in scope, not just redesigning the existing two pages.
5. **Risk-tier collapsing** — 4 real tiers (my recommendation) vs. 3 per the
   literal sketch.
6. **Signal-tree taxonomy** — 6 real agents as-is (my recommendation) vs.
   force-fitting to the sketch's 5 labels.
