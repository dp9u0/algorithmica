---
title: 用 SIMD 求 Argmin
weight: 7
draft: true
---

计算数组的*最小值*是[很容易向量化的](/hpc/simd/reduction)，因为它与其他任何归约（reduction）并无不同：在 AVX2 中，只需用方便的 `_mm256_min_epi32` 内建函数作为内层操作即可。它在一个周期内算出两个 8 元素向量的最小值——甚至比标量情形还快，后者至少需要一次比较和一次条件传送。

找出最小值元素的*索引*（argmin）则难得多，但它仍然可以被非常高效地向量化。在本节中，我们将设计一个算法，以（几乎）与求最小值相同的速度计算 argmin，比朴素的标量方法快约 15 倍。

### 标量基线 {#scalar-baseline}

在我们的基准测试中，先创建一个由随机 32 位整数组成的数组，然后反复在其中查找最小值的索引（若不唯一则取第一个）：

```c++
const int N = (1 << 16);
alignas(32) int a[N];

for (int i = 0; i < N; i++)
    a[i] = rand();
```

为了便于讲述，我们假设 $N$ 是 2 的幂，并且所有实验都在 $N=2^{13}$ 下运行，以免[内存带宽](/hpc/cpu-cache/bandwidth)成为干扰因素。

标量情形下实现 argmin，只需维护索引而非最小值：

```c++
int argmin(int *a, int n) {
    int k = 0;

    for (int i = 0; i < n; i++)
        if (a[i] < a[k])
            k = i;
    
    return k;
}
```

它运行在约 1.5 GFLOPS——意思是平均每秒处理 $1.5 \cdot 10^9$ 个元素，约合每周期 0.75 个（CPU 主频为 2GHz）。

把它与 `std::min_element` 比较一下：

```c++
int argmin(int *a, int n) {
    int k = std::min_element(a, a + n) - a;
    return k;
}
```

<!--

https://github.com/llvm-mirror/libcxx/blob/78d6a7767ed57b50122a161b91f59f19c9bd0d19/include/algorithm#L2489

https://github.com/gcc-mirror/gcc/blob/16e2427f50c208dfe07d07f18009969502c25dc8/libstdc%2B%2B-v3/include/bits/stl_algo.h#L5606

```nasm
lea	r8, 24[rdx]	# __first,
mov	r11d, DWORD PTR [rax]
cmp	DWORD PTR 12[rdx], r11d
cmovl	rax, r10	# __result,, __result, __first
```

```nasm
cmp	eax, r12d	# prephitmp_103, _108	
jle	.L36	#,	
mov	eax, r12d	# prephitmp_103, _108	
mov	ecx, ebp	# k, ivtmp.29	
.L36:	
lea	rdx, 4[r8]	# ivtmp.29,	
```

```nasm
cmp	eax, r12d	# prephitmp_103, _108	
jle	.L36	#,	
mov	eax, r12d	# prephitmp_103, _108	
mov	ecx, ebp	# k, ivtmp.29	
.L36:	
lea	rdx, 4[r8]	# ivtmp.29,	
```

-->

GCC 的这个版本只有约 0.28 GFLOPS——显然，编译器没能穿透这么多层抽象。这也再次提醒我们：永远别用 STL。

### 索引向量 {#vector-of-indices}

标量实现难以向量化的原因在于相邻迭代之间存在依赖。在优化[数组求和](/hpc/simd/reduction)时我们遇到过同样的问题，当时的解法是把数组切成 8 片，每片代表下标模 8 同余的一部分元素。这里可以用同样的技巧，只是还必须把数组下标也考虑进来。

当连续的元素及其索引都在向量中就位后，就可以用[谓词化](/hpc/pipelining/branchless)并行处理它们：

```c++
typedef __m256i reg;

int argmin(int *a, int n) {
    // indices on the current iteration
    reg cur = _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7);
    // the current minimum for each slice
    reg min = _mm256_set1_epi32(INT_MAX);
    // its index (argmin) for each slice
    reg idx = _mm256_setzero_si256();

    for (int i = 0; i < n; i += 8) {
        // load a new SIMD block
        reg x = _mm256_load_si256((reg*) &a[i]);
        // find the slices where the minimum is updated
        reg mask = _mm256_cmpgt_epi32(min, x);
        // update the indices
        idx = _mm256_blendv_epi8(idx, cur, mask);
        // update the minimum (can also similarly use a "blend" here, but min is faster)
        min = _mm256_min_epi32(x, min);
        // update the current indices
        const reg eight = _mm256_set1_epi32(8);
        cur = _mm256_add_epi32(cur, eight);       // 
        // can also use a "blend" here, but min is faster
    }

    // find the argmin in the "min" register and return its real index

    int min_arr[8], idx_arr[8];
    
    _mm256_storeu_si256((reg*) min_arr, min);
    _mm256_storeu_si256((reg*) idx_arr, idx);

    int k = 0, m = min_arr[0];

    for (int i = 1; i < 8; i++)
        if (min_arr[i] < m)
            m = min_arr[k = i];

    return idx_arr[k];
}
```

它运行在约 8–8.5 GFLOPS。迭代之间仍存在一些相互依赖，所以我们可以让每轮迭代处理多于 8 个元素、利用[指令级并行](/hpc/simd/reduction#instruction-level-parallelism)来继续优化。

这会大幅提升性能，但还不足以追上求最小值本身的速度（约 24 GFLOPS），因为还存在另一个瓶颈：每轮迭代需要一次与加载融合的比较、一次与加载融合的取最小、一次混合（blend）和一次加法——处理 8 个元素共需 4 条指令。由于这颗 CPU（Zen 2）的译码宽度只有 4，即便我们想办法消除其他所有瓶颈，性能仍将被限制在 8 × 2 = 16 GFLOPS。

因此，我们转而采用另一种每元素指令数更少的方法。

### 分支不可怕 {#branches-arent-scary}

运行标量版本时，我们多久更新一次最小值？

直觉告诉我们，如果所有值都是独立随机抽取的，那么“下一个元素小于之前所有元素”这一事件应当并不频繁。更精确地说，它的概率等于已处理元素个数的倒数。因此，`a[i] < a[k]` 条件成立的期望次数等于调和级数之和：

$$
\frac{1}{2} + \frac{1}{3} + \frac{1}{4} + \ldots + \frac{1}{n} = O(\ln(n))
$$

也就是说，对一百个元素的数组，最小值平均只更新约 5 次；一千个元素约 7 次；一百万个元素的数组也才 14 次——相对于全部“是否为新最小值”的检查次数而言，这个比例根本不算大。

编译器大概自己推不出这个结论，所以我们来[显式提供](/hpc/compilation/situational)这一信息：

```c++
int argmin(int *a, int n) {
    int k = 0;

    for (int i = 0; i < n; i++)
        if (a[i] < a[k]) [[unlikely]]
            k = i;
    
    return k;
}
```

编译器据此[优化了机器码布局](/hpc/architecture/layout)，CPU 现在能以约 2 GFLOPS 执行这个循环——相比未加提示的循环的 1.5 GFLOPS，提升不大但很可观。

思路来了：既然整个计算过程中最小值只更新十来次，我们完全可以抛弃所有向量混合和索引更新，只维护最小值并定期检查它是否变化。在这个检查内部，更新 argmin 的方法多慢都无所谓，因为它只会被调用寥寥几次。

用 SIMD 实现的话，每轮迭代只需一次向量加载、一次比较和一次“是否为零”的测试：

```c++
int argmin(int *a, int n) {
    int min = INT_MAX, idx = 0;
    
    reg p = _mm256_set1_epi32(min);

    for (int i = 0; i < n; i += 8) {
        reg y = _mm256_load_si256((reg*) &a[i]); 
        reg mask = _mm256_cmpgt_epi32(p, y);
        if (!_mm256_testz_si256(mask, mask)) { [[unlikely]]
            for (int j = i; j < i + 8; j++)
                if (a[j] < min)
                    min = a[idx = j];
            p = _mm256_set1_epi32(min);
        }
    }
    
    return idx;
}
```

它已经能达到约 8.5 GFLOPS，但如今循环的瓶颈变成了吞吐量只有 1 的 `testz` 指令。解决办法是加载两个连续的 SIMD 块并取它们的最小值，让 `testz` 一次性有效地处理 16 个元素：

```c++
int argmin(int *a, int n) {
    int min = INT_MAX, idx = 0;
    
    reg p = _mm256_set1_epi32(min);

    for (int i = 0; i < n; i += 16) {
        reg y1 = _mm256_load_si256((reg*) &a[i]);
        reg y2 = _mm256_load_si256((reg*) &a[i + 8]);
        reg y = _mm256_min_epi32(y1, y2);
        reg mask = _mm256_cmpgt_epi32(p, y);
        if (!_mm256_testz_si256(mask, mask)) { [[unlikely]]
            for (int j = i; j < i + 16; j++)
                if (a[j] < min)
                    min = a[idx = j];
            p = _mm256_set1_epi32(min);
        }
    }
    
    return idx;
}
```

这个版本运行在约 10 GFLOPS。要扫清其余障碍，我们还能做两件事：

- 把块大小增加到 32 个元素，以获得更多指令级并行。
- 优化局部 argmin：与其精确计算它的位置，不如只记下块的下标，最后再回过头来找一次。这样每次命中检查时只需计算最小值并广播到向量，更简单也快得多。

落实这两个优化后，性能提升到了惊人的约 22 GFLOPS：

```c++
int argmin(int *a, int n) {
    int min = INT_MAX, idx = 0;
    
    reg p = _mm256_set1_epi32(min);

    for (int i = 0; i < n; i += 32) {
        reg y1 = _mm256_load_si256((reg*) &a[i]);
        reg y2 = _mm256_load_si256((reg*) &a[i + 8]);
        reg y3 = _mm256_load_si256((reg*) &a[i + 16]);
        reg y4 = _mm256_load_si256((reg*) &a[i + 24]);
        y1 = _mm256_min_epi32(y1, y2);
        y3 = _mm256_min_epi32(y3, y4);
        y1 = _mm256_min_epi32(y1, y3);
        reg mask = _mm256_cmpgt_epi32(p, y1);
        if (!_mm256_testz_si256(mask, mask)) { [[unlikely]]
            idx = i;
            for (int j = i; j < i + 32; j++)
                min = (a[j] < min ? a[j] : min);
            p = _mm256_set1_epi32(min);
        }
    }

    for (int i = idx; i < idx + 31; i++)
        if (a[i] == min)
            return i;
    
    return idx + 31;
}
```

这几乎已到极限，因为光是求最小值本身也只有约 24–25 GFLOPS。

这些“依赖分支”的 SIMD 实现唯一的问题在于，它们依赖“最小值极少被更新”这一事实。对随机输入分布这是成立的，但最坏情况下并非如此。如果用一段递减的数填充数组，上面最后一个实现的性能会跌到约 2.7 GFLOPS——几乎慢 10 倍（不过仍快于标量代码，因为每个块上我们只计算最小值）。

修复它的一种办法是效仿快排那类随机化算法：自己把输入打乱，按随机顺序遍历数组。这能避开最坏情况的惩罚，但由于随机数生成和[内存](/hpc/cpu-cache/prefetching)相关的问题，实现起来颇费周章。还有一种更简单的解法。

### 先求最小值，再找索引 {#find-the-minimum-then-find-the-index}

我们已经知道如何快速地[求数组最小值](/hpc/simd/reduction)、如何快速地[在数组中查找元素](/hpc/simd/masking#searching)——那何不把两步分开：先算出最小值，再去找它？

```c++
int argmin(int *a, int n) {
    int needle = min(a, n);
    int idx = find(a, n, needle);
    return idx;
}
```

若把这两个子程序都实现到最优（参见链接的文章），性能约为随机数组 ~18 GFLOPS、递减数组 ~12 GFLOPS——这说得通，因为我们预计要分别把数组读上 1.5 遍和 2 遍。这本身不算太糟——至少避开了 10 倍的最坏情况惩罚——但问题在于，这一受罚的性能还会延续到更大的数组上，那时我们的瓶颈是[内存带宽](/hpc/cpu-cache/bandwidth)而非计算。

好在，我们已经知道怎么修。可以把数组切成固定大小 $B$ 的块，一边在这些块上求最小值、一边维护全局最小值。当新块的最小值低于全局最小值时，更新它，并记下全局最小值当前所在的块的编号。整个数组处理完后，只需回到那个块，扫描其中的 $B$ 个元素找出 argmin。

这样我们只处理 $(N + B)$ 个元素，既不必牺牲 ½ 也不必牺牲 ⅓ 的性能：

```c++
const int B = 256;

// returns the minimum and its first block
pair<int, int> approx_argmin(int *a, int n) {
    int res = INT_MAX, idx = 0;
    for (int i = 0; i < n; i += B) {
        int val = min(a + i, B);
        if (val < res) {
            res = val;
            idx = i;
        }
    }
    return {res, idx};
}

int argmin(int *a, int n) {
    auto [needle, base] = approx_argmin(a, n);
    int idx = find(a + base, B, needle);
    return base + idx;
}
```

最终实现的成绩是：随机数组约 22 GFLOPS，递减数组约 19 GFLOPS。

包含 `min()` 和 `find()` 在内的完整实现约有 100 行。想看的话可以[一观](https://github.com/sslotin/amh-code/blob/main/argmin/combined.cc)，尽管它离生产级还差得远。

### 总结 {#summary}

所有实现的结果汇总如下：

```
algorithm    rand   decr   reason for the performance difference
-----------  -----  -----  -------------------------------------------------------------
std          0.28   0.28   
scalar       1.54   1.89   efficient branch prediction
+ hinted     1.95   0.75   wrong hint
index        8.17   8.12
simd         8.51   1.65   scalar-based argmin on each iteration
+ ilp        10.22  1.74   ^ same
+ optimized  22.44  2.70   ^ same, but faster because there are less inter-dependencies
min+find     18.21  12.92  find() has to scan the entire array
+ blocked    22.23  19.29  we still have an optional horizontal minimum every B elements
```

对这些结果要有所保留：测量本身[噪声不小](/hpc/profiling/noise)，而且它们只针对两种输入分布、一个特定的数组大小（$N=2^{13}$，恰好是 L1 缓存的容量）、一种特定的架构（Zen 2）、以及一个特定的且略显过时的编译器（GCC 9.3）——编译器优化对基准测试代码的细微改动也非常敏感。

还有一些细枝末节可以优化，但潜在收益不到 10%，我就没折腾。哪天我也许会鼓起勇气，把算法优化到理论极限，处理好不能被块大小整除的数组长度和未对齐内存的情况，然后正经地在多种架构上重跑基准测试，配上 p 值之类的。如果有人抢先做了，请[知会我一声](http://sereja.me/)。

### 致谢 {#acknowledgements}

第一个基于索引的 SIMD 算法由 Wojciech Muła 于 2018 年[设计](http://0x80.pl/notesen/2018-10-03-simd-index-of-min.html)。

感谢 Zach Wegner [指出](https://twitter.com/zwegner/status/1491520929138151425)手动用内建函数实现能提升 Muła 算法的性能（我最初用的是 [GCC 向量类型](/hpc/simd/intrinsics/#gcc-vector-extensions)）。

<!--

Thanks to Alexander Monakov for [being meticulous](https://twitter.com/_monoid/status/1491827976438231049) and pushing me to investigate the STL version.

-->

发表之后我还发现，[BQN](https://mlochbaum.github.io/BQN/) 的创造者 [Marshall Lochbaum](https://www.aplwiki.com/wiki/Marshall_Lochbaum) 2019 年在 Dyalog APL 工作期间设计过一个[非常相似的算法](https://forums.dyalog.com/viewtopic.php?f=13&t=1579&sid=e2cbd69817a17a6e7b1f76c677b1f69e#p6239)。多关注一下数组编程语言的世界吧！
