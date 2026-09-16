---
title: 内存延迟
weight: 2
draft: true
---

尽管[带宽](../bandwidth)是个更复杂的概念，它却比延迟（latency）容易观察和测量得多：你可以直接执行一长串相互独立的读或写请求，能提前看到它们的调度器会重排并重叠这些请求，把延迟藏起来，最大化总吞吐量。

要测量*延迟*，我们需要设计一个让 CPU 无法靠预知我们将请求的内存位置来"作弊"的实验。保证这一点的一个办法是：生成一个大小为 $N$ 的、恰好构成单个环的随机排列，然后反复沿着这个排列走：

```cpp
int p[N], q[N];

// generating a random permutation
iota(p, p + N, 0);
random_shuffle(p, p + N);

// this permutation may contain multiple cycles,
// so instead we use it to construct another permutation with a single cycle
int k = p[N - 1];
for (int i = 0; i < N; i++)
    k = q[k] = p[i];

for (int t = 0; t < K; t++)
    for (int i = 0; i < N; i++)
        k = q[k];
```

与线性迭代相比，以这种方式访问数组的全部元素要*慢得多*——差好几个数量级。它不仅让 [SIMD](/hpc/simd) 无从施展，还会[阻塞流水线](/hpc/pipelining)，制造出一场大规模的指令堵车——它们全都在等同一份数据从内存取回。

这种性能反模式被称为*指针追逐*（pointer chasing），在数据结构中非常常见，尤其是高级语言写的那种：为了支撑动态类型，它们大量使用堆分配的对象和指向这些对象的指针。

![](/en/hpc/cpu-cache/img/latency-throughput.svg)

谈论延迟时，用周期或纳秒比用吞吐量单位更合适，所以我们把这张图换成它的倒数：

![](/en/hpc/cpu-cache/img/permutation-latency.svg)

注意两张图上的"悬崖"都不像带宽那里那么陡峭分明。这是因为即使数组整体放不进上一层缓存，我们仍有一定的机会命中它。

### 理论延迟 {#theoretical-latency}

更正式地，设缓存层级有 $k$ 层，大小为 $s_i$、延迟为 $l_i$，那么期望延迟将不等于最慢的那次访问，而是：

$$
E[L] = \frac{
      s_1 \cdot l_1
    + (s_2 - s_1) \cdot l_2
%    + (s_3 - s_2) \cdot l_3
    + \ldots
    + (N - s_k) \cdot l_{RAM}
    }{N}
$$

如果把最慢缓存层之前发生的一切都抽象掉，公式可以化简成：

$$
E[L] = \frac{N \cdot l_{last} - C}{N} = l_{last} - \frac{C}{N}
$$

随着 $N$ 增大，期望延迟缓慢逼近 $l_{last}$，而如果你眯起眼睛使劲看，吞吐量（延迟的倒数）的图像大致就像由几条经过转置和缩放的双曲线拼成：

$$
\begin{aligned}
E[L]^{-1} &= \frac{1}{l_{last} - \frac{C}{N}}
\\        &= \frac{N}{N \cdot l_{last} - C}
\\        &= \frac{1}{l_{last}} \cdot \frac{N + \frac{C}{l_{last}} - \frac{C}{l_{last}}}{N - \frac{C}{l_{last}}}
\\        &= \frac{1}{l_{last}} \cdot \left(\frac{1}{N \cdot \frac{l_{last}}{C} - 1} + 1\right)
\\        &= \frac{1}{k \cdot (x - x_0)} + y_0
\end{aligned}
$$

要得到实际的延迟数值，我们可以迭代地应用第一个公式，先推出 $l_1$，再推出 $l_2$，依此类推。或者直接看悬崖紧前的值——它们与真实延迟的偏差应在 10-15% 以内。

还有更直接的测量延迟的方法，包括使用[非临时性读取](../bandwidth)，但这个基准测试更能代表实际的访问模式。

<!--

E[L] \approx \frac{s_{k} \cdot l_{k} + (N - s_k) \cdot l_{k+1}}{N}
= l_{k+1} - \frac{s_k \cdot (l_{k+1} - l_k)}{N}

-->

### 频率缩放 {#frequency-scaling}

与带宽类似，所有 CPU 缓存的延迟随时钟频率成比例缩放，而 RAM 不会。开启睿频来改变频率，同样能观察到这个差异。

![](/en/hpc/cpu-cache/img/permutation-boost.svg)

把它画成相对加速比后，这张图开始说得通了。

![](/en/hpc/cpu-cache/img/permutation-boost-speedup.svg)

对整个放进 CPU 缓存的数组规模，你会预期 2 倍的速率；对存放在 RAM 中的数组，则应大致持平。但实际发生的并非如此：即使在 RAM 访问上，低频那次运行也存在一小段固定的延迟。这是因为 CPU 在向主存派发读请求之前得先检查自己的缓存——好把 RAM 带宽省给其他可能需要它的进程。

内存延迟还受到[虚拟内存实现](../paging)的一些细节以及 [RAM 特有的时序](../mlp)的轻微影响，我们稍后讨论。
