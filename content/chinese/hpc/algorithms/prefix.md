---
title: 用 SIMD 求前缀和
weight: 8
draft: true
---

*前缀和*（prefix sum），也称*累积和*（cumulative sum）、*包含式扫描*（inclusive scan）或简称*扫描*（scan），指的是这样的一个数列 $b_i$：它由另一个序列 $a_i$ 按如下规则生成：

$$
\begin{aligned}
b_0 &= a_0
\\ b_1 &= a_0 + a_1
\\ b_2 &= a_0 + a_1 + a_2
\\ &\ldots
\end{aligned}
$$

换言之，输出序列的第 $k$ 个元素是输入序列前 $k$ 个元素之和。

前缀和是许多算法中非常重要的原语，在并行算法中尤其如此——它的计算随处理器数量几乎完美地扩展。遗憾的是，在单个 CPU 核上用 SIMD 并行来加速它要难得多，但我们还是要试一试——并推导出一个比标量基线实现快约 2.5 倍的算法。

### 基线 {#baseline}

作为基线，我们可以直接调用 STL 的 `std::partial_sum`，但为了清晰起见，我们手动实现它：创建一个整数数组，然后依次把前一个元素加到当前元素上：

```c++
void prefix(int *a, int n) {
    for (int i = 1; i < n; i++)
        a[i] += a[i - 1];
}
```

看起来每轮迭代需要两次读取、一次加法和一次写入，但编译器当然会把多余的读取优化掉，改用寄存器作累加器：

```nasm
loop:
    add     edx, DWORD PTR [rax]
    mov     DWORD PTR [rax-4], edx
    add     rax, 4
    cmp     rax, rcx
    jne     loop
```

[展开](/hpc/architecture/loops)循环后，实际只剩两条指令：融合的读-加，以及结果的写回。理论上它应能达到 2 GFLOPS（每 CPU 周期 1 个元素，得益于[超标量处理](/hpc/pipelining)），但由于内存系统必须不断在读与写之间[切换](/hpc/cpu-cache/bandwidth#directional-access)，实际性能在 1.2 到 1.6 GFLOPS 之间，取决于数组大小。

### 向量化 {#vectorization}

实现并行前缀和的一种办法是把数组切成小块，在各块上独立计算*局部*前缀和，然后做第二轮遍历，把之前所有元素之和加到各块的计算结果上进行校正。

![](/en/hpc/algorithms/img/prefix-outline.png)

这样一来，无论是计算局部前缀和的阶段还是累加阶段，每个块都可以并行处理，所以通常会把数组切成与处理器数量相同的块。但由于我们只被允许使用一个 CPU 核，而且 SIMD 中的[非连续内存访问](/hpc/simd/moving#non-contiguous-load)效果不佳，我们不打算这么做。我们将使用固定的块大小——等于一条 SIMD 通道（lane）的容量——并在寄存器内部计算前缀和。

要在寄存器内局部地计算这些前缀和，我们要用另一种并行前缀和方法，它总体上并不高效（总工作量是 $O(n \log n)$ 而非线性），但对数据已在 SIMD 寄存器中的情形足够好。思路是执行 $\log n$ 轮迭代，在第 $k$ 轮把 $a_{i - 2^k}$ 加到 $a_i$ 上——对每个适用的 $i$：

```c++
for (int l = 0; l < logn; l++)
    // (atomically and in parallel):
    for (int i = (1 << l); i < n; i++)
        a[i] += a[i - (1 << l)];
```

可以用归纳法证明这个算法是正确的：若第 $k$ 轮迭代后每个元素 $a_i$ 等于原数组区间 $(i - 2^k, i]$ 的和，那么把 $a_{i - 2^k}$ 加上去之后，它就等于 $(i - 2^{k+1}, i]$ 的和。经过 $O(\log n)$ 轮迭代后，数组就变成了它的前缀和。

要用 SIMD 实现它，可以用[置换](/hpc/simd/shuffling)把第 $i$ 个元素与第 $(i-2^k)$ 个元素对齐，但置换太慢了。我们改用 `sll`（“左移通道”，shift lanes left）指令，它做的正是这件事，还会把无法配对的元素替换为零：

```c++
typedef __m128i v4i;

v4i prefix(v4i x) {
    // x = 1, 2, 3, 4
    x = _mm_add_epi32(x, _mm_slli_si128(x, 4));
    // x = 1, 2, 3, 4
    //   + 0, 1, 2, 3
    //   = 1, 3, 5, 7
    x = _mm_add_epi32(x, _mm_slli_si128(x, 8));
    // x = 1, 3, 5, 7
    //   + 0, 0, 1, 3
    //   = 1, 3, 6, 10
    return x;
}
```

遗憾的是，这条指令的 256 位版本是在两条 128 位通道内各自独立地做字节移位，这在 AVX 中很典型：

```c++
typedef __m256i v8i;

v8i prefix(v8i x) {
    // x = 1, 2, 3, 4, 5, 6, 7, 8
    x = _mm256_add_epi32(x, _mm256_slli_si256(x, 4));
    x = _mm256_add_epi32(x, _mm256_slli_si256(x, 8));
    x = _mm256_add_epi32(x, _mm256_slli_si256(x, 16)); // <- this does nothing
    // x = 1, 3, 6, 10, 5, 11, 18, 26
    return x;
}
```

我们仍可以用它以两倍速度计算 4 元素前缀和，只是累加时得换回 128 位 SSE。让我们写一个便捷函数，端到端地完成局部前缀和的计算：

```c++
void prefix(int *p) {
    v8i x = _mm256_load_si256((v8i*) p);
    x = _mm256_add_epi32(x, _mm256_slli_si256(x, 4));
    x = _mm256_add_epi32(x, _mm256_slli_si256(x, 8));
    _mm256_store_si256((v8i*) p, x);
}
```

接下来是累加阶段，我们再写一个类似的便捷函数：它接受一个指向 4 元素块的指针，外加前一块前缀和组成的 4 元素向量。这个函数的职责是把该前缀和向量加到块上，并把它更新成可传给下一个块的形式（在加法之前广播块内最后一个元素）：

<!--

Not managing to come up with a more characteristic name, we are going to call it `accumulate`:

-->

```c++
v4i accumulate(int *p, v4i s) {
    v4i d = (v4i) _mm_broadcast_ss((float*) &p[3]);
    v4i x = _mm_load_si128((v4i*) p);
    x = _mm_add_epi32(s, x);
    _mm_store_si128((v4i*) p, x);
    return _mm_add_epi32(s, d);
}
```

实现了 `prefix` 和 `accumulate` 之后，剩下的就是把我们的两轮遍历算法粘起来：

```c++
void prefix(int *a, int n) {
    for (int i = 0; i < n; i += 8)
        prefix(&a[i]);
    
    v4i s = _mm_setzero_si128();
    
    for (int i = 4; i < n; i += 4)
        s = accumulate(&a[i], s);
}
```

这个算法已经比标量实现快两倍还多，但对超出 L3 缓存的大数组会变慢——大约只有[双向 RAM 带宽](/hpc/cpu-cache/bandwidth)的一半，因为整个数组要读两遍。

![](/en/hpc/algorithms/img/prefix-simd.svg)

另一个有趣的数据点：如果只执行 `prefix` 阶段，性能约为 8.1 GFLOPS；`accumulate` 阶段稍慢，约 5.8 GFLOPS。做个合理性检验：总性能应为 $\frac{1}{ \frac{1}{5.8} + \frac{1}{8.1} } \approx 3.4$。

### 分块 {#blocking}

于是，大数组上我们遇到了内存带宽问题。如果把数组切成能装进缓存的块、逐块处理，就可以避免从 RAM 重新取回整个数组。传给下一块的信息只需之前各块的总和，所以我们可以设计一个接口与 `accumulate` 类似的 `local_prefix` 函数：

```c++
const int B = 4096; // <- ideally should be slightly less or equal to the L1 cache

v4i local_prefix(int *a, v4i s) {
    for (int i = 0; i < B; i += 8)
        prefix(&a[i]);
    
    for (int i = 0; i < B; i += 4)
        s = accumulate(&a[i], s);

    return s;
}

void prefix(int *a, int n) {
    v4i s = _mm_setzero_si128();
    for (int i = 0; i < n; i += B)
        s = local_prefix(a + i, s);
}
```

（我们得保证 $N$ 是 $B$ 的倍数，不过这类实现细节我们暂且忽略。）

分块版本的表现好得多，而且不只是数组在 RAM 中的情形：

![](/en/hpc/algorithms/img/prefix-blocked.svg)

RAM 情形下相比未分块实现的加速只有约 1.5 倍而非 2 倍。这是因为当我们第二遍遍历已缓存的块时，内存控制器在闲置，而没有去预取下一块——[硬件预取器](/hpc/cpu-cache/prefetching)还不够聪明，识别不出这种模式。

### 连续加载 {#continuous-loads}

解决这一利用不足的问题有好几种办法。最直观的一种是使用[软件预取](/hpc/cpu-cache/prefetching)，在处理当前块的同时显式请求下一块。

把预取加进 `accumulate` 阶段更好，因为它比 `prefix` 慢、对内存的压力也更小：

```c++
v4i accumulate(int *p, v4i s) {
    __builtin_prefetch(p + B); // <-- prefetch the next block
    // ...
    return s;
}
```

对缓存内的数组，性能略有下降；但对 RAM 中的数组，性能进一步逼近 2 GFLOPS：

![](/en/hpc/algorithms/img/prefix-prefetch.svg)

另一种办法是对两个阶段做*交错*（interleaving）。与其以大块为单位把两个阶段分开、交替执行，不如让它们并发运行，`accumulate` 阶段固定滞后若干轮迭代——类似于 [CPU 流水线](/hpc/pipelining)：

```c++
const int B = 64;
//        ^ small sizes cause pipeline stalls
//          large sizes cause cache system inefficiencies

void prefix(int *a, int n) {
    v4i s = _mm_setzero_si128();

    for (int i = 0; i < B; i += 8)
        prefix(&a[i]);

    for (int i = B; i < n; i += 8) {
        prefix(&a[i]);
        s = accumulate(&a[i - B], s);
        s = accumulate(&a[i - B + 4], s);
    }

    for (int i = n - B; i < n; i += 4)
        s = accumulate(&a[i], s);
}
```

这样做还有别的好处：循环以恒定速度推进，减轻了内存系统的压力；调度器能同时看到两个子程序的指令，从而更高效地把指令分派到执行端口——有点像超线程，但发生在代码层面。

出于这些原因，即便是小数组，性能也有提升：

![](/en/hpc/algorithms/img/prefix-interleaved.svg)

最后，既然我们似乎并没有被[内存读取端口](/hpc/pipelining/tables/)或[译码宽度](/hpc/architecture/layout/#cpu-front-end)卡住，那就可以免费加上预取，让性能更上一层楼：

![](/en/hpc/algorithms/img/prefix-interleaved-prefetch.svg)

我们最终取得的加速：小数组在 $\frac{4.2}{1.5} \approx 2.8$ 倍，大数组在 $\frac{2.1}{1.2} \approx 1.75$ 倍之间。

对低精度数据，相对标量代码的加速比可能更高，因为标量代码无论操作数多大，基本上都被限制在每周期一轮迭代；但与[其他一些基于 SIMD 的算法](../argmin)相比，这结果还是有点“平平无奇”。这在很大程度上是因为 AVX 中没有跨完整寄存器的字节移位指令——若有，`accumulate` 阶段就能快一倍——更没有专门的前缀和指令。

### 其他相关工作 {#other-relevant-work}

你可以阅读[这篇来自哥伦比亚大学的论文](http://www.adms-conf.org/2020-camera-ready/ADMS20_05.pdf)，它聚焦于多核场景和 AVX-512（后者[算是](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=3037,4870,6715,4845,3853,90,7307,5993,2692,6946,6949,5456,6938,5456,1021,3007,514,518,7253,7183,3892,5135,5260,3915,4027,3873,7401,4376,4229,151,2324,2310,2324,591,4075,6130,4875,6385,5259,6385,6250,1395,7253,6452,7492,4669,4669,7253,1039,1029,4669,4707,7253,7242,848,879,848,7251,4275,879,874,849,833,6046,7250,4870,4872,4875,849,849,5144,4875,4787,4787,4787,3016,3018,5227,7359,7335,7392,4787,5259,5230,5230,5223,6438,488,483,6165,6570,6554,289,6792,6554,5230,6385,5260,5259,289,288,3037,3009,590,604,633,5230,5259,6554,6554,5259,6547,6554,3841,5214,5229,5260,5259,7335,5259,519,1029,515,3009,3009,3013,3011,515,6527,652,6527,6554,288&text=_mm512_alignr_epi32&techs=AVX_512)有快速的 512 位寄存器字节移位指令），以及[这个 StackOverflow 问题](https://stackoverflow.com/questions/10587598/simd-prefix-sum-on-intel-cpu)，看看更一般的讨论。

本文所讲的大部分内容早已为人所知。据我所知，我的贡献在于交错技术，它带来了约 20% 的适度性能提升。或许还有进一步改进的空间，但不会太多。

CMU 还有一位教授 [Guy Blelloch](https://www.cs.cmu.edu/~blelloch/)，早在 90 年代[向量处理器](https://en.wikipedia.org/wiki/Vector_processor)还流行的年代，就[倡导](https://www.cs.cmu.edu/~blelloch/papers/sc90.pdf)过专门的前缀和硬件。前缀和对并行应用非常重要，而硬件正变得越来越并行，所以也许在未来，CPU 厂商会重拾这个想法，让前缀和的计算变得容易一些。


<!--

There are ways to do it with permutations, but it would kill the performance of the prefix stage.

-->
