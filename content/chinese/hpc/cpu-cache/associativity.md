---
title: 缓存相联度
weight: 11
draft: true
---

考虑在一个大小为 $N=2^{21}$ 的数组上、以固定步长 256 运行[跨步自增循环](../cache-lines)：

```cpp
for (int i = 0; i < N; i += 256)
    a[i]++;
```

然后是这个步长为 257 的循环：

```cpp
for (int i = 0; i < N; i += 257)
    a[i]++;
```

哪一个会先跑完？脑子里会冒出几种考虑：

- 起初你会觉得应该没什么差别，或者第二个循环快 $\frac{257}{256}$ 倍左右，因为它总的迭代次数更少。
- 然后你想起 256 是个漂亮的整数，可能与 [SIMD](/hpc/simd) 或内存系统有点关系，所以也许第一个更快。

但正确答案非常反直觉：第二个循环更快——而且快 10 倍。

这还不只是某一个个别糟糕的步长。对所有是大 2 的幂的倍数的下标，性能都会退化：

![数组大小经过归一化，使总迭代次数保持不变](/en/hpc/cpu-cache/img/strides-small.svg)

这里没有向量化或任何别的花样，两个循环生成的汇编除了步长值以外完全相同。这个效应完全归因于内存系统，特别是一个叫*缓存相联度*（cache associativity）的特性——CPU 缓存硬件实现方式的一个奇特产物。

### 硬件缓存 {#hardware-caches}

我们[从理论上](/hpc/external-memory)研究内存系统时，讨论过在软件中[实现缓存驱逐策略](/hpc/external-memory/policies/)的不同方法。我们重点关注的策略之一是*最近最少使用*（least recently used，LRU），它简单有效，但仍需要一些不简单的数据操作。

在硬件的语境下，这样的方案称为*全相联缓存*（fully associative cache）：我们有 $M$ 个单元，每个都能持有对应于全部 $N$ 个内存位置中任意一个的缓存行；发生争用时，最久未被访问的那个被踢出去、换成新来的。

![全相联缓存](/en/hpc/cpu-cache/img/cache1.png)

全相联缓存的问题在于，"在数百万条缓存行里找出最老的那条"这个操作在软件里就相当难做，在硬件里干脆不可行。你可以做一个 16 项左右的全相联缓存，但管理几百条缓存行就已经要么贵得离谱、要么慢得不值当了。

我们可以求助于另一种简单得多的方法：把 RAM 中每个 64 字节的块映射到唯一一条它可占用的缓存行。比如说，如果内存中有 4096 个块、缓存行有 64 条，那么每条缓存行在任何时刻存储的是 $\frac{4096}{64} = 64$ 个不同块中某一个的内容。

![直接映射缓存](/en/hpc/cpu-cache/img/cache2.png)

直接映射缓存（direct-mapped cache）实现简单，除了标签（tag，即被缓存块的真实内存位置）之外，不需要存储任何与缓存行相关的额外元信息。缺点是表项可能被过快地踢出——例如在映射到同一缓存行的两个地址之间来回弹跳时——导致缓存的整体利用率降低。

因此，我们在直接映射与全相联缓存之间折中：*组相联缓存*（set-associative cache）。它把地址空间划分成相等的组，每组各自作为一个小型的全相联缓存工作。

![组相联缓存（2 路组相联）](/en/hpc/cpu-cache/img/cache3.png)

*相联度*（associativity）就是这些组的大小，换句话说，是每个数据块可以映射到多少条不同的缓存行。相联度越高，缓存的利用就越高效，但成本也越高。

例如，在[我的 CPU](https://en.wikichip.org/wiki/amd/ryzen_7/4700u) 上，L3 缓存是 16 路组相联的，单个核心可用 4MB。这意味着总共有 $\frac{2^{22}}{2^{6}} = 2^{16}$ 条缓存行，它们被分成 $\frac{2^{16}}{16} = 2^{12}$ 组，每组各自作为一个全相联缓存，服务 RAM 的 $(\frac{1}{2^{12}})$ 分之一。

大多数其他 CPU 缓存也是组相联的，包括非数据缓存，比如指令缓存和 TLB。例外是只容纳 64 项或更少的小型专用缓存——它们通常是全相联的。

### 地址翻译 {#address-translation}

只剩下一个含糊之处：缓存行的映射具体是怎么做的。

如果我们在软件里实现组相联缓存，我们会计算内存块地址的某个哈希函数，然后把函数值用作缓存行的下标。在硬件里我们没法真这么做，因为太慢了：例如对 L1 缓存，延迟要求是 4 到 5 个周期，而光是[取个模](/hpc/arithmetic/division)就要大约 10-15 个周期，更别说更复杂的运算了。

取而代之，硬件用了偷懒的办法。它取出需要访问的内存地址，把它拆成三部分——从低位到高位依次是：

- *偏移*（offset）——64B 缓存行内字的下标（$\log_2 64 = 6$ 比特）；
- *索引*（index）——缓存行组的下标（接下来的 $12$ 比特，因为 L3 缓存中有 $2^{12}$ 条缓存行）；
- *标签*（tag）——内存地址的其余部分，用来区分存放在各缓存行里的内存块。

换句话说，所有"中间"部分相同的内存地址都映射到同一组。

![64 项 2 路组相联缓存的地址组成](/en/hpc/cpu-cache/img/address.png)

这让缓存系统实现起来更简单、更便宜，但也让它容易受某些糟糕访问模式之害。

### 病态映射 {#pathological-mappings}

那么，我们刚才说到哪了？哦对：以 256 为步长迭代导致如此可怕减速的原因。

当我们跳过 256 个整数时，指针每次增加 $1024 = 2^{10}$，最后 10 个比特保持不变。由于缓存系统用低 6 位做偏移、接下来 12 位做缓存行索引，我们实际只用到了 L3 缓存中 $2^{12 - (10 - 6)} = 2^8$ 个不同的组，而不是 $2^{12}$ 个，效果等于把我们的 L3 缓存缩小了 $2^4 = 16$ 倍。数组（$N=2^{21}$）放不进 L3 缓存了，溢出到慢一个数量级的 RAM，性能因此下降。

<!--

TODO: Implement this in software:

Inside these sets, cache operates simply as LRU. Instead of storing time, you just store counters: the later an element was accessed, the lower its counter is. In hardware, you need to maintain $n$ counters of $\log_2 n$ bits each. When a cell is accessed, its counter becomes $(n-1)$ (maximum possible), and the others that are larger need to be decremented by one. Then to kick out an element you need to find the counter with zero and replace it, and then decrement everyone else's counters.

Simply speaking, the CPU just maintains these cells containing data, and when reading any cell from the main memory the CPU first looks it up in the cache, and if it contains the data, it reads it and otherwise goes to a higher cache level until it reaches main memory. Simple and beautiful.

along with a "tag" information which helps identify which block it is

-->

缓存相联度效应引发的性能问题在算法中出现得相当频繁，因为出于种种原因，程序员们就是喜欢在给数组编下标时用 2 的幂：

- 如果多维数组的最后一维是 2 的幂，多维数组访问的地址更容易计算，因为只需要一次二进制移位而不是乘法。
- 对 2 的幂取模更容易计算，因为一条按位 `and` 就能完成。
- 在分治算法中，使用 2 的幂的问题规模很方便，甚至往往是必需的。
- 2 是最小的整数底数，所以用递增的 2 的幂序列作为问题规模，是给访存受限算法做基准测试时的常见选择。
- 还有，根据传递性，更自然的 10 的幂也能被稍小一点的 2 的幂整除。

这尤其常适用于使用固定内存布局的隐式数据结构。例如，在大小为 $2^{20}$ 的数组上做[二分查找](/hpc/data-structures/binary-search)，每次查询约需 ~360ns，而在大小为 $(2^{20} + 123)$ 的数组上查找约需 ~300ns。当数组大小是一个大 2 的幂的倍数时，那些"最热"元素——我们在头十来次迭代中最可能请求的那些——的下标也会被一些大的 2 的幂整除，从而映射到同一缓存行——互相踢来踢去，造成约 ~20% 的性能下降。

幸运的是，这类问题更像一种异常现象，算不上严重的麻烦。解决办法通常很简单：避免以 2 的幂为步长迭代，把多维数组的最后一维设成略微不同的长度，或者用别的办法在内存布局中插入"空洞"，或者在数组下标与数据实际存放位置之间建立某种看起来随机的双射。

<!-- seemingly random bijection, link to segment tree, to binary search -->
