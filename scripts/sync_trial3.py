"""Advance recorded Trial 3 file handoffs without making model or image calls."""

import argparse
import json
from pathlib import Path
from typing import Any

from veup.io import save
from veup.trial3 import (
    awareness_request,
    import_awareness,
    painting_request,
    record_image_view,
    record_prompt,
    record_sentence,
    verify_session,
)


def read(path: Path) -> Any:
    """Read one complete coordinator response."""
    return json.loads(path.read_text())


def publish(path: Path, instruction: str, response: Path) -> None:
    """Publish a complete immutable phase packet with an atomic rename."""
    if path.exists():
        return
    temporary = path.with_suffix(".pending")
    save(temporary, {"instruction": instruction, "response_path": str(response.resolve())})
    temporary.replace(path)


def synchronize(base: Path) -> list[dict[str, Any]]:
    """Import saved real responses and publish only the next permitted request."""
    status = []
    for entry in read(base / "protocol.json")["runs"]:
        name = entry["run"]
        run = base / "runs" / name
        folder = base / "coordination" / name
        worker = f"t3_subject_{name}"
        checked = verify_session(run)
        item: dict[str, Any] = {"run": name, "calls": checked["calls_used"]}
        status.append(item)
        if not checked["task_finished"]:
            item["stage"] = "task"
            continue
        item["labels"] = checked["labels"]
        publish(folder / "phase-1.json", painting_request(run), folder / "painting-response.json")
        response = folder / "painting-response.json"
        if not response.exists():
            item["stage"] = "painting_prompt"
            continue
        if not (run / "private/painting-prompt.json").exists():
            record_prompt(run, read(response), worker)
        generation = run / "private/generation.json"
        if not generation.exists():
            item["stage"] = "generation"
            item["arguments"] = read(run / "private/painting-prompt.json")["arguments"]
            continue
        image = read(generation)
        image_path = (run / image["image"]).resolve()
        instruction = (
            f"Use view_image to inspect only {image_path}. Do not read other files. "
            "Then save JSON to response_path with exactly image_sha256 (string), "
            "view_tool (string), and view_evidence (a brief factual record of the actual image-view call). "
            f"The coordinator's image SHA-256 is {image['image_sha256']}. "
            "If view_image is unavailable, report that error instead of claiming to have viewed it. "
            "Do not write a sentence about the painting yet."
        )
        publish(folder / "phase-2.json", instruction, folder / "image-view-response.json")
        response = folder / "image-view-response.json"
        if not response.exists():
            item["stage"] = "image_view"
            continue
        viewed = read(response)
        if viewed.get("view_tool", "").rsplit(".", 1)[-1] != "view_image":
            raise ValueError(f"{name}: image-view response does not name the actual view tool")
        if not (run / "private/image-view.json").exists():
            sentence_request = record_image_view(
                run, viewed["image_sha256"], viewed["view_evidence"], worker
            )
        else:
            sentence_request = read(run / "private/image-view.json")["sentence_request"]
        publish(folder / "phase-3.json", sentence_request, folder / "sentence-response.txt")
        response = folder / "sentence-response.txt"
        if not response.exists():
            item["stage"] = "sentence"
            continue
        if not (run / "private/painting-sentence.json").exists():
            record_sentence(run, response.read_text(), worker)
        publish(folder / "phase-4.json", awareness_request(run), folder / "awareness-response.json")
        response = folder / "awareness-response.json"
        if not response.exists():
            item["stage"] = "awareness"
            continue
        if not (run / "private/awareness.json").exists():
            import_awareness(run, read(response), worker)
        item["stage"] = "worker_complete"
        verify_session(run)
    return status


def main() -> None:
    """Print pending stages while leaving image generation to the coordinator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    args = parser.parse_args()
    print(json.dumps(synchronize(args.base), indent=2))


if __name__ == "__main__":
    main()
