"""TEST keys, TEST verifier registry and TEST trust root.

Everything here is derived from fixed public seeds: it is NOT secret and must
never be used outside this demo. A real deployment loads the Foundation's
registry, signed by 3 of 5 root key holders (see the verifier's
docs/root-key-custody.md).
"""

import base64
import hashlib
import json
from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from gravit_verifier import EvidenceRecord
from gravit_verifier.registry import (
    TrustRoot,
    VerifierRegistry,
    key_id_for,
    registry_signing_message,
    signing_message,
)

TEST_EVALUATION_TIME = "2026-10-11T12:00:00Z"

# key name -> (operator, revoked). Two keys of one operator count as ONE source.
OPERATORS = {
    "verifier-a": ("operator-A", False),
    "verifier-b": ("operator-B", False),
    "verifier-c": ("operator-C", False),
    "verifier-a2": ("operator-A", False),
    "verifier-revoked": ("operator-R", True),
}
ROOTS = [f"root-{n}" for n in range(1, 6)]
ROOT_SIGNERS = ["root-1", "root-3", "root-5"]  # 3 of 5


def _key(name: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"gravit-poc-test-key:" + name.encode()).digest()
    )


def _pub(name: str) -> bytes:
    return _key(name).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def _doc(obj: Dict[str, Any]) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()


def demo_registry() -> VerifierRegistry:
    """The TEST registry, accepted only because 3 of 5 TEST root keys signed it."""
    root = TrustRoot.from_bytes(
        _doc(
            {
                "trust_root_version": 1,
                "threshold": 3,
                "root_keys": [
                    {"key_id": key_id_for(_pub(r)), "public_key": base64.b64encode(_pub(r)).decode()}
                    for r in ROOTS
                ],
            }
        )
    )
    reg = _doc(
        {
            "registry_version": 1,
            "verifiers": [
                {
                    "key_id": key_id_for(_pub(n)),
                    "public_key": base64.b64encode(_pub(n)).decode(),
                    "operator": op,
                    "revoked": rev,
                }
                for n, (op, rev) in OPERATORS.items()
            ],
        }
    )
    msg = registry_signing_message(reg)
    sigs = "".join(
        f"{key_id_for(_pub(r))} {base64.b64encode(_key(r).sign(msg)).decode()}\n" for r in ROOT_SIGNERS
    )
    return VerifierRegistry.from_bytes(reg, sigs, root)


def attest(
    artifact_id: str,
    action_hash: str,
    signer: str,
    theta: float,
    timestamp: str = TEST_EVALUATION_TIME,
    record_id: str = "",
    provenance: str = "",
    result: bool | None = True,
) -> EvidenceRecord:
    """An independent verifier's signed attestation that `action_hash` is sound.
    `signer` may also be an unregistered name (e.g. "ghost") to simulate a forgery.
    `result` is the signed verdict (verifier >= 0.6.0): True supports, False contradicts, None supports nothing."""
    op = OPERATORS.get(signer, ("unregistered", False))[0]
    rec = EvidenceRecord(
        record_id=record_id or f"{signer}:{artifact_id}",
        theta=theta,
        result=result,
        verifier_id=signer,
        timestamp=timestamp,
        provenance=provenance or op,
        integrity_hash=action_hash,
        key_id=key_id_for(_pub(signer)),
    )
    rec.signature = base64.b64encode(_key(signer).sign(signing_message(artifact_id, rec))).decode()
    return rec
