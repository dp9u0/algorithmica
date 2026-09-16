# 翻译状态（translate-chapter 工作文件）

skill 每次启动先读此文件恢复上下文；阶段推进时同步更新。
**并行会话**：多会话各翻一章时，只更新自己章节的行（改前重读）；提交禁止 `git add -A`。
状态：待译 → 翻译中 → 审读中（draft，不发布）→ 已完成

待办清单（要做哪些事）见 `PLAN.md`；本文件只记录完成与进行中状态。

## 总览

- 总量口径（2026-09-13 修正，详见 PLAN §0）：已发布可译 **188 篇**（英文 69 + 俄文 cs 119）；另有草稿/已写未发布 232 篇待分级处理（PLAN §1）
- 英文卷 I 已发布 69 篇：**65 篇已译**（第 1–2 章共 8 篇已发布，第 3–11 章共 57 篇审读中），第 12 章 4 篇翻译中
- 卷 I 草稿译本 **23 篇已全部译出**（2026-09-14，9 章；`[草稿]` 标题前缀 + 永久 `draft: true`，不发布，仅 `hugo serve -D` 可见），待审读
- 卷 II/III 草稿译本 **19 个文件已全部译出**（2026-09-14；整部未发布，全部 `[草稿]` + 永久 draft 不发布），待审读；卷 IV 无源内容（PLAN §3.4 全部补写，远期）
- 导航页 9 篇已完成（书首、各分册/章节首页）
- 站点框架（多语言、搜索、字体、部署配置）已完成

### 已完成里程碑

| 日期          | 内容                                                                                         |
| ------------- | -------------------------------------------------------------------------------------------- |
| 2026-09-11 前 | 站点框架：Hugo 升级 0.166、多语言（zh 默认根路径）、Lunr 中文搜索、字体、GitHub Pages 部署   |
| 2026-09-11    | 第 1 章 Complexity Models：2 篇 + 章节页；1 条译者注                                         |
| 2026-09-12    | 第 2 章 Computer Architecture：6 篇 + 章节页；2 条译者注；实验代码 `code/architecture/` 3 个 |

## 章节表

| 章                              | 目录              | 状态     | 日期       | 备注                                                                                                                                                                                                                                      |
| ------------------------------- | ----------------- | -------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 Complexity Models             | `complexity`      | 已完成 | 2026-09-11 | 2 篇 + 章节页；含 1.2 译者注（向量化平台差异）；草稿 2 篇已译（levels/models，[草稿] 不发布）                                                                                                                                             |
| 2 Computer Architecture         | `architecture`    | 已完成 | 2026-09-12 | 6 篇 + 章节页；`interaction` 草稿已译（[草稿] 不发布）；2 条译者注（Apple M 系列、Arm 向量化实测）；实验代码 `code/architecture/` 3 个                                                                                                     |
| 3 Instruction-Level Parallelism | `pipelining`      | 审读中 | 2026-09-11 | 5 篇正文 + 章节页；`limits`/`scheduling` 草稿已译（[草稿] 不发布）；检查全过，待用户审读后 finish                                                                                                                                          |
| 4 Compilation                   | `compilation`     | 审读中 | 2026-09-11 | 5 篇正文 + 章节页；`abstractions`/`arithmetic`/`limitations` 草稿已译（[草稿] 不发布）；检查全过，待用户审读后 finish                                                                                                                      |
| 5 Profiling                     | `profiling`       | 审读中 | 2026-09-11 | 6 篇正文 + 章节页，无 draft 原文；检查全过，含 2 条译者注（events 0.53s 笔误、mca Each cycle 笔误）                                                                                                                                       |
| 6 Arithmetic                    | `arithmetic`      | 审读中 | 2026-09-12 | 7 篇正文 + 章节页；`bit-hacks`/`compression` 草稿已译（[草稿] 不发布）；检查全过，含 1 条译者注（float 光速 3·10⁹ 数量级笔误）；检查脚本白名单补 half/extended/quadruple/bfloat/uOps 等                                                  |
| 7 Number Theory                 | `number-theory`   | 审读中 | 2026-09-12 | 4 篇正文 + 章节页；`finite`/`cryptography`/`hashing`/`rng`/`error-correction` 草稿已译（[草稿] 不发布）；检查全过，含 1 条译者注（exponentiation 代码 `res` 未定义笔误）                                                                  |
| 8 External Memory               | `external-memory` | 审读中 | 2026-09-12 | 8 篇正文 + 章节页；`management`/`sublinear` 草稿已译（[草稿] 不发布）；检查全过，含 2 条译者注（hash join O(M) 笔误、背包代码 k→w 笔误）                                                                                                    |
| 9 RAM & CPU Caches              | `cpu-cache`       | 审读中 | 2026-09-12 | 11 篇正文 + 章节页，无 draft 原文；检查全过；latency 尾部 "RAM-specific timings" 链接指向 ../mlp 疑为原文笔误（该节实际在 aos-soa），待审读定夺                                                                                           |
| 10 SIMD Parallelism             | `simd`            | 审读中 | 2026-09-12 | 6 篇正文 + 章节页，无 draft 原文；检查全过，含 2 条译者注（counting 溢出公式 ⌊255/8⌋≠15 笔误、popcount 代码 k+=15 边界重复计数）；检查脚本白名单补 gather/scatter/permute                                                                 |
| 11 Algorithm Case Studies       | `algorithms`      | 审读中 | 2026-09-12 | 5 篇正文 + 章节页；`logistic`/`reading-integers`/`sorting` 草稿已译（[草稿] 不发布）；检查全过，含 1 条译者注（Floyd 版 gcd 调用少参数 n 笔误）；白名单补 Pollard/softmax/logit/argmax/rabin-karp、URL 剥离；修复原文两处坏相对链接（`../hpc/arithmetic/…`、`../hpc/cpu-cache/…` 基准路径错误） |
| 12 Data Structure Case Studies  | `data-structures` | 审读中 | 2026-09-13 | 4 篇正文 + 章节页；`hash-tables`/`filters`/`bitset` 草稿已译（[草稿] 不发布）；检查全过，含 2 条译者注（segment-trees 原文两处笔误：`7 = 2×2+1`、unless n is not a power of two）；检查脚本补 `<pre>` 剥离与 ahnentafel 白名单                          |
| Part II Parallel                | `parallel`        | 审读中 | 2026-09-14 | 草稿译本 13 文件全译（卷根 301 词 + GPU 章节页 2614 词 notebook 体 + Concurrency 4 篇/章节页 + Synchronization 章节页 + 空壳 5 个）；`[草稿]` 不发布；检查全过；zh `gpu/_index.md` 对应 en `_index.en.md`（检查脚本已适配） |
| Part III Distributed            | `distributed`     | 审读中 | 2026-09-14 | 6 文件全为空壳（卷根、actor、cloud、mpi/algorithms/mapreduce 章节页），草稿占位已建；`[草稿]` 不发布；检查全过                                                                                                                            |

## 恢复要点

- 审读中的章节：译文 front matter 带 `draft: true`（生产构建不发布），本地预览用 `hugo serve -D`
- 恢复审读：向用户重发审读表（SKILL.md 阶段 4），等用户提问或说 finish
- 翻译中的章节：盘点 `content/chinese/hpc/<dir>/` 缺口，继续未完成篇目
