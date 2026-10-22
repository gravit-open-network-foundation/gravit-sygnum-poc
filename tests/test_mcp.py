import json

from gravit_gate import AuditLog, EpistemicGate, demo_registry
from gravit_gate.testkeys import attest
from pilot.run_pilot import BALANCES, NOW, action_hash, prop, proposal_action, scenarios
from sygnum_integration.mcp_adapter import MCPAdapter, audit_report

EXPECTED = {
    "mcp-001": True,
    "mcp-002": False,  # not KYC
    "mcp-003": False,  # high value needs three operators
    "mcp-004": True,
    "mcp-005": False,  # revoked key
    "mcp-006": False,  # insufficient balance
    "mcp-007": False,  # weak aggregation never becomes a Verified Fact
    "mcp-008": True,
}


def run():
    audit = AuditLog()
    adapter = MCPAdapter(EpistemicGate(demo_registry(), audit), BALANCES)
    return {p["proposal_id"]: adapter.receive_ai_proposal(p, ev, NOW) for _, p, ev in scenarios()}, audit


def test_every_scenario_has_the_expected_outcome():
    decisions, _ = run()
    assert {k: d.execute for k, d in decisions.items()} == EXPECTED


def test_weak_aggregation_is_rejected_by_the_verifier_itself():
    decisions, _ = run()
    d = decisions["mcp-007"]
    assert d.decision is not None and d.decision["final_epistemic_state"] != "Verified Fact"


def test_audit_chain_and_report():
    _, audit = run()
    entries = json.loads(json.dumps(audit.entries))
    assert AuditLog.verify_chain(entries)
    assert "forwarded for human signature" in audit_report(entries[0])
    del entries[1]  # remove an inconvenient entry
    assert not AuditLog.verify_chain(entries)


def _decide(proposal, evidence):
    adapter = MCPAdapter(EpistemicGate(demo_registry(), AuditLog()), BALANCES)
    return adapter.receive_ai_proposal(proposal, evidence, NOW)


def test_signed_contradiction_blocks_even_when_outvoted():
    # verifier 0.6.0: a record signed False is a contradiction, not support
    p = prop("mcp-101", 5_000)
    a, h = f"mcp:{p['proposal_id']}", action_hash(proposal_action(p))
    ok = [attest(a, h, "verifier-a", 0.93), attest(a, h, "verifier-b", 0.9)]
    assert _decide(p, ok).execute
    no = ok + [attest(a, h, "verifier-c", 0.88, result=False)]
    d = _decide(p, no)
    assert not d.execute
    assert d.decision is None or d.decision["final_epistemic_state"] != "Verified Fact"


def test_verdict_less_record_supports_nothing():
    p = prop("mcp-102", 5_000)
    a, h = f"mcp:{p['proposal_id']}", action_hash(proposal_action(p))
    ev = [attest(a, h, "verifier-a", 0.93), attest(a, h, "verifier-b", 0.9, result=None)]
    assert not _decide(p, ev).execute
