---
title: 指令级并行
weight: 3
draft: true
---

程序员听到*并行*（parallelism）这个词时，大多想到的是*多核并行*（multi-core parallelism）——把一个计算显式地拆成若干半独立的*线程*（thread），让它们协作解决同一个问题。

这类并行主要着眼于降低*延迟*、实现*可扩展性*，却无助于提升*效率*。用并行算法确实能解决大上十倍的问题，但至少也要消耗十倍的计算资源。尽管并行硬件正变得[越来越普及](/hpc/complexity/hardware)，并行算法设计也日益成为重要的研究领域，眼下我们仍把自己限制在单个 CPU 核心之内。

但还有另一些并行，就藏在 CPU 核心内部，可以*免费*取用。

<!--

This technique only applies 

Parallel hardware is now everywhere. When you opened this page in your browser, it was retrieved by a 50-core server CPU, then parsed by an 8-core desktop CPU, and then rendered by a 400-core GPU. Not all cores were involved with serving you this page at all times — they might have been doing something else.

Parallelism helps in reducing *latency*. It is important, but for now, our main concern is not *scalability*, but *efficiency* of algorithms.

Sharing computations is an art in itself, but for now, we want to learn how to use resources that we already have more efficiently.

While multi-core parallelism is "cheating," many form of parallelism exist "for free."

Adapting algorithms for parallel hardware is important for achieving *scalability*. In the first part of this book, we will consider this technique "cheating." We only do optimizations that are truly free, and preferably don't take away resources from other processes that might be running concurrently.

-->

### 指令流水线

要执行*任何一条*指令，处理器都得先做大量准备工作，包括：

- 从内存中**取指**（fetch）一段机器码，
- 将其**译码**（decode）并拆分成一条条指令，
- **执行**这些指令——其中可能涉及一些**内存**操作，以及
- 把结果**写回**寄存器。

这一整套操作序列相当*漫长*。哪怕只是把两个存在寄存器里的值 `add` 到一起，也要花多达 15-20 个 CPU 周期。为了隐藏这段延迟，现代 CPU 使用*流水线*（pipelining）：一条指令通过第一阶段后，立刻开始处理下一条，不必等前一条完全执行完毕。

![](/en/hpc/pipelining/img/pipeline.png)

流水线并没有降低*实际*延迟，只是在功能上让它看起来仿佛只由执行和访存阶段组成。这 15-20 个周期你照样得付，只不过在找到要执行的那段指令序列之后付一次就够了。

有鉴于此，硬件厂商更喜欢用*每指令周期数*（cycles per instruction，CPI）而不是"平均指令延迟"之类的指标，作为 CPU 设计的主要性能指标。如果只统计*有用*的指令，它对算法设计而言也是个[相当不错的指标](/hpc/profiling/benchmarking)。

完美流水线化的处理器，其 CPI 应趋近于 1；但要是把流水线的每一级都复制一份使其变"宽"、让同一时间能处理不止一条指令，CPI 实际还能更低。由于缓存和大部分算术逻辑单元（ALU）都可以共享，这比添加一个完整的独立核心便宜得多。这种每周期能执行多条指令的架构称为*超标量*（superscalar）架构，而大多数现代 CPU 都是超标量的。

只有当指令流里含有若干组逻辑上相互独立、可以分开处理的操作时，超标量处理的优势才能发挥出来。指令并不总是以最方便的顺序到来，因此只要可能，现代 CPU 会*乱序*（out of order）执行它们，以提高整体利用率、尽量减少流水线停顿。这套魔法究竟如何运转，是更高级讨论的话题<!--[a more advanced discussion](scheduling)-->；眼下你只需假设：CPU 维护着一个缓冲区，存放着往后一定距离内的待执行指令，一旦某条指令的操作数已算出、且有空闲的执行单元，就立即执行它。

### 一个教育系统的类比

想想我们的教育体系是怎么运转的：

1. 课程按学生群体而非个人讲授，因为把同样的内容一次性广播给所有人效率更高。
2. 一届学生被分成多个班组，由不同的老师带领；作业和其他课程资料在各组之间共享。
3. 每年都把同一门课教给新一届学生，好让老师们始终有事可忙。

这些创新极大提升了整个系统的*吞吐量*（throughput），尽管*延迟*（某个学生从入学到毕业的时间）并没有改变（甚至还可能略微增加，因为一对一辅导其实更有效）。

你可以从中找到许多与现代 CPU 的对应：

1. CPU 用 [SIMD 并行](/hpc/simd)对一整块不同的数据（由 16、32 或 64 字节组成）执行同一个操作。
2. CPU 有多个执行单元，可以同时处理这些指令，并共享 CPU 的其他设施（通常是 2-4 个执行单元）。
3. 指令以流水线方式处理（省下的周期数，大致相当于从幼儿园到博士毕业之间的年数）。

<!-- You can continue "up:" there are multiple school branches (cores), multiple schools (computers), etc. -->

除此之外，还有几个方面也对得上：

- 执行路径随时间推移愈发分化，需要不同的执行单元。
- 有些指令可能因种种原因停顿。
- 有些指令甚至被推测执行（提前执行），随后又被丢弃。
- 有些指令可能被拆成若干可以独立推进的微操作。

为流水线和超标量处理器编程有其独特的挑战，本章就来逐一应对。
