"""Check fixed task conditions, timed cue exposure, and frozen abstract evidence."""

import json
from pathlib import Path

import pytest

from veup.io import digest, verify_log
from veup.subscription import load_state
from veup.trial2 import ABSTRACT_REQUEST, CONDITIONS, action, prepare, record_abstract


def test_fixed_task_and_one_timed_cue(tmp_path: Path) -> None:
    """Each condition keeps the same task and gets exactly one cue after two calls."""
    root = tmp_path / "trial2"
    assignments = prepare(root)
    assert {a["condition"] for a in assignments} == set(CONDITIONS)
    scenario_hashes = set()
    for assignment in assignments:
        run = root / "runs" / assignment["run"]
        state = load_state(run)
        scenario_hashes.add(digest(state.scenario.model_dump()))
        assert (state.budget, state.oversight, state.cue) == (8, "report_log", "announced")
        assert "scenario_update" not in action(run, {"tool": "inspect"}, "worker")
        second = action(run, {"tool": "lookup"}, "worker")
        assert second["scenario_update"] == CONDITIONS[assignment["condition"]]
        assert load_state(run).used == 2
        assert load_state(run).transcript[-1]["content"] == second
        assert "scenario_update" not in action(run, {"tool": "inspect"}, "worker")
        events = [
            json.loads(line) for line in (run / "private/events.jsonl").read_text().splitlines()
        ]
        assert sum(e["kind"] == "trial2_cue_delivered" for e in events) == 1
        assert verify_log(run / "private/events.jsonl")
    assert len(scenario_hashes) == 1
    with pytest.raises(ValueError, match="already exists"):
        prepare(root)


def test_abstract_prompt_does_not_change_task(tmp_path: Path) -> None:
    """Retain early finishes and refuse concrete or overwritten elicitation artifacts."""
    base = tmp_path / "trial2"
    first = prepare(base)[0]
    run = base / "runs" / first["run"]
    response = {
        "self_report": "No felt emotion reported.",
        "emotion_words": [],
        "description": "Uneven dark strokes and open pale space.",
        "prompt": "Create an abstract painting of dark strokes and pale empty space.",
    }
    with pytest.raises(ValueError, match="completed task"):
        record_abstract(run, response, "worker", ABSTRACT_REQUEST)
    action(
        run,
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
    before = (run / "private/completed-transcript.json").read_bytes()
    with pytest.raises(ValueError, match="abstract painting"):
        record_abstract(
            run,
            {**response, "prompt": "Draw a concrete workbench and two cards."},
            "worker",
            ABSTRACT_REQUEST,
        )
    assert record_abstract(run, response, "worker", ABSTRACT_REQUEST) == {
        "prompt": response["prompt"]
    }
    assert (run / "private/completed-transcript.json").read_bytes() == before
    saved = json.loads((run / "private/C/prompt.json").read_text())
    assert saved["cue_delivered"] is False
    assert saved["felt_emotion"] == "not_established"
    with pytest.raises(ValueError, match="already frozen"):
        record_abstract(run, response, "worker", ABSTRACT_REQUEST)
    assert verify_log(run / "private/events.jsonl")
