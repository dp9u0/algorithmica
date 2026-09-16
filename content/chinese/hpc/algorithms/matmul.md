---
title: 矩阵乘法
weight: 20
draft: true
---

<!--
baseline 13.58622 0.5209607970428861
hugepages 16.749895 0.42256312651512146
transposed 12.377302 0.5718441708863531
autovec 3.117215 2.2705806304666187
vectorized 3.075742 2.301196914435606
kernel 2.24264 3.1560517960974566
blocked 0.461477 15.33746643928083
noalloc 0.408031 17.346446716058338
nomove 0.303826 23.295860130469414
blas 0.27489790320396423 25.747333528217077
-->

在本案例研究中，我们将设计并实现几种矩阵乘法算法。

我们从朴素的“三重 for”算法入手，逐步改进，最终得到一个快 50 倍的版本——它与 BLAS 库的性能相当，而代码只有不到 40 行 C。

所有实现都用 GCC 13 编译，运行在一颗主频 2GHz 的 [Zen 2](https://en.wikichip.org/wiki/amd/microarchitectures/zen_2) CPU 上。

## 基线 {#baseline}

$l \times n$ 矩阵 $A$ 与 $n \times m$ 矩阵 $B$ 相乘的结果定义为一个 $l \times m$ 矩阵 $C$，满足：

$$
C_{ij} = \sum_{k=1}^{n} A_{ik} \cdot B_{kj}
$$

为简单起见，我们只考虑 $l = m = n$ 的*方阵*。

要实现矩阵乘法，直接把定义搬进代码即可；但我们将使用一维数组而非二维数组（即矩阵），以把指针运算写得明白：

```c++
void matmul(const float *a, const float *b, float *c, int n) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                c[i * n + j] += a[i * n + k] * b[k * n + j];
}
```

出于稍后会变得明显的原因，我们只用 $48$ 的倍数大小的矩阵做基准测试，但这些实现对其余大小同样是正确的。我们还特意使用 [32 位浮点数](/hpc/arithmetic/ieee-754)，尽管所有实现都可以轻松地[推广](#generalizations)到其他数据类型和运算。

用 `g++ -O3 -march=native -ffast-math -funroll-loops` 编译后，朴素算法做一次 $n = 1920 = 48 \times 40$ 的矩阵乘法需要约 16.7 秒。直观地看，这大约是每纳秒 $\frac{1920^3}{16.7 \times 10^9} \approx 0.42$ 次有用运算（GFLOPS），约合每次乘法 5 个 CPU 周期——目前这成绩可不算好看。

## 转置 {#transposition}

一般而言，优化一个处理大量数据的算法时——$1920^2 \times 3 \times 4 \approx 42$ MB 显然是很大的数据量，因为任何 [CPU 缓存](/hpc/cpu-cache)都装不下它——应当先优化内存、再优化算术，因为内存更有可能成为瓶颈。

字段 $C_{ij}$ 可以看作第 $i$ 行（来自矩阵 $A$）与第 $j$ 列（来自矩阵 $B$）的点积。在上面的内层循环里递增 `k` 时，我们按顺序读取矩阵 `a`，但在遍历 `b` 的一列时每次要跳过 $n$ 个元素，这[不如](/hpc/cpu-cache/aos-soa)顺序迭代快。

一个[众所周知](/hpc/external-memory/oblivious/#matrix-multiplication)的解决此问题的优化，是把矩阵 $B$ 按*列主序*（column-major）存储——或者等价地，在矩阵乘法之前先把它*转置*。这需要 $O(n^2)$ 次额外操作，但保证了最内层循环的顺序读取：

<!--

![](../img/column-major.jpg)

-->

```c++
void matmul(const float *a, const float *_b, float *c, int n) {
    float *b = new float[n * n];

    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            b[i * n + j] = _b[j * n + i];
    
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                c[i * n + j] += a[i * n + k] * b[j * n + k]; // <- note the indices
}
```

这段代码运行约 12.4s，快了约 30%。

稍后会看到，转置的好处远不止顺序内存读取这一条。

## 向量化 {#vectorization}

既然我们要做的只是顺序读取 `a` 和 `b` 的元素、把它们相乘、再把结果累加到一个累加器变量上，就可以用 [SIMD](/hpc/simd/) 指令来整体加速。用 [GCC 向量类型](/hpc/simd/intrinsics/#gcc-vector-extensions)实现相当直接——把矩阵行做[内存对齐](/hpc/cpu-cache/alignment/)、用零填充，然后像计算任何其他[归约](/hpc/simd/reduction/)一样计算乘积之和：

```c++
// a vector of 256 / 32 = 8 floats
typedef float vec __attribute__ (( vector_size(32) ));

// a helper function that allocates n vectors and initializes them with zeros
vec* alloc(int n) {
    vec* ptr = (vec*) std::aligned_alloc(32, 32 * n);
    memset(ptr, 0, 32 * n);
    return ptr;
}

void matmul(const float *_a, const float *_b, float *c, int n) {
    int nB = (n + 7) / 8; // number of 8-element vectors in a row (rounded up)

    vec *a = alloc(n * nB);
    vec *b = alloc(n * nB);

    // move both matrices to the aligned region
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            a[i * nB + j / 8][j % 8] = _a[i * n + j];
            b[i * nB + j / 8][j % 8] = _b[j * n + i]; // <- b is still transposed
        }
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            vec s{}; // initialize the accumulator with zeros

            // vertical summation
            for (int k = 0; k < nB; k++)
                s += a[i * nB + k] * b[j * nB + k];
            
            // horizontal summation
            for (int k = 0; k < 8; k++)
                c[i * n + j] += s[k];
        }
    }

    std::free(a);
    std::free(b);
}
```

$n = 1920$ 时性能约为 2.3 GFLOPS——比转置但未向量化的版本又高了约 4 倍。

![](/en/hpc/algorithms/img/mm-vectorized-barplot.svg)

这个优化看起来既不复杂、也不是矩阵乘法独有的。那为什么编译器不能自己把内层循环[自动向量化](/hpc/simd/auto-vectorization/)呢？

其实它可以；唯一阻碍它的是 `c` 与 `a` 或 `b` 重叠的可能性。要排除它，可以向编译器声明你保证 `c` 不与任何东西[别名](/hpc/compilation/contracts/#memory-aliasing)，方法是给它加上 `__restrict__` 关键字：

<!-- (the compiler already knows that reading `a` and `b` is safe in any order because they are marked as `const`): -->

```c++
void matmul(const float *a, const float *_b, float * __restrict__ c, int n) {
    // ...
}
```

手动向量化与自动向量化的实现表现大致相同。

<!--

The performance is bottlenecked by using a single variable. We could use multiple variables similar to other reductions, but we will solve it later anyway.

-->

## 内存效率 {#memory-efficiency}

有意思的是，这个实现的效率取决于问题规模。

起初，性能（定义为每秒有用运算的次数）随循环管理与水平归约的开销下降而上升。随后在 $n=256$ 附近，性能开始平缓下降——因为矩阵开始装不进[缓存](/hpc/cpu-cache/)（$2 \times 256^2 \times 4 = 512$ KB 恰是 L2 缓存的大小）——性能转为受[内存带宽](/hpc/cpu-cache/bandwidth/)制约。

![](/en/hpc/algorithms/img/mm-vectorized-plot.svg)

同样有意思的是，朴素实现与未向量化的转置版本大体持平——甚至略微更快，因为它不需要做转置。

你或许以为顺序读取会带来某种普遍的性能收益，毕竟取的缓存行更少，但事实并非如此：取 `b` 的第一列确实更慢一点，但接下来 15 次列读取都与第一次落在相同的缓存行里，所以它们无论如何都会被缓存——除非矩阵大到连 `n × cache_line_size` 字节都放不进缓存，而对任何实际的矩阵大小这都不会发生。

真正让性能劣化的，只是少数几个特定的矩阵大小，原因是[缓存关联性](/hpc/cpu-cache/associativity/)的效应：当 $n$ 是大的 2 的幂的倍数时，我们取到的 `b` 的地址很可能全部映射到同一组缓存行，等效缓存容量随之缩水。这解释了 $n = 1920 = 2^7 \times 3 \times 5$ 时 30% 的性能凹陷；而对 $1536 = 2^9 \times 3$ 你能看到更明显的一个：大约比 $n=1535$ 慢 3 倍。

所以，与直觉相反，转置矩阵对缓存并无帮助——而且在朴素的标量实现里，我们本来也没有真正被内存带宽卡住。但向量化的实现肯定被卡住了，那就来提升它的 I/O 效率。

## 寄存器复用 {#register-reuse}

借用 Python 风格的记号指代子矩阵：要计算格子 $C[x][y]$，我们需要计算 $A[x][:]$ 与 $B[:][y]$ 的点积，这需要取 $2n$ 个元素——即便我们把 $B$ 按列主序存储也是如此。

<!-- Any two cells of A and B are used to update some cell of C. -->

要计算 $C[x:x+2][y:y+2]$——一个 $2 \times 2$ 大小的 $C$ 子矩阵——只需要 $A$ 的两行和 $B$ 的两列，即 $A[x:x+2][:]$ 与 $B[:][y:y+2]$，总共含 $4n$ 个元素，却更新*四个*元素而非*一个*——按 I/O 效率算改善了 $\frac{2n / 1}{4n / 4} = 2$ 倍。

<!--

To actually avoid reading more data, we need to read these $2+2$ rows and columns in parallel and update all $2 \times 2$ cells at once using all possible combinations of products.

-->

为避免重复取数，我们需要并行地遍历这些行和列，并计算全部 $2 \times 2$ 种乘积组合。下面是一个概念验证：

```c++
void kernel_2x2(int x, int y) {
    int c00 = 0, c01 = 0, c10 = 0, c11 = 0;

    for (int k = 0; k < n; k++) {
        // read rows
        int a0 = a[x][k];
        int a1 = a[x + 1][k];

        // read columns
        int b0 = b[k][y];
        int b1 = b[k][y + 1];

        // update all combinations
        c00 += a0 * b0;
        c01 += a0 * b1;
        c10 += a1 * b0;
        c11 += a1 * b1;
    }

    // write the results to C
    c[x][y]         = c00;
    c[x][y + 1]     = c01;
    c[x + 1][y]     = c10;
    c[x + 1][y + 1] = c11;
}
```

现在只需在 $C$ 的所有 2×2 子矩阵上调用这个核函数，但我们不打算评测它：虽然这个算法在 I/O 操作上更优，它还是打不过我们基于 SIMD 的实现。我们不如直接推广这个思路，一步到位设计一个类似的*向量化*核函数。

<!-- It also boosts instruction-level parallelism (we don't have to wait between iterations to update the loop state) and saves some cycles from executing the read instructions.

Of course, although better in terms of I/O, this $2 \times 2$ update would not beat our vectorized implementation, so we are not going to try this version in particular and instead will scale the idea right away.

-->

## 设计核函数 {#designing-the-kernel}

我们不设计一个从零计算 $h \times w$ 的 $C$ 子矩阵的核函数，而是声明一个对它做*更新*的函数：使用从 $l$ 到 $r$ 的 $A$ 的列，以及从 $l$ 到 $r$ 的 $B$ 的行。眼下这看起来像是过度泛化，但这个函数接口稍后会派上用场。

<!--

We follow this approach and design a general kernel that updates a $h \times w$ submatrix of C using columns from $l$ to $r$ of $A$ and rows from $l$ to $r$ of $B$ (i.e., not a full computation, but only a partial update — it will be clear why later). 

-->

至于 $h$ 和 $w$ 取多少，有几个性能层面的考量：

- 一般地，要计算一个 $h \times w$ 子矩阵，需要取 $2 \cdot n \cdot (h + w)$ 个元素。为优化 I/O 效率，我们希望 $\frac{h \cdot w}{h + w}$ 这个比值尽量高，这要用大而接近方形的子矩阵来达成。
- 我们想用所有现代 x86 架构都有的 [FMA](https://en.wikipedia.org/wiki/FMA_instruction_set)（“融合乘加”，fused multiply-add）指令。顾名思义，它执行 `c += a * b` 操作——正是点积的核心——一次处理 8 元素向量，免去分别执行向量乘法和加法。<!-- saxpy: Single-Precision A·X Plus Y -->
- 为了更好地利用这条指令，我们要发挥[指令级并行](/hpc/pipelining/)。在 Zen 2 上，`fma` 指令延迟为 5、吞吐量为 2，意味着我们需要并发执行至少 $5 \times 2 = 10$ 条才能喂饱它的执行端口。
- 我们要避免寄存器溢出（不必要地在寄存器与内存之间搬运数据），而我们只有 $16$ 个可用作累加器的逻辑向量寄存器（还要减去那些需要存放临时值的）。

出于这些原因，我们选定 $6 \times 16$ 的核函数。这样，我们一次处理 $96$ 个元素，它们存放在 $6 \times 2 = 12$ 个向量寄存器中。为高效地更新它们，采用如下流程：

<!--

We [broadcast](/hpc/simd/moving/#broadcast) an element of A, and then use it to update the first row ($8 + 8$ elements). Then we load the one below it, and so on. When we have updated the last row, we move to the next $6$ elements to the right.

The final implementation is simpler than it sounds:

-->

```c++
// update 6x16 submatrix C[x:x+6][y:y+16]
// using A[x:x+6][l:r] and B[l:r][y:y+16]
void kernel(float *a, vec *b, vec *c, int x, int y, int l, int r, int n) {
    vec t[6][2]{}; // will be zero-filled and stored in ymm registers

    for (int k = l; k < r; k++) {
        for (int i = 0; i < 6; i++) {
            // broadcast a[x + i][k] into a register
            vec alpha = vec{} + a[(x + i) * n + k]; // converts to a broadcast
            // multiply b[k][y:y+16] by it and update t[i][0] and t[i][1]
            for (int j = 0; j < 2; j++)
                t[i][j] += alpha * b[(k * n + y) / 8 + j]; // converts to an fma
        }
    }

    // write the results back to C
    for (int i = 0; i < 6; i++)
        for (int j = 0; j < 2; j++)
            c[((x + i) * n + y) / 8 + j] += t[i][j];
}
```

我们需要 `t`，是为了让编译器把这些元素存进向量寄存器。我们本可以直接更新它们在 `c` 中的最终去处，但遗憾的是，编译器会把它们写回内存，造成减速（到处加 `__restrict__` 关键字也无济于事）。

展开这些循环、并把 `b` 的加载提升（hoist）出 `i` 循环（`b[(k * n + y) / 8 + j]` 不依赖 `i`，可以只加载一次、在全部 6 轮迭代中复用）之后，编译器生成的代码更接近这样：

<!-- /hpc/simd/intrinsics/#simd-intrinsics -->

```c++
for (int k = l; k < r; k++) {
    __m256 b0 = _mm256_load_ps((__m256*) &b[k * n + y];
    __m256 b1 = _mm256_load_ps((__m256*) &b[k * n + y + 8];
    
    __m256 a0 = _mm256_broadcast_ps((__m128*) &a[x * n + k]);
    t00 = _mm256_fmadd_ps(a0, b0, t00);
    t01 = _mm256_fmadd_ps(a0, b1, t01);

    __m256 a1 = _mm256_broadcast_ps((__m128*) &a[(x + 1) * n + k]);
    t10 = _mm256_fmadd_ps(a1, b0, t10);
    t11 = _mm256_fmadd_ps(a1, b1, t11);

    // ...
}
```

我们用了 $12+3=15$ 个向量寄存器、共 $6 \times 3 + 2 = 20$ 条指令来完成 $16 \times 6 = 96$ 次更新。假设没有其他瓶颈，我们应该能打满 `_mm256_fmadd_ps` 的吞吐量。

注意这个核函数是体系结构相关的。如果没有 `fma`，或者它的吞吐量/延迟不同，或者 SIMD 宽度是 128 或 512 位，我们都会做出不同的设计选择。多平台的 BLAS 实现[搭载许多核函数](https://github.com/xianyi/OpenBLAS/tree/develop/kernel)，每一个都由人工用汇编写成、针对特定体系结构优化。

其余实现平平无奇。与前面向量化的实现类似，只需把矩阵搬进内存对齐的数组，用核函数替换最内层循环：

```c++
void matmul(const float *_a, const float *_b, float *_c, int n) {
    // to simplify the implementation, we pad the height and width
    // so that they are divisible by 6 and 16 respectively
    int nx = (n + 5) / 6 * 6;
    int ny = (n + 15) / 16 * 16;
    
    float *a = alloc(nx * ny);
    float *b = alloc(nx * ny);
    float *c = alloc(nx * ny);

    for (int i = 0; i < n; i++) {
        memcpy(&a[i * ny], &_a[i * n], 4 * n);
        memcpy(&b[i * ny], &_b[i * n], 4 * n); // we don't need to transpose b this time
    }

    for (int x = 0; x < nx; x += 6)
        for (int y = 0; y < ny; y += 16)
            kernel(a, (vec*) b, (vec*) c, x, y, 0, n, ny);

    for (int i = 0; i < n; i++)
        memcpy(&_c[i * n], &c[i * ny], 4 * n);
    
    std::free(a);
    std::free(b);
    std::free(c);
}
```

这改善了基准性能，但只提高了约 40%：

![](/en/hpc/algorithms/img/mm-kernel-barplot.svg)

在更小的数组上加速比高得多（2–3 倍），说明内存带宽问题依然存在：

![](/en/hpc/algorithms/img/mm-kernel-plot.svg)

如果你读过[缓存无关算法](/hpc/external-memory/oblivious/)那一节，就知道这类问题的一种万能解法：把所有矩阵切成四份，执行八次递归的分块矩阵乘法，再小心地把结果合并起来。这个方案实践中可用，但[递归有开销](/hpc/architecture/functions/)，也不便于精调算法，所以我们改走另一条更简单的路。

## 分块 {#blocking}

分治技巧的*缓存感知*替代方案是*缓存分块*（cache blocking）：把数据切成能装进缓存的块，一块一块地处理。如果缓存不止一层，可以做层次化分块：先选一个装得进 L3 缓存的数据块，再把它切成装得进 L2 缓存的块，依此类推。这种做法需要事先知道缓存大小，但通常更容易实现，实践中也更快。

矩阵上的缓存分块不如数组上那么显而易见，但大致思路是：

- 选取 $B$ 的一个装得进 L3 缓存的子矩阵（比如它的一部分列）；
- 选取 $A$ 的一个装得进 L2 缓存的子矩阵（比如它的一部分行）；
- 在已选定的 $B$ 的子矩阵中再选取一个装得进 L1 缓存的子矩阵（它的一部分行）；
- 用核函数更新 $C$ 的相应子矩阵。

Jukka Suomela 做了一个很好的[可视化](https://jukkasuomela.fi/cache-blocking-demo/)（其中展示了多种不同做法；你关心的是最后一种）。

注意先从矩阵 $B$ 开始这一决定并非随意。核函数执行期间，我们读 $A$ 的元素远慢于读 $B$ 的元素：$A$ 一次只取一个元素并广播，然后与 $16$ 个来自 $B$ 的元素相乘。因此我们希望 $B$ 在 L1 缓存里、$A$ 可以留在 L2 缓存里，而不是反过来。

这听起来很复杂，但只需再加三层外层 `for` 循环就能实现；这三层循环合称*宏内核*（macro-kernel），而那个更新 6×16 子矩阵的高度优化的底层函数则称为*微内核*（micro-kernel）：

```c++
const int s3 = 64;  // how many columns of B to select
const int s2 = 120; // how many rows of A to select 
const int s1 = 240; // how many rows of B to select

for (int i3 = 0; i3 < ny; i3 += s3)
    // now we are working with b[:][i3:i3+s3]
    for (int i2 = 0; i2 < nx; i2 += s2)
        // now we are working with a[i2:i2+s2][:]
        for (int i1 = 0; i1 < ny; i1 += s1)
            // now we are working with b[i1:i1+s1][i3:i3+s3]
            // and we need to update c[i2:i2+s2][i3:i3+s3] with [l:r] = [i1:i1+s1]
            for (int x = i2; x < std::min(i2 + s2, nx); x += 6)
                for (int y = i3; y < std::min(i3 + s3, ny); y += 16)
                    kernel(a, (vec*) b, (vec*) c, x, y, i1, std::min(i1 + s1, n), ny);
```

缓存分块彻底消除了内存瓶颈：

![](/en/hpc/algorithms/img/mm-blocked-barplot.svg)

性能不再（显著）受问题规模影响：

![](/en/hpc/algorithms/img/mm-blocked-plot.svg)

注意 $1536$ 处的凹陷仍在：缓存关联性仍在影响性能。要缓解它，可以调整步长常数或在布局中插入空洞，但我们暂且不折腾这个。

## 优化 {#optimization}

要进一步逼近性能极限，还需要几个优化：

- 去掉内存分配，直接操作传给函数的数组。注意 `a` 无需任何处理——我们一次只读它一个元素；`c` 可以用[非对齐](/hpc/simd/moving/#aligned-loads-and-stores)的 `store`——它很少被使用；所以唯一要操心的是读取 `b`。
- 去掉 `std::min`，让尺寸参数（基本）恒定，可以被编译器嵌进机器码（这也能让它更高效地[展开](/hpc/architecture/loops/)微内核循环，并免去运行期检查）。
- 用 12 个向量变量手写微内核（编译器似乎难以把它们留在寄存器里，总是先写到一个临时内存位置、再写到 $C$）。

这些优化很直接但实现起来相当繁琐，所以我们不在这里列出[代码](https://github.com/sslotin/amh-code/blob/main/matmul/v5-unrolled.cc)。有效地支持“奇怪”的矩阵大小还需要更多工作，这也正是我们只对 $48 = \frac{6 \cdot 16}{\gcd(6, 16)}$ 的倍数大小跑基准测试的原因。

<!--

Effectively supporting weird sizes requires a bit more work, and this is the reason why we benchmarked at an array sizes that are divisible by $48 = \frac{6 \cdot 16}{\gcd(6, 16)}$. We leave the code out, because the change is large and tedious and involves slightly modifying the benchmarking code itself. It is straightforward, but we only implement the version for this particular size, whithout any safety checks. Cheating on the benchmark.

But avoiding moving anything pays off. 

-->

这些细小的改进层层叠加，又带来了 50% 的提升：

![](/en/hpc/algorithms/img/mm-noalloc.svg)

我们其实离理论性能极限已经不远——它可以算出来：SIMD 宽度乘以 `fma` 指令吞吐量乘以时钟频率：

$$
\underbrace{8}_{SIMD} \cdot \underbrace{2}_{thr.} \cdot \underbrace{2 \cdot 10^9}_{cycles/sec} = 32 \; GFLOPS \;\; (3.2 \cdot 10^{10})
$$

更有代表性的做法是对比某个实际的库，比如 [OpenBLAS](https://www.openblas.net/)。最省事的方式是直接[从 NumPy 调用矩阵乘法](/hpc/complexity/languages/#blas)。Python 或许带来少许开销，但它最终达到了理论极限的 80%，听起来是可信的（20% 的开销可以接受：矩阵乘法并不是 CPU 生下来唯一要干的事）。

![](/en/hpc/algorithms/img/mm-blas.svg)

我们达到了 BLAS 性能的约 93%、理论性能极限的约 75%——对本质上只有 40 行的 C 代码来说，这已经很了不起了。

有趣的是，整个东西可以揉进单独一个深层嵌套的 `for` 循环，并保持 BLAS 级的性能（假设我们身处 2050 年、用着 GCC 35 版——它终于不再把寄存器溢出搞砸了）：

```c++
for (int i3 = 0; i3 < n; i3 += s3)
    for (int i2 = 0; i2 < n; i2 += s2)
        for (int i1 = 0; i1 < n; i1 += s1)
            for (int x = i2; x < i2 + s2; x += 6)
                for (int y = i3; y < i3 + s3; y += 16)
                    for (int k = i1; k < i1 + s1; k++)
                        for (int i = 0; i < 6; i++)
                            for (int j = 0; j < 2; j++)
                                c[x * n / 8 + i * n / 8 + y / 8 + j]
                                += (vec{} + a[x * n + i * n + k])
                                   * b[n / 8 * k + y / 8 + j];
```

还有一种算术操作渐进更少的做法——[Strassen 算法](/hpc/external-memory/oblivious/#strassen-algorithm)——但它常数很大，只对[非常大的矩阵](https://arxiv.org/pdf/1605.01078.pdf)（$n > 4000$）高效，而那种规模下我们通常反正要么用多进程、要么用某种降维的近似方法。

## 推广 {#generalizations}

FMA 也支持 64 位浮点数，但不支持整数：加法和乘法得分开执行，性能随之下降。如果你能保证所有中间结果都能被 32 或 64 位浮点数精确表示（这[很常见](/hpc/arithmetic/errors/)），把它们转成浮点数算完再转回来可能更快。

这套方法也可以用于一些长得相似的计算。一个例子是按下式定义的“最小加矩阵乘法”（min-plus matrix multiplication）：

$$
(A \circ B)_{ij} = \min_{1 \le k \le n} (A_{ik} + B_{kj})
$$

它也被称为“距离积”（distance product），源于它的图论解释：把它应用于自身 $(D \circ D)$，结果就是由边权矩阵 $D$ 给定的完全带权图中，所有顶点对之间长度为二的最短路径矩阵。

距离积妙在：如果迭代这个过程，计算

$$
D_2 = D \circ D \\
D_4 = D_2 \circ D_2 \\
D_8 = D_4 \circ D_4 \\
\ldots
$$

……我们就能在 $O(\log n)$ 步内求出所有点对的最短路径：

```c++
for (int l = 0; l < logn; l++)
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                d[i][j] = min(d[i][j], d[i][k] + d[k][j]);
```

这需要 $O(n^3 \log n)$ 次操作。如果按一种特定的顺序做这些“两边松弛”，一遍就够——这就是 [Floyd-Warshall 算法](https://en.wikipedia.org/wiki/Floyd%E2%80%93Warshall_algorithm)：

```c++
for (int k = 0; k < n; k++)
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            d[i][j] = min(d[i][j], d[i][k] + d[k][j]);
```

有趣的是，把距离积同样向量化、执行 $O(\log n)$ 次（[也可能更少](https://arxiv.org/pdf/1904.01210.pdf)）、总计 $O(n^3 \log n)$ 次操作，比朴实地以 $O(n^3)$ 次操作执行 Floyd-Warshall 算法更快——虽然快得不多。

作为练习，试着加速这个“三重 for”计算。它比矩阵乘法的情形更难，因为此时迭代之间有了逻辑依赖，必须按特定顺序做更新；但仍然可以设计出[类似的核函数与分块迭代顺序](https://github.com/sslotin/amh-code/blob/main/floyd/blocked.cc)，实现总计 30–50 倍的加速。

## 致谢 {#acknowledgements}

最终算法最初由 Kazushige Goto 设计，是 GotoBLAS 与 OpenBLAS 的基础。作者本人在《[Anatomy of High-Performance Matrix Multiplication](https://www.cs.utexas.edu/~flame/pubs/GotoTOMS_revision.pdf)》中有更详细的阐述。

本文的讲述风格受 Jukka Suomela 的《[Programming Parallel Computers](http://ppc.cs.aalto.fi/)》课程启发，该课程有一个[类似的案例研究](http://ppc.cs.aalto.fi/ch2/)，讲的是加速距离积。
