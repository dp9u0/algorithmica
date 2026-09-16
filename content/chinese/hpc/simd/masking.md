---
title: 掩码与混合
weight: 4
draft: true
---

SIMD 编程较大的挑战之一是它的控制流手段非常有限——因为你对向量施加的操作对它的所有元素都是一样的。

这使得那些通常用 `if` 或任何其他分支就能轻易解决的问题变得困难得多。在 SIMD 中，它们只能靠各种[无分支编程](/hpc/pipelining/branchless)技术来解决，而这些技术用起来并不总是那么直接。

### 掩码 {#masking}

让计算无分支化的主要手段是*谓词化*（predication）——把两个分支的结果都算出来，然后用某种算术技巧或者一条专门的"条件传送"指令来二选一：

```c++
for (int i = 0; i < N; i++)
    a[i] = rand() % 100;

int s = 0;

// branch:
for (int i = 0; i < N; i++)
    if (a[i] < 50)
        s += a[i];

// no branch:
for (int i = 0; i < N; i++)
    s += (a[i] < 50) * a[i];

// also no branch:
for (int i = 0; i < N; i++)
    s += (a[i] < 50 ? a[i] : 0);
```

要向量化这个循环，我们需要两条新指令：

- `_mm256_cmpgt_epi32`，比较两个向量中的整数，第一个元素大于第二个时产生全 1 掩码，否则产生全 0 掩码。
- `_mm256_blendv_epi8`，根据提供的掩码混合（合并）两个向量的值。

通过掩码与混合向量的元素，使得只有被选中的子集参与计算，我们可以用与条件传送类似的方式实现谓词化：

```c++
const reg c = _mm256_set1_epi32(49);
const reg z = _mm256_setzero_si256();
reg s = _mm256_setzero_si256();

for (int i = 0; i < N; i += 8) {
    reg x = _mm256_load_si256( (reg*) &a[i] );
    reg mask = _mm256_cmpgt_epi32(x, c);
    x = _mm256_blendv_epi8(x, z, mask);
    s = _mm256_add_epi32(s, x);
}
```

（为简洁起见，[水平求和以及数组余部的处理](../reduction)等细节在此省略。）

这就是 SIMD 中谓词化的惯常用法，但它并不总是最优的。我们可以利用"被混合的值之一是零"这个事实，用掩码按位 `and` 代替混合：

```c++
const reg c = _mm256_set1_epi32(50);
reg s = _mm256_setzero_si256();

for (int i = 0; i < N; i += 8) {
    reg x = _mm256_load_si256( (reg*) &a[i] );
    reg mask = _mm256_cmpgt_epi32(c, x);
    x = _mm256_and_si256(x, mask);
    s = _mm256_add_epi32(s, x);
}
```

这个循环略快一些，因为在这款特定的 CPU 上，向量 `and` 比 `blend` 少花一个周期。

另外还有几条指令支持掩码输入，最值得注意的是：

- `_mm256_blend_epi32` 内建函数，是一个接受 8 位整数掩码（而不是向量）的 `blend`（所以它末尾没有 `v`）。
- `_mm256_maskload_epi32` 和 `_mm256_maskstore_epi32` 内建函数，从内存加载/向内存存储一个 SIMD 块，并一步完成与掩码的 `and`。

内建向量类型同样可以做谓词化：

```c++
vec *v = (vec*) a;
vec s = {};

for (int i = 0; i < N / 8; i++)
    s += (v[i] < 50 ? v[i] : 0);
```

所有这些版本都在约 13 GFLOPS 的水平上运行，因为这个例子太简单了，编译器自己就能把循环向量化。下面来看一些无法自动向量化的更复杂的例子。

### 查找 {#searching}

在下一个例子中，我们需要在数组中找到一个特定的值并返回它的位置（即 `std::find`）：

```c++
const int N = (1<<12);
int a[N];

int find(int x) {
    for (int i = 0; i < N; i++)
        if (a[i] == x)
            return i;
    return -1;
}
```

为了给 `find` 函数做基准测试，我们把数组填上 $0$ 到 $(N - 1)$ 的数，然后反复查找一个随机元素：

```c++
for (int i = 0; i < N; i++)
    a[i] = i;

for (int t = 0; t < K; t++)
    checksum ^= find(rand() % N);
```

标量版本的性能约为 4 GFLOPS。这个数字把我们不必处理的元素也计入其中，所以请你在脑子里把它除以二（即需要检查的元素比例的期望）。

要向量化它，我们需要把元素向量与被查找值做相等比较得到一个掩码，然后想办法检查这个掩码是否为零。如果不为零，要找的元素就在这 8 个元素的块中。

要检查掩码是否为零，可以使用 `_mm256_movemask_ps` 内建函数，它取向量中每个 32 位元素的第一位，把它们拼成一个 8 位整数掩码。然后我们可以检查这个掩码是否非零——如果是，还可以立刻用 `ctz` 指令得到下标：

```c++
int find(int needle) {
    reg x = _mm256_set1_epi32(needle);

    for (int i = 0; i < N; i += 8) {
        reg y = _mm256_load_si256( (reg*) &a[i] );
        reg m = _mm256_cmpeq_epi32(x, y);
        int mask = _mm256_movemask_ps((__m256) m);
        if (mask != 0)
            return i + __builtin_ctz(mask);
    }

    return -1;
}
```

这个版本达到约 20 GFLOPS，比标量版快约 5 倍。它的热循环只用了 3 条指令：

```nasm
vpcmpeqd  ymm0, ymm1, YMMWORD PTR a[0+rdx*4]
vmovmskps eax, ymm0
test      eax, eax
je        loop
```

检查一个向量是否为零是个常见操作，SIMD 中有一条与 `test` 类似的操作可以用：

```c++
int find(int needle) {
    reg x = _mm256_set1_epi32(needle);

    for (int i = 0; i < N; i += 8) {
        reg y = _mm256_load_si256( (reg*) &a[i] );
        reg m = _mm256_cmpeq_epi32(x, y);
        if (!_mm256_testz_si256(m, m)) {
            int mask = _mm256_movemask_ps((__m256) m);
            return i + __builtin_ctz(mask);
        }
    }

    return -1;
}
```

我们仍然要用 `movemask` 来随后做 `ctz`，但热循环现在少了一条指令：

```nasm
vpcmpeqd ymm0, ymm1, YMMWORD PTR a[0+rdx*4]
vptest   ymm0, ymm0
je       loop
```

这对性能帮助不大，因为 `vptest` 和 `vmovmskps` 的吞吐量都是 1，无论我们在循环里再做什么，它们都会成为计算的瓶颈。

为了绕开这个限制，我们可以按 16 个元素一块来迭代，用按位 `or` 把两个 256 位 AVX2 寄存器各自独立比较的结果合并起来：

```c++
int find(int needle) {
    reg x = _mm256_set1_epi32(needle);

    for (int i = 0; i < N; i += 16) {
        reg y1 = _mm256_load_si256( (reg*) &a[i] );
        reg y2 = _mm256_load_si256( (reg*) &a[i + 8] );
        reg m1 = _mm256_cmpeq_epi32(x, y1);
        reg m2 = _mm256_cmpeq_epi32(x, y2);
        reg m = _mm256_or_si256(m1, m2);
        if (!_mm256_testz_si256(m, m)) {
            int mask = (_mm256_movemask_ps((__m256) m2) << 8)
                     +  _mm256_movemask_ps((__m256) m1);
            return i + __builtin_ctz(mask);
        }
    }

    return -1;
}
```

扫清这个障碍之后，性能现在峰值约 34 GFLOPS。但为什么不是 40？不应该快一倍吗？

下面是循环一次迭代在汇编中的样子：

```nasm
vpcmpeqd ymm2, ymm1, YMMWORD PTR a[0+rdx*4]
vpcmpeqd ymm3, ymm1, YMMWORD PTR a[32+rdx*4]
vpor     ymm0, ymm3, ymm2
vptest   ymm0, ymm0
je       loop
```

每次迭代我们都要执行 5 条指令。虽然所有相关执行端口的吞吐量都允许平均一个周期做完，但我们做不到，因为这款 CPU（Zen 2）的译码宽度是 4。因此，性能被限制在理论值的 ⅘。

<!--

To process the CPU (Zen 2) can only process 4. Here is the relevant part of the [llvm-mca report](/hpc/profiling/mca):

vpcmpeqd 013
vpcmpeqd 013
vpor 0123
vptest 2

[7]    [8]    [9]    [10]   Instructions:
0.46   0.09    -     0.45   vpcmpeqd	ymm2, ymm1, ymmword ptr [4*rdx + a]
0.40   0.09   0.22   0.29   vpcmpeqd	ymm3, ymm1, ymmword ptr [4*rdx + a+32]
0.34   0.11   0.08   0.47   vpor	ymm0, ymm3, ymm2
 -     1.00   1.00    -     vptest	ymm0, ymm0

-->

为了缓解这一点，我们可以再一次把每次迭代处理的 SIMD 块数量翻倍：

```c++
unsigned get_mask(reg m) {
    return _mm256_movemask_ps((__m256) m);
}

reg cmp(reg x, int *p) {
    reg y = _mm256_load_si256( (reg*) p );
    return _mm256_cmpeq_epi32(x, y);
}

int find(int needle) {
    reg x = _mm256_set1_epi32(needle);

    for (int i = 0; i < N; i += 32) {
        reg m1 = cmp(x, &a[i]);
        reg m2 = cmp(x, &a[i + 8]);
        reg m3 = cmp(x, &a[i + 16]);
        reg m4 = cmp(x, &a[i + 24]);
        reg m12 = _mm256_or_si256(m1, m2);
        reg m34 = _mm256_or_si256(m3, m4);
        reg m = _mm256_or_si256(m12, m34);
        if (!_mm256_testz_si256(m, m)) {
            unsigned mask = (get_mask(m4) << 24)
                          + (get_mask(m3) << 16)
                          + (get_mask(m2) << 8)
                          +  get_mask(m1);
            return i + __builtin_ctz(mask);
        }
    }

    return -1;
}
```

现在它达到 43 GFLOPS 的吞吐量——比最初的标量实现快约 10 倍。

把它扩展到每周期 64 个值并无帮助：小数组会因为在命中条件时执行所有这些额外的 `movemask` 而吃亏，而大数组无论如何都会受限于[内存带宽](/hpc/cpu-cache/bandwidth)。

### 计数 {#counting-values}

作为最后的练习，让我们统计一个值在数组中出现的次数，而不只是找它的第一次出现：

```c++
int count(int x) {
    int cnt = 0;
    for (int i = 0; i < N; i++)
        cnt += (a[i] == x);
    return cnt;
}
```

要向量化它，只需要把比较掩码逐元素转换成 1 或 0，再求和：

```c++
const reg ones = _mm256_set1_epi32(1);

int count(int needle) {
    reg x = _mm256_set1_epi32(needle);
    reg s = _mm256_setzero_si256();

    for (int i = 0; i < N; i += 8) {
        reg y = _mm256_load_si256( (reg*) &a[i] );
        reg m = _mm256_cmpeq_epi32(x, y);
        m = _mm256_and_si256(m, ones);
        s = _mm256_add_epi32(s, m);
    }

    return hsum(s);
}
```

两种实现都在约 15 GFLOPS 的水平：第一个编译器自己就能向量化。

但有一个编译器找不到的技巧：注意到全 1 的掩码在按整数重新解释时是[-1](/hpc/arithmetic/integer)。所以我们可以省掉"与上最低位"那一步，直接使用掩码本身，最后把结果取反即可：

```c++
int count(int needle) {
    reg x = _mm256_set1_epi32(needle);
    reg s = _mm256_setzero_si256();

    for (int i = 0; i < N; i += 8) {
        reg y = _mm256_load_si256( (reg*) &a[i] );
        reg m = _mm256_cmpeq_epi32(x, y);
        s = _mm256_add_epi32(s, m);
    }

    return -hsum(s);
}
```

在这个特定的体系结构上，这并没有提升性能，因为吞吐量实际上卡在更新 `s` 上：存在对上一次迭代的依赖，所以循环快不过每周期一次迭代。我们可以利用[指令级并行](../reduction#instruction-level-parallelism)，把累加器一分为二：

```c++
int count(int needle) {
    reg x = _mm256_set1_epi32(needle);
    reg s1 = _mm256_setzero_si256();
    reg s2 = _mm256_setzero_si256();

    for (int i = 0; i < N; i += 16) {
        reg y1 = _mm256_load_si256( (reg*) &a[i] );
        reg y2 = _mm256_load_si256( (reg*) &a[i + 8] );
        reg m1 = _mm256_cmpeq_epi32(x, y1);
        reg m2 = _mm256_cmpeq_epi32(x, y2);
        s1 = _mm256_add_epi32(s1, m1);
        s2 = _mm256_add_epi32(s2, m2);
    }

    s1 = _mm256_add_epi32(s1, s2);

    return -hsum(s1);
}
```

现在它达到约 22 GFLOPS 的性能，这已经是上限了。

在把这段代码适配到更短的数据类型时，请记住累加器可能溢出。为了解决这个问题，可以再加一个更宽的累加器，并定期中断循环，把局部累加器中的值加到它上面，然后重置局部累加器。例如，对 8 位整数而言，这意味着再写一个执行 $\lfloor \frac{256-1}{8} \rfloor = 15$ 次迭代的内层循环。

> **译者注**：原文算式有误：⌊(256−1)/8⌋ = 31，并非 15；15 对应的是 ⌊(256−1)/16⌋（每个 8 位计数器每轮迭代最多累加 16 的情形）。而就本节的计数而言，每个字节计数器每轮迭代至多加 1（改用全 1 掩码直接累加时，每个字节每轮也至多匹配一次），安全上限应为 255 轮。

<!-- TODO: 8-bit example -->
<!-- TODO: ILP first, -1 second -->
