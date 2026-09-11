---
title: 现代硬件上的算法
menuTitle: HPC
weight: 5
#authors:
#- Sergey Slotin
#created: "Feb 2021"
#date: 2021-09-16
noToc: true
---

这是一本即将完成的高性能计算书籍——《现代硬件上的算法》（Algorithms for Modern Hardware），作者是 [Sergey Slotin](http://sereja.me/)。本站为其中文翻译版。

它的目标读者非常广泛：从性能工程师、实用算法研究者，到刚修完高级算法课程、想学习比把 $O(n \log n)$ 优化到 $O(n \log \log n)$ 更实际的程序加速方法的计算机专业本科生。

本书全部材料[托管在 GitHub](https://github.com/algorithmica-org/algorithmica) 上，示例代码在[单独的仓库](https://github.com/sslotin/scmm-code)中。这不是一个协作式项目，但非常欢迎任何贡献与反馈。

### 常见问题

**纠错。** 如果你在任何页面上发现错误，请按以下优先级任选其一：

- 直接修复：点击任意页面右上角的铅笔图标，在 GitHub 上编辑页面源码并提交（源码链接同样在右上角）；
- 在 [GitHub 上创建 issue](https://github.com/algorithmica-org/algorithmica/issues)；
- [联系原作者](http://sereja.me/)；

或者在其他讨论本书的网站上留言——原作者会关注 [HackerNews](https://news.ycombinator.com/from?site=algorithmica.org)、[CodeForces](https://codeforces.com/profile/sslotin) 和 [Twitter](https://twitter.com/sergey_slotin) 上被提及的大部分讨论。

**发布日期。** 本书分为若干部分，作者计划按顺序完成，各部分之间会有较长间隔。第一部分"性能工程"截至 2022 年 3 月已完成约 75%，原计划当年夏天超过 95%。

对这样一本开源书籍而言，"发布"实质上意味着：

- 完成所有核心章节并填补所有 TODO；
- 基本冻结目录（案例研究章节除外）；
- 做最后一轮深度文字编辑（希望能有专业编辑帮忙——原作者至今没搞明白英语逗号怎么用）；
- 绘制插图（目前的插图不少是"借"来的）；
- 制作适合打印的 PDF 并找到最佳分发方式。

在那之后，主要是修错，以及根据技术变化和新算法进展做一些小修改。电子书/纸质版很可能以"随心付"（pay what you want）方式销售，且网页版将永远完全免费在线阅读。

**预订 / 资助本书。** 由于作者的国籍和出生地，你无法直接资助——除非找到一种既符合国际制裁、又不资助[战争](https://en.wikipedia.org/wiki/2022_Russian_invasion_of_Ukraine)、还不会让作者因逃税入狱的方式。

所以，不必费心。如果你想支持这本书，把它分享出去、帮忙修修错别字就足够了。

> **译者注**：本节为原作者的个人说明，资助渠道针对原书，与中文翻译站无关；原书网页版始终免费在线阅读。

**翻译。** 网站有专门的机制来创建和管理翻译——已有好心人联系原作者，愿意把书翻译成意大利语和中文（作者本人也会把至少一部分翻译成他的母语俄语）。

> **译者注**：本站即此处所述的中文翻译。

不过，由于本书仍在演进，至少在第一部分完成之前开始翻译可能不是最好的时机。话虽如此，非常鼓励你翻译任何单篇文章并发布在自己的博客里——只需把链接发给原作者，等集中式翻译启动时可以合并回去。

**关于俄文版的"翻译"。** [ru.algorithmica.org/cs/](https://ru.algorithmica.org/cs/) 上的文章并非讲高级性能工程，而主要是经典计算机科学算法——不讨论超出渐进复杂度之外的加速手段。那里的信息大多不是独有的，互联网上其他地方已有英文版本，例如风格相近的 [cp-algorithms.com](https://cp-algorithms.com/)。

**在高校教授性能工程。** 作者写这本书的目标之一，是改变计算机科学——更准确地说，算法设计——在高校的授课方式。展开说说。

有两本影响深远的教材，是大多数计算机科学课程的基础。它们无疑都是杰出的，但[其中一本](https://en.wikipedia.org/wiki/The_Art_of_Computer_Programming)已有 50 年历史，[另一本](https://en.wikipedia.org/wiki/Introduction_to_Algorithms)也有 30 年了，而[此后的计算机早已天翻地覆](/en/hpc/complexity/hardware)。渐进复杂度不再是唯一的决定因素。在现代实用算法设计中，你会选择更能利用硬件各类并行特性的方法，而不是那个在星系级输入规模下理论原始操作数更少的方法。

然而，大多数高校的计算机科学课程完全忽视了这一转变。尽管有一些旨在纠偏的优秀课程——如 MIT 的"[Performance Engineering of Software Systems](https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-172-performance-engineering-of-software-systems-fall-2018/)"、阿尔托大学（Aalto University）的"[Programming Parallel Computers](https://ppc.cs.aalto.fi/)"，以及 Denis Bakhvalov 的非学术课程"[Performance Ninja](https://github.com/dendibakh/perf-ninja)"——大多数计算机科学毕业生仍然把现代硬件当成 1990 年代的东西。

作者真正想实现的，是让性能工程在算法导论之后立即开课。写这个领域的第一本系统教材是其中重要一环，这也是作者急于在夏天前完成本书、好让高校在下一个学年采用它的原因。但开设一门新课程需要的远不止教材：还需要平衡的课程大纲、课程基础设施、讲义幻灯片、实验作业……因此在完成主体书籍之后的一段时间里，作者将致力于*教授*性能工程的课程材料和工具——也期待与更多想把它变为现实的人合作。

### 第一部分：性能工程

第一部分讲计算机体系结构基础和单线程算法优化。

它依次介绍 CPU 优化的主要主题——缓存、SIMD、流水线等——并给出简短的 C++ 示例，随后是大型案例研究，我们通常会在其中相对某个 STL 算法或数据结构取得显著加速。

规划目录：

```
0. Preface
1. Complexity Models
 1.1. Modern Hardware
 1.2. Programming Languages
 1.3. Models of Computation
 1.4. When to Optimize
2. Computer Architecture
 1.1. Instruction Set Architectures
 1.2. Assembly Language
 1.3. Loops and Conditionals
 1.4. Functions and Recursion
 1.5. Indirect Branching
 1.6. Machine Code Layout
 1.7. System Calls
 1.8. Virtualization
3. Instruction-Level Parallelism
 3.1. Pipeline Hazards
 3.2. The Cost of Branching
 3.3. Branchless Programming
 3.4. Instruction Tables
 3.5. Instruction Scheduling
 3.6. Throughput Computing
 3.7. Theoretical Performance Limits
4. Compilation
 4.1. Stages of Compilation
 4.2. Flags and Targets
 4.3. Situational Optimizations
 4.4. Contract Programming
 4.5. Non-Zero-Cost Abstractions
 4.6. Compile-Time Computation
 4.7. Arithmetic Optimizations
 4.8. What Compilers Can and Can't Do
5. Profiling
 5.1. Instrumentation
 5.2. Statistical Profiling
 5.3. Program Simulation
 5.4. Machine Code Analyzers
 5.5. Benchmarking
 5.6. Getting Accurate Results
6. Arithmetic
 6.1. Floating-Point Numbers
 6.2. Interval Arithmetic
 6.3. Newton's Method
 6.4. Fast Inverse Square Root
 6.5. Integers
 6.6. Integer Division
 6.7. Bit Manipulation
(6.8. Data Compression)
7. Number Theory
 7.1. Modular Inverse
 7.2. Montgomery Multiplication
(7.3. Finite Fields)
(7.4. Error Correction)
 7.5. Cryptography
 7.6. Hashing
 7.7. Random Number Generation
8. External Memory
 8.1. Memory Hierarchy
 8.2. Virtual Memory
 8.3. External Memory Model
 8.4. External Sorting
 8.5. List Ranking
 8.6. Eviction Policies
 8.7. Cache-Oblivious Algorithms
 8.8. Spacial and Temporal Locality
(8.9. B-Trees)
(8.10. Sublinear Algorithms)
(9.13. Memory Management)
9. RAM & CPU Caches
 9.1. Memory Bandwidth
 9.2. Memory Latency
 9.3. Cache Lines
 9.4. Memory Sharing
 9.5. Memory-Level Parallelism
 9.6. Prefetching
 9.7. Alignment and Packing
 9.8. Pointer Alternatives
 9.9. Cache Associativity
 9.10. Memory Paging
 9.11. AoS and SoA
10. SIMD Parallelism
 10.1. Intrinsics and Vector Types
 10.2. Moving Data
 10.3. Reductions
 10.4. Masking and Blending
 10.5. In-Register Shuffles
 10.6. Auto-Vectorization and SPMD
11. Algorithm Case Studies
 11.1. Binary GCD
(11.2. Prime Number Sieves)
 11.3. Integer Factorization
 11.4. Logistic Regression
 11.5. Big Integers & Karatsuba Algorithm
 11.6. Fast Fourier Transform
 11.7. Number-Theoretic Transform
 11.8. Argmin with SIMD
 11.9. Prefix Sum with SIMD
 11.10. Reading Decimal Integers
 11.11. Writing Decimal Integers
(11.12. Reading and Writing Floats)
(11.13. String Searching)
 11.14. Sorting
 11.15. Matrix Multiplication
12. Data Structure Case Studies
 12.1. Binary Search
 12.2. Static B-Trees
(12.3. Search Trees)
 12.4. Segment Trees
(12.5. Tries)
(12.6. Range Minimum Query)
 12.7. Hash Tables
(12.8. Bitmaps)
(12.9. Probabilistic Filters)
```

我们将加速的部分精彩案例：

- GCD 快 2 倍（对比 `std::gcd`）
- 二分查找快 8–15 倍（对比 `std::lower_bound`）
- 线段树快 5–10 倍（对比树状数组）
- 哈希表快 5 倍（对比 `std::unordered_map`）
- popcount 快 2 倍（对比反复调用 `popcnt`）
- 整数序列解析快 35 倍（对比 `scanf`）
- 排序快 ? 倍（对比 `std::sort`）
- 求和快 2 倍（对比 `std::accumulate`）
- 前缀和快 2–3 倍（对比朴素实现）
- argmin 快 10 倍（对比朴素实现）
- 数组查找快 10 倍（对比 `std::find`）
- 搜索树快 15 倍（对比 `std::set`）
- 矩阵乘法快 100 倍（对比"for-for-for"）
- 机器字长整数因式分解的最优算法（每个 60 位整数约 0.4ms）
- 最优的 Karatsuba 乘法
- 最优的 FFT

篇幅：450–600 页
发布日期：原计划 2022 年 Q3

### 第二部分：并行算法

并发、并行模型、上下文切换、绿色线程、并发运行时、缓存一致性、同步原语、OpenMP、归约、扫描、链表排序、图算法、无锁数据结构、异构计算、CUDA、kernel、warp、block、矩阵乘法、排序。

篇幅：150–200 页
发布日期：2023–2024？

### 第三部分：分布式计算

网络、消息传递、actor 模型、通信受限算法、分布式原语、all-reduce、MapReduce、流处理、查询计划、存储、分片、压缩、分布式数据库、一致性、可靠性、调度、工作流引擎、云计算。

发布日期：???（大概率能完成）

### 第四部分：软件与硬件

LLVM IR、编译器优化与后端、解释器、JIT 编译、Cython、JAX、Numba、Julia、OpenCL、DPC++、oneAPI、（基础）Verilog、FPGA、ASIC、TPU 及其他 AI 加速器。

发布日期：???（大概率完不成）

### 致谢

本书大量取材于许多人的博客文章、研究论文、会议演讲及其他工作：

- [Agner Fog](https://agner.org/optimize/)
- [Daniel Lemire](https://lemire.me/en/#publications)
- [Andrei Alexandrescu](https://erdani.com/index.php/about/)
- [Chandler Carruth](https://twitter.com/chandlerc1024)
- [Wojciech Muła](http://0x80.pl/articles/index.html)
- [Malte Skarupke](https://probablydance.com/)
- [Travis Downs](https://travisdowns.github.io/)
- [Brendan Gregg](https://www.brendangregg.com/blog/index.html)
- [Andreas Abel](http://embedded.cs.uni-saarland.de/abel.php)
- [Jakob Kogler](https://cp-algorithms.com/)
- [Igor Ostrovsky](http://igoro.com/)
- [Steven Pigeon](https://hbfs.wordpress.com/)
- [Denis Bakhvalov](https://easyperf.net/notes/)
- [Paul Khuong](https://pvk.ca/)
- [Pat Morin](https://cglab.ca/~morin/)
- [Victor Eijkhout](https://www.tacc.utexas.edu/about/directory/victor-eijkhout)
- [Robert van de Geijn](https://www.cs.utexas.edu/~rvdg/)
- [Edmond Chow](https://www.cc.gatech.edu/~echow/)
- [Peter Cordes](https://stackoverflow.com/users/224132/peter-cordes)
- [Geoff Langdale](https://branchfree.org/)
- [Matt Kulukundis](https://twitter.com/JuvHarlequinKFM)
- [Georg Sauthoff](https://gms.tf/)
- [Danila Kutenin](https://danlark.org/author/kutdanila/)
- [Ivica Bogosavljević](https://johnysswlab.com/author/ibogi/)
- [Matt Pharr](https://pharr.org/matt/)
- [Jan Wassenberg](https://research.google/people/JanWassenberg/)
- [Marshall Lochbaum](https://mlochbaum.github.io/publications.html)
- [Pavel Zemtsov](https://pzemtsov.github.io/)
- [Gustavo Duarte](https://manybutfinite.com/)
- [Nyaan](https://nyaannyaan.github.io/library/)
- [Nayuki](https://www.nayuki.io/category/programming)
- [Konstantin](http://const.me/)
- [InstLatX64](https://twitter.com/InstLatX64)
- [ridiculous_fish](https://ridiculousfish.com/blog/)
- [Z boson](https://stackoverflow.com/users/2542702/z-boson)
- [Creel](https://www.youtube.com/c/WhatsACreel)

### 免责声明：技术选型

本书示例使用 C++、GCC、x86-64、CUDA 和 Spark，但所传达的底层原理并不局限于这些技术。

说句良心话，作者对这些选择都不算满意：它们只是当下最普及、最稳定、因此对读者最有帮助的技术。作者个人会分别选 C / Rust / [Carbon?](https://github.com/carbon-language/carbon-lang)、LLVM、arm、OpenCL 和 Dask；也许将来会有更换部分技术栈的第 2 版。
