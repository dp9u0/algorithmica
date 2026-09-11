---
title: 编程语言
aliases:
  - /hpc/analyzing-performance
weight: 2
---

如果你正在读这本书，那么在你的计算机科学之旅中，多半有过某个瞬间开始在意代码的效率。

我的是在高中：那时我意识到，做网站、写"有用"的程序是考不上大学的，于是踏入了算法竞赛这个激动人心的世界。我的编程水平还行——至少对一个高中生而言——但在此之前我从没认真想过我的代码要跑多久。突然间这变得重要起来：每道题现在都有严格的时间限制。我开始数我的操作。一秒钟能做多少个？

要回答这个问题，我当时对计算机体系结构知之甚少。但我也不需要正确答案——我需要一条经验法则。我的推理过程是："2–3GHz 意味着每秒执行 20 到 30 亿条指令，而在一个对数组元素做点什么的简单循环里，我还得递增循环计数器、判断循环结束条件、做数组索引之类，那就在每个有用操作之外再留 3–5 条指令的余量"，最后我采用 $5 \cdot 10^8$ 作为估计值。这些说法没有一句是对的，但"数出算法需要的操作数再除以这个数"对我的用例来说是个不错的经验法则。

真实的答案当然要复杂得多，而且高度取决于你心目中的"操作"是什么。它可以是[指针追逐](/hpc/cpu-cache/latency)这类低至 $10^7$ 的操作，也可以是 [SIMD 加速](/hpc/simd)的线性代数这种高达 $10^{11}$ 的操作。为了展示这种悬殊的差异，我们将用不同语言实现矩阵乘法作为案例研究——并深入计算机是如何执行它们的。

<!--

Because of this logic, and also because of the [computation model](../) postulated in CS 101, many programmers have a misconception that computers can execute a certain number of "operations" per second, and that using different programming languages has some sort of [multiplier effect](https://benchmarksgame-team.pages.debian.net/benchmarksgame/index.html) on that number:

- "you can execute about $5 \cdot 10^8$ operations per second on this machine,"
- "C is 2 times faster than Java,"
- "Python is 100x slower than C++."

-->

## 语言的类型

<!--

Processors can be thought of as *state machines*. They keep their *state* in several fixed-length *registers*, one of which, the instruction pointer, indicates a memory location of the next instruction to be read and executed. This instruction somehow modifies the registers and moves the instruction pointer to the next instruction to be executed, and so on.

These instructions — called *machine code* — are binary encoded, quirky and very difficult to work with, so no sane person writes them directly nowadays. Instead, we use higher-level programming languages and employ alternative means to feed instructions to the processor.

-->

在最底层，计算机执行由二进制编码的*指令*组成的*机器码*，用来控制 CPU。机器码专属于特定硬件、行为古怪，与之共事需要极大的智力投入，因此人们造出计算机之后最先做的事情之一就是创造*编程语言*——把计算机运作方式的某些细节抽象掉，简化编程过程。

编程语言本质上只是一个接口。用任何语言写出的程序都只是一种更友好高层表示，最终仍需在某个时刻转换成机器码才能在 CPU 上执行——而实现这种转换有好几种不同的途径：

- 从程序员视角看，语言分两类：*编译型*——执行前先做预处理；*解释型*——运行时由一个叫*解释器*的独立程序执行。
- 从计算机视角看，语言也分两类：*原生*（native）——直接执行机器码；*托管*（managed）——依赖某种*运行时*来执行。

既然在解释器里跑机器码没有意义，语言总共就分三种：

- 解释型语言，如 Python、JavaScript、Ruby。
- 带运行时的编译型语言，如 Java、C#、Erlang（以及运行在它们 VM 之上的语言，如 Scala、F#、Elixir）。
- 编译型原生语言，如 C、Go、Rust。

执行计算机程序没有"正确"的方式：每种方法各有收益与代价。解释器和虚拟机提供了灵活性，带来动态类型、运行时修改代码、自动内存管理等不错的高级特性，但也不可避免地伴随着性能代价——我们这就来谈谈。

### 解释型语言

下面是一个纯 Python 的按定义实现的 $1024 \times 1024$ 矩阵乘法：

```python
import time
import random

n = 1024

a = [[random.random()
      for row in range(n)]
      for col in range(n)]

b = [[random.random()
      for row in range(n)]
      for col in range(n)]

c = [[0
      for row in range(n)]
      for col in range(n)]

start = time.time()

for i in range(n):
    for j in range(n):
        for k in range(n):
            c[i][j] += a[i][k] * b[k][j]

duration = time.time() - start
print(duration)
```

这段代码跑 630 秒。超过 10 分钟！

我们给这个数字找找参照。运行它的 CPU 时钟频率是 1.4GHz，即每秒 $1.4 \cdot 10^9$ 个周期，整个计算合计接近 $10^{15}$ 个周期——最内层循环里每次乘法约 880 个周期。

如果想想 Python 为了搞明白程序员的意图都得做些什么，这就不奇怪了：

- 解析表达式 `c[i][j] += a[i][k] * b[k][j]`；
- 试图弄清 `a`、`b`、`c` 是什么，在带类型信息的特殊哈希表里查这些名字；
- 得知 `a` 是个列表，取出它的 `[]` 运算符，取得 `a[i]` 的指针，发现它也是个列表，再取一次 `[]` 运算符，拿到 `a[i][k]` 的指针，最后才拿到元素本身；
- 查它的类型，发现是 `float`，取出实现 `*` 运算符的方法；
- 对 `b` 和 `c` 重复以上全部，最后把结果加赋给 `c[i][j]`。

诚然，Python 这类广泛使用的语言的解释器已经优化得很好，在同一段代码反复执行时可以跳过其中一些步骤。但由于语言设计本身，相当可观的开销仍然不可避免。如果能去掉所有这些类型检查和指针追逐，我们能不能把每次乘法的周期数压到接近 1，或者说接近原生乘法的"成本"？

### 托管语言

同样的矩阵乘法过程，用 Java 实现：

```java
import java.util.Random;

public class Matmul {
    static int n = 1024;
    static double[][] a = new double[n][n];
    static double[][] b = new double[n][n];
    static double[][] c = new double[n][n];

    public static void main(String[] args) {
        Random rand = new Random();

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                a[i][j] = rand.nextDouble();
                b[i][j] = rand.nextDouble();
                c[i][j] = 0;
            }
        }

        long start = System.nanoTime();

        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                for (int k = 0; k < n; k++)
                    c[i][j] += a[i][k] * b[k][j];

        double diff = (System.nanoTime() - start) * 1e-9;
        System.out.println(diff);
    }
}
```

现在跑 10 秒，折合每次乘法约 13 个 CPU 周期——比 Python 快 63 倍。考虑到我们需要从内存中非顺序地读取 `b` 的元素，这个运行时间已经大致是"应该有的"水平了。

Java 是*编译型*但非*原生*的语言。程序先编译成*字节码*，再由虚拟机（JVM）解释执行。为了达到更高性能，频繁执行的部分（比如最内层的 `for` 循环）会在运行期间编译成机器码，之后几乎零开销地执行。这项技术叫*即时编译*（just-in-time compilation，JIT）。

JIT 编译不是语言本身的特性，而是其实现的特性。Python 也有 JIT 编译的实现叫 [PyPy](https://www.pypy.org/)，不做任何代码改动，跑上面的程序约需 12 秒。

### 编译型语言

现在轮到 C：

```cpp
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

#define n 1024
double a[n][n], b[n][n], c[n][n];

int main() {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            a[i][j] = (double) rand() / RAND_MAX;
            b[i][j] = (double) rand() / RAND_MAX;
        }
    }

    clock_t start = clock();

    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                c[i][j] += a[i][k] * b[k][j];

    float seconds = (float) (clock() - start) / CLOCKS_PER_SEC;
    printf("%.4f\n", seconds);

    return 0;
}
```

用 `gcc -O3` 编译后跑 9 秒。

看起来提升不大——比 Java 和 PyPy 快的那 1–3 秒可以归功于省掉的 JIT 编译时间——但我们还没用上 C 更好的编译器生态。加上 `-march=native` 和 `-ffast-math` 选项，时间骤降到 0.6 秒！

这里发生的事情是：我们向编译器[告知](/hpc/compilation/flags/)了正在使用的 CPU 的确切型号（`-march=native`），并给了它重排[浮点计算](/hpc/arithmetic/float)的自由（`-ffast-math`），于是编译器利用这些信息，用[向量化](/hpc/simd)实现了加速。

并不是说 PyPy 和 Java 的 JIT 编译器不可能在不大改源代码的情况下调校到同样的性能，但对直接编译成原生代码的语言来说，这确实更容易。

> **译者注**：原文的 15 倍加速基于 GNU GCC + x86。在 Apple Silicon + Apple clang 上实测，`-O3` 已不再自动向量化（反汇编无 `fmla`/`fmul`），加 `-ffast-math` 后才生成向量指令，耗时仅从 1.66s 降到 1.55s——**具体倍数高度依赖编译器与平台，但"编译器优化带来数量级差异"这一结论不变**：同一台机器上，纯 Python 110.8s、C `-O3` 1.66s、NumPy（OpenBLAS）0.0054s，跨度 20500 倍。复现代码与完整实测数据见 [code/complexity/languages/](https://github.com/dp9u0/algorithmica/blob/master/code/complexity/languages/README.md)。

### BLAS

最后，看看专家级优化实现的能力。我们测试一个广泛使用的优化线性代数库 [OpenBLAS](https://www.openblas.net/)。最简单的用法是回到 Python，通过 `numpy` 调用它：

```python
import time
import numpy as np

n = 1024

a = np.random.rand(n, n)
b = np.random.rand(n, n)

start = time.time()

c = np.dot(a, b)

duration = time.time() - start
print(duration)
```

现在只需约 0.12 秒：比自动向量化的 C 版本快约 5 倍，比最初的 Python 实现快约 5250 倍！

通常你见不到这么戏剧性的提升。目前我们还讲不清这具体是怎么做到的。OpenBLAS 的稠密矩阵乘法实现通常是[5000 行手写汇编](https://github.com/xianyi/OpenBLAS/blob/develop/kernel/x86_64/dgemm_kernel_16x2_haswell.S)，并针对*每一种*体系结构单独调校。在后面的章节里，我们会逐一讲解所有相关技术，然后[回到](/hpc/algorithms/matmul)这个例子，用不到 40 行 C 写出我们自己的 BLAS 级实现。

### 要点

这一节的关键教训是：使用原生、底层的语言并不必然给你性能；但它给你对性能的*控制权*。

与"每秒 N 个操作"这个简化模型相伴，许多程序员还有另一个误解：用不同的编程语言会以某种倍率作用于这个数字。这样思考、并按性能[给语言排名](https://benchmarksgame-team.pages.debian.net/benchmarksgame/index.html)没有太大意义：编程语言本质上只是工具，用*让渡一部分*性能控制权来换取便利的抽象。无论执行环境如何，把硬件提供的机会用足，在很大程度上仍然是程序员自己的工作。
