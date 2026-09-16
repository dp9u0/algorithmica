---
title: 预取
weight: 6
draft: true
---

利用内存硬件中可用的[免费并发](../mlp)，如果下一个要访问的数据的位置可以预测，提前*预取*（prefetch）它是很有益的。当流水线中没有[数据或控制冒险](/hpc/pipelining/hazards)时，这件事很容易做：CPU 可以直接跑到指令流前面，乱序执行内存操作。

但有时候，内存位置并不出现在指令流中，却仍然能以很高的概率被预测到。这些情况下，可以用其他手段预取它们：

- 显式地：单独读取下一个数据字或同一缓存行中的任意字节，把它提升进缓存层级。
- 隐式地：使用线性迭代这类简单访问模式，内存硬件能检测到它们并自动开始预取。

隐藏内存延迟对性能至关重要，所以本节我们将深入研究各种预取技术。

### 硬件预取 {#hardware-prefetching}

让我们修改[指针追逐](../latency)基准测试来展示硬件预取的效果。现在，我们以这样一种方式生成排列：沿着排列迭代时，CPU 会请求连续的缓存行，但缓存行内部的元素仍以随机顺序访问：

```cpp
int p[15], q[N];

iota(p, p + 15, 1);

for (int i = 0; i + 16 < N; i += 16) {
    random_shuffle(p, p + 15);
    int k = i;
    for (int j = 0; j < 15; j++)
        k = q[k] = i + p[j];
    q[k] = i + 16;
}
```

画图没有意义，因为图会是完全平的：无论数组多大，延迟都是 3ns。尽管指令调度器仍然看不出我们接下来要取什么，内存预取器仅凭观察内存访问就能检测出模式，并提前开始加载下一条缓存行，把延迟掩盖掉。

对大多数用例来说，硬件预取已经足够聪明，但它只检测简单的模式。你可以并行地向前或向后迭代多个数组，步长或许小到中等，但也仅此而已。对更复杂的任何模式，预取器都搞不明白发生了什么，需要我们自己帮它一把。

### 软件预取 {#software-prefetching}

软件预取最简单的办法，是用 `mov` 或任何其他内存指令加载缓存行中的任意字节，但 CPU 有专门的 `prefetch` 指令，它只把缓存行提升上来而不对其做任何事。这条指令不是 C 或 C++ 标准的一部分，但在大多数编译器中以 `__builtin_prefetch` 内建函数的形式提供：

```c++
__builtin_prefetch(&a[k]);
```

很难找到一个它能派上用场的*简单*例子。要让指针追逐基准测试从软件预取中受益，我们需要构造一个同时满足以下条件的排列：绕整个数组循环、无法被硬件预取器预测、下一个地址又容易计算。

幸运的是，[线性同余生成器](https://en.wikipedia.org/wiki/Linear_congruential_generator)有一个性质：如果模数 $n$ 是素数，生成器的周期将恰好是 $n$。所以，用以当前下标为状态的 LCG 所生成的排列，正好具备我们需要的全部性质：

```cpp
const int n = find_prime(N); // largest prime not exceeding N

for (int i = 0; i < n; i++)
    q[i] = (2 * i + 1) % n;
```

运行它时，性能与普通的随机排列相当。但现在我们有了向前窥探的能力：

```cpp
int k = 0;

for (int t = 0; t < K; t++) {
    for (int i = 0; i < n; i++) {
        __builtin_prefetch(&q[(2 * k + 1) % n]);
        k = q[k];
    }
}
```

计算下一个地址有一些开销，但对足够大的数组，速度几乎快了两倍：

![](/en/hpc/cpu-cache/img/sw-prefetch.svg)

有趣的是，我们可以向前预取不止一个元素，利用 LCG 函数中的这个模式：

$$
\begin{aligned}
   f(x)   &= 2 \cdot x + 1
\\ f^2(x) &= 4 \cdot x + 2 + 1
\\ f^3(x) &= 8 \cdot x + 4 + 2 + 1
\\ &\ldots
\\ f^k(x) &= 2^k \cdot x + (2^k - 1)
\end{aligned}
$$

因此，要提前加载第 `D` 个元素，可以这样：

```cpp
__builtin_prefetch(&q[((1 << D) * k + (1 << D) - 1) % n]);
```

如果我们在每次迭代都执行这个请求，平均就会同时向前预取 `D` 个元素，把吞吐量提升 `D` 倍。忽略 `D` 太大时的整数溢出等问题，我们可以把平均延迟任意压低，直到逼近计算下一个下标的成本（在本例中，它由[取模运算](/hpc/arithmetic/division)主导）。

![](/en/hpc/cpu-cache/img/sw-prefetch-others.svg)

注意这只是一个人为构造的例子；往实际程序里塞软件预取时，失败的次数往往多于成功。这很大程度上是因为你需要发出一条单独的内存指令，它可能与其他指令争抢资源。与此同时，硬件预取 100% 无害，因为它只在内存和缓存总线不忙时才启动。

做软件预取时还可以指定数据要被搬到缓存的哪一层——当你不确定会不会用到它、不想踢掉已在 L1 缓存里的东西时有用。可以用 `_mm_prefetch` 内建函数实现，它接受一个整数值作为第二个参数，用于指定缓存层级。它与[非临时性加载和存储](../bandwidth#bypassing-the-cache)搭配使用会很有用。

<!--

In the bandwidth benchmark, we iterated over array and fetched its elements. Although separately each memory read in that case is not different from the fetch in pointer chasing, they run much faster because they can are overlapped: and in fact, CPU issues read requests in advance without waiting for the old ones to complete, so that the results come about the same time as the CPU needs them.

Apart from having a very large pipeline and using the fact that scheduler can look ahead in it, modern memory controllers can detect simple patterns such as iterating backwards, forwards, including using constant small-ish strides.

### Speculative Execution

In fact, this sometimes works even when we are not sure which instruction is going to be executed next due to [speculative execution]. Consider the following example:

```cpp
bool cond = some_long_memory_operation();

if (cond)
    do_this_fast_operation();
else
    do_that_fast_operation();
```

What most modern CPUs do is they start evaluating one (most likely) branch without waiting for the condition to be computed. If they are right, then you will progress faster, and if they are wrong, the worst thing will happen is they discard some useless computation. This includes memory operations too, including cache system — because, well, we wait for a hundred cycles anyway, why not evaluate at least one of the branches ahead of time. By the way, this is what Meltdown was all about.

-->
