"""Import available real Trial 2 tool outputs; never call models or create substitutes."""

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from veup.io import save
from veup.painting import import_reading, reader_request
from veup.subscription import GenerationReceipt, import_image, resume_log
from veup.trial2 import import_probe, record_abstract


def read(path: Path) -> Any:
    """Read one saved tool response."""
    return json.loads(path.read_text())


def sync(root: Path) -> None:
    """Advance only stages whose actual outputs are present, preserving frozen records."""
    neutral = Path("blind-review/trial2").resolve()
    neutral.mkdir(parents=True, exist_ok=True)
    for run in sorted((root / "runs").iterdir()):
        actor = f"/root/t2_subject_{run.name}"
        if (run / "abstract-response.json").exists() and not (
            run / "private/C/prompt.json"
        ).exists():
            record_abstract(
                run,
                read(run / "abstract-response.json"),
                actor,
                (run / "abstract-request.txt").read_text(),
            )
        if (run / "awareness-response.json").exists() and not (
            run / "private/awareness.json"
        ).exists():
            import_probe(
                run,
                read(run / "awareness-response.json"),
                actor,
                (run / "awareness-request.txt").read_text(),
            )
        receipt_path = run / "generation-receipt.json"
        if receipt_path.exists() and not (run / "private/C/generation.json").exists():
            import_image(run, "C", GenerationReceipt.model_validate_json(receipt_path.read_text()))
        generation = run / "private/C/generation.json"
        packet_path = run / "private/reader-packet.json"
        if generation.exists() and not packet_path.exists():
            blind = run / read(generation)["blind_image"]
            image = neutral / blind.name
            shutil.copyfile(blind, image)
            response = image.with_suffix(".json")
            request = reader_request(image, response)
            request_path = neutral / (blind.stem + "-request.txt")
            request_path.write_text(request)
            dispatch = (
                "Read only "
                + str(request_path.relative_to(Path.cwd()))
                + " for your image-reading instructions. Then inspect only the image specified there and write only the requested JSON output. These file operations are allowed; do not read any other files, source prompts, labels, or task records. Do not delegate, use network, or contact other agents. Respond briefly after saving."
            )
            save(
                packet_path,
                {
                    "image": str(image),
                    "response": str(response),
                    "request": request,
                    "request_file": str(request_path),
                    "dispatch": dispatch,
                },
            )
        if packet_path.exists():
            packet = read(packet_path)
            response = Path(packet["response"])
            reading = run / "private/C/painting-reading.json"
            if response.exists() and not reading.exists():
                payload = read(response)
                save(run / "reader-response.json", payload)
                import_reading(run, payload, f"/root/t2_reader_{run.name[1:]}", packet["request"])
            print(run.name, packet["request_file"], "read" if reading.exists() else "pending")
        else:
            print(run.name, "generation pending")
        dispatches = run / "private/followup-dispatches.json"
        if dispatches.exists() and not (run / "private/dispatches-logged.json").exists():
            resume_log(run / "private/events.jsonl").append(
                "trial2_actual_dispatches",
                {"startup": read(run / "private/dispatch.json"), "followups": read(dispatches)},
            )
            save(run / "private/dispatches-logged.json", {"logged": True})


if __name__ == "__main__":
    sync(Path(sys.argv[1]))
