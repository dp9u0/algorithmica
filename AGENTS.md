# AGENTS.md — Algorithmica 中文翻译项目约定

本仓库是 [algorithmica-org/algorithmica](https://github.com/algorithmica-org/algorithmica) 的中文翻译 fork。上游已停止维护，本仓库为独立延续项目。所有翻译和站点改动遵循以下规则。

## 构建与验证

- Hugo 0.166+（`hugo --gc --minify` 构建，`hugo serve` 本地预览；中文默认语言在根路径，en 在 `/en/`，ru 在 `/ru/`）
- 任何改动后运行构建确认无错误；涉及内容的改动需在本地 server 上目检渲染效果（公式、代码块、图片、目录）

## 翻译规则

### 链接规则（重点）

1. **上游引用用原项目地址**：书页译文里原文提到项目仓库、issue、原作者个人页时（如"材料托管在 GitHub"、"创建 issue"、FAQ 里的链接），保持指向原地址（`github.com/algorithmica-org/algorithmica`、`sereja.me` 等），不改指到本 fork。
   **例外——站点首页（`content/chinese/_index.md`）是译者导航页**，不是译文：issue 与 PR 指向本 fork（`dp9u0/algorithmica`），同时明确列出原项目仓库、英文官网（en.algorithmica.org）、俄文官网（ru.algorithmica.org）和本站仓库；原文问题引导到原项目仓库反馈。
2. **页头"译文"互链指向官方原站**：文章头部 en/ru 译文链接渲染为 `https://en.algorithmica.org/…`、`https://ru.algorithmica.org/…`（模板 `header.html` 已实现，勿改回站内地址）；zh 译文链接指向本站。
3. **译文正文链接一律站内**：章节互链、图片引用等使用本站路径，不外链官方站。写法见下"路径写法"。

### 路径写法（render hook 自动处理前缀）

- 根绝对路径（`/hpc/simd`）= 当前语言的树：中文页渲染为 `/hpc/simd`，英文页渲染为 `/en/hpc/simd`
- 跨语言引用显式写前缀：中文页复用英文图片写 `/en/hpc/…/img/…`（`/en/`、`/ru/`、`/zh/` 开头不改写）
- `static/` 已有资源（如 `/img/…`）不加前缀
- 未翻译目标用相对路径（`../bandwidth`），翻译完成自动生效

### 内容规则

- 中文放 `content/chinese/`，目录结构与 `content/english/` 完全一致（相同路径自动互译关联）
- front matter 只译 `title`、`menuTitle`、`part`（三者都会展示给读者：页面标题、侧边栏分册缩写、侧边栏部分名）；`weight`、`authors`、`prerequisites`、`aliases` 等保持原样
- 代码块、`$…$` / `$$…$$` 公式、shortcode、TikZ 块**原样保留**，代码注释可不译
- 人名、术语首次出现时可括注原文，如"缓存行（cache line）"

### 语义分级（硬约束）

- **开场页**（`content/chinese/_index.md`、`content/chinese/hpc/_index.md`）是译者导航页，可改编：讲清本站定位、各方链接、翻译进展
- **正式章节必须忠实原文，不改写**：作者的第一人称、玩笑、行文节奏、举例全部保留；宁可直译得不优雅，不擅自"改进"；数字、倍数、结论逐一对照

### 译者注

仅两类情况加注，克制使用；格式为紧跟相关段落的引用块 `> **译者注**：…`：

1. 原文内容对本翻译站语境不适用（作者请求资助、"本书今夏发布"等以原书身份的表述）
2. 原文疑似理论/事实错误——**不修改原文**，加注指出

另一来源是用户审读时的讨论沉淀：用户认为值得保留的讨论，按上述格式插入合适位置。

### Git

- commit message 用**英文**；单章一个 commit，如 `Translate chapter 2 (Computer Architecture): 11 articles`

### 翻译流程

使用 skill：`/translate-chapter [<chapter-dir>]`（翻译+检查+自查+交审读）、`/translate-chapter finish`（用户确认后更新进展并提交）。机械检查脚本：`.claude/skills/translate-chapter/scripts/check_translation.py`。

## 署名

- 页脚已含原作者版权 + 中文翻译署名（`i18n/zh.toml`），新增页面无需单独处理
- 中文首页的译者信息引用块保留 fork 与原项目双链接
