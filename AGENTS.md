# AGENTS.md — Algorithmica 中文翻译项目约定

本仓库是 [algorithmica-org/algorithmica](https://github.com/algorithmica-org/algorithmica) 的中文翻译 fork。上游已停止维护，本仓库为独立延续项目。所有翻译和站点改动遵循以下规则。

**内容版图与规划见 `PLAN.md`**：英文书（未完成，卷 I 69 篇已发布，卷 II/III 整部草稿）与俄文四册（cs 册 119 篇已发布，math/ml/dl 整册草稿）是两套无重叠的内容。草稿处理方向已定（草稿译本 + 二次编辑、译者补写，分级见 PLAN §1）：草稿原文随章译出、打草稿标记、译文不发布（见下"内容规则·草稿译本"）；二次编辑与发布时点、译者补写流程按 PLAN §2 剩余约定推进。

## 构建与验证

- Hugo 0.166+（`hugo --gc --minify` 构建，`hugo serve` 本地预览；中文默认语言在根路径，en 在 `/en/`，ru 在 `/ru/`）
- 任何改动后运行构建确认无错误；涉及内容的改动需在本地 server 上目检渲染效果（公式、代码块、图片、目录）

## 翻译规则

### 链接规则（重点）

1. **上游引用用原项目地址**：书页译文里原文提到项目仓库、issue、原作者个人页时（如"材料托管在 GitHub"、"创建 issue"、FAQ 里的链接），保持指向原地址（`github.com/algorithmica-org/algorithmica`、`sereja.me` 等），不改指到本 fork。
   **例外——站点首页（`content/chinese/_index.md`）是译者导航页**，不是译文：issue 与 PR 指向本 fork（`dp9u0/algorithmica`），同时明确列出原项目仓库、英文官网（en.algorithmica.org）、俄文官网（ru.algorithmica.org）和本站仓库；原文问题引导到原项目仓库反馈。
2. **页头"译文"互链指向官方原站**：文章头部 en/ru 译文链接渲染为 `https://en.algorithmica.org/…`、`https://ru.algorithmica.org/…`（模板 `header.html` 已实现，勿改回站内地址）；zh 译文链接指向本站。
3. **译文正文链接一律站内**：章节互链、图片引用等使用本站路径，不外链官方站。写法见下"路径写法"。

站点部署在 **GitHub Pages 项目站**，地址是 `https://dp9u0.github.io/algorithmica/`——所有 URL 必须带 `/algorithmica` 子路径前缀。

### 路径写法（render hook 自动处理前缀）

- 根绝对路径（`/hpc/simd`）= 当前语言的树：中文页渲染为 `/algorithmica/hpc/simd`，英文页渲染为 `/algorithmica/en/hpc/simd`
- 跨语言引用显式写前缀：中文页复用英文图片写 `/en/hpc/…/img/…`（`/en/`、`/ru/`、`/zh/` 开头不改写）
- `static/` 已有资源（如 `/img/…`）不加语言前缀，但仍会带 `/algorithmica` 子路径
- 未翻译目标用相对路径（`../bandwidth`），翻译完成自动生效

### ⚠️ 子路径陷阱（改模板/内容时必读）

`hugo serve` 从站点根提供服务，**会掩盖子路径 bug**——链接在本地正常、上线后 404。改任何链接/资源路径后必须跑 `check_urls.py`（已并入检查脚本）。

两条硬规则：

1. **模板里不要写裸的根绝对路径**（`href='/foo'`、`src='/icons/x.svg'`）。用 `{{ "foo" | relURL }}`。
2. **`relURL` 对以 `/` 开头的输入原样返回**（不加前缀）。所以参数必须**不带前导斜杠**：`{{ "icons/x.svg" | relURL }}` 对，`{{ "/icons/x.svg" | relURL }}` 错。

历史教训：blog 侧边栏标题、静态资源、render hook 输出的语言前缀路径都曾因此漏掉子路径，导致图标缺失、图片不显示、左上角链接跳错站。

### 内容规则

- 中文放 `content/chinese/`，目录结构与 `content/english/` 完全一致（相同路径自动互译关联）
- front matter 只译 `title`、`menuTitle`、`part`（三者都会展示给读者：页面标题、侧边栏分册缩写、侧边栏部分名）；`weight`、`authors`、`prerequisites`、`aliases` 等保持原样
- **草稿译本**：原文 front matter 带 `draft: true`（原作者写就但未发布，官方站上没有该页——页头"译文"链接与官方原文链接均为死链）的篇目照常翻译，但 `title`（及 `menuTitle`，如有）加 `[草稿]` 前缀（如 `[草稿]哈希表`），且译文的 `draft: true` **永久保留**——不随章节 finish 发布，仅本地 `hugo serve -D` 可见；对照原文用上游源文件（`github.com/algorithmica-org/algorithmica/blob/master/content/english/hpc/…`）
- 代码块、`$…$` / `$$…$$` 公式、shortcode、TikZ 块**原样保留**，代码注释可不译
- 人名、术语首次出现时可括注原文，如"缓存行（cache line）"
- **译出的标题一律带英文显式锚点**：`### 循环展开 {#loop-unrolling}`——slug 取自英文原标题（小写、空格转 `-`、去标点）。中文标题会改变 Goldmark 自动锚点，不加则跨章 `#fragment` 链接静默失效；检查脚本第 [7] 步校验全部 fragment

### 语义分级（硬约束）

- **开场页**（`content/chinese/_index.md`、`content/chinese/hpc/_index.md`）是译者导航页，可改编：讲清本站定位、各方链接、翻译进展
- **正式章节必须忠实原文，不改写**：作者的第一人称、玩笑、行文节奏、举例全部保留；宁可直译得不优雅，不擅自"改进"；数字、倍数、结论逐一对照

### 译者注

三类情况可加注，**克制使用**（一章通常 0–2 条；讨论沉淀类宁缺毋滥，读者是来读原文的）；格式为紧跟相关段落的引用块 `> **译者注**：…`：

1. 原文内容对本翻译站语境不适用（作者请求资助、"本书今夏发布"等以原书身份的表述）
2. 原文疑似理论/事实错误——**不修改原文**，加注指出
3. 有价值的讨论沉淀：审读中经用户确认值得保留的展开（实验复现、平台差异、概念延伸等）；有配套代码时附 `code/` 链接

第 3 类由用户决定取舍——译者不自行判断"有价值"就加注。

### 译者代码

译者的验证/实验代码放仓库根的 `code/`（不在 `content/` 内，否则会被 Hugo 当内容处理），目录名与书章节目录一致。原作者把完整代码放在独立仓库 [sslotin/scmm-code](https://github.com/sslotin/scmm-code)，书正文只内联讲解性片段；本目录是译者自己的实验代码。

代码进入译文有两种方式：

1. **内联片段**：讲解性的一小段代码直接写进译文（与原书做法一致）
2. **译者注 + 链接**：成组的实验代码留在 `code/`，译文里用引用块给出链接。链接用**绝对 GitHub URL** 指向本仓库 master 分支（译文页面与源码路径层级不同，相对链接不可靠），如：
   ```markdown
   > **译者注**：本节结论我在本地复现验证过，代码见 [code/cpu-cache/cache-lines.cpp](https://github.com/dp9u0/algorithmica/blob/master/code/cpu-cache/cache-lines.cpp)。
   ```

复现代码写清编译命令与观察结果（文件头注释或目录 README）；结论与原文不一致时，优先怀疑自己的实验，确认无误再作为译者注指出。

### Git

- commit message 用**英文**；单章一个 commit，如 `Translate chapter 2 (Computer Architecture): 11 articles`

### 翻译流程

使用 skill：`/translate-chapter [<chapter-dir>]`（翻译+检查+自查+交审读）、`/translate-chapter finish`（用户确认后更新进展并提交）。机械检查脚本：`.claude/skills/translate-chapter/scripts/check_translation.py`。

## 署名

- 页脚已含原作者版权 + 中文翻译署名（`i18n/zh.toml`），新增页面无需单独处理
- 中文首页的译者信息引用块保留 fork 与原项目双链接
