"""Append-only, hash-chained audit log (the History Keeper principle):
every entry carries a timestamp and the hash of the previous entry, so an
entry can be added but never changed or removed without breaking the chain."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

GENESIS = "0" * 64


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class AuditLog:
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    @property
    def head(self) -> str:
        return self.entries[-1]["entry_hash"] if self.entries else GENESIS

    def append(self, timestamp: str, body: Dict[str, Any]) -> Dict[str, Any]:
        entry = {"seq": len(self.entries), "timestamp": timestamp, "prev_hash": self.head, "body": body}
        entry["entry_hash"] = hashlib.sha256(canonical(entry)).hexdigest()
        self.entries.append(entry)
        return entry

    @staticmethod
    def verify_chain(entries: List[Dict[str, Any]]) -> bool:
        prev = GENESIS
        for i, e in enumerate(entries):
            body = {k: v for k, v in e.items() if k != "entry_hash"}
            if e["seq"] != i or e["prev_hash"] != prev:
                return False
            if hashlib.sha256(canonical(body)).hexdigest() != e["entry_hash"]:
                return False
            prev = e["entry_hash"]
        return True

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in self.entries), encoding="utf-8")
