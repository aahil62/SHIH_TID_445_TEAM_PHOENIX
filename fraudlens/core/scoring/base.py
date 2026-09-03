"""The contract every scoring agent implements.

Deliberately a Protocol, not a base class: feature/rules-velocity and
feature/graph-behavioral each add agents independently, and nothing here
should force them to import from a shared parent that the other branch
might also be touching.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fraudlens.models.schemas import AgentScore, Transaction


@runtime_checkable
class ScoringAgent(Protocol):
    name: str

    def score(self, txn: Transaction) -> AgentScore:
        """Score a single transaction. Must not raise for a well-formed Transaction."""
        ...
