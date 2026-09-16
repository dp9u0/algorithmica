---
title: 存储层级
weight: 1
draft: true
---

现代计算机的内存是高度层级化的。它由多个速度和容量各异的*缓存层*（cache layer）组成：*较高*的层级通常存放从*较低*层级最频繁访问的数据，以降低延迟；每一层通常比下一层快上一个数量级，但也更小和/或更昂贵。

![](/en/hpc/external-memory/img/hierarchy.png)

抽象地看，各类存储设备都可以描述为这样的模块：具有一定的存储容量 $M$，能以大小为 $B$ 的块（而不是单个字节！）读写数据，且完成一次读写需要固定的时间。

从这个角度看，每种内存类型都有几个重要特征：

- *总容量* $M$；
- *块大小* $B$；
- *延迟*，即取回一个字节需要多长时间；
- *带宽*，它可能高于"块大小 × 延迟"这一简单乘积，这意味着多个 I/O 操作可以"重叠"进行；
- 摊还意义上的*成本*，包括芯片价格、能耗、维护费用等等。

下面是 2021 年主流硬件的一张粗略对比表：

| 类型 | $M$      | $B$ | 延迟 | 带宽 | 美元/GB/月[^pricing] |
|:-----|:---------|-----|---------|-----------|:------------------|
| L1   | 10K      | 64B | 2ns     | 80G/s     | -                 |
| L2   | 100K     | 64B | 5ns     | 40G/s     | -                 |
| L3   | 1M/核    | 64B | 20ns    | 20G/s     | -                 |
| RAM  | GB 级    | 64B | 100ns   | 10G/s     | 1.5               |
| SSD  | TB 级    | 4K  | 0.1ms   | 5G/s      | 0.17              |
| HDD  | TB 级    | -   | 10ms    | 1G/s      | 0.04              |
| S3   | $\infty$ | -   | 150ms   | $\infty$  | 0.02[^S3]         |

实际上，每种内存类型都有许多具体细节，下面我们逐一过一遍。

[^pricing]: 定价信息取自 [Google Cloud Platform](https://cloud.google.com/products/calculator?skip_cache=true)。
[^S3]: 云存储通常分[多个层级](https://aws.amazon.com/s3/storage-classes/)，数据访问频率越低的层级越便宜。

### 易失性存储器 {#volatile-memory}

RAM 层及以上的部分统称*易失性存储器*（volatile memory），因为一旦断电或遭遇其他灾难，其中的数据不会保留。它速度很快，因此被用来在计算机通电期间存放临时数据。

从快到慢依次是：

- **CPU 寄存器**，即 CPU 用来存放全部中间值的零时间访问数据单元，也可以看作一种内存类型。寄存器的数量有限（例如"通用"寄存器只有 16 个），某些情况下出于性能原因，你可能需要把它们全用上。
- **CPU 缓存。**现代 CPU 有多层缓存（L1、L2，常有 L3，偶尔甚至有 L4）。最低的一层在核间共享，容量通常随核数扩展（例如 10 核 CPU 的 L3 缓存应有 10M 左右）。
- **随机存取存储器（RAM）**，这是第一种可扩展的内存类型：如今在公有云上已经能租到半 TB 内存的主机。你的大部分工作数据就应当存放在这里。

CPU 缓存体系有一个重要概念——*缓存行*（cache line），它是 CPU 与 RAM 之间数据传输的基本单位。多数架构上缓存行大小为 64 字节，这意味着整个主存被划分成 64 字节的块，而每当你请求（读或写）单个字节时，无论你愿不愿意，都会连同取回它在同一缓存行里的其余 63 个邻居。

CPU 层面的缓存是自动进行的，依据是缓存行的最近访问时间。被访问时，缓存行的内容会被放置到最低的一层缓存，随后若未及时再次被访问，便逐渐被驱逐到更高的层级。程序员无法显式控制这个过程，但详细了解它如何运作是值得的，我们将在[下一章](/hpc/cpu-cache)里做这件事。

<!--

Caching is done not with a separate chip, but is embedded in the CPU itself. There are also multi-socket systems that support installing multiple CPUs in the motherboard. In this case, they have separate caching systems, and more over, each socket often becomes *local* to a certain part of the main memory and thus has increased latency (~100ns) for accessing locations outside of it. Such architectures are called NUMA ("Non-Uniform Memory Access") and used as a way to increase the total amount of RAM. We will not consider them for now, but they will become important in the context of parallel computing.

There are other caches inside CPUs that are used for something other than data. Instructions are fetched from memory roughly the same way that the data is fetched, so it is important not to wait for the instructions to load. For this reason, CPUs also have *instruction cache*, which, as the name suggests, is used for caching instructions that are read from the main memory. Its size and performance are about the same as for the L1 cache, and since it is not large, it makes sense to make binaries small in size so that the CPU does not "starve" from not being to fetch instructions in time.

-->

### 非易失性存储器 {#non-volatile-memory}

CPU 缓存和 RAM 中的数据单元只是温和地存放着寥寥几个电子（它们会周期性泄漏，因而需要周期性刷新），而*非易失性存储器*（non-volatile memory）的数据单元里存着数百个电子。这让数据能在断电后长期保存，代价则是性能和寿命——电子一多，它们与硅原子相撞的机会也就多了。

<!-- error correction -->

以持久方式存储数据的办法有很多，但从程序员的角度看，主要的是这几种：

- **固态硬盘（SSD）。**延迟相当低，在 0.1ms（$10^5$ ns）量级，但成本高昂，且寿命有限——每个单元只能写入有限次，这进一步放大了成本问题。移动设备和大多数笔记本电脑用的是它，因为它紧凑且没有活动部件。
- **机械硬盘（HDD）**很特别，因为它实际上是[旋转的物理盘片](https://www.youtube.com/watch?v=3owqvmMf6No&feature=emb_title)，上面搭载着读写磁头。要读一个存储位置，你得等盘片旋转到正确的位置，再把磁头非常精确地移过去。由此产生了一些非常怪异的访问模式：随机读取一个字节，可能和读取紧随其后的 1MB 数据花同样长的时间——通常在毫秒量级。由于这是计算机中除散热系统之外唯一带有机械活动部件的部分，机械硬盘相当容易损坏（数据中心 HDD 的平均寿命约 3 年）。
- **网络附加存储**（network-attached storage），即利用网络中的其他设备来存储数据。它有两种截然不同的形态。第一种是网络文件系统（NFS），一个通过网络挂载另一台计算机文件系统的协议。另一种是基于 API 的分布式存储系统，最著名的当属 [Amazon S3](https://aws.amazon.com/s3/)，其底层由公有云的一批存储优化机器组成，内部通常使用廉价的 HDD 或某些[更奇特的](https://aws.amazon.com/storagegateway/vtl/)存储类型。只要位于同一数据中心，NFS 有时甚至能比 HDD 还快；而公有云中的对象存储延迟通常在 50-100ms。它们通常是高度分布式且带副本的，以获得更好的可用性。

由于 SSD/HDD 明显慢于 RAM，这一层及以下的部分通常统称*外部存储器*。

与 CPU 缓存不同，外部存储器是可以显式控制的。这在许多场景下很有用，但大多数程序员只想把它抽象掉、当作主存的延伸来使用，而操作系统恰好能通过[虚拟内存](../virtual)做到这一点。
