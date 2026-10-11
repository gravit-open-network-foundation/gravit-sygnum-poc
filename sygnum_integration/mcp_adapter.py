"""
Adapter for AI-agent proposals arriving via Sygnum's Model Context Protocol
(MCP) - simulated, since Sygnum's MCP endpoint is not public.

Flow: the AI agent proposes a transfer -> the Gravit epistemic gate checks it
(bank rules, attestations bound to this exact proposal, the public Gravit
Verifier) -> only a verified proposal goes to a human for signature (four-eyes
principle) -> an audit report is produced from the hash-chained log.

The verification itself is the real Gravit Verifier v0.5.0.
"""

from typing import Any, Dict, List, Optional

from gravit_verifier import EvidenceRecord

from gravit_gate import EpistemicGate, GateDecision

ASSETS = {"dCHF", "CHFAU"}  # plus tokenized equity, prefix "EQ-"
KYC_CLIENTS = {"client-0001", "client-0002", "client-0003"}  # demo client book
HIGH_VALUE_FROM = 100_000  # CHF equivalent: needs three independent operators
MAX_TRANSFER = 1_000_000


def proposal_action(p: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("proposal_id", "agent_id", "from_client", "to_client", "asset", "amount", "reason")
    return {k: p.get(k) for k in keys}


def policy_error(p: Dict[str, Any], balances: Dict[str, Dict[str, float]]) -> Optional[str]:
    asset = p.get("asset", "")
    if asset not in ASSETS and not str(asset).startswith("EQ-"):
        return f"asset {asset!r} is not held in custody"
    for side in ("from_client", "to_client"):
        if p.get(side) not in KYC_CLIENTS:
            return f"{side} {p.get(side)!r} is not a KYC-verified client"
    amount = p.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        return "amount must be a positive number"
    if amount > MAX_TRANSFER:
        return f"amount exceeds the limit {MAX_TRANSFER}"
    held = balances.get(p["from_client"], {}).get(asset, 0)
    if amount > held:
        return f"insufficient balance: {p['from_client']} holds {held} {asset}"
    return None


class MCPAdapter:
    def __init__(self, gate: EpistemicGate, balances: Dict[str, Dict[str, float]]) -> None:
        self.gate = gate
        self.balances = balances

    def receive_ai_proposal(
        self, proposal: Dict[str, Any], attestations: List[EvidenceRecord], evaluation_time: str
    ) -> GateDecision:
        """execute == True means: verified, ready for the human signature."""
        high_value = float(proposal.get("amount") or 0) >= HIGH_VALUE_FROM
        return self.gate.check(
            artifact_id=f"mcp:{proposal.get('proposal_id')}",
            action=proposal_action(proposal),
            evidence=attestations,
            evaluation_time=evaluation_time,
            policy_error=policy_error(proposal, self.balances),
            min_operators=3 if high_value else 2,
            high_impact=high_value,
        )


def audit_report(entry: Dict[str, Any]) -> str:
    """Human-readable report of one audit-log entry, for compliance and auditors."""
    b = entry["body"]
    a = b["action"]
    d = b.get("decision") or {}
    lines = [
        f"Audit entry #{entry['seq']}  {entry['timestamp']}",
        f"  Proposal   {a['proposal_id']} by {a['agent_id']}: {a['amount']} {a['asset']} "
        f"{a['from_client']} -> {a['to_client']} ({a['reason']})",
        f"  Outcome    {'VERIFIED - forwarded for human signature' if b['execute'] else 'BLOCKED'}",
        f"  Reason     {b['reason']}",
        f"  Operators  {', '.join(b['independent_operators']) or '-'}",
        f"  Decision   {d.get('decision_id', '-')}  state {d.get('final_epistemic_state', '-')}",
        f"  Proposal hash  {b['action_hash']}",
        f"  Chain      prev {entry['prev_hash'][:16]}...  this {entry['entry_hash'][:16]}...",
    ]
    return "\n".join(lines)
