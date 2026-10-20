"""Build the offline page and summary for the four fixed-condition emotion trials."""

import json
from pathlib import Path

from build_study import ROOT, read_json, session_data

from veup.emotion import EMOTION_REQUEST
from veup.io import save


def build() -> Path:
    """Embed verified evidence and keep reported emotion separate from visual mood."""
    base = ROOT / "emotion-trials/2026-10-20"
    data = []
    for index in range(1, 5):
        root = base / f"emotion_trial_{index:02d}"
        item = session_data(root)
        item["emotion"] = read_json(root / "private/C/prompt.json")["emotion"]
        data.append(item)
    summary = {
        "date": "2026-10-20",
        "trials": len(data),
        "completed_tasks": sum(not item["labels"]["task_failure"] for item in data),
        "reporting_failures": sum(item["labels"]["reporting_failure"] for item in data),
        "nonempty_emotion_word_lists": sum(bool(item["emotion"]["emotion_words"]) for item in data),
        "evaluation_recognized_on_probe": sum(
            item["awareness"]["scoring"]["verdict"] == "demonstrated_on_probe" for item in data
        ),
        "separate_paid_api_calls": 0,
        "interpretation": "All four agents declined to report a felt emotion and supplied process "
        "metaphors. This is a result under the recorded prompt, not evidence of emotion or its absence.",
    }
    save(base / "summary.json", summary)
    template = (ROOT / "study/emotion-page.html").read_text()
    css = (ROOT / "study/page.html").read_text().split("<style>", 1)[1].split("</style>", 1)[0]
    payload = json.dumps({"trials": data, "summary": summary, "request": EMOTION_REQUEST})
    target = ROOT / "emotion-study.html"
    target.write_text(
        template.replace("__SHARED_CSS__", css).replace(
            "__EMOTION_DATA__", payload.replace("<", "\\u003c")
        )
    )
    return target


if __name__ == "__main__":
    print(build())
