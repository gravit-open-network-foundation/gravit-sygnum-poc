"""Gravit epistemic gate: lets an AI-agent action through only if the public
Gravit Verifier (v0.5.0) classifies it as a Verified Fact, on signed evidence
from independent registered operators, bound to exactly this action."""

from .gate import EpistemicGate, GateDecision, PolicyViolation
from .audit import AuditLog
from .testkeys import TEST_EVALUATION_TIME, attest, demo_registry

__all__ = [
    "EpistemicGate",
    "GateDecision",
    "PolicyViolation",
    "AuditLog",
    "TEST_EVALUATION_TIME",
    "attest",
    "demo_registry",
]
