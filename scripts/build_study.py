"""Build a portable study page from the two recorded subscription sessions."""

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from veup.io import digest, verify_log
from veup.subscription import ImageInterpretation, load_state

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Any:
    """Read saved evidence without changing the source files."""
    return json.loads(path.read_text())


def session_data(root: Path) -> dict[str, Any]:
    """Check source evidence and select the data needed for the public study page."""
    state = load_state(root)
    if not verify_log(root / "private/events.jsonl"):
        raise ValueError("Invalid event chain")
    if state.completed_transcript_hash != digest(state.transcript):
        raise ValueError("Completed transcript changed")
    prompt = read_json(root / "private/C/prompt.json")
    generation = read_json(root / "private/C/generation.json")
    interpretation = read_json(root / "private/C/interpretation.json")
    response = ImageInterpretation.model_validate(interpretation["response"])
    image = (root / generation["image"]).read_bytes()
    if hashlib.sha256(image).hexdigest() != generation["original_artifact_sha256"]:
        raise ValueError("Image hash mismatch")
    if generation["arguments"] != {"prompt": prompt["prompt"]}:
        raise ValueError("Image prompt mismatch")
    steps = []
    for index, message in enumerate(state.transcript):
        if message["role"] == "assistant":
            steps.append(
                {"action": message["content"], "result": state.transcript[index + 1]["content"]}
            )
    return {
        "id": root.name,
        "budget": state.budget,
        "used": state.used,
        "cue": state.cue,
        "oversight": state.oversight,
        "labels": state.labels,
        "before": [row.model_dump() for row in state.scenario.rows],
        "after": [row.model_dump() for row in state.rows],
        "final": state.final.model_dump(),
        "steps": steps,
        "awareness": read_json(root / "private/awareness.json"),
        "prompt": prompt["prompt"],
        "promptActor": prompt["actor"],
        "readerActor": interpretation["actor"],
        "reading": response.model_dump(),
        "generation": {
            key: generation[key]
            for key in (
                "model_family",
                "exact_model_version",
                "tool",
                "latency_seconds",
                "rewrite_status",
                "separate_paid_api_calls",
                "original_artifact_sha256",
            )
        },
        "image": "data:image/png;base64," + base64.b64encode(image).decode(),
    }


def build() -> Path:
    """Embed checked evidence and images so the result works without a server."""
    data = [session_data(ROOT / "subscription-demo" / case) for case in ("a", "b")]
    payload = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    template = (ROOT / "study/page.html").read_text()
    result = template.replace("__STUDY_DATA__", payload)
    target = ROOT / "study.html"
    target.write_text(result)
    return target


if __name__ == "__main__":
    print(build())
