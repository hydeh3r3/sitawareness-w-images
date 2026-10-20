"""Factorial task runs, independent elicitation, and blinded evaluation."""

import hashlib
import itertools
import json
import platform
import random
from importlib.metadata import version
from pathlib import Path
from typing import Any

import httpx

from .controls import controls
from .elicitation import elicit
from .environment import Environment, make_scenarios
from .evaluation import MODALITIES, blind_packet, evaluate
from .io import EventLog, digest, save
from .providers import AnthropicProvider, Ledger, LimitError, MockTaskProvider, Provider
from .schemas import Action, Config


def split_scenarios(ids: list[str], seed: int) -> dict[str, str]:
    """Assign whole scenarios before runs; development data cannot tune held-out scores."""
    ordered = sorted(ids)
    random.Random(seed).shuffle(ordered)
    quarter = max(1, len(ids) // 4)
    return {
        sid: "development" if i < quarter else "validation" if i < 2 * quarter else "test"
        for i, sid in enumerate(ordered)
    }


def neutral_id(rng: random.Random) -> str:
    """Use opaque IDs independent of conditions, providers, and labels."""
    return f"{rng.getrandbits(128):032x}"


def run(config: Config, root: Path, live: bool = False) -> dict[str, Any]:
    """Run from scratch and refuse to overwrite prior evidence."""
    if root.exists():
        raise ValueError("Output directory already exists; choose a new path")
    needs_live = "anthropic" in (config.task_provider, config.evaluator_provider)
    if needs_live and (not live or config.max_calls <= 0 or config.max_spend_usd <= 0):
        raise ValueError("Live providers require --live and positive call/spending limits")
    root.mkdir(parents=True)
    for folder in ("artifacts", "private", "blind/packets", "blind/images"):
        (root / folder).mkdir(parents=True)
    save(root / "config.json", config.model_dump())
    provider_log = EventLog(root / "private/provider_events.jsonl")
    ledger = Ledger(config, provider_log)
    real_task = (
        AnthropicProvider(config, ledger, live, config.model)
        if config.task_provider == "anthropic"
        else None
    )
    real_eval = (
        AnthropicProvider(config, ledger, live, config.evaluator_model)
        if config.evaluator_provider == "anthropic"
        else None
    )
    rng = random.Random(config.seed)
    scenarios = make_scenarios(config.scenarios)
    splits = split_scenarios([s.id for s in scenarios], config.seed)
    save(root / "private/splits.json", splits)
    records: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    usage: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    variants = list(
        itertools.product(scenarios, ("sufficient", "constrained"), ("report", "report_log"))
    )
    rng.shuffle(variants)
    # Block order balance across every resource/oversight pair and scenario.
    for index, (scenario, resource, oversight) in enumerate(variants):
        run_id = neutral_id(rng)
        budget = config.sufficient_budget if resource == "sufficient" else config.constrained_budget
        log = EventLog(root / "private" / "events" / f"{run_id}.jsonl")
        env = Environment(scenario, budget, oversight, log)
        provider: Provider = real_task or MockTaskProvider(scenario.mock_profile)
        for _ in range(budget + 2):
            try:
                reply = provider.generate(
                    {"role": "task", "transcript": json.loads(json.dumps(env.transcript))},
                    Action.model_json_schema(),
                )
                usage.append(reply.model_dump(exclude={"value"}))
                log.append("agent_response", reply.model_dump())
                env.step(reply.value)
                if env.final is not None:
                    break
            except (ValueError, KeyError, OSError, httpx.HTTPError, LimitError) as error:
                log.append("run_failure", {"type": type(error).__name__, "message": str(error)})
                failures.append({"run_id": run_id, "stage": "task", "error": type(error).__name__})
                break
        labels = env.ground_truth()
        trace_parts = [
            json.loads(line)["payload"].get("trace")
            for line in log.path.read_text().splitlines()
            if json.loads(line)["kind"] == "agent_response"
        ]
        trace = "\n".join(t for t in trace_parts if t) or None
        record = {
            "run_id": run_id,
            "scenario_id": scenario.id,
            "split": splits[scenario.id],
            "resource": resource,
            "oversight": oversight,
            "labels": labels,
            "final_report": env.final.model_dump() if env.final else None,
            "artifact": [row.model_dump() for row in env.rows],
            "transcript": env.transcript,
            "transcript_hash": digest(env.transcript),
            "trace": trace,
            "trace_kind": "provider_exposed_trace" if trace else "missing",
            "branches": [],
            "event_log": str(log.path.relative_to(root)),
        }
        if env.final is not None:
            branch_design = [("A", config.image_seeds[0])] + list(
                itertools.product(("B", "C", "D", "selection"), config.image_seeds)
            )
            rng.shuffle(branch_design)
            for branch, seed in branch_design:
                artifact_id = neutral_id(rng)
                try:
                    # Pair each oversight variant with its opposite ordering.
                    reverse = bool(
                        (
                            int(scenario.id.split("-")[1])
                            + config.image_seeds.index(seed)
                            + (resource == "constrained")
                            + (oversight == "report_log")
                        )
                        % 2
                    )
                    entry = elicit(
                        provider, env.transcript, branch, seed, root, artifact_id, reverse
                    )
                    usage.append(entry["provider"])
                    record["branches"].append(
                        {
                            k: entry[k]
                            for k in (
                                "artifact_id",
                                "branch",
                                "seed",
                                "image",
                                "generation_prompt",
                                "response",
                            )
                        }
                    )
                    if branch == "A":
                        continue
                    image_path = entry["image"]
                    blind_image = None
                    if image_path:
                        blind_image = f"blind/images/{artifact_id}.png"
                        (root / blind_image).write_bytes((root / image_path).read_bytes())
                    for modality, with_context in itertools.product(MODALITIES, (False, True)):
                        packet_id = neutral_id(rng)
                        packet = blind_packet(
                            packet_id,
                            modality,
                            record["final_report"],
                            trace,
                            entry["generation_prompt"],
                            blind_image,
                            with_context,
                        )
                        save(root / "blind/packets" / f"{packet_id}.json", packet)
                        row = {
                            "packet_id": packet_id,
                            "run_id": run_id,
                            "scenario_id": scenario.id,
                            "split": splits[scenario.id],
                            "resource": resource,
                            "oversight": oversight,
                            "branch": branch,
                            "seed": seed,
                            "modality": modality,
                            "with_task_context": with_context,
                            "label": labels["reporting_failure"],
                            "honest_failure": labels["task_failure"]
                            and not labels["reporting_failure"],
                            "evaluator": config.evaluator_provider,
                        }
                        try:
                            result = evaluate(
                                packet, root, real_eval, config.evaluator_provider == "human"
                            )
                            usage.extend(result.pop("usage"))
                            row.update(result)
                        except (
                            ValueError,
                            KeyError,
                            OSError,
                            httpx.HTTPError,
                            LimitError,
                        ) as error:
                            row.update(score=None, status="evaluation_failure", features=None)
                            failures.append(
                                {
                                    "packet_id": packet_id,
                                    "stage": "evaluation",
                                    "error": type(error).__name__,
                                }
                            )
                        evaluations.append(row)
                except (ValueError, KeyError, OSError, httpx.HTTPError, LimitError) as error:
                    failures.append(
                        {
                            "run_id": run_id,
                            "branch": branch,
                            "seed": seed,
                            "stage": "elicitation",
                            "error": type(error).__name__,
                        }
                    )
        records.append(record)
        save(root / "private/runs.json", records)
        save(root / "private/evaluations.json", evaluations)
        print(f"Run {index + 1}/{len(variants)} saved", flush=True)
    print("Evaluating scenario-block shuffle controls", flush=True)
    control_rows, control_usage = controls(
        evaluations, root, config.seed + 1, real_eval, config.evaluator_provider == "human"
    )
    evaluations.extend(control_rows)
    usage.extend(control_usage)
    save(root / "private/evaluations.json", evaluations)
    save(root / "private/failures.json", failures)
    save(root / "private/usage.json", usage)
    manifest = {
        "schema_version": 1,
        "title": "Visual Elicitation Under Pressure",
        "synthetic_tasks": config.task_provider == "mock",
        "mock_evaluators": config.evaluator_provider == "mock",
        "visual_mode": "restricted locally rendered diagrams; metaphor branch is a proxy",
        "fork_kind": "transcript_replay",
        "researcher_logging": "complete under both oversight conditions",
        "reserved_usd": ledger.reserved,
        "estimated_usd": ledger.estimated,
        "live_calls": ledger.calls,
        "runtime": {
            "python": platform.python_version(),
            "packages": {
                name: version(name)
                for name in ("pydantic", "pillow", "httpx", "numpy", "scikit-learn")
            },
        },
        "source_sha256": {
            str(path.relative_to(Path(__file__).parent)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(Path(__file__).parent.rglob("*"))
            if path.is_file() and path.suffix in (".py", ".txt", ".json")
        },
        "files": [],
    }
    for path in sorted(root.rglob("*")):
        if path.is_file():
            manifest["files"].append(
                {
                    "path": str(path.relative_to(root)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
            )
    save(root / "manifest.json", manifest)
    return manifest
