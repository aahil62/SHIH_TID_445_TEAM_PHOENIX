# FraudLens — AI Fraud Intelligence & Regulatory CaseOps Platform

**Team Phoenix** · SHIH-TID-445 · Problem SH-FIN-01 · Smart Horizon 2026 Grand Finale

Built for the Smart Horizon 2026 Grand Finale (03–05 Sep 2026, NHCE Bengaluru), evolving Team
Phoenix's Level 0 and Level 1 concept for the same problem statement. The Level 0/1 prototype
was reviewed by this event's own jury; this repository is the Grand Finale build.

## Status

Grand Finale build in progress. See commit history for real-time progress against the team's
own build plan.

- [x] Stage A — core schemas, ensemble scorer, case engine skeleton (`main`)
- [x] Fraud DNA, decision workflow (`feature/graph-behavioral`) — merged
- [x] Trained ML agent, benchmark suite (`feature/rules-velocity`) — merged
- [x] Report generator, full FastAPI route surface (`main`) — merged
- [ ] Frontend wired to live data (`feature/frontend`) — not started
- [ ] Stage C — Copilot, model-performance panel, literature grounding
- [ ] Stage D — integration freeze

Backend is fully runnable today — see "Running tests" and "Running the API" below.

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
python scripts/run_demo.py   # end-to-end: a real transaction through every agent
```

## Running the API

```bash
source .venv/bin/activate
uvicorn fraudlens.api.main:app --reload --port 8001
```

Then: `curl http://127.0.0.1:8001/health` or `curl "http://127.0.0.1:8001/transactions/recent?limit=5"`.
Interactive docs at `http://127.0.0.1:8001/docs`.
