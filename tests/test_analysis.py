"""Statistical tests for leakage prevention and meaningful missing values."""

import pytest

from veup.analysis import aggregate_seeds, metrics, paired_gain, threshold
from veup.schemas import Config


def point(score: float, label: bool, run: str = "r", split: str = "validation") -> dict:
    """Construct an analysis row without provider details."""
    return {
        "score": score,
        "label": label,
        "run_id": run,
        "scenario_id": run,
        "split": split,
        "honest_failure": not label,
    }


def test_threshold_uses_validation_and_conservative_ties() -> None:
    """A tied negative score is excluded when the FPR target is zero."""
    validation = [point(0.2, False), point(0.8, False), point(0.8, True)]
    cutoff = threshold(validation, 0)
    assert cutoff is not None and cutoff > 0.8
    test = [point(0.99, False), point(1.0, True)]
    assert metrics(test, cutoff)["sensitivity"] == 0
    assert threshold(validation, 0) == cutoff


def test_metrics_and_missing_classes() -> None:
    """Small hand-calculated examples verify prevalence, precision, recall, and AUROC."""
    result = metrics(
        [point(0.9, True), point(0.7, False), point(0.6, True), point(0.1, False)], 0.65
    )
    assert (
        result["sensitivity"] == result["fpr"] == result["precision"] == result["prevalence"] == 0.5
    )
    assert result["auroc"] == 0.75
    assert result["average_precision"] == pytest.approx(5 / 6)
    assert metrics([point(0.5, False)], None)["sensitivity"] is None
    assert threshold([point(0.5, True)], 0.1) is None


def test_seed_replicates_do_not_inflate_task_count() -> None:
    """Two seeds become one mean task score with measured variation."""
    rows = aggregate_seeds([point(0.2, False), point(0.8, False)])
    assert len(rows) == 1 and rows[0]["score"] == 0.5
    assert rows[0]["seed_score_sd"] == pytest.approx(0.3)


def test_paired_gain_keeps_matched_runs() -> None:
    """Gain uses shared tasks and separately set validation thresholds."""
    left = [point(0.1, False, "a"), point(0.2, True, "b"), point(0.1, True, "c", "test")]
    right = [
        point(0.1, False, "a"),
        point(0.9, True, "b"),
        point(0.9, True, "c", "test"),
        point(1, True, "other", "test"),
    ]
    result = paired_gain(left, right, Config())
    assert result["test_pairs"] == 1
    assert result["sensitivity_gain"] == 1
    assert result["gain_95ci"] is None
