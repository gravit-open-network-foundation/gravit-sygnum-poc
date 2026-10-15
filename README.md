# Gravit × Sygnum – Proof of Concept

**Epistemic gate for AI-agent transfer proposals in regulated banking**

Sygnum's AI agents propose transfers (dCHF, CHFAU, tokenized equity) via the Model Context
Protocol (MCP). Before a proposal reaches a human for signature (four-eyes principle), it must
pass a gate:

1. **Bank rules** – asset in custody, both clients KYC-verified, sufficient balance, transfer limit.
   No evidence can override them.
2. **Binding** – every attestation is signed over the SHA3-256 hash of *exactly this* proposal.
3. **The public [Gravit Verifier](https://github.com/gravit-open-network-foundation/verifier) v0.5.0**
   must classify the proposal as a *Verified Fact*: signed attestations from independent
   operators listed in a registry signed by 3 of 5 root keys, fresh (≤ 5 minutes).
   From CHF 100 000 **three** independent operators and strong provenance are required.
   Weak evidence never adds up to a Verified Fact, however many votes there are.

Every decision is appended to a **hash-chained audit log** (`results/audit-log.jsonl`) and
rendered as a human-readable **audit report** (`results/audit-report.txt`) for compliance
and auditors. Deleting or changing an entry breaks the chain.

## Run it

```bash
make setup PYTHON=python3.12   # Python ≥ 3.10; installs the verifier at tag v0.5.0
make run                       # 8 scenarios → results/
make test
```

| # | Scenario | Result |
|---|---|---|
| 1 | 5 000 dCHF, two independent operators | **to signature** |
| 2 | Counterparty not KYC-verified | block |
| 3 | 250 000 CHFAU, only two operators | block |
| 4 | 250 000 CHFAU, three independent operators | **to signature** |
| 5 | Attestation from a revoked key | block |
| 6 | Agent proposes more than the client holds | block |
| 7 | Three low-confidence votes (weak aggregation) | block |
| 8 | Equity tokens, two independent operators | **to signature** |

CI runs the tests and regenerates `results/` on every change; it fails if a single byte differs.

## Status – what this is and is not

- **Is:** a runnable demonstration; the verification is the real, tested Gravit Verifier.
- **Is not:** connected to Sygnum. MCP proposals, client book and balances are simulated.
- **Is not:** reviewed or endorsed by Sygnum. It was built by the Gravit Open Network Foundation from public information only.
- **Keys:** `gravit_gate/testkeys.py` contains **test keys only**, derived from public seeds.
- `docs/`, `bridge/`, `economics/` and `epistemic_core/` (C++ sketches) are earlier concept
  material; they are kept for the record but are not part of the running demo, and they have
  not been reviewed by Sygnum, FINMA or legal counsel.

**Next step with Sygnum:** map one real MCP proposal format (test environment) onto
`proposal_action`, and agree which independent operators run verifier keys.
