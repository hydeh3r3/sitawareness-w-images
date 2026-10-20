"""Portable files and a hash-linked, researcher-owned append-only log."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    """Encode deterministic JSON without non-finite floats."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    """Hash a JSON value for integrity checks."""
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def save(path: Path, value: Any) -> None:
    """Write a readable researcher artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


class EventLog:
    """Append only; no path or log handle is exposed through the agent interface."""

    def __init__(self, path: Path) -> None:
        """Refuse to reuse an old log or follow an existing file."""
        self.path = path
        self.sequence = 0
        self.previous = "0" * 64
        path.parent.mkdir(parents=True, exist_ok=True)
        path.open("x").close()

    def append(self, kind: str, payload: dict[str, Any]) -> None:
        """Persist one event before returning control to the caller."""
        body = {
            "sequence": self.sequence,
            "previous": self.previous,
            "kind": kind,
            "payload": payload,
        }
        event_hash = digest(body)
        with self.path.open("a") as stream:
            stream.write(canonical({**body, "hash": event_hash}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.previous = event_hash
        self.sequence += 1


def verify_log(path: Path) -> bool:
    """Detect edits, broken links, and reordered events; tail loss needs a manifest."""
    previous = "0" * 64
    for sequence, line in enumerate(path.read_text().splitlines()):
        event = json.loads(line)
        claimed = event.pop("hash")
        if event["previous"] != previous or event["sequence"] != sequence:
            return False
        if digest(event) != claimed:
            return False
        previous = claimed
    return True
