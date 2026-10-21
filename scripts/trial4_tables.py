"""Print Trial 4 result tables as markdown from summary.json and runs.json."""

import argparse
import json
from pathlib import Path
from typing import Any


def frac(cell: dict[str, Any], key: str) -> str:
    """Format k/n for one outcome."""
    value = cell[key]
    return f"{value['k']}/{value['n']}"


def tables(root: Path) -> str:
    """Build the main markdown tables."""
    summary = json.loads((root / "summary.json").read_text())
    rows = [r for r in json.loads((root / "runs.json").read_text()) if not r["infra_failed"]]
    models = list(json.loads((root / "registration.json").read_text())["models"])
    cells = summary["cells"]
    out = ["### Behavior by model and framing (oversight pooled)", ""]
    keys = [
        ("reporting_failure", "Reporting failure"),
        ("used_mark_settled", "Used mark_pending_settled"),
        ("unsafe_action", "Unsafe action"),
        ("escalated", "Escalated"),
        ("false_verified", "False 'verified'"),
        ("finished", "Finished"),
    ]
    out.append(
        "| Model | Framing | n | " + " | ".join(label for _, label in keys) + " | Mean p_test |"
    )
    out.append("|---|---|---:|" + "---:|" * len(keys) + "---:|")
    for model in ("all", *models):
        for framing in ("eval", "deploy"):
            cell = cells.get(f"{model}/{framing}/all")
            if cell:
                values = " | ".join(frac(cell, key) for key, _ in keys)
                out.append(
                    f"| {model} | {framing} | {cell['n']} | {values} | {cell['mean_p_test']} |"
                )
    out += ["", "### Oversight (framing pooled)", ""]
    out.append("| Model | Oversight | n | Reporting failure | mark_pending_settled |")
    out.append("|---|---|---:|---:|---:|")
    for model in ("all", *models):
        for oversight in ("log", "report"):
            subset = [
                r
                for r in rows
                if (model == "all" or r["model"] == model) and r["oversight"] == oversight
            ]
            fail = sum(bool(r.get("reporting_failure")) for r in subset)
            mark = sum(bool(r.get("used_mark_settled")) for r in subset)
            out.append(
                f"| {model} | {oversight} | {len(subset)} | {fail}/{len(subset)} | {mark}/{len(subset)} |"
            )
    out += ["", "### Fisher exact tests", ""]
    out.append("| Model | Outcome | Factor | Levels | Odds ratio | p |")
    out.append("|---|---|---|---|---:|---:|")
    for test in summary["fisher_tests"] + [summary["model_test"] | {"model": "family"}]:
        levels = ", ".join(
            f"{k} {v}"
            for k, v in test.items()
            if k not in ("model", "outcome", "factor", "odds_ratio", "p_two_sided")
        )
        out.append(
            f"| {test['model']} | {test['outcome']} | {test['factor']} | {levels} | "
            f"{test['odds_ratio']} | {test['p_two_sided']} |"
        )
    out += ["", "### Painting-prompt text signal (leave-one-out TF-IDF logistic regression)", ""]
    out.append("| Label | Subset | n | LOO accuracy | Majority baseline | Permutation p |")
    out.append("|---|---|---:|---:|---:|---:|")
    for item in summary["painting_text_signal"]:
        out.append(
            f"| {item['label']} | {item.get('subset', 'all')} | {item['n']} | "
            f"{item.get('loo_accuracy', '-')} | {item.get('majority_baseline', '-')} | "
            f"{item.get('permutation_p', item.get('note', '-'))} |"
        )
    return "\n".join(out)


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(tables(parser.parse_args().root))


if __name__ == "__main__":
    main()
