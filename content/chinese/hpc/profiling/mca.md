---
title: 机器码分析器
weight: 4
draft: true
---

*机器码分析器*（machine code analyzer）是这样一种程序：它取一小段汇编代码，使用编译器所能获得的信息，在特定微架构上[模拟](../simulation)其执行，输出整个代码块的延迟和吞吐量，以及 CPU 内各种资源的逐周期精确利用率。

### 使用 `llvm-mca`

机器码分析器有很多种，但我个人偏好 `llvm-mca`，你多半可以通过包管理器随 `clang` 一起安装它。你也可以通过一个叫 [UICA](https://uica.uops.info) 的网页工具使用它，或者在 [Compiler Explorer](https://godbolt.org/) 里把语言选成 "Analysis"。

`llvm-mca` 做的事情是：对给定的汇编片段运行设定次数的迭代，并计算每条指令资源使用情况的统计数据，这有助于找出瓶颈所在。

我们用数组求和作为简单的例子：

```asm
loop:
    addl (%rax), %edx
    addq $4, %rax
    cmpq %rcx, %rax
    jne	 loop
````

下面是 `llvm-mca` 针对 Skylake 微架构对它的分析：

```yaml
Iterations:        100
Instructions:      400
Total Cycles:      108
Total uOps:        500

Dispatch Width:    6
uOps Per Cycle:    4.63
IPC:               3.70
Block RThroughput: 0.8
```

它首先输出关于这个循环和硬件的一般信息：

- 它"跑"了这个循环 100 次，总共执行 400 条指令、花了 108 个周期，相当于平均每周期执行 $\frac{400}{108} \approx 3.7$ 条[指令](/hpc/complexity/hardware)（IPC）。
- 这颗 CPU 理论上每周期最多能执行 6 条指令（[发射宽度](/hpc/architecture/layout)）。
- 每个周期理论上平均可以在 0.8 个周期内执行完（[块倒数吞吐量](/hpc/pipelining/tables)）。

> **译者注**：原文此条为 "Each cycle in theory can be executed in 0.8 cycles on average"。结合上方输出中的 `Block RThroughput: 0.8`，作者指的应是"每个（循环体）块"而非"每个周期"，疑为笔误。

- 这里的 "uOps" 指的是 CPU 把每条指令拆分成的微操作（例如融合的 load-add 由两个 uOp 组成）。

接着它给出每条具体指令的信息：

```yaml
Instruction Info:
[1]: uOps
[2]: Latency
[3]: RThroughput
[4]: MayLoad
[5]: MayStore
[6]: HasSideEffects (U)

[1]    [2]    [3]    [4]    [5]    [6]    Instructions:
 2      6     0.50    *                   addl	(%rax), %edx
 1      1     0.25                        addq	$4, %rax
 1      1     0.25                        cmpq	%rcx, %rax
 1      1     0.50                        jne	-11
```

这里面没有任何[指令表](/hpc/pipelining/tables)里没有的东西：

- 每条指令被拆分成多少个 uOp；
- 每条指令需要多少个周期才能完成（延迟）；
- 在摊还意义下，每条指令需要多少个周期完成（倒数吞吐量）——考虑到它的多个副本可以同时执行。

然后它输出可能是最重要的部分——各条指令在何时、何处执行：

```yaml
Resource pressure by instruction:
[0]    [1]    [2]    [3]    [4]    [5]    [6]    [7]    [8]    [9]    Instructions:
 -      -     0.01   0.98   0.50   0.50    -      -     0.01    -     addl (%rax), %edx
 -      -      -      -      -      -      -     0.01   0.99    -     addq $4, %rax
 -      -      -     0.01    -      -      -     0.99    -      -     cmpq %rcx, %rax
 -      -     0.99    -      -      -      -      -     0.01    -     jne  -11
```

由于对执行端口的争用会造成[结构冒险](/hpc/pipelining/hazards)，对于面向吞吐量的循环，端口常常成为瓶颈，这张图有助于诊断原因所在。它给不出那种逐周期完美的甘特图之类的东西，但给出了每条指令所占用的执行端口的汇总统计，让你能找出哪一个端口过载了。

<!--

A CPU is a very complicated thing, but in essence, there are several "ports" that specialize on particular kinds of instructions. These ports often become the bottleneck, and the chart above helps in diagnosing why.

We are not ready to discuss how this works yet, but will talk about it in detail in the last chapter.

-->
