---
title: 外部存储器
weight: 8
draft: true
---

把两个数相加要花多长时间？`add` 是使用频率最高的指令之一，其本身的执行只需一个周期。所以，如果数据已经加载进寄存器，那么只需要一个周期。

但在一般情况下（`*c = *a + *b`），我们需要先从内存中取出操作数：

```nasm
mov eax, DWORD PTR [rsi]
add eax, DWORD PTR [rdi]
mov DWORD PTR [rdx], eax
```

<!--

When you fetch anything from memory, the request goes through an incredibly complex system of address translation units and caching layers, and if the data wasn't in any of them, the request proceeds off-chip to either temporary (RAM) or persistent (HDD, SSD) memory. This causes the total latency to be influenced by many factors such as and even [which part of the chip it is physically located](https://randomascii.wordpress.com/2022/01/12/5-5-mm-in-1-25-nanoseconds/).

-->

从内存中取任何数据时，在数据抵达之前总有那么一段延迟。而且，这个请求并不会直达它最终所在的存储位置，而是要先经过一套由地址转换单元和缓存层组成的复杂系统，它们既服务于内存管理，也用于降低延迟。

因此，这个问题唯一正确的答案是"视情况而定"——主要取决于操作数存放在哪里：

- 如果数据存放在主存（RAM）中，取回它大约需要 ~100ns，约合 200 个周期，之后写回还要再花 200 个周期。
- 如果它最近被访问过，那么很可能已被*缓存*，取回耗时会更短，具体取决于上次访问距今多久——最慢的一层缓存约 ~50 个周期，最快的大约 4-5 个周期。
- 但它也可能存放在某种*外部存储器*（external memory）上，比如机械硬盘；这种情况下，一次访问大约需要 5ms，粗略相当于 $10^7$ 个周期（！）。

内存性能之所以有如此巨大的差异，是因为内存硬件并不遵循与 CPU 芯片相同的[硅缩放定律](/hpc/complexity/hardware)。内存仍在通过其他途径改进，但如果说 50 年前内存时延与指令延迟还大体处于同一量级，如今它已经远远落后了。

![](/en/hpc/external-memory/img/memory-vs-compute.png)

为了不至于成为太强的限制因素，现代内存系统正变得越来越[层级化](hierarchy)：较高的层以牺牲一部分容量来换取更低的延迟。由于这些特征在不同层之间可能相差多个数量级——各类外部存储器之间尤其如此——对许多内存密集型算法来说，头等大事是在一切之前先优化 I/O 操作。

这催生了一种新的代价模型，称为*外部存储器模型*（external memory model）：它唯一的原语操作是按块读写，其余一切——只要只涉及存放在容量有限的本地内存中的数据——代价均为零。它孕育了*外部存储器算法*（external memory algorithms）这个激动人心的新领域，本章就将研究它。

<!--

It becomes ever more important to optimize

Modern computers grow ever more powerful, but their memory systems can't quite pick up with the increase in computing power, because they don't follow the same [laws of silicon scaling](/hpc/complexity/hardware) as CPU chips do.

If a CPU core has a frequency of 3 GHz, it roughly means that it is capable of executing up to $3 \cdot 10^9$ operations per second, depending on what constitutes an "operation." This is the baseline: on modern architectures, it can be increased by techniques such as SIMD and instruction-level parallelism up to $10^{11}$ operations per second, if the computation allows it.

But for many algorithms, the CPU is not the bottleneck. Before trying to optimize performance above that baseline, we need to learn not to drop below it, and the number one reason for this is memory.

-->
