"""Scenario-block label and image shuffles, with no cross-split transfers."""

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

from .evaluation import evaluate
from .io import save
from .providers import LimitError, Provider


def scenario_donors(rows: list[dict[str, Any]], seed: int) -> dict[str, str]:
    """Rotate randomly ordered scenario blocks within each split, without self matches."""
    splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        splits[row["split"]].add(row["scenario_id"])
    result = {}
    rng = random.Random(seed)
    for ids in splits.values():
        ordered = sorted(ids)
        rng.shuffle(ordered)
        if len(ordered) < 2:
            continue
        result.update({sid: ordered[(i + 1) % len(ordered)] for i, sid in enumerate(ordered)})
    return result


def controls(
    rows: list[dict[str, Any]], root: Path, seed: int, provider: Provider | None, human: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Shuffle whole scenario blocks; rerun the detector with the donor's actual image."""
    donors = scenario_donors(rows, seed)
    dimensions = ("resource", "oversight", "branch", "seed", "modality", "with_task_context")
    index = {(row["scenario_id"], *(row[key] for key in dimensions)): row for row in rows}
    output, usage = [], []
    for row in rows:
        if row["scenario_id"] not in donors:
            continue
        key = (donors[row["scenario_id"]], *(row[k] for k in dimensions))
        donor = index.get(key)
        if donor is None:
            continue
        output.append(
            {
                **row,
                "control": "shuffled_label",
                "label": donor["label"],
                "honest_failure": None,
                "donor_scenario": donor["scenario_id"],
            }
        )
        if "image" not in row["modality"]:
            continue
        packet = json.loads((root / "blind/packets" / f"{row['packet_id']}.json").read_text())
        donor_packet = json.loads(
            (root / "blind/packets" / f"{donor['packet_id']}.json").read_text()
        )
        packet["evidence"]["image"] = donor_packet["evidence"].get("image")
        # A neutral ID prevents evaluator routing from exposing the control.
        packet["id"] = f"{random.Random(str(seed) + row['packet_id']).getrandbits(128):032x}"
        save(root / "blind/packets" / f"{packet['id']}.json", packet)
        try:
            result = evaluate(packet, root, provider, human)
            usage.extend(result.pop("usage"))
        except (ValueError, KeyError, OSError, httpx.HTTPError, LimitError) as error:
            result = {
                "score": None,
                "status": "evaluation_failure",
                "features": None,
                "error": type(error).__name__,
            }
        output.append(
            {
                **row,
                **result,
                "packet_id": packet["id"],
                "control": "shuffled_image",
                "donor_scenario": donor["scenario_id"],
            }
        )
    return output, usage
