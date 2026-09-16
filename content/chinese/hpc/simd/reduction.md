---
title: 归约
weight: 3
draft: true
---

*归约*（reduction，函数式编程中也称为*折叠* / folding）是指对一段任意元素求某个满足结合律和交换律的操作（即 $(a \circ b) \circ c = a \circ (b \circ c)$ 且 $a \circ b = b \circ a$）的值。

归约最简单的例子是计算数组的和：

```c++
int sum(int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++)
        s += a[i];
    return s;
}
```

这个朴素的做法并不容易向量化，因为循环的状态（当前前缀上的和 $s$）依赖于前一次迭代。克服这一点的办法是：把单个标量累加器 $s$ 拆成 8 个独立的累加器，让 $s_i$ 存放原数组中每隔 8 个元素、偏移为 $i$ 的那些元素之和：

$$
s_i = \sum_{j=0}^{n / 8} a_{8 \cdot j + i }
$$

如果把这 8 个累加器存放在一个 256 位向量中，我们就可以通过把数组连续的 8 元素段加上去，一次更新它们全部。用[向量扩展](../x86-simd)写起来很直接：

```c++
int sum_simd(v8si *a, int n) {
    //       ^ you can just cast a pointer normally, like with any other pointer type
    v8si s = {0};

    for (int i = 0; i < n / 8; i++)
        s += a[i];
    
    int res = 0;
    
    // sum 8 accumulators into one
    for (int i = 0; i < 8; i++)
        res += s[i];

    // add the remainder of a
    for (int i = n / 8 * 8; i < n; i++)
        res += a[i];
        
    return res;
}
```

这个方法也可以用于其他归约，比如求数组的最小值或异或和。

### 指令级并行 {#instruction-level-parallelism}

我们的实现与编译器自动生成的结果一致，但它其实不是最优的：只用一个累加器时，向量加法完成之前我们[只能等待](/hpc/pipelining/throughput)，循环每次迭代之间要隔一个周期，而在这个微架构上相应指令的[吞吐量](/hpc/pipelining/tables/)是 2。

如果我们再次把数组分成 $B \geq 2$ 份，并为每份使用*单独的*累加器，就能打满向量加法的吞吐量，把性能再提高一倍：

```c++
const int B = 2; // how many vector accumulators to use

int sum_simd(v8si *a, int n) {
    v8si b[B] = {0};

    for (int i = 0; i + (B - 1) < n / 8; i += B)
        for (int j = 0; j < B; j++)
            b[j] += a[i + j];

    // sum all vector accumulators into one
    for (int i = 1; i < B; i++)
        b[0] += b[i];
    
    int s = 0;

    // sum 8 scalar accumulators into one
    for (int i = 0; i < 8; i++)
        s += b[0][i];

     // add the remainder of a
    for (int i = n / (8 * B) * (8 * B); i < n; i++)
        s += a[i];

    return s;
}
```

如果你拥有的相关执行端口多于 2 个，可以相应地增大 `B` 常量，但这个 $n$ 倍的性能提升只对装得进 L1 缓存的数组有效——再大的数组，瓶颈就在[内存带宽](/hpc/cpu-cache/bandwidth)上了。

### 水平求和 {#horizontal-summation}

把存放在向量寄存器中的 8 个累加器加总成单个标量以得到总和，这一步称为"水平求和"（horizontal summation）。

虽然逐个提取标量再相加也只花常数个周期，但用一条[专门的指令](https://software.intel.com/sites/landingpage/IntrinsicsGuide/#techs=AVX,AVX2&text=_mm256_hadd_epi32&expand=2941)可以算得稍快一些，它把寄存器中相邻的元素两两相加。

![SSE/AVX 中的水平求和。注意输出是怎么存放的：这种 (a b a b) 交错形式在归约操作中很常见](/en/hpc/simd/img/hsum.png)

由于这是一个非常特定的操作，只能用 SIMD 内建函数来完成——不过对于标量代码，编译器大概也会生成几乎相同的过程：

```c++
int hsum(__m256i x) {
    __m128i l = _mm256_extracti128_si256(x, 0);
    __m128i h = _mm256_extracti128_si256(x, 1);
    l = _mm_add_epi32(l, h);
    l = _mm_hadd_epi32(l, l);
    return _mm_extract_epi32(l, 0) + _mm_extract_epi32(l, 1);
}
```

还有[一些其他类似的指令](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#techs=AVX,AVX2&ig_expand=3037,3009,5135,4870,4870,4872,4875,833,879,874,849,848,6715,4845&text=horizontal)，例如用于整数乘法或计算相邻元素绝对差（用于图像处理）的指令。

还有一条很特别的指令 `_mm_minpos_epu16`，计算 8 个 16 位整数中的水平最小值及其下标。这是唯一一条一步完成的水平归约：其他所有水平归约都要分多步计算。
