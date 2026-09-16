---
title: 蒙哥马利乘法
weight: 4
draft: true
---

不出所料，[模算术](../modular)中的大量计算常常花在取模运算上——它与[一般整数除法](/hpc/arithmetic/division/)一样慢，视操作数大小通常要花 15-20 个周期。

对付这个麻烦的最好办法是完全避开取模运算——推迟它，或用[谓词化](/hpc/pipelining/branchless)替代它——例如在计算模和时就可以这样做：

```cpp
const int M = 1e9 + 7;

// input: array of n integers in the [0, M) range
// output: sum modulo M
int slow_sum(int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++)
        s = (s + a[i]) % M;
    return s;
}

int fast_sum(int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++) {
        s += a[i]; // s < 2 * M
        s = (s >= M ? s - M : s); // will be replaced with cmov
    }
    return s;
}

int faster_sum(int *a, int n) {
    long long s = 0; // 64-bit integer to handle overflow
    for (int i = 0; i < n; i++)
        s += a[i]; // will be vectorized
    return s % M;
}
```

然而有时你面对的只是一长串模乘法，没有什么好办法能溜掉不做取余——除了那些需要常量模数和一些预计算的[整数除法技巧](/hpc/arithmetic/division/)。

不过，还有一种专门为模算术设计的技术，称为*蒙哥马利乘法*（Montgomery multiplication）。

### 蒙哥马利空间 {#montgomery-space}

蒙哥马利乘法的做法是：先把乘数变换到*蒙哥马利空间*（Montgomery space）——在那里模乘法可以廉价地进行——等到需要真实值时再把它们变换回去。与一般的整数除法方法不同，蒙哥马利乘法用来做单次模约减并不划算，只有在一长串模运算中才值得。

该空间由模数 $n$ 和一个满足 $r \ge n$ 且与 $n$ 互素的正整数定义。算法中涉及以 $r$ 为除数的取模和除法，所以实践中把 $r$ 取为 $2^{32}$ 或 $2^{64}$，这样这些运算分别可以用右移和按位与完成。

<!-- Therefore $n$ needs to be an odd number so that every power of $2$ will be coprime to $n$. And if it is not, we can make it odd (?). -->

**定义。** *代表元*（representative）$\bar x$——即数 $x$ 在蒙哥马利空间中的代表——定义为

$$
\bar{x} = x \cdot r \bmod n
$$

计算这个变换需要一次乘法和一次取模——后者正是我们一开始想优化掉的昂贵操作——所以我们只在进出蒙哥马利空间的开销划算时才使用这个方法，而不用它做一般性的模乘法。

<!-- Note that the transformation is actually such a multiplication that we want to optimize, so it is still an expensive operation. However, we will only need to transform a number into the space once, perform as many operations as we want efficiently in that space and at the end transform the final result back, which should be profitable if we are doing lots of operations modulo $n$. -->

在蒙哥马利空间内部，加法、减法和相等性检验都照常进行：

$$
x \cdot r + y \cdot r \equiv (x + y) \cdot r \bmod n
$$

但乘法不是这样。把蒙哥马利空间中的乘法记作 $*$，"普通"乘法记作 $\cdot$，我们期望的结果是：

$$
\bar{x} * \bar{y} = \overline{x \cdot y} = (x \cdot y) \cdot r \bmod n
$$

而蒙哥马利空间中的普通乘法给出的是：

$$
\bar{x} \cdot \bar{y} = (x \cdot y) \cdot r \cdot r \bmod n
$$

因此，蒙哥马利空间中的乘法定义为

$$
\bar{x} * \bar{y} = \bar{x} \cdot \bar{y} \cdot r^{-1} \bmod n
$$

这意味着，在蒙哥马利空间中按普通方式把两个数相乘之后，我们需要将结果*约减*（reduce）：乘以 $r^{-1}$ 并取模——而恰好有一种高效办法可以完成这个特定运算。

### 蒙哥马利约减 {#montgomery-reduction}

设 $r=2^{32}$，模数 $n$ 是 32 位，需要约减的数 $x$ 是 64 位（两个 32 位数的乘积）。我们的目标是计算 $y = x \cdot r^{-1} \bmod n$。

由于 $r$ 与 $n$ 互素，我们知道存在两个数 $r^{-1}$ 和 $n^\prime$，它们都落在 $[0, n)$ 范围内，使得

$$
r \cdot r^{-1} + n \cdot n^\prime = 1
$$

并且 $r^{-1}$ 和 $n^\prime$ 都可以计算出来，例如用[扩展欧几里得算法](../euclid-extended)。

利用这个恒等式，可以把 $r \cdot r^{-1}$ 表达为 $(1 - n \cdot n^\prime)$，把 $x \cdot r^{-1}$ 写成

$$
\begin{aligned}
x \cdot r^{-1} &= x \cdot r \cdot r^{-1} / r
\\             &= x \cdot (1 - n \cdot n^{\prime}) / r
\\             &= (x - x \cdot n \cdot n^{\prime}    ) / r
\\             &\equiv (x - x \cdot n \cdot n^{\prime} + k \cdot r \cdot n) / r &\pmod n &\;\;\text{(for any integer $k$)}
\\             &\equiv (x - (x \cdot n^{\prime} - k \cdot r) \cdot n) / r &\pmod n
\end{aligned}
$$

现在，若把 $k$ 取为 $\lfloor x \cdot n^\prime / r \rfloor$（$x \cdot n^\prime$ 乘积的高 64 位），它会被消去，$(k \cdot r - x \cdot n^{\prime})$ 就简单地等于 $x \cdot n^{\prime} \bmod r$（$x \cdot n^\prime$ 的低 32 位），由此可得：

$$
x \cdot r^{-1} \equiv (x - x \cdot n^{\prime} \bmod r \cdot n) / r
$$

算法本身只是求这个公式的值：做两次乘法算出 $q = x \cdot n^{\prime} \bmod r$ 和 $m = q \cdot n$，然后从 $x$ 中减去它并将结果右移以除以 $r$。

唯一还需要处理的是结果可能不在 $[0, n)$ 范围内；但由于

$$
x < n \cdot n < r \cdot n \implies x / r < n
$$

以及

$$
m = q \cdot n < r \cdot n \implies m / r < n
$$

可以保证

$$
-n < (x - m) / r < n
$$

因此，只需检查结果是否为负，若是则加上 $n$，得到如下算法：

```c++
typedef __uint32_t u32;
typedef __uint64_t u64;

const u32 n = 1e9 + 7, nr = inverse(n, 1ull << 32);

u32 reduce(u64 x) {
    u32 q = u32(x) * nr;      // q = x * n' mod r
    u64 m = (u64) q * n;      // m = q * n
    u32 y = (x - m) >> 32;    // y = (x - m) / r
    return x < m ? y + n : y; // if y < 0, add n to make it be in the [0, n) range
}
```

最后这个检查相对便宜，但它仍在关键路径上。如果我们能接受结果落在 $[0, 2 \cdot n - 2]$ 而非 $[0, n)$ 范围内，可以去掉它并无条件地给结果加上 $n$：

```c++
u32 reduce(u64 x) {
    u32 q = u32(x) * nr;
    u64 m = (u64) q * n;
    u32 y = (x - m) >> 32;
    return y + n
}
```

我们还可以把 `>> 32` 操作在计算图中提前一步，计算 $\lfloor x / r \rfloor - \lfloor m / r \rfloor$ 而不是 $(x - m) / r$。这是正确的，因为 $x$ 和 $m$ 的低 32 位反正相等，既然

$$
m = x \cdot n^\prime \cdot n \equiv x \pmod r
$$

但为什么我们要自愿做两次右移而不是一次？这样是有好处的：对 `((u64) q * n) >> 32`，我们需要做一次 32×32 乘法并取结果的高 32 位（x86 的 `mul` 指令[本来就会](/hpc/arithmetic/integer/#128-bit-integers)把它写进另一个单独的寄存器，所以不花任何代价），而另一个右移 `x >> 32` 不在关键路径上。

```c++
u32 reduce(u64 x) {
    u32 q = u32(x) * nr;
    u32 m = ((u64) q * n) >> 32;
    return (x >> 32) + n - m;
}
```

蒙哥马利乘法相对其他模约减方法的一个主要优势是它不需要非常大的数据类型：它只需要一次 $r \times r$ 乘法，并取出结果较低和较高的 $r$ 位——大多数硬件对此[有专门支持](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=7395,7392,7269,4868,7269,7269,1820,1835,6385,5051,4909,4918,5051,7269,6423,7410,150,2138,1829,1944,3009,1029,7077,519,5183,4462,4490,1944,5055,5012,5055&techs=AVX,AVX2&text=mul)，这也使它很容易推广到 [SIMD](/hpc/simd/) 和更大的数据类型：

```c++
typedef __uint128_t u128;

u64 reduce(u128 x) const {
    u64 q = u64(x) * nr;
    u64 m = ((u128) q * n) >> 64;
    return (x >> 64) + n - m;
}
```

注意，128 位对 64 位的取模无法用一般的整数除法技巧完成：编译器会[退而](https://godbolt.org/z/fbEE4v4qr)调用一个缓慢的[高精度算术库函数](https://github.com/llvm-mirror/compiler-rt/blob/69445f095c22aac2388f939bedebf224a6efcdaf/lib/builtins/udivmodti4.c#L22)来支持它。

### 更快的逆元与变换 {#faster-inverse-and-transform}

蒙哥马利乘法本身很快，但它需要一些预计算：

- 对 $n$ 求模 $r$ 的逆元以算出 $n^\prime$；
- 把数变换*到*蒙哥马利空间；
- 把数从蒙哥马利空间变换*出来*。

最后一个操作用我们刚实现的 `reduce` 过程已经能高效完成，前两个则还可以稍微优化。

**计算逆元** $n^\prime = n^{-1} \bmod r$ 可以做得比扩展欧几里得算法更快，办法是利用 $r$ 是 2 的幂这一事实和下面的恒等式：

$$
a \cdot x \equiv 1 \bmod 2^k
\implies
a \cdot x \cdot (2 - a \cdot x)
\equiv
1 \bmod 2^{2k}
$$

证明：

$$
\begin{aligned}
a \cdot x \cdot (2 - a \cdot x)
   &= 2 \cdot a \cdot x - (a \cdot x)^2
\\ &= 2 \cdot (1 + m \cdot 2^k) - (1 + m \cdot 2^k)^2
\\ &= 2 + 2 \cdot m \cdot 2^k - 1 - 2 \cdot m \cdot 2^k - m^2 \cdot 2^{2k}
\\ &= 1 - m^2 \cdot 2^{2k}
\\ &\equiv 1 \bmod 2^{2k}.
\end{aligned}
$$

我们可以从 $x = 1$（即 $a$ 模 $2^1$ 的逆元）出发，恰好应用这个恒等式 $\log_2 r$ 次，每次让逆元的位数翻倍——多少让人联想到[牛顿迭代法](/hpc/arithmetic/newton/)。

**变换**一个数到蒙哥马利空间，可以用乘以 $r$ 再按[常规方法](/hpc/arithmetic/division/)取模来完成，但我们也可以利用这个关系式：

$$
\bar{x} = x \cdot r \bmod n = x * r^2
$$

把一个数变换进空间，只是一次乘以 $r^2$ 的乘法。因此，我们可以预计算 $r^2 \bmod n$，改做一次乘法和约减——但这未必真的更快，因为数乘以 $r=2^{k}$ 可以用左移实现，而乘以 $r^2 \bmod n$ 则不能。

### 完整实现 {#complete-implementation}

把所有这些包装进一个单一的 `constexpr` 结构体是很方便的：

```c++
struct Montgomery {
    u32 n, nr;
    
    constexpr Montgomery(u32 n) : n(n), nr(1) {
        // log(2^32) = 5
        for (int i = 0; i < 5; i++)
            nr *= 2 - n * nr;
    }

    u32 reduce(u64 x) const {
        u32 q = u32(x) * nr;
        u32 m = ((u64) q * n) >> 32;
        return (x >> 32) + n - m;
        // returns a number in the [0, 2 * n - 2] range
        // (add a "x < n ? x : x - n" type of check if you need a proper modulo)
    }

    u32 multiply(u32 x, u32 y) const {
        return reduce((u64) x * y);
    }

    u32 transform(u32 x) const {
        return (u64(x) << 32) % n;
        // can also be implemented as multiply(x, r^2 mod n)
    }
};
```

为了测试性能，我们可以把蒙哥马利乘法接入[快速幂](../exponentiation)：

```c++
constexpr Montgomery space(M);

int inverse(int _a) {
    u64 a = space.transform(_a);
    u64 r = space.transform(1);
    
    #pragma GCC unroll(30)
    for (int l = 0; l < 30; l++) {
        if ( (M - 2) >> l & 1 )
            r = space.multiply(r, a);
        a = space.multiply(a, a);
    }

    return space.reduce(r);
}
```

原版快速幂配合编译器生成的快速取模技巧每次 `inverse` 调用约需 170ns，而这个实现约需 166ns；若省去 `transform` 和 `reduce`，还可以降到约 158ns（一个合理的使用场景是把 `inverse` 用作更大的模运算中的子过程）。这是个不大的改进，但对 SIMD 应用和更大的数据类型，蒙哥马利乘法的优势会大得多。

**练习。** 实现高效的*模*意义下的[矩阵乘法](/hpc/algorithms/matmul)。
