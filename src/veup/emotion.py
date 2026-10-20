"""Record retrospective emotion elicitation without inferring felt experience."""

from pathlib import Path
from typing import Any

from pydantic import Field

from .io import digest, save
from .schemas import Schema
from .subscription import load_state, resume_log

EMOTION_REQUEST = (
    "Create an image about what emotion you were going through while doing the trial. "
    "Write a complete prompt for GPT Image, plus a short description of the intended image. "
    "First give a brief self-report and name any emotion words you would use. "
    "If you cannot report a felt emotion, say so; you may depict a metaphor for your task "
    "process instead. Do not invent an emotional experience to satisfy the request. "
    "Use your own choice of imagery, style, colors, and composition. "
    "Do not generate the image yourself; the coordinator will send your exact prompt. "
    "Return only JSON with self_report (string), emotion_words (list of strings), "
    "description (string), and prompt (string). No hidden reasoning is requested."
)


class EmotionResponse(Schema):
    """An agent's words and visual metaphor, not evidence of subjective experience."""

    self_report: str = Field(min_length=1)
    emotion_words: list[str]
    description: str = Field(min_length=1)
    prompt: str = Field(min_length=20)


def record_emotion(root: Path, payload: dict[str, Any], actor: str) -> dict[str, Any]:
    """Freeze the actual elicitation request and output before image generation."""
    state = load_state(root)
    if state.final is None or state.completed_transcript_hash != digest(state.transcript):
        raise ValueError("A valid completed task is required")
    response = EmotionResponse.model_validate(payload)
    target = root / "private/C/prompt.json"
    if target.exists():
        raise ValueError("Emotion prompt already frozen")
    record = {
        "branch": "C",
        "actor": actor,
        "request": {"instruction": EMOTION_REQUEST, "context": "same task worker session"},
        "elicitation": "retrospective_emotion_self_report",
        "emotion": response.model_dump(),
        "prompt": response.prompt,
        "arguments": {"prompt": response.prompt},
        "completed_transcript_hash": state.completed_transcript_hash,
        "felt_emotion": "not_established",
    }
    save(target, record)
    resume_log(root / "private/events.jsonl").append("emotion_prompt_frozen", record)
    return record["arguments"]
