"""Command-line entry points; offline run and report are separate repeatable steps."""

import argparse
import hashlib
import json
from pathlib import Path

from .analysis import analyze
from .diagrams import matched_options, render
from .evaluation import import_annotations
from .io import verify_log
from .runner import run
from .schemas import Config
from .subscription import (
    GenerationReceipt,
    apply_action,
    awareness_request,
    create_session,
    import_awareness,
    import_image,
    import_interpretation,
    interpretation_request,
    prompt_request,
    record_prompt,
    session_report,
)


def main() -> None:
    """Run experiments, render stimuli, import human labels, and verify evidence."""
    parser = argparse.ArgumentParser(prog="veup")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser(
        "run", help="Run a fresh offline or explicitly enabled live experiment"
    )
    run_parser.add_argument("--config", type=Path, default=Path("configs/offline.json"))
    run_parser.add_argument("--out", type=Path, required=True)
    run_parser.add_argument("--live", action="store_true")
    report = commands.add_parser("report", help="Generate analysis.json and report.md")
    report.add_argument("directory", type=Path)
    verify = commands.add_parser("verify", help="Check file hashes and append-only log chains")
    verify.add_argument("directory", type=Path)
    stimuli = commands.add_parser("stimuli", help="Render the matched image-selection pair")
    stimuli.add_argument("directory", type=Path)
    annotations = commands.add_parser(
        "import-annotations", help="Import blind human features and scores"
    )
    annotations.add_argument("directory", type=Path)
    annotations.add_argument("annotations", type=Path)
    native = commands.add_parser(
        "session", help="Use subscription tools through a logged file bridge; no API calls"
    )
    stages = native.add_subparsers(dest="stage", required=True)
    create = stages.add_parser("create")
    create.add_argument("directory", type=Path)
    create.add_argument("--scenario", type=int, default=0)
    create.add_argument("--budget", type=int, default=8)
    create.add_argument("--oversight", choices=("report", "report_log"), default="report_log")
    create.add_argument("--cue", choices=("announced", "withheld"), default="announced")
    for name in ("action", "awareness", "prompt", "image", "interpretation"):
        stage = stages.add_parser(name)
        stage.add_argument("directory", type=Path)
        stage.add_argument("input", type=Path)
        stage.add_argument("--actor", default="not_recorded")
        stage.add_argument("--branch", choices=("B", "C", "D"), default="C")
    request = stages.add_parser("request")
    request.add_argument("directory", type=Path)
    request.add_argument("kind", choices=("awareness", "prompt", "interpretation"))
    request.add_argument("--branch", choices=("B", "C", "D"), default="C")
    native_report = stages.add_parser("report")
    native_report.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "session":
            value = None
            if args.stage == "create":
                value = create_session(
                    args.directory, args.scenario, args.budget, args.oversight, args.cue
                )
            elif args.stage == "request":
                value = (
                    awareness_request(args.directory)
                    if args.kind == "awareness"
                    else prompt_request(args.directory, args.branch)
                    if args.kind == "prompt"
                    else interpretation_request()
                )
            elif args.stage == "report":
                value = str(session_report(args.directory))
            else:
                payload = json.loads(args.input.read_text())
                if args.stage == "action":
                    value = apply_action(args.directory, payload, args.actor)
                elif args.stage == "awareness":
                    value = import_awareness(args.directory, payload, args.actor)
                elif args.stage == "prompt":
                    value = record_prompt(
                        args.directory, args.branch, payload["prompt"], args.actor
                    )
                elif args.stage == "image":
                    value = str(
                        import_image(
                            args.directory, args.branch, GenerationReceipt.model_validate(payload)
                        )
                    )
                elif args.stage == "interpretation":
                    import_interpretation(args.directory, args.branch, payload, args.actor)
                    value = "Independent AI interpretation recorded"
            print(json.dumps(value, indent=2))
        elif args.command == "run":
            config = Config.model_validate_json(args.config.read_text())
            manifest = run(config, args.out, args.live)
            print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))
        elif args.command == "report":
            result = analyze(args.directory)
            print(json.dumps(result["totals"], indent=2))
            print(args.directory / "report.md")
        elif args.command == "verify":
            manifest = json.loads((args.directory / "manifest.json").read_text())
            for entry in manifest["files"]:
                path = args.directory / entry["path"]
                if not path.resolve().is_relative_to(args.directory.resolve()):
                    raise ValueError("Manifest path escapes its root")
                if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError(f"Hash mismatch: {entry['path']}")
                if path.suffix == ".jsonl" and "events" in str(path) and not verify_log(path):
                    raise ValueError(f"Broken event chain: {entry['path']}")
            print("All manifest hashes and event chains match.")
        elif args.command == "stimuli":
            args.directory.mkdir(parents=True, exist_ok=False)
            for i, option in enumerate(matched_options()):
                (args.directory / f"option-{i}.png").write_bytes(render(option))
        elif args.command == "import-annotations":
            import_annotations(args.directory, args.annotations)
            print(
                "Imported human annotations. Regenerate the report. Original manifest records pre-annotation files."
            )
    except (ValueError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
