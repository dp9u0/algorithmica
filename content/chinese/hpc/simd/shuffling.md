---
title: 寄存器内混洗
weight: 6
draft: true
---

[掩码](../masking)让你可以只对向量元素的一个子集施加操作。这是一种非常有效且常用的数据操纵技术，但在很多情况下，你需要执行更高级的操作：在向量寄存器内部置换值，而不只是与其他向量混合。

问题在于，为每种可能的用例在硬件中加一条专门的元素混洗指令是不现实的。我们能做的，是只加一条通用的置换指令，它接受一组置换的下标，而这些下标可以用预先算好的查找表产生。

这个笼统的想法也许太抽象了，所以我们直接进入例子。

### 混洗与 Popcount {#shuffles-and-popcount}

*种群计数*（population count），也称*汉明权重*（Hamming weight），是统计一个二进制串中 `1` 的个数。

这是一种高频操作，所以 x86 上有一条专门的指令计算一个字的种群计数：

```c++
const int N = (1<<12);
int a[N];

int popcnt() {
    int res = 0;
    for (int i = 0; i < N; i++)
        res += __builtin_popcount(a[i]);
    return res;
}
```

它也支持 64 位整数，把总吞吐量提高了一倍：

```c++
int popcnt_ll() {
    long long *b = (long long*) a;
    int res = 0;
    for (int i = 0; i < N / 2; i++)
        res += __builtin_popcountl(b[i]);
    return res;
}
```

所需的指令只有两条：与加载融合的 popcount，以及加法。它们的吞吐量都很高，所以这段代码每个周期大约处理 $8+8=16$ 字节——瓶颈在这款 CPU 的译码宽度 4 上。

这些指令大约在 2008 年随 SSE4 加入 x86 CPU。让我们暂时回到向量化尚未出现的年代，试着用其他手段实现 popcount。

最朴素的办法是逐位遍历二进制串：

```c++
__attribute__ (( optimize("no-tree-vectorize") ))
int popcnt() {
    int res = 0;
    for (int i = 0; i < N; i++)
        for (int l = 0; l < 32; l++)
            res += (a[i] >> l & 1);
    return res;
}
```

不出所料，它比每个周期 ⅛ 字节略快一点——大约 0.2。

我们可以试着按字节而不是单个位来处理：[预先计算](/hpc/compilation/precalc)一张 256 个元素的小*查找表*，存放每个字节的种群计数，然后在遍历数组原始字节时查询它：

```c++
struct Precalc {
    alignas(64) char counts[256];

    constexpr Precalc() : counts{} {
        for (int m = 0; m < 256; m++)
            for (int i = 0; i < 8; i++)
                counts[m] += (m >> i & 1);
    }
};

constexpr Precalc P;

int popcnt() {
    auto b = (unsigned char*) a; // careful: plain "char" is signed
    int res = 0;
    for (int i = 0; i < 4 * N; i++)
        res += P.counts[b[i]];
    return res;
}
```

现在它每周期大约处理 2 字节，改用 16 位字（`unsigned short`）后可以升到约 2.7。

这个解法相比 `popcnt` 指令仍然很慢，但现在它可以被向量化了。与其尝试通过 [gather](../moving#non-contiguous-load) 指令加速，我们换一条路：把查找表做得足够小、装进一个寄存器，然后用专门的 [pshufb](https://software.intel.com/sites/landingpage/IntrinsicsGuide/#text=pshuf&techs=AVX,AVX2&expand=6331) 指令并行地查询它的值。

128 位 SSE3 中最初的 `pshufb` 接受两个寄存器：一个存放 16 个字节值的查找表，另一个是 16 个 4 位下标（0 到 15）的向量，指明每个位置各取哪个字节。在 256 位 AVX2 中，我们没有得到带别扭 5 位下标的 32 字节查找表，而是一条在两个 128 位通道（lane）上各自独立执行同样混洗操作的指令。

于是，针对我们的用例，我们创建一张 16 字节的查找表，存放每个半字节（nibble，即半个字节）的种群计数，重复两遍：

```c++
const reg lookup = _mm256_setr_epi8(
    /* 0 */ 0, /* 1 */ 1, /* 2 */ 1, /* 3 */ 2,
    /* 4 */ 1, /* 5 */ 2, /* 6 */ 2, /* 7 */ 3,
    /* 8 */ 1, /* 9 */ 2, /* a */ 2, /* b */ 3,
    /* c */ 2, /* d */ 3, /* e */ 3, /* f */ 4,

    /* 0 */ 0, /* 1 */ 1, /* 2 */ 1, /* 3 */ 2,
    /* 4 */ 1, /* 5 */ 2, /* 6 */ 2, /* 7 */ 3,
    /* 8 */ 1, /* 9 */ 2, /* a */ 2, /* b */ 3,
    /* c */ 2, /* d */ 3, /* e */ 3, /* f */ 4
);
```

现在，要计算一个向量的种群计数，我们把它的每个字节拆成低半字节和高半字节，然后用这张查找表取出各自的计数。剩下的只是把它们小心地加起来：

```c++
const reg low_mask = _mm256_set1_epi8(0x0f);

int popcnt() {
    int k = 0;

    reg t = _mm256_setzero_si256();

    for (; k + 15 < N; k += 15) {
        reg s = _mm256_setzero_si256();
        
        for (int i = 0; i < 15; i += 8) {
            reg x = _mm256_load_si256( (reg*) &a[k + i] );
            
            reg l = _mm256_and_si256(x, low_mask);
            reg h = _mm256_and_si256(_mm256_srli_epi16(x, 4), low_mask);

            reg pl = _mm256_shuffle_epi8(lookup, l);
            reg ph = _mm256_shuffle_epi8(lookup, h);

            s = _mm256_add_epi8(s, pl);
            s = _mm256_add_epi8(s, ph);
        }

        t = _mm256_add_epi64(t, _mm256_sad_epu8(s, _mm256_setzero_si256()));
    }

    int res = hsum(t);

    while (k < N)
        res += __builtin_popcount(a[k++]);

    return res;
}
```

这段代码每周期大约处理 30 字节。理论上内层循环可以做到 32，但我们不得不每 15 次迭代就停一次，因为 8 位计数器可能溢出。

> **译者注**：这段代码照原样运行会在组边界重复计数：外层每轮经内层两次加载实际覆盖 16 个元素（`a[k]` 到 `a[k+15]`），而 `k` 只前进 15，`a[k+15]` 会再被下一轮统计一次；把 `k += 15` 改为 `k += 16`（外层条件相应调整为 `k + 16 <= N`）即可修正。另外，"每 15 次迭代"的溢出说明与代码不符：`s` 在每轮外层迭代末尾都折叠进 `t` 并重置，每个 8 位计数器每轮最多累加 16，并不会溢出；15 对应的是让 `s` 跨轮连续累积时的上限 ⌊(256−1)/16⌋ = 15。

`pshufb` 指令在一些 SIMD 算法中如此重要，以至于 [Wojciech Muła](http://0x80.pl/)——想出这个算法的人——把它用作自己的 [Twitter 用户名](https://twitter.com/pshufb)。你还可以更快地计算种群计数：去看看他那个收录了各种向量化 popcount 实现的 [GitHub 仓库](https://github.com/WojciechMula/sse-popcount)，以及他[最近的论文](https://arxiv.org/pdf/1611.07612.pdf)，其中有对当时最新技术的详细讲解。

### 置换与查找表 {#permutations-and-lookup-tables}

本章最后一个主要例子是 `filter`（过滤）。它是一种非常重要的数据处理原语，接受一个数组作为输入，只写出满足给定谓词的元素（保持原有顺序）。

在单线程的标量情形下，它只需维护一个每次写入时递增的计数器即可实现：

```c++
int a[N], b[N];

int filter() {
    int k = 0;

    for (int i = 0; i < N; i++)
        if (a[i] < P)
            b[k++] = a[i];

    return k;
}
```

要向量化它，我们将使用 `_mm256_permutevar8x32_epi32` 内建函数。它接受一个值的向量，并用一个下标向量逐个选取。尽管名字叫 *permute*（置换），它并不置换值，只是*复制*它们以组成一个新向量：结果中出现重复是允许的。

我们算法的总体思路如下：

- 在数据向量上计算谓词——在这个例子中，就是执行比较得到掩码；
- 用 `movemask` 指令得到一个 8 位标量掩码；
- 用这个掩码去索引一张查找表，得到一个把满足谓词的元素（按原有顺序）移到向量开头的置换；
- 用 `_mm256_permutevar8x32_epi32` 内建函数执行置换；
- 把整个置换后的向量写入缓冲区——末尾可能带一些垃圾，但它的前缀是正确的；
- 计算标量掩码的种群计数，并按该数量移动缓冲区指针。

首先，我们需要预先计算这些置换：

```c++
struct Precalc {
    alignas(64) int permutation[256][8];

    constexpr Precalc() : permutation{} {
        for (int m = 0; m < 256; m++) {
            int k = 0;
            for (int i = 0; i < 8; i++)
                if (m >> i & 1)
                    permutation[m][k++] = i;
        }
    }
};

constexpr Precalc T;
```

然后就可以实现算法本身了：

```c++
const reg p = _mm256_set1_epi32(P);

int filter() {
    int k = 0;

    for (int i = 0; i < N; i += 8) {
        reg x = _mm256_load_si256( (reg*) &a[i] );
        
        reg m = _mm256_cmpgt_epi32(p, x);
        int mask = _mm256_movemask_ps((__m256) m);
        reg permutation = _mm256_load_si256( (reg*) &T.permutation[mask] );
        
        x = _mm256_permutevar8x32_epi32(x, permutation);
        _mm256_storeu_si256((reg*) &b[k], x);
        
        k += __builtin_popcount(mask);
    }

    return k;
}
```

向量化版本实现起来要费些功夫，但它比标量版本快 6-7 倍（当 `P` 的值过低或过高时加速比会略降，因为[分支变得可预测](/hpc/pipelining/branching)了）。

![](/en/hpc/simd/img/filter.svg)

循环性能仍然相对较低——每次迭代花 4 个 CPU 周期——因为在这款特定的 CPU（Zen 2）上，`movemask`、`permute` 和 `store` 的吞吐量都很低，而且都得经过同一个执行端口（P2）。在大多数其他 x86 CPU 上，你可以预期它快约 2 倍。

在 AVX-512 上，过滤还能实现得明显更快：它有一条专门的"[compress](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=7395,7392,7269,4868,7269,7269,1820,1835,6385,5051,4909,4918,5051,7269,6423,7410,150,2138,1829,1944,3009,1029,7077,519,5183,4462,4490,1944,1395&text=_mm512_mask_compress_epi32)"指令，接受一个数据向量和一个掩码，把未被掩码的元素连续地写出。它在各种依赖过滤子程序的算法（比如快速排序）中带来了巨大差异。

<!--

You can use either registers or fetch them from memory. There are some others that use immediates (compile-time constant too?)

_mm256_permute2x128_si256 — swaps lines
_mm256_slli_si256 srli
_mm256_permute_ps uses a mask

https://stackoverflow.com/questions/9795529/how-to-find-the-horizontal-maximum-in-a-256-bit-avx-vector Norbert P. and Peter Cordes 

_MM_SHUFFLE

https://stackoverflow.com/questions/37088449/macro-for-generating-immediates-for-avx-shuffle-intrinsics

-->
