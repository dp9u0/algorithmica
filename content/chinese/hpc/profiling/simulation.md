---
title: 程序模拟
weight: 3
draft: true
---

最后一种剖析方法（或者说一类方法）不是靠实际运行程序来收集数据，而是用专门的工具*模拟*它，分析"应该会发生什么"。

<!--

There are many subcategories of such profilers, differing in which aspect of computation is simulated, but the one we are going to focus on in this section is *machine code analyzers*.

The last approach (or rather a group of them) is not to gather the data by actually running the program, but to analyze what should happen by *simulating* it with specialized tools, which roughly fall into two categories.

-->

这类剖析器也有很多子类，区别在于模拟的是计算的哪个方面。本文将聚焦于[缓存](/hpc/cpu-cache)和[分支预测](/hpc/pipelining/branching)，为此我们使用 [Cachegrind](https://valgrind.org/docs/manual/cg-manual.html)——它是 [Valgrind](https://valgrind.org/) 中面向剖析的部分，而 Valgrind 是内存泄漏检测和内存调试领域一款久经考验的工具。

### 用 Cachegrind 剖析

Cachegrind 本质上是检查二进制文件中的"有意思的"指令——即执行内存读/写和条件/间接跳转的指令——并把它们替换成用软件数据结构模拟相应硬件操作的代码。因此它不需要访问源码，可以处理已经编译好的程序，任何程序都可以像这样跑：

```bash
valgrind --tool=cachegrind --branch-sim=yes ./run
#       also simulate branch prediction ^   ^ any command, not necessarily one process
```

它会对所有涉及的二进制文件插装，运行它们，然后输出一份类似 [perf stat](../events) 的摘要：

```
I   refs:      483,664,426
I1  misses:          1,858
LLi misses:          1,788
I1  miss rate:        0.00%
LLi miss rate:        0.00%

D   refs:      115,204,359  (88,016,970 rd   + 27,187,389 wr)
D1  misses:      9,722,664  ( 9,656,463 rd   +     66,201 wr)
LLd misses:         72,587  (     8,496 rd   +     64,091 wr)
D1  miss rate:         8.4% (      11.0%     +        0.2%  )
LLd miss rate:         0.1% (       0.0%     +        0.2%  )

LL refs:         9,724,522  ( 9,658,321 rd   +     66,201 wr)
LL misses:          74,375  (    10,284 rd   +     64,091 wr)
LL miss rate:          0.0% (       0.0%     +        0.2%  )

Branches:       90,575,071  (88,569,738 cond +  2,005,333 ind)
Mispredicts:    19,922,564  (19,921,919 cond +        645 ind)
Mispred rate:         22.0% (      22.5%     +        0.0%   )
```

我们喂给 Cachegrind 的正是[上一节](../events)用过的同一份示例代码：创建一个含一百万个随机整数的数组，排序，然后在其上执行一百万次二分查找。Cachegrind 给出的数字与 perf 大致相同，只是 perf 实测的内存读取数和分支数略有虚高，这是[推测执行](/hpc/pipelining)所致：这些操作确实在硬件中发生了，因而递增了硬件计数器，但它们的结果被丢弃，并不影响实际性能，模拟中也就把它们忽略了。

Cachegrind 只模拟第一级（数据用 `D1`，指令用 `I1`）和最后一级（`LL`，统一缓存），其参数是从系统中推断出来的。这并不构成任何限制——你也可以从命令行另行设置，比如要模拟 L2 缓存：`--LL=<size>,<associativity>,<line size>`。

到目前为止，它似乎只是拖慢了我们的程序，还没有提供任何 `perf stat` 给不了的信息。要挖掘摘要之外的更多内容，我们可以查看它默认转储到同一目录下的那个剖析信息文件，名为 `cachegrind.out.<pid>`。它是人类可读的，但一般要通过 `cg_annotate` 命令来查看：

```bash
cg_annotate cachegrind.out.4159404 --show=Dr,D1mr,DLmr,Bc,Bcm
#                                    ^ we are only interested in data reads and branches
```

它首先显示运行时所用的参数，包括缓存系统的特性：

```
I1 cache:         32768 B, 64 B, 8-way associative
D1 cache:         32768 B, 64 B, 8-way associative
LL cache:         8388608 B, 64 B, direct-mapped
```

它没有把 L3 缓存搞对：实际上它不是统一的（总共 8M，但单个核心只能看到 4M），而且是 16 路组相联，不过我们暂时忽略这一点。

接下来，它输出一份类似 `perf report` 的逐函数摘要：

```
Dr         D1mr      DLmr Bc         Bcm         file:function
--------------------------------------------------------------------------------
19,951,476 8,985,458    3 41,902,938 11,005,530  ???:query()
24,832,125   585,982   65 24,712,356  7,689,480  ???:void std::__introsort_loop<...>
16,000,000        60    3  9,935,484    129,044  ???:random_r
18,000,000         2    1  6,000,000          1  ???:random
 4,690,248    61,999   17  5,690,241  1,081,230  ???:setup()
 2,000,000         0    0          0          0  ???:rand
```

可以看到，排序阶段有大量分支预测失败，而二分查找阶段则同时有大量 L1 缓存未命中和分支预测失败。这些信息用 perf 是拿不到的——它只能告诉你整个程序的总计数。

Cachegrind 的另一大特色是对源代码的逐行标注。为此，你需要带调试信息（`-g`）编译程序，然后要么明确告诉 `cg_annotate` 要标注哪些源文件，要么直接传 `--auto=yes` 选项，让它标注它能触及的一切（包括标准库的源代码）。

整个"从源码到分析"的流程如下：

```bash
g++ -O3 -g sort-and-search.cc -o run
valgrind --tool=cachegrind --branch-sim=yes --cachegrind-out-file=cachegrind.out ./run
cg_annotate cachegrind.out --auto=yes --show=Dr,D1mr,DLmr,Bc,Bcm
```

由于 glibc 的实现不太可读，为了讲解清楚，我们用自己的二分查找替换 `lower_bound`，它会被标注成这样：

```c++
Dr         D1mr      DLmr Bc         Bcm       
         .         .    .          .         .  int binary_search(int x) {
         0         0    0          0         0      int l = 0, r = n - 1;
         0         0    0 20,951,468 1,031,609      while (l < r) {
         0         0    0          0         0          int m = (l + r) / 2;
19,951,468 8,991,917   63 19,951,468 9,973,904          if (a[m] >= x)
         .         .    .          .         .              r = m;
         .         .    .          .         .          else
         0         0    0          0         0              l = m + 1;
         .         .    .          .         .      }
         .         .    .          .         .      return l;
         .         .    .          .         .  }
```

遗憾的是，Cachegrind 只追踪内存访问和分支。当瓶颈由别的原因造成时，我们需要[其他模拟工具](../mca)。
