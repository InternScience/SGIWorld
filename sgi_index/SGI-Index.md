# SGI-Index

Generated at: 2026-04-19 03:49:08 UTC

## SGI-Index 简介

SGI-Index 是 SGIWorld 的 score-only 综合模型能力指数。它参考 Artificial Analysis Intelligence Index 的 composite benchmark 思路，把多个能力维度的评测聚合成一个 0-100 分的综合分，而不是用单一 benchmark 代表整体能力。

当前版本不估算 compute、token usage 或 cost，因为本地 CSV 中没有这些字段。JSON 输出保留了扩展字段，便于后续加入 score-vs-compute、score-vs-cost 或 score-vs-token 视图。

## 数据来源

输入目录：`test_results`

读取的 CSV 文件：

- `Evaluation-v1_AstroVisBench_表格.csv`
- `Evaluation-v1_CMPhysBench_CMPhysBench.csv`
- `Evaluation-v1_ChemBench_ChemBench.csv`
- `Evaluation-v1_EarthSE_表格.csv`
- `Evaluation-v1_ResearchBench_表格.csv`
- `Evaluation-v1_SFE_SFE.csv`
- `Evaluation-v1_SciCode_表格.csv`
- `Evaluation-v1_TRQA_表格.csv`

宽表中的 benchmark 顺序：`AstroVisBench`, `ChemBench`, `CMPhysBench`, `EarthSE`, `ResearchBench`, `SciCode`, `SFE`, `TRQA`

## 评分字段选择规则

- 每个 CSV 的第一列作为模型名称列，并清理 UTF-8 BOM、全角字符和前后空白。
- `Avg Score`、`Avg Score（acc）` 等平均分列存在且包含有效值时优先使用。
- 平均分列存在但为空时，不直接使用空值；脚本会按 benchmark 专属规则选择代表性字段或合理数值子指标。
- `Parent items`、`父记录`、`检查` 等明显非分数字段会被忽略。
- 模型名称默认不做人工合并；仅合并显式配置的源数据别名，避免把不同模型误合并。

- **AstroVisBench**：来源 `Evaluation-v1_AstroVisBench_表格.csv`；SGI 主分数字段：`process_success_rate`, `visualize_success_rate`, `process_average_variable_inspection_score`, `visualize_no_error_rate`；选择规则：后备子指标均值；辅助数值字段：-。
- **ChemBench**：来源 `Evaluation-v1_ChemBench_ChemBench.csv`；SGI 主分数字段：`Avg Score(acc)`；选择规则：平均分列 `Avg Score(acc)`；辅助数值字段：-。
- **CMPhysBench**：来源 `Evaluation-v1_CMPhysBench_CMPhysBench.csv`；SGI 主分数字段：`Avg Score`；选择规则：平均分列 `Avg Score`；辅助数值字段：-。
- **EarthSE**：来源 `Evaluation-v1_EarthSE_表格.csv`；SGI 主分数字段：`Avg Score`；选择规则：平均分列 `Avg Score`；辅助数值字段：`Atmosphere`, `Biosphere`, `Cryosphere`, `Hydrosphere`, `Lithosphere`。
- **ResearchBench**：来源 `Evaluation-v1_ResearchBench_表格.csv`；SGI 主分数字段：`generate_avg_score`, `retrival_hit@3`；选择规则：后备子指标均值；辅助数值字段：-。
- **SciCode**：来源 `Evaluation-v1_SciCode_表格.csv`；SGI 主分数字段：`Main Problem Resolve Rate`；选择规则：主指标 `Main Problem Resolve Rate`；辅助数值字段：`Subproblem Resolve Rate`。
- **SFE**：来源 `Evaluation-v1_SFE_SFE.csv`；SGI 主分数字段：`Avg Score`；选择规则：平均分列 `Avg Score`；辅助数值字段：-。
- **TRQA**：来源 `Evaluation-v1_TRQA_表格.csv`；SGI 主分数字段：`Avg Score(acc)`；选择规则：平均分列 `Avg Score(acc)`；辅助数值字段：-。

## 模型别名合并规则

以下源数据名称被合并到统一模型名。合并发生在每个 benchmark 读入后；如果同一个 benchmark 内多个源名称映射到同一模型，其分数取均值。

| Canonical model | Merged source names |
| --- | --- |
| Gemini-3-Pro | Gemini-3-pro, Grmini-3-Pro |
| GPT-5.1 | GPT-5-1 |

## 归一化规则

所有进入 SGI-Index 聚合的 benchmark 分数都会统一到 0-100。对每个 benchmark，如果选中分数的有效最大值 `<= 1.5`，则视为 0-1 比例分并乘以 100；否则视为已经是 0-100 分。

## 权重规则

默认 SGI-Index 使用等权重：

```json
{
  "AstroVisBench": 1,
  "ChemBench": 1,
  "CMPhysBench": 1,
  "EarthSE": 1,
  "ResearchBench": 1,
  "SciCode": 1,
  "SFE": 1,
  "TRQA": 1
}
```

对每个模型，SGI-Index 是其可用 benchmark 分数的加权平均值。缺失 benchmark 不填 0，并在输出中记录 `num_benchmarks_available` 和 `missing_benchmarks`。

## Top Models 排行榜

| Rank | Model | Aliases merged | SGI-Index | Available Benchmarks |
| --- | --- | --- | --- | --- |
| 1 | Gemini-3-Pro | Gemini-3-pro, Grmini-3-Pro | 54.57 | 8 |
| 2 | Qwen3-VL-235B-A22B-Instruct |  | 53.74 | 3 |
| 3 | Claude-opus-4-5-20251101-thinking |  | 53.03 | 8 |
| 4 | GPT-5 |  | 51.02 | 8 |
| 5 | Claude 4.5 Sonnet |  | 48.82 | 8 |
| 6 | GPT-o3 |  | 47.68 | 8 |
| 7 | Kimi-k2 |  | 47.67 | 7 |
| 8 | Gemini-2.5-Pro |  | 47.59 | 8 |
| 9 | Qwen3-Max |  | 47.09 | 8 |
| 10 | Claude4-1-Opus |  | 46.72 | 8 |
| 11 | Seed-1.8 |  | 46.33 | 8 |
| 12 | GPT-5.1 | GPT-5-1 | 46.13 | 8 |
| 13 | Seed1.6-vision |  | 45.80 | 8 |
| 14 | GPT-5.2 |  | 45.30 | 8 |
| 15 | InternS1 |  | 45.19 | 8 |

完整排行榜：`/home/zhangwenlong/jarvisdata/projects/SGIWorld/sgi_index/sgi_index.csv`

## Benchmark 说明和使用字段

| Benchmark | Source file | Selected field(s) | Fallback | Normalization | Valid/Rows | Weight |
| --- | --- | --- | --- | --- | --- | --- |
| AstroVisBench | Evaluation-v1_AstroVisBench_表格.csv | `process_success_rate`, `visualize_success_rate`, `process_average_variable_inspection_score`, `visualize_no_error_rate` | 是 | max <= 1.5，按 0-1 比例分乘以 100 | 24/24 | 1 |
| ChemBench | Evaluation-v1_ChemBench_ChemBench.csv | `Avg Score(acc)` | 否 | 按 0-100 分处理 | 24/24 | 1 |
| CMPhysBench | Evaluation-v1_CMPhysBench_CMPhysBench.csv | `Avg Score` | 否 | 按 0-100 分处理 | 25/25 | 1 |
| EarthSE | Evaluation-v1_EarthSE_表格.csv | `Avg Score` | 否 | 按 0-100 分处理 | 24/24 | 1 |
| ResearchBench | Evaluation-v1_ResearchBench_表格.csv | `generate_avg_score`, `retrival_hit@3` | 是 | max <= 1.5，按 0-1 比例分乘以 100 | 24/24 | 1 |
| SciCode | Evaluation-v1_SciCode_表格.csv | `Main Problem Resolve Rate` | 否 | 按 0-100 分处理 | 27/27 | 1 |
| SFE | Evaluation-v1_SFE_SFE.csv | `Avg Score` | 否 | 按 0-100 分处理 | 21/21 | 1 |
| TRQA | Evaluation-v1_TRQA_表格.csv | `Avg Score(acc)` | 否 | 按 0-100 分处理 | 24/24 | 1 |

## 缺失数据说明

| Model | Available benchmarks | Missing benchmarks |
| --- | --- | --- |
| Qwen3-VL-235B-A22B-Instruct | 3 | AstroVisBench, ChemBench, CMPhysBench, ResearchBench, SciCode |
| Kimi-k2 | 7 | SFE |
| Ling-flash-2.0 | 7 | SFE |
| Qwen3-VL-235B-A22B-Thinking | 5 | EarthSE, SFE, TRQA |
| DeepSeek-R1 | 7 | SFE |
| InterS1-mini | 1 | AstroVisBench, ChemBench, EarthSE, ResearchBench, SciCode, SFE, TRQA |
| S1-base | 1 | AstroVisBench, ChemBench, CMPhysBench, EarthSE, ResearchBench, SFE, TRQA |
| MiniMax-M2.5 | 1 | AstroVisBench, ChemBench, CMPhysBench, EarthSE, ResearchBench, SFE, TRQA |
| seed-2.0 | 1 | AstroVisBench, ChemBench, CMPhysBench, EarthSE, ResearchBench, SFE, TRQA |

## 方法局限性

- SGI-Index 当前只衡量分数，不包含 latency、cost、token usage、参数量或 compute-normalized efficiency。
- 等权重是透明默认设置，并不代表所有 benchmark 在科学意义上必然同等重要。
- 脚本只合并显式配置的模型别名，不推断未知别名。这可以避免误合并，但未配置的源数据写法差异仍会拆成多行。
- 按“可用 benchmark 平均”排名会让只覆盖少数高分 benchmark 的模型排位偏高；使用排行榜时应同时查看 `num_benchmarks_available`。
- 综合平均可能掩盖模型在单项 benchmark 上的强弱差异，应结合 CSV 和 JSON 中的单项分数一起解读。
