# Algorithmica 中文翻译 · 内容版图与进展

本文件说明原项目两部分内容的关系、各自的完成状态、以及中文翻译的规划与进展。规则（怎么翻）见 `AGENTS.md`；流程见 `.claude/skills/translate-chapter/`。

## 一、原项目：两套互相独立的内容

**关键结论：英文书与俄文四册没有内容重叠，也没有互相翻译关系。** 不存在"俄文 HPC 缺失"——俄文站从没有过 HPC 部分（已核验：全部 1083 个 commit 中无任何 `content/russian/hpc` 记录，俄文正文引用 HPC 时直接外链 `en.algorithmica.org/hpc/`）。

| | 英文站 `en.algorithmica.org` | 俄文站 `ru.algorithmica.org` |
|---|---|---|
| 内容 | 《现代硬件上的算法》单本书 | 四套课程材料：CS / Math / ML / DL |
| 主题 | 性能工程（缓存、SIMD、流水线……） | 经典算法、数学、机器学习、深度学习 |
| 起始 | 2021 年 | 2017 年（Tinkoff Generation 教学用） |
| 作者 | Sergey Slotin 单人创作 | 作者 + 师生协作 |
| 状态 | **写作中，未完成** | 主体完成，部分草稿 |

作者在英文书 FAQ 中明确：俄文站讲的是经典算法而非性能工程，与本书是两回事；作者的俄语 HPC 版计划是"至少翻译一部分"，尚未落地。

## 二、英文书《现代硬件上的算法》完成状态

**未完成。** 原书规划四部分，只有**第一部分 Performance Engineering** 有正式目录（12 章）；第二、三、四部分目前只有章节设想，主体未写。

### 第一部分 Performance Engineering（12 章）

TOC 中还有 14 个条目作者标注为未编写（目录里带括号的条目，如 `(6.8. Data Compression)`、`(12.5. Tries)`）。

| 章 | 出处目录 | 已发布 | 草稿 | 中文 |
|---|---|---|---|---|
| 1 Complexity Models | `complexity` | 2 | 2 | **已完成** |
| 2 Computer Architecture | `architecture` | 6 | 1 | 待译 |
| 3 Instruction-Level Parallelism | `pipelining` | 5 | 2 | 待译 |
| 4 Compilation | `compilation` | 5 | 3 | 待译 |
| 5 Profiling | `profiling` | 6 | 0 | 待译 |
| 6 Arithmetic | `arithmetic` | 7 | 2 | 待译 |
| 7 Number Theory | `number-theory` | 4 | 5 | 待译 |
| 8 External Memory | `external-memory` | 8 | 2 | 待译 |
| 9 RAM & CPU Caches | `cpu-cache` | 11 | 0 | 待译 |
| 10 SIMD Parallelism | `simd` | 6 | 0 | 待译 |
| 11 Algorithm Case Studies | `algorithms` | 5 | 3 | 待译 |
| 12 Data Structure Case Studies | `data-structures` | 4 | 3 | 待译 |
| | **合计** | **69** | **23** | **3/69** |

### 第二、三、四部分（主体未写）

| 部分 | 主题 | 出处目录 | 已发布 | 草稿 | 中文 |
|---|---|---|---|---|---|
| Part II Parallel Algorithms | 并发、并行、GPU | `parallel` | 8 | 1 | 待译 |
| Part III Distributed Computing | 网络、MapReduce | `distributed` | 2 | 0 | 待译 |
| Part IV Software & Hardware | LLVM、JIT、FPGA | — | 0 | 0 | — |

**可翻译总量（英文）：已发布 79 篇。** `draft: true` 的 24 篇是作者未完成草稿，不发布、也不翻译——若日后作者完成，再随上游更新补译。

## 三、俄文四册完成状态

| 分册 | 目录 | 已发布 | 草稿 | 已发布字数 | 中文 |
|---|---|---|---|---|---|
| 算法 CS | `cs` | 119 | 104 | 8.9 万 | 计划中 |
| 数学 Math | `math` | 53 | 0 | 2.7 万 | 计划中 |
| 机器学习 ML | `ml` | 29 | 0 | 7.3 千 | 计划中 |
| 深度学习 DL | `dl` | 31 | 0 | 3.0 千 | 计划中 |
| | **合计** | **232** | **104** | **12.7 万** | |

CS 册的 104 篇草稿集中在早期整理中的内容；Math/ML/DL 三册已基本全部发布。可翻译总量（俄文）：已发布 232 篇。

## 四、中文翻译进展

- **翻译顺序**：先英文 HPC 书（按书序逐章），俄文四册随后
- **当前进度**：第 1 章《复杂度模型》已完成（3 篇：章节页、现代硬件、编程语言）
- **单章流程**：见 skill —— 翻译 → 机械检查 → 语义自查 → 译者审读 → 收尾提交
- **译者注**：书首页 2 条（本站定位、资助说明）；正式章节暂无

### 里程碑

| 阶段 | 内容 | 状态 |
|---|---|---|
| 框架 | 站点、多语言、搜索、字体、部署配置 | 已完成 |
| Part I 第 1 章 | Complexity Models | 已完成 |
| Part I 第 2–12 章 | 按书序推进（69 篇） | 进行中 |
| Part II / III | Parallel / Distributed（10 篇） | 计划中 |
| 俄文四册 | CS / Math / ML / DL（232 篇） | 计划中 |
