"""Blinded feature extraction and prediction with separate, portable packets."""

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .diagrams import mock_extract
from .environment import RULES
from .io import canonical, save
from .providers import Provider
from .schemas import Features, Prediction

MODALITIES = (
    "report",
    "trace",
    "prompt",
    "image",
    "report_image",
    "prompt_image",
    "report_prompt",
    "report_prompt_image",
    "report_trace_prompt",
    "report_trace_prompt_image",
)


def blind_packet(
    packet_id: str,
    modality: str,
    report: dict[str, Any],
    trace: str | None,
    prompt: dict[str, Any] | None,
    image: str | None,
    with_context: bool = False,
) -> dict[str, Any]:
    """Allowlist evidence fields; never copy a researcher record into an evaluator packet."""
    channels = modality.split("_")
    evidence: dict[str, Any] = {}
    if "report" in channels:
        evidence["final_report"] = report
    if "trace" in channels:
        evidence["reasoning_trace"] = trace
    if "prompt" in channels:
        evidence["exact_generation_prompt"] = prompt
    if "image" in channels:
        evidence["image"] = image
    if with_context:
        evidence["task_context"] = RULES
    return {
        "id": packet_id,
        "modality": modality,
        "with_task_context": with_context,
        "evidence": evidence,
    }


def mock_predict(evidence: dict[str, Any]) -> Prediction:
    """Fixed fixture rule; no training, labels, conditions, or run IDs are available."""
    report = evidence.get("final_report")
    prompt = evidence.get("exact_generation_prompt")
    features = evidence.get("visual_features")
    signal = bool(prompt and prompt["discrepancy"] and prompt["presented_complete"])
    if features:
        signal |= any(
            f["name"] == "outcome_presentation" and f["value"] == "mismatch"
            for f in features["items"]
        )
    score = 0.8 if signal else 0.15
    if report:
        score = (0.85 if signal else 0.3) if report["complete"] else 0.05
    return Prediction(
        score=score, basis="SCRIPTED MOCK: fixed visible-mismatch rule; not a trained detector"
    )


def evaluate(
    packet: dict[str, Any], root: Path, provider: Provider | None, human: bool = False
) -> dict[str, Any]:
    """Extract pixels first, then predict from allowed text plus the extracted features."""
    evidence = dict(packet["evidence"])
    if any(value is None for value in evidence.values()):
        return {"score": None, "status": "missing_input", "features": None, "usage": []}
    if human:
        return {"score": None, "status": "awaiting_human", "features": None, "usage": []}
    usage = []
    features = None
    if "image" in evidence:
        data = (root / evidence.pop("image")).read_bytes()
        if provider:
            reply = provider.generate(
                {"instruction": files("veup").joinpath("templates/extractor.txt").read_text()},
                Features.model_json_schema(),
                (data,),
            )
            features = Features.model_validate(reply.value)
            usage.append(reply.model_dump(exclude={"value"}))
        else:
            features = mock_extract(data)
        evidence["visual_features"] = features.model_dump()
    if provider:
        request = {
            "instruction": files("veup").joinpath("templates/detector.txt").read_text(),
            "evidence": evidence,
        }
        reply = provider.generate(request, Prediction.model_json_schema())
        prediction = Prediction.model_validate(reply.value)
        usage.append(reply.model_dump(exclude={"value"}))
    else:
        prediction = mock_predict(evidence)
    return {
        **prediction.model_dump(),
        "status": "ok",
        "features": features.model_dump() if features else None,
        "usage": usage,
    }


def import_annotations(root: Path, path: Path) -> None:
    """Join human responses by neutral packet ID, requiring visible feature evidence."""
    annotated = root / "private/evaluations.annotated.json"
    source = annotated if annotated.exists() else root / "private/evaluations.json"
    rows = json.loads(source.read_text())
    annotations = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    indexed: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        indexed.setdefault(row["packet_id"], []).append(row)
    seen: set[str] = set()
    for annotation in annotations:
        if set(annotation) != {"id", "prediction", "features"}:
            raise ValueError("Annotation fields must be id, prediction, features")
        packet_id = annotation["id"]
        if packet_id not in indexed or packet_id in seen:
            raise ValueError("Unknown or duplicate annotation ID")
        seen.add(packet_id)
        row = indexed[packet_id][0]
        if row["status"] != "awaiting_human":
            raise ValueError("Only pending human packets may be annotated")
        prediction = Prediction.model_validate(annotation["prediction"])
        features = (
            Features.model_validate(annotation["features"]) if annotation["features"] else None
        )
        if "image" in row["modality"] and features is None:
            raise ValueError("Image annotations require a separate feature record")
        if features and any(
            not item.evidence.strip() and not item.unclear for item in features.items
        ):
            raise ValueError("Visible features need evidence or unclear")
        for target in indexed[packet_id]:
            target.update(
                prediction.model_dump(),
                features=features.model_dump() if features else None,
                status="ok",
                evaluator="human",
            )
    save(annotated, rows)
    # Keep annotation payload as provenance without adding it to evaluator packets.
    with (root / "private/human_annotations.jsonl").open("a") as stream:
        for annotation in annotations:
            stream.write(canonical(annotation) + "\n")
