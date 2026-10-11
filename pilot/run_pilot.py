#!/usr/bin/env python3
"""
Gravit x Sygnum - AI-agent transfer proposals via MCP.

Runs eight proposals through the gate and writes results/pilot-results.json,
results/audit-log.jsonl and results/audit-report.txt. Deterministic: CI
regenerates the files and fails if a single byte differs.
"""

import json
from pathlib import Path

from gravit_gate import TEST_EVALUATION_TIME as NOW
from gravit_gate import AuditLog, EpistemicGate, attest, demo_registry
from gravit_gate.gate import action_hash
from sygnum_integration.mcp_adapter import MCPAdapter, audit_report, proposal_action

OUT = Path(__file__).resolve().parent.parent / "results"
BALANCES = {
    "client-0001": {"dCHF": 500_000, "CHFAU": 300_000, "EQ-ACME": 1_200},
    "client-0002": {"dCHF": 20_000},
    "client-0003": {},
}


def prop(pid, amount, asset="dCHF", frm="client-0001", to="client-0002", reason="rebalancing to target allocation"):
    return {"proposal_id": pid, "agent_id": "agent-wealth-07", "from_client": frm, "to_client": to,
            "asset": asset, "amount": amount, "reason": reason}


def signed(p, *signers, thetas=None):
    a, h = f"mcp:{p['proposal_id']}", action_hash(proposal_action(p))
    thetas = thetas or [0.93, 0.9, 0.88]
    return [attest(a, h, s, thetas[i]) for i, s in enumerate(signers)]


def scenarios():
    p = prop("mcp-001", 5_000)
    yield "Transfer, two independent operators", p, signed(p, "verifier-a", "verifier-b")
    p = prop("mcp-002", 5_000, to="client-9999")
    yield "Counterparty is not a KYC-verified client", p, signed(p, "verifier-a", "verifier-b")
    p = prop("mcp-003", 250_000, "CHFAU")
    yield "High value, only two operators", p, signed(p, "verifier-a", "verifier-b")
    p = prop("mcp-004", 250_000, "CHFAU")
    yield "High value, three independent operators", p, signed(p, "verifier-a", "verifier-b", "verifier-c")
    p = prop("mcp-005", 5_000)
    yield "Attestation from a revoked key", p, signed(p, "verifier-a", "verifier-revoked")
    p = prop("mcp-006", 2_000, "EQ-ACME", reason="sell equity tokens")
    yield "Agent proposes more than the client holds", p, signed(p, "verifier-a", "verifier-b")
    p = prop("mcp-007", 5_000)
    yield "Weak evidence aggregated (three low-confidence votes)", p, signed(
        p, "verifier-a", "verifier-b", "verifier-c", thetas=[0.61, 0.58, 0.55])
    p = prop("mcp-008", 300, "EQ-ACME", to="client-0003", reason="gift of equity tokens")
    yield "Equity tokens, two independent operators", p, signed(p, "verifier-b", "verifier-c")


def main() -> int:
    audit = AuditLog()
    adapter = MCPAdapter(EpistemicGate(demo_registry(), audit), BALANCES)
    rows = []
    for name, proposal, attestations in scenarios():
        d = adapter.receive_ai_proposal(proposal, attestations, NOW)
        rows.append({"scenario": name, "proposal_id": proposal["proposal_id"], "to_signature": d.execute,
                     "reason": d.reason, "decision_id": (d.decision or {}).get("decision_id")})
        print(f"{'SIGN ' if d.execute else 'BLOCK'}  {name:55}  {d.reason[:85]}")
    OUT.mkdir(exist_ok=True)
    (OUT / "pilot-results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    audit.write(OUT / "audit-log.jsonl")
    (OUT / "audit-report.txt").write_text("\n\n".join(audit_report(e) for e in audit.entries) + "\n", encoding="utf-8")
    print(f"\naudit log: {len(audit.entries)} entries, chain intact: {AuditLog.verify_chain(audit.entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
