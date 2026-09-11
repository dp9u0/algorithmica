---
name: translate-chapter
description: 翻译 Algorithmica/HPC 书的一个章节：读取英文原文→按 AGENTS.md 规则翻译→机械检查→语义自查→交用户审读→（用户确认后）更新进展并 git 提交。触发词：翻译下一章 / 翻译第 N 章 / translate chapter / translate-chapter finish。
---

# 翻译一章（translate-chapter）

内容规则以仓库根 `AGENTS.md` 为唯一事实源（链接规则、front matter、路径写法、术语括号注等），本 skill 只编排流程，不复制规则。

用法：
- `/translate-chapter` —— 书序中下一个未翻译章节
- `/translate-chapter <chapter-dir>` —— 指定章节（如 `cpu-cache`，即 `content/english/hpc/<chapter-dir>/`）
- `/translate-chapter finish` —— 用户审读确认后的收尾（阶段 5）

## 阶段 0 · 准备

1. 确定章节：列 `content/english/hpc/` 下各章，比对 `content/chinese/hpc/` 找出下一个未翻译的（按 en front matter 的 weight 排序）
2. 列出该章全部源文件；`draft: true` 的跳过并在报告中说明
3. 若 `content/chinese/hpc/<chapter>/` 已有半成品，先盘点缺口，不重译已完成篇目
4. `grep` 已译章节确认术语先例（如"缓存行""渐进复杂度"），保持全书一致；发现同一术语两种译法要统一

## 阶段 1 · 翻译

逐篇执行，严格遵守 AGENTS.md。要点回顾：

- front matter 只译 `title`、`menuTitle`、`part`；`weight`/`authors`/`prerequisites`/`aliases` 原样
- 代码块、`$…$`/`$$…$$` 公式、shortcode、TikZ、作者的 HTML 注释 **逐字保留**
- 图片路径改 `/en/<章节路径>/img/…`（复用英文资源，注意相对路径 `../img/` 的基准是文章所在目录）
- 根绝对链接（`/hpc/simd`）保持原样，render hook 自动加前缀

**语义分级（硬约束）**：
- 开场页（`content/chinese/_index.md`、`hpc/_index.md`）→ 译者导航/改编，讲清本站定位
- 正式章节 → **忠实原文，不改写**。作者的第一人称、玩笑、行文节奏、举例全部保留；宁可直译得不优雅，不擅自"改进"

## 阶段 2 · 机械检查

运行（构建 + 全部自动检查，退出码非 0 即有真问题）：

```bash
python3 .claude/skills/translate-chapter/scripts/check_translation.py content/chinese/hpc/<chapter>
```

脚本覆盖：构建零警告、代码块逐字比对（忽略空白）、公式序列一致、全站死链扫描（zh 缺失但 en 存在 = 预期 404，自动白名单）、图片存在性、英文残留启发式扫描。修复所有报告的问题后重跑至通过。

## 阶段 3 · 语义自查（人工通读一遍译文对照原文）

- 数字、倍数、时间、结论逐一核对（如 630s/63 倍这类）
- 术语首现括号注、全文一致性
- **译者注触发条件（仅两类，克制使用）**：
  1. 原文内容对本翻译站语境不适用（作者请求资助、"本书今夏发布"等以原书身份的表述）
  2. 原文疑似理论/事实错误——**不修改原文**，加注指出供读者参考
- 格式：紧跟相关段落的引用块 `> **译者注**：…`

## 阶段 4 · 用户审读（在此停止）

输出审读表后**停住等待**，不催促、不自作主张收尾：

```
| 篇目 | 本站中文 | 官方英文原文 |
|---|---|---|
| … | http://localhost:1313/hpc/<chapter>/<article>/ | https://en.algorithmica.org/hpc/<chapter>/<article>/ |
```

用户会对照原文提问、讨论。用户认为值得沉淀的讨论，按译者注格式插入合适位置（讨论本身也可能修正译文——先改译文，再决定是否还需加注）。

**反馈捕获**：审读中用户纠正的译法，若根因是规则缺口（而非一次性措辞偏好），或用户明说"记一下/这个要进规则"，立即追加到本 skill 目录的 `FEEDBACK.md`（收件箱）。同类问题第二次出现或用户明确偏好才记，不记一次性调整。

## 阶段 5 · 收尾（仅当用户明确说"完成/收尾/finish"）

1. 应用全部议定的修改与译者注
2. 重跑阶段 2 检查脚本确认通过
3. 更新进展：`content/chinese/_index.md` 的翻译进展表 + `README.md` 的翻译状态行
4. **回顾（自优化）**：回顾本章整个周期的摩擦点——
   - 检查脚本的误报/漏报（如新专有名词触发残留扫描）→ 调白名单或加检查
   - 反复出现的术语/措辞修正 → 写进 AGENTS.md 或建术语表
   - 流程本身的别扭之处 → 改 SKILL.md
   把 `FEEDBACK.md` 中已采纳的条目提升到对应文件后**从收件箱删除**
5. git 提交（**commit message 用英文**），单章一个 commit，如：`Translate chapter 9 (RAM & CPU Caches): 12 articles`；规则/脚本的修订可并入同一 commit 或单独一个
6. 报告本章篇数与下一章预告
