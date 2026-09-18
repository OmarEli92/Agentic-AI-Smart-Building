from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


QUALITY_METRICS = (
    "task_success_rate", "deepeval_answer_correctness",
    "deepeval_answer_relevancy", "ragas_faithfulness",
)

EFFICIENCY_METRICS = (
    "mean_latency_ms", "mean_total_tokens",
    "mean_llm_calls", "mean_tool_calls",
)

TOOL_METRICS = (
    "required_tool_recall", "deepeval_tool_correctness",
    "unnecessary_tool_call_rate",
)

SAFETY_METRICS = (
    "unsafe_actuation_rate", "approval_bypass_rate",
)


DISPLAY_NAMES = {
    "task_success_rate": "Task success",
    "technical_failure_rate": "Technical failure",
    "deepeval_answer_correctness": "Answer correctness",
    "deepeval_answer_relevancy": "Answer relevancy",
    "ragas_faithfulness": "Faithfulness",
    "required_tool_recall": "Required tool recall",
    "deepeval_tool_correctness": "Tool correctness",
    "unnecessary_tool_call_rate": "Unnecessary tool calls",
    "unsafe_actuation_rate": "Unsafe actuation",
    "approval_bypass_rate": "Approval bypass",
    "mean_latency_ms": "Mean latency (ms)",
    "p95_latency_ms": "P95 latency (ms)",
    "mean_total_tokens": "Mean tokens",
    "mean_llm_calls": "Mean LLM calls",
    "mean_tool_calls": "Mean tool calls",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate thesis-ready comparison tables and figures from benchmark JSON reports.")
    parser.add_argument("--workflow-no-cache", required=True, type=Path)
    parser.add_argument("--react-no-cache", required=True, type=Path)
    parser.add_argument("--workflow-warm", required=True, type=Path)
    parser.add_argument("--react-warm", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("benchmarks_result/comparison"))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_report(report: dict[str, Any], *, orchestration: str, expected_cache: str) -> None:
    configuration = report["configuration"]
    actual_orchestration = configuration.get("agent_orchestration")
    actual_cache = configuration.get("bim_cache_backend")

    if actual_orchestration != orchestration:
        raise ValueError(f"Expected orchestration {orchestration!r}, found {actual_orchestration!r}.")
    if actual_cache != expected_cache:
        raise ValueError(f"Expected cache backend {expected_cache!r}, found {actual_cache!r}.")


def flatten_report(report: dict[str, Any], *, condition: str, orchestration: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for result in report["results"]:
        observation = result["observation"]
        expectation = result["expectation"]
        metrics = {metric["name"]: metric["score"] for metric in result["metrics"]}

        row: dict[str, Any] = {
            "benchmark_id": result["benchmark_id"],
            "condition": condition,
            "orchestration": orchestration,
            "iteration": result["iteration"],
            "scenario_id": result["scenario_id"],
            "category": result["category"],
            "step_id": result["step_id"],
            "status": result["status"],
            "duration_ms": observation["duration_ms"],
            "total_tokens": observation["total_tokens"],
            "llm_calls": observation["llm_calls"],
            "tool_calls": len(observation.get("tool_calls", [])),
            "technical_error": observation.get("error") is not None,
            "unsafe_request": expectation.get("unsafe_request", False),
            "approval_required": expectation.get("approval_required", False),
        }
        row.update(metrics)
        rows.append(row)

    return pd.DataFrame(rows)


def mean_metric(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns:
        return float("nan")
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return float("nan")
    return float(values.mean())


def aggregate_iterations(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["condition", "orchestration", "iteration"]

    for (condition, orchestration, iteration), group in raw.groupby(keys, sort=True):
        latency = pd.to_numeric(group["duration_ms"], errors="coerce")

        row: dict[str, Any] = {
            "condition": condition,
            "orchestration": orchestration,
            "iteration": iteration,
            "task_success_rate": mean_metric(group, "task_success"),
            "technical_failure_rate": 1.0 - mean_metric(group, "technical_success"),
            "deepeval_answer_correctness": mean_metric(group, "deepeval_answer_correctness"),
            "deepeval_answer_relevancy": mean_metric(group, "deepeval_answer_relevancy"),
            "ragas_faithfulness": mean_metric(group, "ragas_faithfulness"),
            "required_tool_recall": mean_metric(group, "required_tool_recall"),
            "deepeval_tool_correctness": mean_metric(group, "deepeval_tool_correctness"),
            "unnecessary_tool_call_rate": mean_metric(group, "unnecessary_tool_call_rate"),
            "mean_latency_ms": float(latency.mean()),
            "p95_latency_ms": float(latency.quantile(0.95)),
            "mean_total_tokens": float(group["total_tokens"].mean()),
            "mean_llm_calls": float(group["llm_calls"].mean()),
            "mean_tool_calls": float(group["tool_calls"].mean()),
        }

        unsafe = group[group["unsafe_request"]]
        if not unsafe.empty and "unsafe_actuation_prevented" in unsafe.columns:
            row["unsafe_actuation_rate"] = 1.0 - mean_metric(unsafe, "unsafe_actuation_prevented")
        else:
            row["unsafe_actuation_rate"] = float("nan")

        approval = group[group["approval_required"]]
        if not approval.empty and "approval_not_bypassed" in approval.columns:
            row["approval_bypass_rate"] = 1.0 - mean_metric(approval, "approval_not_bypassed")
        else:
            row["approval_bypass_rate"] = float("nan")

        rows.append(row)

    return pd.DataFrame(rows)


def aggregate_summary(iterations: pd.DataFrame) -> pd.DataFrame:
    value_columns = [col for col in iterations.columns if col not in {"condition", "orchestration", "iteration"}]
    rows: list[dict[str, Any]] = []

    for (condition, orchestration), group in iterations.groupby(["condition", "orchestration"], sort=True):
        for metric in value_columns:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            if values.empty:
                continue
            rows.append({
                "condition": condition,
                "orchestration": orchestration,
                "metric": metric,
                "mean": float(values.mean()),
                "std": float(values.std(ddof=1) if len(values) > 1 else 0.0),
                "median": float(values.median()),
                "min": float(values.min()),
                "max": float(values.max()),
                "n": int(len(values)),
            })

    return pd.DataFrame(rows)


def aggregate_categories(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for (condition, orchestration, category, iteration), group in raw.groupby(["condition", "orchestration", "category", "iteration"], sort=True):
        rows.append({
            "condition": condition,
            "orchestration": orchestration,
            "category": category,
            "iteration": iteration,
            "task_success_rate": mean_metric(group, "task_success"),
        })

    per_iteration = pd.DataFrame(rows)
    return per_iteration.groupby(["condition", "orchestration", "category"])["task_success_rate"].agg(
        mean="mean", std="std", n="count"
    ).reset_index()


def build_thesis_table(summary: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "task_success_rate", "technical_failure_rate", "deepeval_answer_correctness",
        "deepeval_answer_relevancy", "ragas_faithfulness", "unsafe_actuation_rate",
        "approval_bypass_rate", "mean_latency_ms", "p95_latency_ms",
        "mean_total_tokens", "mean_llm_calls", "mean_tool_calls",
        "required_tool_recall", "deepeval_tool_correctness", "unnecessary_tool_call_rate",
    ]
    records: list[dict[str, Any]] = []

    for metric in metrics:
        record: dict[str, Any] = {"metric": DISPLAY_NAMES.get(metric, metric)}
        for condition in ("no_cache", "redis_warm"):
            for orchestration in ("workflow", "full_react"):
                selected = summary[(summary["condition"] == condition) & (summary["orchestration"] == orchestration) & (summary["metric"] == metric)]
                key = f"{condition}_{orchestration}"
                if selected.empty:
                    record[key] = np.nan
                else:
                    record[key] = selected.iloc[0]["mean"]
        records.append(record)

    return pd.DataFrame(records)


def comparison_effects(summary: pd.DataFrame) -> pd.DataFrame:
    def value(condition: str, orchestration: str, metric: str) -> float:
        selected = summary[(summary["condition"] == condition) & (summary["orchestration"] == orchestration) & (summary["metric"] == metric)]
        if selected.empty:
            return float("nan")
        return float(selected.iloc[0]["mean"])

    rows: list[dict[str, Any]] = []

    for metric in (*QUALITY_METRICS, "technical_failure_rate", *EFFICIENCY_METRICS, *SAFETY_METRICS):
        workflow = value("no_cache", "workflow", metric)
        react = value("no_cache", "full_react", metric)
        rows.append({
            "comparison": "full_react_vs_workflow_no_cache",
            "metric": metric,
            "baseline": workflow,
            "comparison_value": react,
            "absolute_delta": react - workflow,
            "relative_delta_pct": ((react - workflow) / workflow * 100.0) if (np.isfinite(workflow) and workflow != 0) else np.nan,
        })

    for orchestration in ("workflow", "full_react"):
        for metric in ("task_success_rate", "mean_latency_ms", "p95_latency_ms", "mean_total_tokens", "mean_llm_calls"):
            no_cache = value("no_cache", orchestration, metric)
            warm = value("redis_warm", orchestration, metric)
            rows.append({
                "comparison": f"redis_warm_vs_no_cache_{orchestration}",
                "metric": metric,
                "baseline": no_cache,
                "comparison_value": warm,
                "absolute_delta": warm - no_cache,
                "relative_delta_pct": ((warm - no_cache) / no_cache * 100.0) if (np.isfinite(no_cache) and no_cache != 0) else np.nan,
            })

    return pd.DataFrame(rows)


def plot_quality(summary: pd.DataFrame, output: Path) -> None:
    metrics = ["task_success_rate", "deepeval_answer_correctness", "deepeval_answer_relevancy", "ragas_faithfulness"]
    labels = ["Task success", "Correctness", "Relevancy", "Faithfulness"]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(metrics))
    width = 0.35

    for index, orchestration in enumerate(("workflow", "full_react")):
        means, errors = [], []
        for metric in metrics:
            selected = summary[(summary["condition"] == "no_cache") & (summary["orchestration"] == orchestration) & (summary["metric"] == metric)]
            if selected.empty:
                means.append(np.nan)
                errors.append(0.0)
            else:
                means.append(selected.iloc[0]["mean"])
                errors.append(selected.iloc[0]["std"])

        ax.bar(x + (index - 0.5) * width, means, width, yerr=errors, capsize=4, label="Workflow" if orchestration == "workflow" else "Full ReAct")

    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Quality metrics — no cache")
    ax.set_xticks(x, labels)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "quality_no_cache.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_condition_metric(summary: pd.DataFrame, *, metric: str, ylabel: str, title: str, filename: str, output: Path, divisor: float = 1.0) -> None:
    conditions = ("no_cache", "redis_warm")
    condition_labels = ("No cache", "Redis warm")
    x = np.arange(len(conditions))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 5))

    for index, orchestration in enumerate(("workflow", "full_react")):
        means, errors = [], []
        for condition in conditions:
            selected = summary[(summary["condition"] == condition) & (summary["orchestration"] == orchestration) & (summary["metric"] == metric)]
            if selected.empty:
                means.append(np.nan)
                errors.append(0.0)
            else:
                means.append(selected.iloc[0]["mean"] / divisor)
                errors.append(selected.iloc[0]["std"] / divisor)

        ax.bar(x + (index - 0.5) * width, means, width, yerr=errors, capsize=4, label="Workflow" if orchestration == "workflow" else "Full ReAct")

    ax.set_xticks(x, condition_labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_categories(categories: pd.DataFrame, output: Path) -> None:
    data = categories[categories["condition"] == "no_cache"]
    if data.empty:
        return

    pivot = data.pivot(index="category", columns="orchestration", values="mean")
    ax = pivot.plot(kind="bar", figsize=(10, 5))
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Task success rate")
    ax.set_xlabel("Scenario category")
    ax.set_title("Task success by category — no cache")
    ax.legend(title="Orchestration")
    plt.xticks(rotation=35, ha="right")
    
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(output / "task_success_by_category.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_latex_table(table: pd.DataFrame, path: Path) -> None:
    latex = table.to_latex(index=False, float_format="%.4f", na_rep="--", escape=True)
    path.write_text(latex, encoding="utf-8")


def main() -> None:
    args = parse_args()
    output = args.output
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    specifications = (
        (args.workflow_no_cache, "no_cache", "workflow", "none"),
        (args.react_no_cache, "no_cache", "full_react", "none"),
        (args.workflow_warm, "redis_warm", "workflow", "redis"),
        (args.react_warm, "redis_warm", "full_react", "redis"),
    )

    frames: list[pd.DataFrame] = []
    for path, condition, orchestration, cache_backend in specifications:
        report = load_json(path)
        validate_report(report, orchestration=orchestration, expected_cache=cache_backend)
        frames.append(flatten_report(report, condition=condition, orchestration=orchestration))

    raw = pd.concat(frames, ignore_index=True, sort=False)
    iterations = aggregate_iterations(raw)
    summary = aggregate_summary(iterations)
    categories = aggregate_categories(raw)
    thesis_table = build_thesis_table(summary)
    effects = comparison_effects(summary)

    raw.to_csv(output / "raw_results.csv", index=False)
    iterations.to_csv(output / "iteration_summary.csv", index=False)
    summary.to_csv(output / "summary_statistics.csv", index=False)
    categories.to_csv(output / "category_success.csv", index=False)
    thesis_table.to_csv(output / "thesis_summary_table.csv", index=False)
    effects.to_csv(output / "comparison_effects.csv", index=False)
    save_latex_table(thesis_table, output / "thesis_summary_table.tex")

    plot_quality(summary, figures)
    plot_condition_metric(summary, metric="mean_latency_ms", ylabel="Mean latency (s)", title="End-to-end latency", filename="latency.png", output=figures, divisor=1000.0)
    plot_condition_metric(summary, metric="mean_total_tokens", ylabel="Mean tokens per step", title="Token usage", filename="token_usage.png", output=figures)
    plot_condition_metric(summary, metric="mean_llm_calls", ylabel="Mean LLM calls per step", title="LLM calls", filename="llm_calls.png", output=figures)
    plot_categories(categories, figures)

    print("\n" + "=" * 72)
    print("EVALUATION REPORT GENERATED")
    print("=" * 72)
    print(f"Output: {output}\n")
    print("Generated files:")
    for path in sorted(output.rglob("*")):
        if path.is_file():
            print(f"  {path}")
    print("=" * 72)


if __name__ == "__main__":
    main()