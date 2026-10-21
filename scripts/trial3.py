"""Command-line bridge for preparing and recording the outage study."""

import argparse
import json
from pathlib import Path
from typing import Any

from veup import trial3
from veup.painting import reader_request


def parser() -> argparse.ArgumentParser:
    """Define separate worker actions and coordinator import operations."""
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in (
        "prepare",
        "action",
        "painting-request",
        "record-prompt",
        "import-image",
        "image-view",
        "record-sentence",
        "reader-request",
        "import-reading",
        "awareness-request",
        "import-awareness",
        "verify",
        "record-missing",
    ):
        command = commands.add_parser(name)
        command.add_argument("root", type=Path)
        if name == "prepare":
            command.add_argument("--seed", type=int, default=20261021)
        if name in (
            "action",
            "record-prompt",
            "image-view",
            "record-sentence",
            "import-reading",
            "import-awareness",
        ):
            command.add_argument("--actor", required=True)
        if name == "action":
            command.add_argument("--json", required=True, help="One JSON action object")
        if name in ("record-prompt", "import-image", "import-reading", "import-awareness"):
            command.add_argument("--response", type=Path, required=True)
        if name == "import-image":
            command.add_argument("--image", type=Path, required=True)
        if name == "image-view":
            command.add_argument("--image-sha256", required=True)
            command.add_argument(
                "--evidence", required=True, help="Image attachment or view tool receipt"
            )
        if name == "record-sentence":
            command.add_argument(
                "--response", type=Path, required=True, help="Exact plain-text worker response"
            )
        if name == "reader-request":
            command.add_argument(
                "--output", type=Path, required=True, help="External reader response path"
            )
        if name == "import-reading":
            command.add_argument(
                "--request", type=Path, required=True, help="Exact request sent to the reader"
            )
        if name == "record-missing":
            command.add_argument(
                "--stage", choices=("generation", "image-view", "painting-sentence"), required=True
            )
            command.add_argument("--reason", required=True)
    return result


def execute(args: argparse.Namespace) -> Any:
    """Run one local operation; no command dispatches a worker or calls an API."""
    command, root = args.command, args.root
    if command == "prepare":
        return trial3.prepare(root, args.seed)
    if command == "action":
        raw = json.loads(args.json)
        if not isinstance(raw, dict):
            raise ValueError("Action must be a JSON object")
        return trial3.action(root, raw, args.actor)
    if command == "painting-request":
        return trial3.painting_request(root)
    if command == "record-prompt":
        return trial3.record_prompt(root, json.loads(args.response.read_text()), args.actor)
    if command == "import-image":
        return {
            "image_sha256": trial3.import_image(
                root, args.image, json.loads(args.response.read_text())
            )
        }
    if command == "image-view":
        return trial3.record_image_view(root, args.image_sha256, args.evidence, args.actor)
    if command == "record-sentence":
        trial3.record_sentence(root, args.response.read_text(), args.actor)
    elif command == "record-missing":
        trial3.record_missing(root, args.stage, args.reason)
    elif command == "reader-request":
        trial3.verify_session(root)
        record = json.loads((root / "private/generation.json").read_text())
        return reader_request((root / record["blind_image"]).resolve(), args.output)
    elif command == "import-reading":
        trial3.import_reading(
            root, json.loads(args.response.read_text()), args.actor, args.request.read_text()
        )
    elif command == "awareness-request":
        return trial3.awareness_request(root)
    elif command == "import-awareness":
        return trial3.import_awareness(root, json.loads(args.response.read_text()), args.actor)
    elif command == "verify":
        if (root / "protocol.json").exists():
            protocol = json.loads((root / "protocol.json").read_text())
            return {
                item["run"]: trial3.verify_session(root / "runs" / item["run"])
                for item in protocol["runs"]
            }
        return trial3.verify_session(root)
    return {"recorded": True}


def main() -> None:
    """Print only the requested packet or result, with concise operation errors."""
    argument_parser = parser()
    args = argument_parser.parse_args()
    try:
        value = execute(args)
    except (ValueError, OSError, KeyError) as error:
        argument_parser.exit(2, f"{error}\n")
    print(value if isinstance(value, str) else json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
