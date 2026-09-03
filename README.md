# FraudLens — AI Fraud Intelligence & Regulatory CaseOps Platform

**Team Phoenix** · SHIH-TID-445 · Problem SH-FIN-01 · Smart Horizon 2026 Grand Finale

Built for the Smart Horizon 2026 Grand Finale (03–05 Sep 2026, NHCE Bengaluru), evolving Team
Phoenix's Level 0 and Level 1 concept for the same problem statement. The Level 0/1 prototype
was reviewed by this event's own jury; this repository is the Grand Finale build.

## Status

Grand Finale build in progress. See commit history for real-time progress against the team's
own build plan.

- [x] Stage A — core schemas, ensemble scorer, case engine skeleton (`main`)
- [ ] Stage B — Fraud DNA, decision workflow, full API, frontend, trained ML agent, benchmark suite
- [ ] Stage C — Copilot, model-performance panel, literature grounding
- [ ] Stage D — integration freeze

## Branches

| Branch | Scope |
|---|---|
| `main` | Schemas, ensemble scorer, case engine, integration |
| `feature/rules-velocity` | Rule agent, velocity agent, synthetic data → trained ML agent, benchmark suite |
| `feature/graph-behavioral` | Graph agent, behavioral agent → Fraud DNA, decision workflow |
| `feature/frontend` | Next.js analyst console |

## Running tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
```
