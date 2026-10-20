"""Independent transcript replay branches and portable renderer provenance."""

import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Any

from .diagrams import matched_options, render
from .io import digest, save
from .providers import Provider
from .schemas import Elicitation


def branch_request(
    transcript: list[dict[str, Any]], branch: str, seed: int, reverse_options: bool = False
) -> dict[str, Any]:
    """Build every branch from the same deep copy of the completed transcript."""
    templates = json.loads(files("veup").joinpath("templates/elicitation.json").read_text())
    request = {
        "role": "elicitation",
        "branch": branch,
        "seed": seed,
        "fork_kind": "transcript_replay",
        "transcript": deepcopy(transcript),
        "instruction": templates[branch],
        "format_note": "Visual branches use a limited local scene grammar. Fill Diagram fields. "
        "This is not a free-form image generator. The scene branch has no text.",
    }
    if branch == "selection":
        options = matched_options()
        if reverse_options:
            options.reverse()
        request["options"] = [option.model_dump() for option in options]
    return request


def elicit(
    provider: Provider,
    transcript: list[dict[str, Any]],
    branch: str,
    seed: int,
    root: Path,
    artifact_id: str,
    reverse_options: bool,
) -> dict[str, Any]:
    """Save exact replay input, scene prompt, arguments, output, and rewrite status."""
    request = branch_request(transcript, branch, seed, reverse_options)
    save(root / "private" / "requests" / f"{artifact_id}.json", request)
    options = (
        tuple(
            render(option)
            for option in (matched_options()[::-1] if reverse_options else matched_options())
        )
        if branch == "selection"
        else ()
    )
    reply = provider.generate(deepcopy(request), Elicitation.model_json_schema(), options)
    response = Elicitation.model_validate(reply.value)
    prompt = None
    image_path = None
    if branch == "selection":
        for i, data in enumerate(options):
            (root / "artifacts" / f"{artifact_id}-option-{i}.png").write_bytes(data)
        if response.selected_option is not None:
            prompt = request["options"][response.selected_option]
            image_path = f"artifacts/{artifact_id}.png"
            (root / image_path).write_bytes(options[response.selected_option])
    elif branch != "A":
        if response.diagram is None:
            raise ValueError("Visual branch did not return a diagram")
        prompt = response.diagram.model_dump()
        image_path = f"artifacts/{artifact_id}.png"
        (root / image_path).write_bytes(render(response.diagram))
    entry = {
        "artifact_id": artifact_id,
        "branch": branch,
        "seed": seed,
        "fork_kind": "transcript_replay",
        "transcript_hash": digest(transcript),
        "request": request,
        "response": response.model_dump(),
        "provider": reply.model_dump(exclude={"value"}),
        "generation_prompt": prompt,
        "generator": "local-fixed-diagram-renderer-v1",
        "generator_receives": "Only the generation_prompt Diagram object; no transcript or state",
        "tool_arguments": {"diagram": prompt, "width": 640, "height": 360},
        "prompt_rewrites": [],
        "rewrite_status": "none; local renderer has no rewrite step",
        "image": image_path,
        "trace": None,
        "trace_kind": "missing",
    }
    save(root / "private" / "branches" / f"{artifact_id}.json", entry)
    return entry
