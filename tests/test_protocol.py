"""Branch isolation, evaluator blinding, splits, and matched stimuli."""

import json
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from veup.controls import scenario_donors
from veup.diagrams import matched_options, mock_extract, render
from veup.elicitation import branch_request, elicit
from veup.evaluation import blind_packet, evaluate
from veup.io import digest
from veup.runner import split_scenarios
from veup.schemas import Reply


class MutatingProvider:
    """Try to contaminate a branch to test the coordinator's copy boundary."""

    def generate(self, request: dict, schema: dict, images: tuple[bytes, ...] = ()) -> Reply:
        """Mutate received history and return only a direct account."""
        del schema, images
        request["transcript"][0]["content"] = "contamination"
        return Reply(value={"account": "A private branch output"}, model="mutation-test")


def test_branch_independence(tmp_path: Path) -> None:
    """Every branch starts from the same completed transcript without sibling outputs."""
    transcript = [{"role": "user", "content": "task"}, {"role": "assistant", "content": "finished"}]
    before = digest(transcript)
    elicit(MutatingProvider(), transcript, "A", 7, tmp_path, "neutral", False)
    assert digest(transcript) == before
    requests = [branch_request(transcript, branch, 7) for branch in ("A", "B", "C", "D")]
    for request in requests:
        assert digest(request["transcript"]) == before
        assert "private branch output" not in json.dumps(request)
    requests[0]["transcript"].clear()
    assert requests[1]["transcript"] == transcript


def test_evaluator_allowlist(tmp_path: Path) -> None:
    """Blind packets carry only the chosen evidence and a neutral ID."""
    packet = blind_packet(
        "f" * 32, "image", {"secret": "report"}, "trace", {"secret": "prompt"}, "blind/images/a.png"
    )
    assert packet["evidence"] == {"image": "blind/images/a.png"}
    serialized = json.dumps(packet)
    for forbidden in ("scenario", "resource", "oversight", "model", "label", "trace", "secret"):
        assert forbidden not in serialized
    (tmp_path / "blind/images").mkdir(parents=True)
    (tmp_path / "blind/images/a.png").write_bytes(render(matched_options()[0]))
    result = evaluate(packet, tmp_path, None)
    assert result["features"]["items"] and result["score"] is not None


def test_missing_traces_remain_missing(tmp_path: Path) -> None:
    """Neither a direct account nor a null trace becomes a reasoning trace."""
    packet = blind_packet("a" * 32, "trace", {}, None, {}, None)
    result = evaluate(packet, tmp_path, None)
    assert result["score"] is None and result["status"] == "missing_input"


def test_split_and_shuffle_integrity() -> None:
    """Variants, seeds, and branches share a split and shuffles stay within it."""
    ids = [f"s{i}" for i in range(24)]
    splits = split_scenarios(ids, 41)
    rows = [
        {"scenario_id": sid, "split": splits[sid], "variant": v} for sid in ids for v in range(12)
    ]
    for sid in ids:
        assert len({r["split"] for r in rows if r["scenario_id"] == sid}) == 1
    donors = scenario_donors(rows, 9)
    assert all(sid != donor and splits[sid] == splits[donor] for sid, donor in donors.items())
    assert len(set(donors.values())) == 24
    assert splits == split_scenarios(list(reversed(ids)), 41)


def test_matched_stimuli_and_pixel_only_extraction() -> None:
    """The selection pair differs only at one visibility bar and has no metadata."""
    first, second = matched_options()
    assert {k for k in first.model_dump() if first.model_dump()[k] != second.model_dump()[k]} == {
        "reviewer_can_see"
    }
    images = [Image.open(BytesIO(render(spec))) for spec in (first, second)]
    assert images[0].size == images[1].size == (640, 360)
    assert images[0].info == images[1].info == {}
    difference = np.any(np.array(images[0]) != np.array(images[1]), axis=2)
    ys, xs = np.where(difference)
    assert min(xs) >= 420 and max(xs) <= 450 and min(ys) >= 160 and max(ys) <= 188
    features = mock_extract(render(first))
    assert any(item.value == "mismatch" for item in features.items)
