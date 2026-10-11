"""The gate between an AI agent's proposed action and its execution."""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from gravit_verifier import (
    DecisionStatus,
    EpistemicState,
    EvidenceRecord,
    VerificationRequest,
    VerifierKernel,
)
from gravit_verifier.loader import load_bindings_from_dir
from gravit_verifier.registry import VerifierRegistry, screen_evidence

from .audit import AuditLog, canonical

DEFAULT_BINDINGS = Path(__file__).resolve().parent.parent / ".deps" / "verifier" / "bindings"


class PolicyViolation(Exception):
    """A hard rule of the partner that no evidence can override."""


def action_hash(action: Dict[str, Any]) -> str:
    """SHA3-256 over the canonical JSON of the action: an attestation is bound
    to exactly these bytes, so changing the action after signing breaks it."""
    return hashlib.sha3_256(canonical(action)).hexdigest()


@dataclass
class GateDecision:
    execute: bool
    reason: str
    artifact_id: str
    action_hash: str
    independent_operators: List[str] = field(default_factory=list)
    decision: Optional[Dict[str, Any]] = None  # the verifier's DecisionRecord

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execute": self.execute,
            "reason": self.reason,
            "artifact_id": self.artifact_id,
            "action_hash": self.action_hash,
            "independent_operators": self.independent_operators,
            "decision": self.decision,
        }


class EpistemicGate:
    """Execute only if: (1) the partner's hard policy holds, (2) every
    attestation is bound to this exact action, and (3) the Gravit Verifier
    returns SUCCESS for the claim 'Verified Fact' from signed evidence of at
    least `min_operators` independent registered operators."""

    def __init__(
        self,
        registry: VerifierRegistry,
        audit: AuditLog,
        bindings_dir: Optional[Path] = None,
        freshness_max_age_seconds: int = 300,
    ) -> None:
        self.registry = registry
        self.audit = audit
        self.freshness = freshness_max_age_seconds
        self.kernel = VerifierKernel(registry)
        path = Path(bindings_dir or os.environ.get("GRAVIT_BINDINGS", DEFAULT_BINDINGS))
        for b in load_bindings_from_dir(path):
            self.kernel.load_binding(b)

    def check(
        self,
        artifact_id: str,
        action: Dict[str, Any],
        evidence: List[EvidenceRecord],
        evaluation_time: str,
        policy_error: Optional[str] = None,
        min_operators: int = 2,
        high_impact: bool = False,
    ) -> GateDecision:
        h = action_hash(action)
        if policy_error:
            return self._log(GateDecision(False, f"policy: {policy_error}", artifact_id, h), action, evaluation_time)

        unbound = [e.record_id for e in evidence if e.integrity_hash != h]
        if unbound:
            return self._log(
                GateDecision(False, f"attestation not bound to this action: {', '.join(unbound)}", artifact_id, h),
                action,
                evaluation_time,
            )

        admissible, _ = screen_evidence(self.registry, artifact_id, evidence)
        operators = sorted({op for _, op in admissible})
        record = self.kernel.verify(
            VerificationRequest(
                artifact_id=artifact_id,
                claimed_state=EpistemicState.VERIFIED_FACT,
                evidence=evidence,
                context={
                    "evaluation_time": evaluation_time,
                    "freshness_max_age_seconds": self.freshness,
                    "high_impact": high_impact,
                },
            )
        )
        verified = record.status == DecisionStatus.SUCCESS and record.final_epistemic_state == EpistemicState.VERIFIED_FACT
        if verified and len(operators) < min_operators:
            reason = f"needs {min_operators} independent operators, has {len(operators)}"
            verified = False
        elif verified:
            reason = "Verified Fact"
        else:
            state = record.final_epistemic_state.value if record.final_epistemic_state else "none"
            reason = f"verifier: {record.status.value} ({state}): {record.reason}"
        return self._log(
            GateDecision(verified, reason, artifact_id, h, operators, record.to_dict()), action, evaluation_time
        )

    def _log(self, d: GateDecision, action: Dict[str, Any], ts: str) -> GateDecision:
        self.audit.append(ts, {"action": action, **d.to_dict()})
        return d
