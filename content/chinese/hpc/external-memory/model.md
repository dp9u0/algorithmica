---
title: 外部存储器模型
weight: 3
draft: true
---

要对访存受限（memory-bound）算法的性能进行推理，我们需要一种代价模型：它对昂贵的块 I/O 操作更敏感，但又不过分严苛、仍然实用。

### 缓存感知模型 {#cache-aware-model}

在[标准 RAM 模型](/hpc/complexity)中，我们忽略了原语操作的完成时间并不相等这一事实。最重要的是，它不区分作用在不同类型内存上的操作，把实际耗时 ~50ns 的 RAM 读取与耗时 ~5ms 的 HDD 读取等量齐观——后者大约是前者的 $10^5$ 倍。

本着类似的精神，在*外部存储器模型*中，我们干脆忽略所有非 I/O 的操作。更具体地说，我们只考虑缓存层级中的某一层，并对硬件和问题做如下假设：

- 数据集的大小为 $N$，全部存放在*外部*存储器中；我们可以按每块 $B$ 个元素的方式、在单位时间内读写它（读一整块和只读一个元素耗时相同）。
- 我们可以在*内部*存储器中存放 $M$ 个元素，也就是说最多能同时容纳 $\left \lfloor \frac{M}{B} \right \rfloor$ 个块。
- 我们只关心 I/O 操作：在读取和写入之间完成的任何计算都是免费的。
- 我们额外假设 $N \gg M \gg B$。

在这个模型中，我们用算法的高层 *I/O 操作*数（IOPS）来度量其性能——也就是执行期间对外部存储器读出或写入的块的总数。

我们将主要关注内部存储器是 RAM、外部存储器是 SSD 或 HDD 的情形，不过我们要发展的这套底层分析技术适用于缓存层级中的任何一层。在这些设定下，合理的块大小 $B$ 约为 1MB，内部存储器大小 $M$ 通常是几个 GB，而 $N$ 最多可达几个 TB。

### 数组扫描 {#array-scan}

<!-- The external memory model can be used very efficiently without sacrificing simplicity. -->

举个简单的例子：当我们逐个元素遍历数组来求和时，我们隐含地是按 $O(B)$ 个元素一批加载的；用外部存储器模型的话说，就是一块一块地处理它们：

$$
\underbrace{a_1, a_2, a_3,} _ {B_1}
\underbrace{a_4, a_5, a_6,} _ {B_2}
\ldots
\underbrace{a_{n-3}, a_{n-2}, a_{n-1}} _ {B_{m-1}}
$$

因此，在外部存储器模型中，求和以及其他线性数组扫描的复杂度是

$$
SCAN(N) \stackrel{\text{def}}{=} O\left(\left \lceil \frac{N}{B} \right \rceil \right) \; \text{IOPS}
$$

你可以像这样显式地实现外部数组扫描：

```c++
FILE *input = fopen("input.bin", "rb");

const int M = 1024;
int buffer[M], sum = 0;

// while the file is not fully processed
while (true) {
    // read up to M of 4-byte elements from the input stream
    int n = fread(buffer, 4, M, input);
    //  ^ the number of elements that were actually read

    // if we can't read any more elements, finish
    if (n == 0)
        break;
    
    // sum elements in-memory
    for (int i = 0; i < n; i++)
        sum += buffer[i];
}

fclose(input);
printf("%d\n", sum);
```

注意，在大多数情况下，操作系统会自动完成这种缓冲。即使数据只是从普通文件重定向到了标准输入，操作系统也会缓冲它的流，并（默认）按 ~4KB 的块读取。
