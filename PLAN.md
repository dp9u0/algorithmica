# Algorithmica 中文站 · 翻译与补写计划

本文件只列**要做的事**。已完成与进行中见 `STATUS.md`；规则（怎么翻）见 `AGENTS.md`；流程见 `.claude/skills/translate-chapter/`。

## 0. 内容基线（2026-09-13 全量盘点）

- 英文书（en）与俄文四册（ru）无内容重叠，已核验上游全部 commit
- **已发布可译 = 188 篇**：英文 69（仅卷 I）+ 俄文 cs 119。修正旧口径：英文 Part II/III 与俄文 math/ml/dl 线上均未发布（官方 sitemap 无对应 URL、逐一直接探测 404），并非已发布；文件级 `draft:` 标记与线上状态不一致（卷 II 子页大多未标，`/hpc/hardware/` 的 200 是旧目录重定向占位页），发布状态判定以线上为准
- 上游 2022-05 停更（Part II 最后改动 2022-05-18），草稿不会再由上游完成 → 草稿与缺口由本站自行处理
- 俄文四册的西里尔文件名遗留（如 math/probability/`Вероятность.md`）在对应册启动时定中文文件名规范

| 内容源          | 卷                        | 已发布          | 已写未发布（草稿）         | 完全未写             |
| --------------- | ------------------------- | --------------- | -------------------------- | -------------------- |
| hpc 英文书      | I Performance Engineering | 69              | 23 篇正文 + 卷根 3 页      | 13 个目录条目        |
|                 | II Parallel Computing     | 0               | 7 篇 + 1 空壳 + 若干章节页 | 前言规划的大部分主题 |
|                 | III Distributed Computing | 0               | 2 篇 + 3 空章节页          | 前言规划的大部分主题 |
|                 | IV Software & Hardware    | 0               | 0                          | 全部                 |
| cs 俄文算法册   | —                         | 119             | 104                        | —                    |
| math 俄文数学册 | —                         | 0（整册 draft） | 43                         | —                    |
| ml 俄文 ML 册   | —                         | 0（整册 draft） | 26                         | —                    |
| dl 俄文 DL 册   | —                         | 0（整册 draft） | 22                         | —                    |

## 1. 工作类型与草稿分级

| 类型     | 定义                                       | 页面标注                                                     |
| -------- | ------------------------------------------ | ------------------------------------------------------------ |
| 译文     | 已发布原文的忠实翻译（现行流程）           | 无                                                           |
| 草稿译本 | 译作者草稿 + 译者二次编辑（补全、顺稿）    | 页首标注"译自作者未完成草稿（截至 2022-05），含译者二次编辑" |
| 译者补写 | 原作者仅有目录条目或空标题，正文由译者撰写 | 页首显著标注"本节原作者仅列入目录，正文为译者补写"           |

草稿按词数分级：**A** ≥500 词，可直接翻译 + 编辑；**B** 300–500 词，半成品；**C** <200 词，空壳，事实上的补写。

## 2. P0 前置（草稿发布与译者补写启动前完成）

草稿译本的翻译标记已定（2026-09-13，规则见 `AGENTS.md`"草稿译本"）：标题 `[草稿]` 前缀 + 译文永久 `draft: true` 不发布，可随章启动。剩余项针对**草稿发布阶段与译者补写**：

1. 草稿发布前定稿页首标注块（§1 的"译自作者未完成草稿…"）与侧栏视觉区分、front matter 键
2. translate-chapter skill 补"译者补写"流程（草稿译本流程已并入）
3. 检查脚本覆盖新页面类型（标注块存在性、front matter 键合法性、草稿译本 `[草稿]` 标记校验）
4. 公开上线前向原仓库确认翻译授权（v3 无内容 LICENSE；俄文页脚为 CC BY-SA 4.0）——独立于翻译进度，随上线节点处理

## 3. hpc 英文书

### 3.1 卷 I Performance Engineering（12 章）

已发布 69 篇已全部译出（审读/收尾中，见 `STATUS.md`）。其余待办：

**草稿译本（按章，23 篇）——已全部译出（2026-09-14，`[草稿]` 标题前缀 + 永久 `draft: true` 不发布，标记规则见 `AGENTS.md`"草稿译本"；下表保留作分级盘点记录）**

| 章                              | A 级                                                           | B 级                                               | C 级（≈补写）                                                                            |
| ------------------------------- | -------------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 1 Complexity Models             | levels·When to Optimize（1191 词）                             | models·Models of Computation（306）                | —                                                                                        |
| 2 Computer Architecture         | —                                                              | —                                                  | interaction·Interrupts and System Calls（118）                                           |
| 3 Instruction-Level Parallelism | scheduling·Instruction Scheduling（660）                       | limits·Theoretical Performance Limits（338）       | —                                                                                        |
| 4 Compilation                   | abstractions·Non-Zero-Cost Abstractions（534）                 | limitations·What Compilers Can and Can't Do（494） | arithmetic·Arithmetic Optimizations（10）                                                |
| 6 Arithmetic                    | bit-hacks·Bit Manipulation（658）                              | —                                                  | compression·Data Compression（10）                                                       |
| 7 Number Theory                 | finite·Finite Fields（1057）、cryptography·Cryptography（842） | hashing·Hashing（299）                             | error-correction（10）、rng·Random Number Generation（26）                               |
| 8 External Memory               | —                                                              | —                                                  | management·Memory Management（9）、sublinear·Sublinear Algorithms（10）                  |
| 11 Algorithm Case Studies       | logistic·Optimizing Logistic Regression（699）                 | —                                                  | reading-integers·Reading Decimal Integers（175）、sorting·Sorting（8）                   |
| 12 Data Structure Case Studies  | —                                                              | —                                                  | hash-tables·Hash Tables（169）、bitset·Bitmaps（8）、filters·Probabilistic Filters（40） |

第 5、9、10 章无草稿。

**卷根级页面（4 个）——草稿译本唯一余量（章节草稿已全部完成）**

| 页面                                            | 处理                                                       |
| ----------------------------------------------- | ---------------------------------------------------------- |
| `stats.md`（3572 词，概率论附录，A 级）         | 草稿译本，作为卷 I 附录                                    |
| `preface.md`（487 词，B 级）                    | 低优先：与本站译者导航页（hpc 首页）内容重叠，启动时定取舍 |
| `summary.md`（127 词，全卷优化 checklist 雏形） | C 级，按补写完成（需与卷 I 各章内容联动）                  |
| `slides/`（26 词，课程幻灯片尝试）              | 不处理                                                     |

**译者补写（原作者列入目录但零内容，13 个条目）**

| 章  | 条目                       | 备注                                              |
| --- | -------------------------- | ------------------------------------------------- |
| 2   | Virtualization             |                                                   |
| 6   | Interval Arithmetic        | 原章用 IEEE-754、Rounding Errors 两篇顶了规划位置 |
| 8   | B-Trees                    | 已被 ch12 Search Trees 覆盖，启动时定取舍         |
| 11  | Prime Number Sieves        |                                                   |
| 11  | Big Integers & Karatsuba   | 高价值                                            |
| 11  | Fast Fourier Transform     | 高价值                                            |
| 11  | Number-Theoretic Transform | 高价值                                            |
| 11  | Writing Decimal Integers   | 与 reading-integers 草稿配对                      |
| 11  | Reading and Writing Floats |                                                   |
| 11  | String Searching           |                                                   |
| 12  | Tries                      |                                                   |
| 12  | Range Minimum Query        |                                                   |

ch11 缺口最大（规划 15 篇，现有 8 篇），FFT / NTT / Karatsuba 是性能工程招牌案例，补写价值最高。

### 3.2 卷 II Parallel Computing（整部草稿）

**草稿译本已完成（2026-09-14，13 文件，`[草稿]` + 永久 draft 不发布）**：卷根（301 词，含摩尔定律配图）、Concurrency 章（章节页 + processes / threads / fibers / event-driven 4 篇）、Synchronization 章节页（109 词，2 代码块）、GPU 章节页（2614 词，Jupyter notebook 转写体；zh 文件名 `_index.md` 对应 en `_index.en.md`，检查脚本已适配）。

剩余为补写：

- 空壳 4 个：mutex（Mutual Exclusion）、openmp、cuda、runtimes（Threading Runtimes）——原 PLAN 误记为有正文的"草稿译本"，实为空壳
- 前言规划未写主题：上下文切换、绿色线程、缓存一致性、reductions / scans / list ranking、图算法、lock-free 数据结构、kernels / warps / blocks、GPU 矩阵乘法与排序

### 3.3 卷 III Distributed Computing（整部草稿）

**草稿占位已建（2026-09-14，6 文件全为空壳，`[草稿]` + 永久 draft 不发布）**：卷根、actor、cloud、mpi / distributed-algorithms / mapreduce 章节页——原 PLAN 误记 Actor Model / Cloud Computing 为有正文的"草稿译本"，实为空壳。

剩余为补写：

- Actor Model、Cloud Computing 正文
- mpi / distributed-algorithms / mapreduce 章节页内容
- 前言规划主题：网络与消息传递、通信受限算法、分布式原语、all-reduce、MapReduce、流处理、查询计划、存储与分片、压缩、分布式数据库、一致性、可靠性、调度、工作流引擎

### 3.4 卷 IV Software & Hardware（零内容，远期）

全部补写。规划主题：LLVM IR、编译器优化与后端、解释器、JIT、Cython、JAX、Numba、Julia、OpenCL、DPC++、oneAPI、XLA、Verilog、FPGA、ASIC、TPU 与 AI 加速器。

## 4. 俄文四册（cs / math / ml / dl）

章名以俄文原文为准，下表中文名为计划用标注。

### 4.1 cs 算法册（119 已发布 + 104 草稿，36 章，按俄文站首页分组）

主线：119 篇按章翻译。

| 分组     | 章（已发布/草稿）                                                                       |
| -------- | --------------------------------------------------------------------------------------- |
| 算法分析 | 计算复杂度 2/3 · 排序 6/6 · 二分与交互题 2/4 · 序列 1/4 · 任务分解 5/2 · 算术 2/3       |
| 数据结构 | 基础数据结构 4/5 · 搜索树 3/4 · 集合结构 2/1 · 区间查询 4/4 · 可持久化 4/0 · 线段树 3/4 |
| 动态规划 | DP 通用技巧 2/3 · 组合优化 3/4 · 组合对象 3/3 · 子集 DP 2/2 · 分层 DP 4/0 · 博弈论 1/7  |
| 数学     | 代数 8/1 · 模运算 3/4 · 因数分解与素数 2/4                                              |
| 图论     | 图遍历 10/1 · 最短路 3/4 · 连通性与生成树 5/5 · 有根树 5/4 · 匹配 4/1 · 网络流 1/5      |
| 计算几何 | 几何基元 4/1 · 凸包 5/2 · 进阶几何 2/1                                                  |
| 字符串   | 子串搜索 3/1 · 哈希 3/1 · 字符串结构 4/2                                                |
| 其他     | 数值方法 2/1 · 编程技术 2/5 · 启发式算法 0/2                                            |

104 篇草稿：启动 cs 时按 §1 分级逐章盘点后决定译/补。草稿集中章：博弈论 1/7、网络流 1/5、编程技术 2/5、因数分解 2/4、启发式 0/2。

### 4.2 math 数学册（整册草稿，43 篇，6 章）

草稿译本流程。发布方式先定：整册译完一次性发布 or 随译随发。

algebra 代数 5 · calculus 微积分 2 · combinatorics 组合数学 12 · geometry 几何 1 · number-theory 数论 10 · probability 概率论 13

### 4.3 ml 机器学习册（整册草稿，26 篇，10 章）

数据处理 3 · 降维 2 · 集成学习 4 · 基础概念 1 · 模型 3 · 预处理 1 · 任务与指标 5 · 排序学习 2 · 强化学习 3 · 统计 2

### 4.4 dl 深度学习册（整册草稿，22 篇，7 章）

进阶 3 · 辅助主题 1 · 计算机视觉 3 · 基础 2 · 生成模型 4 · 层与组件 4 · NLP 5

## 5. 优先级

当前：英文卷 I 69 篇正文 + 卷 I–III 草稿译本 42 文件已全部译出（审读/收尾中，见 `STATUS.md`）。

1. 卷 I–III 审读收尾：finish（状态更新 + TERMS 补录 + git 提交；草稿保持不发布）
2. 卷 I 卷根级页面：`stats.md`（3572 词，A 级）草稿译本；`preface.md` / `summary.md` 启动时定取舍
3. 补写启动前 P0（§2 剩余项：译者补写流程进 skill、检查脚本覆盖新页面类型）
4. 卷 I 补写：ch11 高价值条目优先（Big Integers & Karatsuba、FFT、NTT），C 级空壳（§3.1 C 列 12 篇）随后
5. 卷 II / III 补写：空壳 4+6 个 + 前言规划主题
6. 俄文 cs 册 119 篇（草稿 104 篇随章盘点）
7. 俄文 math / ml / dl 整册草稿 91 篇
8. 卷 IV（远期，全部补写）
