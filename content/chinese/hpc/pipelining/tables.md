---
title: 指令表
weight: 3
draft: true
---

<!-- This poses some additional challenges in coordinating how to execute the instructions — and also in which order. -->

把执行的各个阶段交错起来，是数字电子学里的一般思想。它不仅用在 CPU 的主流水线上，也用在单条指令乃至[内存](/hpc/cpu-cache/mlp)的层面。大多数执行单元都有自己的小流水线，能在上一条指令之后仅仅一两个周期就接收下一条。

在这个语境下，给指令使用两种不同的"[代价](/hpc/complexity)"是合理的：

- *延迟*（latency）：需要多少个周期才能拿到一条指令的结果。
- *吞吐量*（throughput）：平均每周期能执行多少条指令。

<!-- alternative throughput definitions, maybe in scheduling? -->

针对具体架构的延迟和吞吐量数据，可以从一类叫做[指令表](https://www.agner.org/optimize/instruction_tables.pdf)的专门文档中获取。下面是我的 Zen 2 的一些示例值（凡各处有差异，均以 32 位操作数为准）：

| 指令        | 延迟    | 倒数吞吐量 |
|-------------|---------|:------------|
| `jmp`       | -       | 2           |
| `mov r, r`  | -       | 1/4         |
| `mov r, m`  | 4       | 1/2         |
| `mov m, r`  | 3       | 1           |
| `add`       | 1       | 1/3         |
| `cmp`       | 1       | 1/4         |
| `popcnt`    | 1       | 1/4         |
| `mul`       | 3       | 1           |
| `div`       | 13-28   | 13-28       |

几点说明：

- 由于我们的头脑太习惯"越大越糟"的成本模型，大家用得更多的是吞吐量的*倒数*而非吞吐量本身。
- 如果某条指令特别高频，可以复制它的执行单元来提高其吞吐量——甚至可以超过每周期一条，但不会超过[译码宽度](/hpc/architecture/layout)。
- 有些指令的延迟为 0。这意味着它们只用于控制调度器，并不会到达执行阶段。但它们的倒数吞吐量仍不为零，因为 [CPU 前端](/hpc/architecture/layout)仍要处理它们。
- 大多数指令是流水线化的。如果某指令的倒数吞吐量为 $n$，通常意味着它的执行单元要过 $n$ 个周期才能接收下一条指令（若它小于 1，则说明存在多个执行单元，每个都能在下一周期接收新指令）。一个著名的例外是[整数除法](/hpc/arithmetic/division)：它的流水线化要么非常差，要么根本没做。
- 有些指令的延迟是可变的，不仅取决于操作数的大小，还取决于操作数的值。对于内存操作（包括带内存操作数的融合指令，如 `add`），延迟通常按最好情况（L1 缓存命中）标注。

还有许多重要的小细节，但目前这个心智模型已经够用了。

<!--

This mental model covers 80% of your needs.

Some instruction tables also list execution ports (or sometimes "pipes"). This is mostly relevant for SIMD.

This is a bit of an advanced and not well understood topic. Documentation is very obscure. people have to reverse engineer it. There are reasons to believe that folks at Intel don't know that themselves. The most comprehensive one is probably, uops.info.

There are tools like llvm-mca, but they aren't perfect either.

-->
