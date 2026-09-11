# 译者代码（your-code）

这里放**译者（dp9u0）在学习过程中编写的验证代码**，用于复现书中的结论、做对照实验，并作为译者注的支撑材料。

与原作者的分工：原作者把完整基准测试代码放在独立仓库 [sslotin/scmm-code](https://github.com/sslotin/scmm-code)，书正文里只内联讲解性片段；本目录是译者自己的实验代码，不替代原作者仓库。

## 目录约定

```
your-code/
├── README.md              # 本文件
└── <chapter-dir>/         # 与 content/english/hpc/<chapter-dir> 同名
    ├── README.md          # 本章实验说明（可选）
    └── <topic>.cpp        # 一个主题一个文件，文件名对应译文里的篇目
```

- 目录名与书章节目录一致（如 `cpu-cache`、`simd`），便于和译文对照
- 文件名对应文章名（如 `cache-lines.cpp` 对应《缓存行》）
- 语言默认 C++，其他语言在文件名或 README 里标明

## 怎么跑

每个目录自包含，能直接编译（示例）：

```bash
c++ -O3 -march=native -o cache-lines cpu-cache/cache-lines.cpp && ./cache-lines
```

建议在文件头注释里写清编译命令和观察到的结果，方便日后回溯。

## 与译文的关联

代码以两种方式进入译文（详见 `AGENTS.md`「译者代码」一节）：

1. **内联片段**：讲解性的一小段代码直接写进译文 md
2. **译者注 + 链接**：成组的实验代码留在本目录，译文里用引用块给出链接：

   ```markdown
   > **译者注**：本节结论我在本地复现验证过，代码见 [your-code/cpu-cache/cache-lines.cpp](https://github.com/dp9u0/algorithmica/blob/master/your-code/cpu-cache/cache-lines.cpp)。
   ```

   链接一律用**绝对 GitHub URL**（指向本仓库 master 分支），因为译文页面和源码文件不在同一路径层级，相对链接不可靠。
