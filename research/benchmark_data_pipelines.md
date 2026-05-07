# Benchmark Data Construction Pipelines

## SFE (Scientists' First Exam)

**Paper:** arXiv:2506.10521  
**规模:** 830 VQA pairs | 66 tasks | 5 disciplines | 3 cognitive levels

### 数据构建管线

#### 1. 任务设计阶段（Task Design）

- 由5个学科（Astronomy, Chemistry, Earth Science, Life Science, Materials Science）的领域科学家主导
- 定义了66个多模态任务，归属18个科学方向
- 任务按3个认知层次分类：
  - **L1 Signal Perception** (202 QA pairs)：从科学原始数据可视化中识别关键组件
  - **L2 Attribute Understanding** (503 QA pairs)：解释领域专家知识
  - **L3 Comparative Reasoning** (125 QA pairs)：通过多源科学图像的结构化比较推导现象学洞察

#### 2. 数据来源（Data Sources）

- 使用**原生科学原始数据格式**（非合成图像）
- 包括：光谱数据、显微镜图像、天文观测、分子结构、地质图、材料表征数据等
- 所有数据来自真实科学实验、模拟或观测工作流

#### 3. 问题构建（Question Construction）

- 由博士级领域科学家**手动设计** VQA pairs
- 三种题型：
  - **MCQ**（多选题）
  - **Exact Match**（精确匹配）
  - **Open-ended**（开放式问答）
- 每个问题都设计为必须依赖视觉理解才能回答（不可仅通过文本回答）
- 全部双语构建（EN + ZH）

#### 4. 质量控制（Quality Control）

- 多位领域科学家交叉验证（cross-review）
- 确保问题的科学严谨性和认知层次正确性
- 难度校准：确保对当前SOTA模型有足够挑战性（GPT-o3仅34.08%）

#### 5. 评估体系

- 多维度评分：ROUGE、BERTScore、BLEU、METEOR、LLM-as-Judge (GPT-4o, 0-10分)
- 定位任务用IoU + Acc@{0.1, 0.3, 0.5, 0.7, 0.9}
- 支持lmms-eval和SciEvalKit两套评测框架

---

## MSEarth (Multimodal Earth Science)

**Paper:** arXiv:2505.20740 (ACL 2026 Main Conference)  
**规模:** 3000 MCQs + 1500 Open-ended | 5 Earth spheres | 8 disciplines | 66 sub-disciplines

### 数据构建管线

#### 1. 文献收集（Literature Collection）

- 从**40万+篇** open-access 地球科学 PDF 论文中收集（OpenDataLab提供）
- 覆盖5个Earth spheres：atmosphere, cryosphere, hydrosphere, lithosphere, biosphere
- 8个主要学科、66个子学科
- 经过筛选后约83K篇论文包含高质量地球观测图像，进一步筛选至约64K篇用于精炼标注

#### 2. PDF解析（Document Parsing）

- 使用 **MinerU** 进行 PDF 结构化解析，转换为结构化JSON
- 提取图表、表格、公式等多模态内容
- 通过regex匹配识别引用各图表的上下文段落
- 保留图文关联关系

#### 3. 图注增强（Caption Enrichment — MSEarthCap）

- 使用 **GPT-4o** 结合图表、原始标题和上下文论文段落生成"refined captions"
- 平均标题长度从37.56 tokens增强到136.29 tokens
- 确保每张图的语义信息完整可用

#### 4. QA 生成（Question-Answer Generation — MSEarthQA）

- GPT-4o 基于图表 + 原始标题 + refined caption 自动生成候选问答对
- Prompt设计鼓励生成需要refined caption才能回答的问题
- 生成两类题目：MCQ（多选题）和 Open-ended（开放式问答）

#### 5. 多智能体投票验证（Multi-Agent Voting Validation）

5个MLLM组成验证委员会：Qwen2.5-VL-72B, Qwen2.5-VL-7B, InternVL2.5-7B, InternVL2.5-78B, GPT-4o

三阶段难度筛选：

- **Phase A:** 仅给原始标题，5个模型全部回答正确 → 标记为"easy"（~70%），从测试集剔除
- **Phase B:** 给refined caption，>60%模型回答正确 → 标记为"specialized QA"（~20%）
- **Phase C:** 仅用70B+模型，回答正确 → 标记为"hard QA"（~5%）；剩余~5%视为有缺陷，丢弃

训练集组成：20% Phase A + 80% Phase B

#### 6. 图像分类过滤

- 使用 Qwen-2.5-VL-72B 和 Qwen2-VL-7B-Instruct 对图像分类
- 区分地球观测图像 vs. 无关图像
- 多次采样确保分类鲁棒性

#### 7. 人工标注与审核（Human Annotation & Review）

- 标注员通过标注公司招募，持有**地球科学硕士学位**
- 评估4个维度：图像推理类型、科学问题类型、完整性、正确性
- **4位地球科学博士候选人**进行最终质量评估
- Krippendorff's alpha = 0.695（评估者间一致性）
- 最终人工筛除216条无效MCQ + 89条无效Open-ended

---

## 两者对比

| 维度 | SFE | MSEarth |
|------|-----|---------|
| 数据来源 | 真实科学实验原始数据 | 40万+学术论文中的图表 |
| 问题生成方式 | 博士科学家手动设计 | GPT-4o自动生成 + 人工审核 |
| PDF解析工具 | N/A（非论文来源） | MinerU |
| 质量控制 | 专家交叉验证 | 多MLLM投票 + 博士审核 |
| 自动化程度 | 低（专家驱动） | 高（LLM驱动 + 人工把关） |
| 规模 | 830题 | 4500题 |
| 特色 | 认知层次分级、原生数据格式 | 大规模管线、难度分阶段筛选 |
| 评估框架 | lmms-eval / SciEvalKit | 自有评测系统 |
