---
title: 搬运数据
aliases: [/hpc/simd/vectorization]
weight: 2
draft: true
---

如果你花过一点时间研究[那份参考手册](https://software.intel.com/sites/landingpage/IntrinsicsGuide)，可能已经注意到向量操作基本上分为两大类：

1. 执行某种逐元素操作的指令（`+`、`*`、`<`、`acos` 等）。
2. 负责加载、存储、掩码、混洗，以及笼统地说搬运数据的指令。

逐元素指令用起来很容易，而 SIMD 最大的挑战在于先把数据装进向量寄存器，而且开销要足够低，整件事才划算。

### 对齐的加载与存储 {#aligned-loads-and-stores}

在内存与 SIMD 寄存器之间读写内容的操作各有两个版本：`load` / `loadu` 和 `store` / `storeu`。字母"u"代表"非对齐"（unaligned）。区别在于：前者只在被读/写的块完整落在一个[缓存行](/hpc/cpu-cache/cache-lines)之内时才能正确工作（否则会崩溃），而后者无论哪种情况都能工作，只是在块跨越缓存行时略有性能损失。

有时候，尤其是当"内层"操作非常轻量时，这个性能差异会变得显著（至少因为你需要取两个缓存行而不是一个）。作为一个极端的例子，下面这种把两个数组相加的方式：

```c++
for (int i = 3; i + 7 < n; i += 8) {
    __m256i x = _mm256_loadu_si256((__m256i*) &a[i]);
    __m256i y = _mm256_loadu_si256((__m256i*) &b[i]);
    __m256i z = _mm256_add_epi32(x, y);
    _mm256_storeu_si256((__m256i*) &c[i], z);
}
```

……比对齐版本慢大约 30%：

```c++
for (int i = 0; i < n; i += 8) {
    __m256i x = _mm256_load_si256((__m256i*) &a[i]);
    __m256i y = _mm256_load_si256((__m256i*) &b[i]);
    __m256i z = _mm256_add_epi32(x, y);
    _mm256_store_si256((__m256i*) &c[i], z);
}
```

在第一个版本中，假设数组 `a`、`b`、`c` 都是 64 字节*对齐*的（它们首元素的地址能被 64 整除，因而都从缓存行的开头起始），大约一半的读和写会是"坏"的，因为它们跨越了缓存行边界。

注意，这个性能差异是由缓存系统而不是指令本身造成的。在大多数现代体系结构上，只要块都只落在一个缓存行内，`loadu` / `storeu` 内建函数应当与 `load` / `store` 一样快。后者的优势在于，它们可以充当免费的运行时断言，确保所有读和写都是对齐的。

因此，在分配时正确地[对齐](/hpc/cpu-cache/alignment)数组和其他数据很重要，这也是编译器不能总是高效地[自动向量化](../auto-vectorization)的原因之一。对大多数用途来说，我们只需要保证任何 32 字节的 SIMD 块都不会跨越缓存行边界，可以用 `alignas` 说明符指定这个对齐：

<!--

By default, when you allocate an array, the only guarantee about its alignment you get is that none of its elements are split by a cache line. For an array of `int`, this means that it gets the alignment of 4 bytes (`sizeof int`), which lets you load exactly one cache line when reading any element. For our purposes, we want to guarantee that any (256-bit = 32-byte) SIMD block will not be split, so we need to specify the alignment of 32 bytes. For static arrays, we can do so with the `alignas` specifier:

-->

```c++
alignas(32) float a[n];

for (int i = 0; i < n; i += 8) {
    __m256 x = _mm256_load_ps(&a[i]);
    // ...
}
```

[内建向量类型](../intrinsics)已经带有相应的对齐要求，并假定对齐的内存读写——所以分配一个 `v8si` 数组总是安全的，但从 `int*` 转换过来时，你必须确保它是对齐的。

与标量的情形类似，许多算术指令可以把内存地址作为操作数——[向量加法](../intrinsics)就是一个例子——尽管你不能作为内建函数显式地这样用，只能依赖编译器。还有另外几条从内存读取 SIMD 块的指令，其中值得注意的是[非暂存](/hpc/cpu-cache/bandwidth#bypassing-the-cache)（non-temporal）的加载和存储操作，它们不会把访问的数据在缓存层级中提升。

### 寄存器别名 {#register-aliasing}

第一个 SIMD 扩展 MMX 的起点相当小。它只用 64 位向量，这些向量被巧妙地别名为 [80 位浮点数](/hpc/arithmetic/ieee-754)的尾数部分，这样就不用引入一套单独的寄存器。随着后续扩展中向量变宽，向量寄存器采用了与通用寄存器相同的[寄存器别名](/hpc/architecture/assembly#instructions-and-registers)机制来保持向后兼容：`xmm0` 是 `ymm0` 的前半部分（128 位），`xmm1` 是 `ymm1` 的前半部分，以此类推。

这个特性，加上向量寄存器位于浮点单元（FPU）中这一事实，使得在向量寄存器与通用寄存器之间搬运数据略微麻烦。

### 提取与插入 {#extract-and-insert}

要从向量中*提取*（extract）某个特定的值，可以使用 `_mm256_extract_epi32` 及类似的内建函数。它把要提取的整数的下标作为第二个参数，并根据该值生成不同的指令序列。

如果需要提取第一个元素，它会生成 `vmovd` 指令（作用于 `xmm0`，即向量的前半部分）：

```nasm
vmovd eax, xmm0
```

对于 SSE 向量的其他元素，它会生成可能略慢一些的 `vpextrd`：

```nasm
vpextrd eax, xmm0, 1
```

要提取 AVX 向量后半部分的任何元素，它得先提取出后半部分，再提取标量本身。举个例子，下面是它提取最后一个（第八个）元素的方式：

```nasm
vextracti128 xmm0, ymm0, 0x1
vpextrd      eax, xmm0, 3
```

还有一个类似的 `_mm256_insert_epi32` 内建函数，用于覆盖特定元素：

```nasm
mov          eax, 42

; v = _mm256_insert_epi32(v, 42, 0);
vpinsrd xmm2, xmm0, eax, 0
vinserti128     ymm0, ymm0, xmm2, 0x0

; v = _mm256_insert_epi32(v, 42, 7);
vextracti128 xmm1, ymm0, 0x1
vpinsrd      xmm2, xmm1, eax, 3
vinserti128  ymm0, ymm0, xmm2, 0x1
```

要点：在向量寄存器与标量数据之间来回搬运很慢，尤其是当目标不是第一个元素时。

### 构造常量 {#making-constants}

如果需要填充的不只是一个元素而是整个向量，可以使用 `_mm256_setr_epi32` 内建函数：

```c++
__m256 iota = _mm256_setr_epi32(0, 1, 2, 3, 4, 5, 6, 7);
```

这里的"r"代表"reversed"（逆序）——这是从 [CPU 的视角](/hpc/arithmetic/integer#integer-types)来说的，不是对人来说的。还有一个不带"r"的 `_mm256_set_epi32`，它从相反的方向填充值。两者主要都用于创建编译期常量，随后用一次块加载取进寄存器。如果你的用例是把向量填成零，请改用 `_mm256_setzero_si256`：它让寄存器与自身做 `xor`。

在内建向量类型中，直接使用普通的花括号初始化即可：

```c++
vec zero = {};
vec iota = {0, 1, 2, 3, 4, 5, 6, 7};
```

### 广播 {#broadcast}

除了只修改一个元素，你还可以把单个值*广播*（broadcast）到所有位置上：

```nasm
; __m256i v = _mm256_set1_epi32(42);
mov          eax, 42
vmovd        xmm0, eax
vpbroadcastd ymm0, xmm0
```

这是个高频操作，所以也可以直接用内存位置：

```nasm
; __m256 v = _mm256_broadcast_ss(&a[i]);
vbroadcastss ymm0, DWORD PTR [rdi]
```

使用内建向量类型时，可以先创建一个零向量，再把标量加上去：

```c++
vec v = 42 + vec{};
```

### 映射到数组 {#mapping-to-arrays}

如果想避开这一切复杂性，可以直接把向量倾倒到内存里，再按标量把值读回来：

```c++
void print(__m256i v) {
    auto t = (unsigned*) &v;
    for (int i = 0; i < 8; i++)
        std::cout << std::bitset<32>(t[i]) << " ";
    std::cout << std::endl;
}
```

这算不上快，严格说也不合法（C++ 标准没有规定这样转换数据会发生什么），但它简单，而我经常用这段代码在调试时打印向量的内容。

<!-- vector types syntax -->

### 非连续加载 {#non-contiguous-load}

后来的 SIMD 扩展加入了专门的"gather"与"scatter"指令，可以使用任意的数组下标非顺序地读/写数据。不过它们并不能快 8 倍，通常受限于内存而非 CPU，但对某些应用（比如稀疏线性代数）仍然很有用。

gather 自 AVX2 起可用，而各种 scatter 指令自 AVX512 起可用。

![](/en/hpc/simd/img/gather-scatter.png)

来看看它们是否比标量读取更快。首先，我们创建一个大小为 $N$ 的数组和 $Q$ 个随机读查询：

```c++
int a[N], q[Q];

for (int i = 0; i < N; i++)
    a[i] = rand();

for (int i = 0; i < Q; i++)
    q[i] = rand() % N;
```

在标量代码中，我们把查询指定的元素逐一加到校验和上：

```c++
int s = 0;

for (int i = 0; i < Q; i++)
    s += a[q[i]];
```

而在 SIMD 代码中，我们使用 `gather` 指令并行地对 8 个不同的下标做同样的事：

```c++
reg s = _mm256_setzero_si256();

for (int i = 0; i < Q; i += 8) {
    reg idx = _mm256_load_si256( (reg*) &q[i] );
    reg x = _mm256_i32gather_epi32(a, idx, 4);
    s = _mm256_add_epi32(s, x);
}
```

它们的表现大致相当，只有当数组装得进 L1 缓存时是例外：

![](/en/hpc/simd/img/gather.svg)

`gather` 和 `scatter` 的目的不是让内存操作更快，而是把数据取进寄存器，以便对其执行重度计算。对任何比单纯一次加法更贵的操作来说，它们都极其划算。

缺少（快速的）gather 和 scatter 指令，使得 CPU 上的 SIMD 编程与支持独立内存访问的真正的并行计算环境大不相同。你必须始终绕开这一点，采用各种方式把数据组织成连续的，以便装入寄存器。
