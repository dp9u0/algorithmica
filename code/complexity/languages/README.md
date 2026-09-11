# 编程语言 —— 矩阵乘法基准测试

对应译文：第 1 章《复杂度模型》之《[编程语言](/content/chinese/hpc/complexity/languages.md)》
原文：https://en.algorithmica.org/hpc/complexity/languages/

同一段 $1024 \times 1024$ 矩阵乘法，用四种方式实现，观察语言/实现方式带来的数量级差异。

| 文件 | 实现 | 原文报告耗时 |
| --- | --- | --- |
| `matmul.py` | 纯 Python 三重循环 | 630 s |
| `Matmul.java` | Java（JIT 编译） | 10 s |
| `matmul.c` | C（`gcc -O3`） | 9 s |
| `matmul.c` + `-march=native -ffast-math` | C（自动向量化） | 0.6 s |
| `matmul_numpy.py` | NumPy（OpenBLAS） | 0.12 s |

原文的 CPU 时钟频率为 1.4GHz（据其推算每次乘法约 880 个周期）。

## 运行

```bash
# Python（纯解释）
python3 matmul.py

# Java
javac Matmul.java && java Matmul

# C —— 先用原文命令，再试优化选项
cc -O3 -o matmul matmul.c && ./matmul
cc -O3 -march=native -ffast-math -o matmul_fast matmul.c && ./matmul_fast

# NumPy（需要 numpy）
python3 matmul_numpy.py
```

## 实测记录

环境：Apple M5（10 核）/ macOS，`gcc` 实为 Apple clang 21，Python 3.9.6 CPython，NumPy 2.0.2（OpenBLAS）。

| 实现 | 原文报告 | 本机实测 | 相对纯 Python |
| --- | --- | --- | --- |
| 纯 Python | 630 s | 110.8 s | 1× |
| C `-O3` | 9 s | 1.66 s | 67× |
| C `-O3 -march=native` | — | 1.74 s | 64× |
| C `-O3 -ffast-math` | — | 1.42 s | 78× |
| C `-O3 -march=native -ffast-math` | 0.6 s（较 `-O3` 快 15×） | 1.55 s | 71× |
| NumPy（OpenBLAS） | 0.12 s | 0.0054 s（稳态；首跑 0.016 s） | 20500× |

反汇编（`otool -tv`）计数：`-O3` 无浮点向量指令，`-ffast-math` 才生成 `fmla`/`fmul`。

这两点与原文不同，均源于工具链差异（GNU GCC + x86 vs Apple clang + ARM）：

1. 原文 `-march=native -ffast-math` 带来 15 倍加速，本机仅约 1.07 倍（噪声范围内）
2. 但核心结论更强：本机四档跨度 20500 倍（原文约 5250 倍），"实现方式带来数量级差异"不因平台改变

## 提示

- 数字应与原文的数量级一致，但**绝对值会因机器不同而不同**——原文强调的正是"渐进复杂度之外，实际性能取决于硬件与实现"
- 复现结果与原文差异较大时，先核对编译选项与 CPU 型号，再考虑作为译者注指出
- NumPy 需先安装（`python3 -m venv venv && venv/bin/pip install numpy`）；无 JDK 时 Java 版跳过
