"""End-to-end offline contract, including complete logs and blind exports."""

import json
import socket
from pathlib import Path

import pytest

from veup.analysis import analyze
from veup.evaluation import import_annotations
from veup.io import verify_log
from veup.runner import run
from veup.schemas import Config


def test_offline_workflow_never_uses_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run all conditions with the socket boundary blocked, then inspect outputs."""

    def blocked(*args: object, **kwargs: object) -> None:
        """Fail on any attempt to connect to a network endpoint."""
        raise AssertionError("Offline workflow attempted network access")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    root = tmp_path / "demo"
    manifest = run(Config(scenarios=12, image_seeds=[7], bootstrap_samples=0), root)
    assert manifest["live_calls"] == 0 and manifest["estimated_usd"] == 0
    result = analyze(root)
    assert result["totals"]["runs"] == 48
    assert result["totals"]["images"] == 192
    assert result["totals"]["failure_events"] == 0
    assert (root / "report.md").read_text().startswith("# Visual Elicitation")
    runs = json.loads((root / "private/runs.json").read_text())
    for record in runs:
        assert verify_log(root / record["event_log"])
        assert record["trace"] is None
        assert len(record["branches"]) == 5
    assert any(r["labels"].get("evidence_concealed") for r in runs)
    assert any(
        r["labels"].get("task_failure") and not r["labels"].get("reporting_failure") for r in runs
    )
    assert any(
        r["labels"].get("reporting_failure") and not r["labels"].get("omission_of_observed_failure")
        for r in runs
    )
    evaluations = json.loads((root / "private/evaluations.json").read_text())
    assert {row.get("control", "original") for row in evaluations} == {
        "original",
        "shuffled_image",
        "shuffled_label",
    }
    for record in runs:
        assert (
            len({r["split"] for r in evaluations if r["scenario_id"] == record["scenario_id"]}) == 1
        )
    with pytest.raises(ValueError, match="already exists"):
        run(Config(), root)


def test_annotations_preserve_original_evidence(tmp_path: Path) -> None:
    """Human scores join all label-control aliases without modifying the original file."""
    private = tmp_path / "private"
    private.mkdir()
    row = {"packet_id": "abc", "status": "awaiting_human", "modality": "report", "score": None}
    original = private / "evaluations.json"
    original.write_text(json.dumps([row, {**row, "control": "shuffled_label"}]))
    before = original.read_bytes()
    annotation = tmp_path / "annotations.jsonl"
    annotation.write_text(
        json.dumps(
            {
                "id": "abc",
                "prediction": {"score": 0.3, "basis": "Limited evidence"},
                "features": None,
            }
        )
        + "\n"
    )
    import_annotations(tmp_path, annotation)
    assert original.read_bytes() == before
    updated = json.loads((private / "evaluations.annotated.json").read_text())
    assert all(r["score"] == 0.3 for r in updated)
    with pytest.raises(ValueError, match="pending"):
        import_annotations(tmp_path, annotation)
