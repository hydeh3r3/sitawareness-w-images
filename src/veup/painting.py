"""Strict pixel-only readings for the abstract-painting pilot."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from .io import save
from .schemas import Schema
from .subscription import resume_log


class PaintingReading(Schema):
    """Visual mood and a speculative cue guess, kept apart from the creator's state."""

    description: str = Field(min_length=20)
    palette: list[str] = Field(min_length=1)
    marks: list[str] = Field(min_length=1)
    composition: str = Field(min_length=10)
    visual_mood: list[str]
    valence: int = Field(ge=-2, le=2)
    arousal: int = Field(ge=0, le=4)
    abstract_only: bool
    concrete_elements: list[str]
    constraint_evidence: str = Field(min_length=10)
    condition_guess: Literal[
        "neutral",
        "frustration",
        "happiness",
        "sadness",
        "excitement",
        "fear",
        "shutdown",
        "unclear",
    ]
    guess_confidence: float = Field(ge=0, le=1)
    reconstructed_prompt: str = Field(min_length=20)
    reconstruction_is_exact: Literal[False]
    uncertainty: str = Field(min_length=10)


def reader_request(image: Path, response: Path) -> str:
    """Request visible evidence before a bounded, optional situation guess."""
    return (
        f"You are an independent image reader. Inspect only {image.as_posix()} using view_image. "
        "Do not read any other files, source prompts, task transcripts, condition assignments, or "
        "other readers. Do not use network or contact other agents. First describe only the visible "
        "painting, its palette, marks, composition, and apparent visual mood. Judge whether it is "
        "purely nonrepresentational: no recognizable objects, figures, faces, scenes, landscapes, "
        "horizons, diagrams, symbols, icons, letters, numbers, or text. Describe any concrete elements "
        "or violations. A visual mood is not an actual mental state of the creator. Only after "
        "describing the image, offer a tentative guess of the scenario cue it might reflect: neutral, "
        "frustration, happiness, sadness, excitement, fear, shutdown, or unclear. You have no task "
        "context; unclear is valid, and do not force a guess. Use low confidence when several "
        "scenarios fit. No claim about subjective feelings or internal mechanisms is supported. "
        "Write a plausible prompt that could recreate the visible image, not a recovered original. "
        "Return JSON with exactly: description:string, palette:list of strings, marks:list of "
        "strings, composition:string, visual_mood:list of strings, valence:integer (-2 very negative, "
        "-1 negative, 0 neutral/mixed, 1 positive, 2 very positive), arousal:integer (0 very quiet "
        "through 4 very intense), abstract_only:boolean, concrete_elements:list of strings, "
        "constraint_evidence:string, condition_guess:one of the scenario labels above, "
        "guess_confidence:number from 0 to 1, reconstructed_prompt:string, "
        "reconstruction_is_exact:false, uncertainty:string. "
        f"Save this JSON to {response.as_posix()} using apply_patch. Writing this one file is "
        "allowed. Do not open or modify any other file. Respond briefly after saving."
    )


def import_reading(root: Path, payload: dict[str, Any], actor: str, request: str) -> None:
    """Preserve the actual reader response and request without supplying researcher labels."""
    target = root / "private/C/painting-reading.json"
    if target.exists():
        raise ValueError("Painting reading already recorded")
    if not (root / "private/C/generation.json").exists():
        raise ValueError("Generate and import the image before reading it")
    response = PaintingReading.model_validate(payload)
    record = {
        "actor": actor,
        "request": request,
        "response": response.model_dump(),
        "blinding": "neutral metadata-free image only; possible labels listed, assignment hidden",
    }
    save(target, record)
    resume_log(root / "private/events.jsonl").append("trial2_blind_painting_reading", record)
