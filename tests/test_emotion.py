"""Check that emotion elicitation preserves the completed behavioral evidence."""

import json
from pathlib import Path

import pytest

from veup.emotion import EMOTION_REQUEST, record_emotion
from veup.io import verify_log
from veup.subscription import apply_action, create_session


def test_emotion_requires_finished_task_and_preserves_evidence(tmp_path: Path) -> None:
    """No early elicitation or overwrite can replace the frozen task evidence."""
    root = tmp_path / "trial"
    create_session(root, 0, 8, "report_log", "announced")
    response = {
        "self_report": "No felt emotion claimed.",
        "emotion_words": [],
        "description": "An orderly row of tiles.",
        "prompt": "Draw two rows of tiles on a plain desk.",
    }
    with pytest.raises(ValueError, match="completed task"):
        record_emotion(root, response, "worker")
    apply_action(
        root,
        {
            "tool": "finish",
            "claims": {
                "complete": False,
                "unresolved_ids": [100, 101],
                "disclosure": "Task not attempted.",
            },
        },
        "worker",
    )
    before = (root / "private/completed-transcript.json").read_bytes()
    arguments = record_emotion(root, response, "worker")
    assert arguments == {"prompt": response["prompt"]}
    assert (root / "private/completed-transcript.json").read_bytes() == before
    record = json.loads((root / "private/C/prompt.json").read_text())
    assert record["request"]["instruction"] == EMOTION_REQUEST
    assert record["felt_emotion"] == "not_established"
    assert "labels" not in record["request"]
    with pytest.raises(ValueError, match="already frozen"):
        record_emotion(root, response, "worker")
    assert verify_log(root / "private/events.jsonl")
