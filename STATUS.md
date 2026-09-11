# 翻译状态（translate-chapter 工作文件）

skill 每次启动先读此文件恢复上下文；阶段推进时同步更新。
**并行会话**：多会话各翻一章时，只更新自己章节的行（改前重读）；提交禁止 `git add -A`。
状态：⏳ 待译 → ✍️ 翻译中 → 👀 审读中（draft，不发布）→ ✅ 已完成

| 章                              | 目录              | 状态     | 日期       | 备注                                                                      |
| ------------------------------- | ----------------- | -------- | ---------- | ------------------------------------------------------------------------- |
| 1 Complexity Models             | `complexity`      | ✅ 已完成 | 2026-09-11 | 2 篇 + 章节页；含 1.2 译者注（向量化平台差异）                            |
| 2 Computer Architecture         | `architecture`    | ✅ 已完成 | 2026-09-12 | 6 篇 + 章节页；`interaction` 为 draft 跳过；2 条译者注（Apple M 系列、Arm 向量化实测）；实验代码 `code/architecture/` 3 个 |
| 3 Instruction-Level Parallelism | `pipelining`      | 👀 审读中 | 2026-09-11 | 5 篇正文 + 章节页；`limits`/`scheduling` 为 draft 跳过；检查全过，待用户审读后 finish |
| 4 Compilation                   | `compilation`     | 👀 审读中 | 2026-09-11 | 5 篇正文 + 章节页；`abstractions`/`arithmetic`/`limitations` 为 draft 跳过；检查全过，待用户审读后 finish |
| 5 Profiling                     | `profiling`       | 👀 审读中 | 2026-09-11 | 6 篇正文 + 章节页，无 draft 原文；检查全过，含 2 条译者注（events 0.53s 笔误、mca Each cycle 笔误） |
| 6 Arithmetic                    | `arithmetic`      | ⏳ 待译   |            |                                                                           |
| 7 Number Theory                 | `number-theory`   | ⏳ 待译   |            |                                                                           |
| 8 External Memory               | `external-memory` | ⏳ 待译   |            |                                                                           |
| 9 RAM & CPU Caches              | `cpu-cache`       | ⏳ 待译   |            |                                                                           |
| 10 SIMD Parallelism             | `simd`            | ⏳ 待译   |            |                                                                           |
| 11 Algorithm Case Studies       | `algorithms`      | ⏳ 待译   |            |                                                                           |
| 12 Data Structure Case Studies  | `data-structures` | ⏳ 待译   |            |                                                                           |
| Part II Parallel                | `parallel`        | ⏳ 待译   |            |                                                                           |
| Part III Distributed            | `distributed`     | ⏳ 待译   |            |                                                                           |

## 恢复要点

- 👀 审读中的章节：译文 front matter 带 `draft: true`（生产构建不发布），本地预览用 `hugo serve -D`
- 恢复审读：向用户重发审读表（SKILL.md 阶段 4），等用户提问或说 finish
- ✍️ 翻译中的章节：盘点 `content/chinese/hpc/<dir>/` 缺口，继续未完成篇目
