#!/usr/bin/env python3
"""Build the SGI-Index from local benchmark CSV files.

The script intentionally reads every CSV in test_results instead of relying on a
hard-coded model list. Benchmark-specific rules are limited to score-column
selection and fallback handling.
"""

from __future__ import annotations

import argparse
import json
import math
import numbers
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_WEIGHTS: dict[str, float] = {
    "AstroVisBench": 1,
    "ChemBench": 1,
    "CMPhysBench": 1,
    "EarthSE": 1,
    "ResearchBench": 1,
    "SciCode": 1,
    "SFE": 1,
    "TRQA": 1,
}

KNOWN_BENCHMARKS = tuple(DEFAULT_WEIGHTS.keys())

AVG_SCORE_CANDIDATES = (
    "Avg Score",
    "Avg Score(acc)",
    "Avg Score（acc）",
    "Average Score",
    "Average Score(acc)",
    "avg_score",
    "avg score",
)

BENCHMARK_FALLBACKS: dict[str, list[str]] = {
    "AstroVisBench": [
        "process_success_rate",
        "visualize_success_rate",
        "process_average_variable_inspection_score",
        "visualize_no_error_rate",
    ],
    "ResearchBench": [
        "generate_avg_score",
        "retrival_hit@3",
    ],
}

BENCHMARK_PRIMARY_COLUMNS: dict[str, list[str]] = {
    "SciCode": [
        "Main Problem Resolve Rate",
    ],
}

NON_SCORE_COLUMNS = {
    "parentitems",
    "parentitem",
    "父记录",
    "检查",
    "check",
    "notes",
    "note",
    "comment",
    "comments",
}

EXTENSION_FIELDS = {
    "compute": None,
    "cost": None,
    "token_usage": None,
}

RAW_MODEL_ALIASES = {
    "Gemini-3-pro": "Gemini-3-Pro",
    "Gemini-3-Pro": "Gemini-3-Pro",
    "Grmini-3-Pro": "Gemini-3-Pro",
    "GPT-5-1": "GPT-5.1",
    "GPT-5.1": "GPT-5.1",
}


@dataclass
class BenchmarkResult:
    name: str
    source_file: str
    scores: pd.DataFrame
    details: dict[str, Any]


def clean_text(value: Any) -> str:
    """Normalize BOM, full-width characters, and surrounding whitespace."""

    text = "" if value is None else str(value)
    text = text.replace("\ufeff", "")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_key(value: Any) -> str:
    """Return a comparison key that is tolerant to spaces and punctuation."""

    text = clean_text(value).lower()
    return re.sub(r"[\s_\-()（）]+", "", text)


def clean_columns(columns: list[Any]) -> list[str]:
    """Clean column names while preserving uniqueness after normalization."""

    seen: dict[str, int] = {}
    cleaned: list[str] = []
    for column in columns:
        base = clean_text(column)
        suffix = seen.get(base, 0)
        seen[base] = suffix + 1
        cleaned.append(base if suffix == 0 else f"{base}.{suffix}")
    return cleaned


def canonical_model_name(model: Any) -> str:
    """Apply explicit source-data alias fixes without inventing new aliases."""

    cleaned = clean_text(model)
    cleaned_key = compact_key(cleaned)
    for raw_alias, canonical in RAW_MODEL_ALIASES.items():
        if cleaned_key == compact_key(raw_alias):
            return canonical
    return cleaned


def infer_benchmark_name(path: Path) -> str:
    name_key = compact_key(path.stem)
    for benchmark in KNOWN_BENCHMARKS:
        if compact_key(benchmark) in name_key:
            return benchmark

    parts = [clean_text(part) for part in path.stem.split("_") if clean_text(part)]
    if len(parts) >= 2:
        return parts[1]
    return clean_text(path.stem)


def read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = clean_columns(list(df.columns))
    if df.empty:
        return df

    model_column = df.columns[0]
    df[model_column] = df[model_column].map(clean_text)
    df = df[df[model_column] != ""].copy()
    return df


def find_column(df: pd.DataFrame, candidates: list[str] | tuple[str, ...]) -> str | None:
    candidate_keys = {compact_key(candidate) for candidate in candidates}
    for column in df.columns:
        if compact_key(column) in candidate_keys:
            return column
    return None


def find_avg_score_column(df: pd.DataFrame) -> str | None:
    direct = find_column(df, AVG_SCORE_CANDIDATES)
    if direct:
        return direct

    for column in df.columns[1:]:
        key = compact_key(column)
        if key in {"avgscore", "averagescore", "avgscoreacc", "averagescoreacc"}:
            return column
    return None


def to_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    text = series.astype(str).map(clean_text)
    text = text.str.replace("%", "", regex=False)
    text = text.str.replace(",", "", regex=False)
    text = text.replace({"": None, "nan": None, "None": None})
    return pd.to_numeric(text, errors="coerce")


def is_non_score_column(column: str) -> bool:
    return compact_key(column) in NON_SCORE_COLUMNS


def numeric_score_columns(df: pd.DataFrame, model_column: str) -> list[str]:
    columns: list[str] = []
    for column in df.columns:
        if column == model_column or is_non_score_column(column):
            continue
        numeric = to_numeric(df[column])
        if numeric.notna().any():
            columns.append(column)
    return columns


def row_mean(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    numeric = pd.concat([to_numeric(df[column]) for column in columns], axis=1)
    numeric.columns = columns
    return numeric.mean(axis=1, skipna=True)


def choose_score_series(
    df: pd.DataFrame,
    benchmark: str,
    model_column: str,
) -> tuple[pd.Series, dict[str, Any]]:
    avg_column = find_avg_score_column(df)
    avg_series = to_numeric(df[avg_column]) if avg_column else None
    avg_has_values = bool(avg_series is not None and avg_series.notna().any())

    info: dict[str, Any] = {
        "average_score_column": avg_column,
        "fallback_used": False,
        "selected_columns": [],
        "selection_rule": "",
        "ignored_columns": [
            column for column in df.columns if column != model_column and is_non_score_column(column)
        ],
        "auxiliary_numeric_columns": [],
    }

    primary_candidates = BENCHMARK_PRIMARY_COLUMNS.get(benchmark, [])
    primary_column = find_column(df, primary_candidates) if primary_candidates else None
    if primary_column:
        info["selected_columns"] = [primary_column]
        info["selection_rule"] = f"主指标 `{primary_column}`"
        return to_numeric(df[primary_column]), info

    if avg_column and avg_has_values:
        info["selected_columns"] = [avg_column]
        info["selection_rule"] = f"平均分列 `{avg_column}`"
        return avg_series, info

    fallback_candidates = BENCHMARK_FALLBACKS.get(benchmark, [])
    fallback_columns = [
        column
        for column in (find_column(df, [candidate]) for candidate in fallback_candidates)
        if column is not None
    ]
    if fallback_columns:
        info["fallback_used"] = True
        info["selected_columns"] = fallback_columns
        info["selection_rule"] = "后备子指标均值"
        return row_mean(df, fallback_columns), info

    numeric_columns = numeric_score_columns(df, model_column)
    if avg_column in numeric_columns:
        numeric_columns.remove(avg_column)

    if not numeric_columns:
        info["fallback_used"] = True
        info["selection_rule"] = "未找到有效数值分数字段"
        return pd.Series([math.nan] * len(df), index=df.index, dtype="float64"), info

    first_numeric = numeric_columns[0]
    first_key = compact_key(first_numeric)
    if any(token in first_key for token in ("main", "score", "acc", "accuracy", "rate", "resolve")):
        info["fallback_used"] = True
        info["selected_columns"] = [first_numeric]
        info["selection_rule"] = f"第一列代表性数值指标 `{first_numeric}`"
        return to_numeric(df[first_numeric]), info

    info["fallback_used"] = True
    info["selected_columns"] = numeric_columns
    info["selection_rule"] = "合理数值子指标均值"
    return row_mean(df, numeric_columns), info


def normalize_score(series: pd.Series) -> tuple[pd.Series, dict[str, Any]]:
    valid = series.dropna()
    raw_max = float(valid.max()) if not valid.empty else None
    raw_min = float(valid.min()) if not valid.empty else None
    ratio_scaled = bool(raw_max is not None and raw_max <= 1.5)
    normalized = series * 100 if ratio_scaled else series
    return normalized, {
        "raw_min": raw_min,
        "raw_max": raw_max,
        "scale_factor": 100 if ratio_scaled else 1,
        "normalization_rule": "max <= 1.5，按 0-1 比例分乘以 100" if ratio_scaled else "按 0-100 分处理",
        "normalized_min": float(normalized.dropna().min()) if normalized.notna().any() else None,
        "normalized_max": float(normalized.dropna().max()) if normalized.notna().any() else None,
    }


def build_benchmark_result(path: Path) -> BenchmarkResult:
    df = read_csv(path)
    benchmark = infer_benchmark_name(path)
    if df.empty:
        empty_scores = pd.DataFrame(columns=["model", benchmark])
        return BenchmarkResult(
            name=benchmark,
            source_file=path.name,
            scores=empty_scores,
            details={
                "benchmark": benchmark,
                "source_file": path.name,
                "rows": 0,
                "valid_scores": 0,
                "error": "CSV has no rows",
            },
        )

    model_column = df.columns[0]
    score_series, selection_info = choose_score_series(df, benchmark, model_column)
    normalized, normalization_info = normalize_score(score_series)

    result = pd.DataFrame(
        {
            "model": df[model_column].map(canonical_model_name),
            "source_model": df[model_column].map(clean_text),
            benchmark: normalized,
        }
    )
    duplicate_models = sorted(result.loc[result["model"].duplicated(), "model"].unique().tolist())
    model_aliases = {
        model: sorted(set(aliases))
        for model, aliases in result.groupby("model")["source_model"].apply(list).to_dict().items()
    }
    if duplicate_models:
        result = result.groupby("model", as_index=False)[benchmark].mean()
    else:
        result = result[["model", benchmark]]

    selected_columns = selection_info.get("selected_columns", [])
    auxiliary_columns = [
        column
        for column in numeric_score_columns(df, model_column)
        if column not in selected_columns
    ]
    selection_info["auxiliary_numeric_columns"] = auxiliary_columns

    details = {
        "benchmark": benchmark,
        "source_file": path.name,
        "model_column": model_column,
        "rows": int(len(df)),
        "valid_scores": int(result[benchmark].notna().sum()),
        "duplicate_models_averaged": duplicate_models,
        "model_aliases": {
            model: aliases
            for model, aliases in model_aliases.items()
            if aliases != [model]
        },
        "weight": DEFAULT_WEIGHTS.get(benchmark, 1),
        **selection_info,
        **normalization_info,
    }
    return BenchmarkResult(benchmark, path.name, result, details)


def weighted_average(row: pd.Series, benchmarks: list[str], weights: dict[str, float]) -> float:
    numerator = 0.0
    denominator = 0.0
    for benchmark in benchmarks:
        value = row.get(benchmark)
        weight = float(weights.get(benchmark, 1))
        if pd.notna(value) and weight > 0:
            numerator += float(value) * weight
            denominator += weight
    return numerator / denominator if denominator else math.nan


def round_or_none(value: Any, digits: int = 2) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        return round(float(value), digits)
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        return round_or_none(value)
    return value


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        text = str(value)
        return text.replace("|", "\\|")

    lines = [
        "| " + " | ".join(cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    return "\n".join(lines)


def format_field_list(fields: list[str]) -> str:
    if not fields:
        return "-"
    return ", ".join(f"`{field}`" for field in fields)


def build_report(
    leaderboard: pd.DataFrame,
    benchmark_details: list[dict[str, Any]],
    csv_files: list[str],
    benchmark_order: list[str],
    output_paths: dict[str, Path],
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    top = leaderboard.head(15)
    top_rows = [
        [
            int(row["rank"]),
            row["model"],
            row.get("model_aliases", ""),
            f"{row['SGI-Index']:.2f}" if pd.notna(row["SGI-Index"]) else "",
            int(row["num_benchmarks_available"]),
        ]
        for _, row in top.iterrows()
    ]

    benchmark_rows = []
    for detail in benchmark_details:
        benchmark_rows.append(
            [
                detail["benchmark"],
                detail["source_file"],
                format_field_list(detail.get("selected_columns", [])),
                "是" if detail.get("fallback_used") else "否",
                detail.get("normalization_rule", ""),
                f"{detail.get('valid_scores', 0)}/{detail.get('rows', 0)}",
                detail.get("weight", 1),
            ]
        )

    missing_rows = []
    missing_df = leaderboard[leaderboard["missing_benchmarks"].astype(str) != ""]
    for _, row in missing_df.iterrows():
        missing_rows.append(
            [
                row["model"],
                int(row["num_benchmarks_available"]),
                row["missing_benchmarks"],
            ]
        )

    missing_section = (
        markdown_table(
            ["Model", "Available benchmarks", "Missing benchmarks"],
            missing_rows,
        )
        if missing_rows
        else "所有出现在 CSV 并进入聚合的模型都没有缺失 benchmark 分数。"
    )

    alias_rows = [
        [row["model"], row["model_aliases"]]
        for _, row in leaderboard[leaderboard["model_aliases"].astype(str) != ""].iterrows()
    ]
    alias_section = (
        markdown_table(["Canonical model", "Merged source names"], alias_rows)
        if alias_rows
        else "未发现需要合并的显式模型别名。"
    )

    score_selection_lines = []
    for detail in benchmark_details:
        fields = format_field_list(detail.get("selected_columns", []))
        auxiliary = format_field_list(detail.get("auxiliary_numeric_columns", []))
        score_selection_lines.append(
            f"- **{detail['benchmark']}**：来源 `{detail['source_file']}`；"
            f"SGI 主分数字段：{fields}；选择规则：{detail.get('selection_rule', '')}；"
            f"辅助数值字段：{auxiliary}。"
        )

    files_list = "\n".join(f"- `{file_name}`" for file_name in csv_files)
    benchmark_order_text = ", ".join(f"`{benchmark}`" for benchmark in benchmark_order)

    report = f"""# SGI-Index

Generated at: {generated_at}

## SGI-Index 简介

SGI-Index 是 SGIWorld 的 score-only 综合模型能力指数。它参考 Artificial Analysis Intelligence Index 的 composite benchmark 思路，把多个能力维度的评测聚合成一个 0-100 分的综合分，而不是用单一 benchmark 代表整体能力。

当前版本不估算 compute、token usage 或 cost，因为本地 CSV 中没有这些字段。JSON 输出保留了扩展字段，便于后续加入 score-vs-compute、score-vs-cost 或 score-vs-token 视图。

## 数据来源

输入目录：`test_results`

读取的 CSV 文件：

{files_list}

宽表中的 benchmark 顺序：{benchmark_order_text}

## 评分字段选择规则

- 每个 CSV 的第一列作为模型名称列，并清理 UTF-8 BOM、全角字符和前后空白。
- `Avg Score`、`Avg Score（acc）` 等平均分列存在且包含有效值时优先使用。
- 平均分列存在但为空时，不直接使用空值；脚本会按 benchmark 专属规则选择代表性字段或合理数值子指标。
- `Parent items`、`父记录`、`检查` 等明显非分数字段会被忽略。
- 模型名称默认不做人工合并；仅合并显式配置的源数据别名，避免把不同模型误合并。

{chr(10).join(score_selection_lines)}

## 模型别名合并规则

以下源数据名称被合并到统一模型名。合并发生在每个 benchmark 读入后；如果同一个 benchmark 内多个源名称映射到同一模型，其分数取均值。

{alias_section}

## 归一化规则

所有进入 SGI-Index 聚合的 benchmark 分数都会统一到 0-100。对每个 benchmark，如果选中分数的有效最大值 `<= 1.5`，则视为 0-1 比例分并乘以 100；否则视为已经是 0-100 分。

## 权重规则

默认 SGI-Index 使用等权重：

```json
{json.dumps(DEFAULT_WEIGHTS, ensure_ascii=False, indent=2)}
```

对每个模型，SGI-Index 是其可用 benchmark 分数的加权平均值。缺失 benchmark 不填 0，并在输出中记录 `num_benchmarks_available` 和 `missing_benchmarks`。

## Top Models 排行榜

{markdown_table(["Rank", "Model", "Aliases merged", "SGI-Index", "Available Benchmarks"], top_rows)}

完整排行榜：`{output_paths['csv'].as_posix()}`

## Benchmark 说明和使用字段

{markdown_table(["Benchmark", "Source file", "Selected field(s)", "Fallback", "Normalization", "Valid/Rows", "Weight"], benchmark_rows)}

## 缺失数据说明

{missing_section}

## 方法局限性

- SGI-Index 当前只衡量分数，不包含 latency、cost、token usage、参数量或 compute-normalized efficiency。
- 等权重是透明默认设置，并不代表所有 benchmark 在科学意义上必然同等重要。
- 脚本只合并显式配置的模型别名，不推断未知别名。这可以避免误合并，但未配置的源数据写法差异仍会拆成多行。
- 按“可用 benchmark 平均”排名会让只覆盖少数高分 benchmark 的模型排位偏高；使用排行榜时应同时查看 `num_benchmarks_available`。
- 综合平均可能掩盖模型在单项 benchmark 上的强弱差异，应结合 CSV 和 JSON 中的单项分数一起解读。
"""
    return report


def build_index(input_dir: Path, output_dir: Path) -> dict[str, Path]:
    csv_paths = sorted(input_dir.glob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    benchmark_results = [build_benchmark_result(path) for path in csv_paths]
    seen_names: set[str] = set()
    for result in benchmark_results:
        if result.name in seen_names:
            raise ValueError(f"Duplicate benchmark name inferred: {result.name}")
        seen_names.add(result.name)

    result_by_name = {result.name: result for result in benchmark_results}
    benchmark_order = [
        benchmark for benchmark in DEFAULT_WEIGHTS if benchmark in result_by_name
    ] + [
        result.name for result in benchmark_results if result.name not in DEFAULT_WEIGHTS
    ]
    benchmark_results = [result_by_name[benchmark] for benchmark in benchmark_order]
    weights = {benchmark: DEFAULT_WEIGHTS.get(benchmark, 1) for benchmark in benchmark_order}
    benchmark_details = [result.details for result in benchmark_results]
    model_aliases: dict[str, set[str]] = {}
    for detail in benchmark_details:
        for model, aliases in detail.get("model_aliases", {}).items():
            model_aliases.setdefault(model, {model}).update(aliases)

    merged: pd.DataFrame | None = None
    for result in benchmark_results:
        merged = result.scores if merged is None else merged.merge(result.scores, on="model", how="outer")

    if merged is None:
        raise RuntimeError("No benchmark data was loaded")

    merged["SGI-Index"] = merged.apply(
        lambda row: weighted_average(row, benchmark_order, weights),
        axis=1,
    )
    merged["num_benchmarks_available"] = merged[benchmark_order].notna().sum(axis=1).astype(int)
    merged["missing_benchmarks"] = merged[benchmark_order].isna().apply(
        lambda row: ", ".join(row.index[row].tolist()),
        axis=1,
    )
    merged["model_aliases"] = merged["model"].map(
        lambda model: ", ".join(sorted(model_aliases.get(model, {model}) - {model}))
    )

    merged = merged.sort_values(["SGI-Index", "model"], ascending=[False, True], na_position="last")
    merged["rank"] = merged["SGI-Index"].rank(method="min", ascending=False).astype(int)

    leaderboard = merged[[
        "rank",
        "model",
        "model_aliases",
        "SGI-Index",
        *benchmark_order,
        "num_benchmarks_available",
        "missing_benchmarks",
    ]].copy()

    for field, default in EXTENSION_FIELDS.items():
        leaderboard[field] = default

    csv_output = output_dir / "sgi_index.csv"
    json_output = output_dir / "sgi_index.json"
    frontend_output = output_dir / "sgi_index_frontend.json"
    md_output = output_dir / "SGI-Index.md"

    display_leaderboard = leaderboard.copy()
    for column in ["SGI-Index", *benchmark_order]:
        display_leaderboard[column] = display_leaderboard[column].round(2)
    display_leaderboard.to_csv(csv_output, index=False, encoding="utf-8-sig")

    records = []
    for _, row in display_leaderboard.iterrows():
        record = row.to_dict()
        aliases = sorted(model_aliases.get(record["model"], {record["model"]}) - {record["model"]})
        record["model_aliases"] = aliases
        record["missing_benchmarks"] = [
            item.strip()
            for item in str(record["missing_benchmarks"]).split(",")
            if item.strip()
        ]
        record["benchmark_scores"] = {
            benchmark: round_or_none(record.get(benchmark))
            for benchmark in benchmark_order
        }
        records.append(json_safe(record))

    payload = {
        "metadata": {
            "name": "SGI-Index",
            "description": "Score-only composite benchmark for SGIWorld model evaluation.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "methodology_reference": "Inspired by Artificial Analysis Intelligence Index composite benchmark methodology.",
            "score_scale": "0-100",
            "aggregation": "weighted average over available benchmark scores; missing scores are not filled with zero",
            "efficiency_metrics_available": False,
            "extension_fields": EXTENSION_FIELDS,
            "model_aliases": {
                canonical: sorted(aliases)
                for canonical, aliases in model_aliases.items()
                if aliases - {canonical}
            },
        },
        "weights": weights,
        "benchmarks": json_safe(benchmark_details),
        "leaderboard": records,
    }
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    frontend_payload = {
        "name": "SGI-Index",
        "score_scale": "0-100",
        "weights": weights,
        "benchmarks": [
            {
                "name": detail["benchmark"],
                "source_file": detail["source_file"],
                "selected_fields": detail.get("selected_columns", []),
                "normalization": detail.get("normalization_rule"),
            }
            for detail in benchmark_details
        ],
        "leaderboard": [
            {
                "rank": record["rank"],
                "model": record["model"],
                "model_aliases": record["model_aliases"],
                "sgi_index": record["SGI-Index"],
                "num_benchmarks_available": record["num_benchmarks_available"],
                "missing_benchmarks": record["missing_benchmarks"],
                "benchmark_scores": record["benchmark_scores"],
                **EXTENSION_FIELDS,
            }
            for record in records
        ],
    }
    frontend_output.write_text(
        json.dumps(frontend_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = build_report(
        display_leaderboard,
        benchmark_details,
        [path.name for path in csv_paths],
        benchmark_order,
        {
            "csv": csv_output,
            "json": json_output,
            "frontend_json": frontend_output,
            "markdown": md_output,
        },
    )
    md_output.write_text(report, encoding="utf-8")

    return {
        "csv": csv_output,
        "json": json_output,
        "frontend_json": frontend_output,
        "markdown": md_output,
    }


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build SGI-Index from local CSV benchmark files.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=project_root / "test_results",
        help="Directory containing benchmark CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "sgi_index",
        help="Directory where SGI-Index outputs will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = build_index(args.input_dir, args.output_dir)
    print("SGI-Index generated successfully.")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
