# Algorithmica 中文版

本仓库是 [algorithmica-org/algorithmica](https://github.com/algorithmica-org/algorithmica) 的 fork，目标是将其英文书籍 *Algorithms for Modern Hardware*（《现代硬件上的算法》）翻译为中文。

- 原作者：[Sergey Slotin](http://sereja.me/) 与 [Tinkoff Generation](https://fintech.tinkoff.ru/study/generation/) 的师生
- 中文翻译与维护：[dp9u0](https://github.com/dp9u0)
- 翻译状态：框架已就绪，按书序逐章翻译中（已完成：第 1 章 复杂度模型；英文版 `models`/`levels` 两篇为作者未完成草稿，暂不翻译）

## 翻译约定

- 中文是默认语言（站点根路径 `/`）；英文在 `/en/`，俄文在 `/ru/`
- 中文内容放在 `content/chinese/`，目录结构与 `content/english/` 完全一致（相同路径的页面会自动互链）
- front matter 只译 `title`；`weight`、`authors` 等保持原样
- 代码块、`$…$` 公式、shortcode、TikZ 图原样保留
- 链接路径规则（render hook 会自动处理）：
  - 正文里的根绝对链接（如 `/hpc/simd`）渲染时自动加当前语言前缀——中文页写成 `/hpc/simd` 即指向 `/hpc/simd`，英文页同样的写法指向 `/en/hpc/simd`
  - 跨语言引用显式写前缀：中文页复用英文图片用 `/en/hpc/…/img/…`；`/en/`、`/ru/`、`/zh/` 开头的路径不会被改写
  - `static/` 下已有的资源（如 `/img/…`）不会被加前缀
- 内部相对链接（`../bandwidth`）保持不动——目标章节未翻译前是 404，翻译完成后自动生效

## 本地开发

```bash
git clone --recurse-submodules https://github.com/dp9u0/algorithmica
cd algorithmica
hugo serve  # http://localhost:1313/zh/
```

需要 [Hugo extended](https://gohugo.io/)（编译 Sass）。中文搜索需要较新浏览器（Chrome/Edge 87+、Safari 14.1+、Firefox 125+，依赖 `Intl.Segmenter` 分词）。

## 与上游同步

```bash
git remote add upstream https://github.com/algorithmica-org/algorithmica.git
git fetch upstream && git merge upstream/master
```

本 fork 对上游的改动刻意保持最小（见 git 历史），以降低合并冲突。

## 版权与许可

- 站点主题代码：MIT，© 2021 Sergey Slotin（见 `themes/algorithmica/LICENSE`）
- 书籍内容：俄文版以 CC BY-SA 4.0 分发；英文 HPC 书未附许可声明，中文翻译已尽量保留原作者署名与原文链接，正式公开发布前建议与原作者确认翻译授权

---

# Algorithmica v3 (upstream)

Algorithmica is an open-access web book dedicated to the art and science of computing.

You can contribute via [Prose](https://prose.io/) by clicking on the pencil icon on the top right on any page or by editing its source directly on GitHub. We use a slightly different Markdown dialect, so if you are not sure that the change is correct (for example, editing an intricate LaTeX formula), you can install [Hugo](https://gohugo.io/) and build the site locally — or just create a pull request, and a preview link will be automatically generated for you.

If you happen to speak Russian, please also read the [contributing guidelines](https://ru.algorithmica.org/contributing/).

---

Key technical changes from the [previous version](https://github.com/algorithmica-org/articles):

* pandoc -> Hugo
* CSS -> Sass
* Github Pages -> Netlify
* Yandex.Metrica -> ~~Google Analytics~~ went back to Metrica
* algorithmica.org/{lang}/* -> {lang}.algorithmica.org/*
* Rich metadata support (language, sections, TOCs, authors...)
* Automated global table of contents
* Theming support
* Search support (Lunr)
