---
title: 整数分解
weight: 3
draft: true
---

把整数分解成素数的乘积，是计算[数论](/hpc/number-theory/)的核心问题。它至少从公元前 3 世纪起就有人[研究](https://www.cs.purdue.edu/homes/ssw/chapter3.pdf)，人们还发展出了[许多方法](https://en.wikipedia.org/wiki/Category:Integer_factorization_algorithms)，各自对不同类型的输入高效。

在本案例研究中，我们专门考虑*字长级*（word-sized）整数的分解：也就是 $10^9$ 和 $10^{18}$ 这个量级的数。与本书其他章节不同，在这一篇里你可能会真的学到渐进意义上更优的算法：我们从几个基本方法入手，逐步构建出运行时间为 $O(\sqrt[4]{n})$ 的 *Pollard rho 算法*，并把它优化到能在 0.3–0.4ms 内分解 60 位半素数（semiprime）、比之前的最佳实现快约 3 倍的地步。

<!--
Integer factorization is interesting because of the RSA problem.
Unlike other case studies of this book, in this one you will actually learn an asymptotically better algorithm that you've never known before — Pollard rho algorithm — which we optimize so that it is almost 4 times faster than the existing implementation, to the best of my knowledge.
-->

### 基准测试 {#benchmark}

对所有方法，我们都实现一个 `find_factor` 函数：它接受一个正整数 $n$，返回它的任意一个非平凡因子（若该数是素数则返回 `1`）：

```c++
// I don't feel like typing "unsigned long long" each time
typedef __uint16_t u16;
typedef __uint32_t u32;
typedef __uint64_t u64;
typedef __uint128_t u128;

u64 find_factor(u64 n);
```

要求完整分解，可以对 $n$ 反复应用它、约去已找到的因子，直到再也找不到新的因子为止：

```c++
vector<u64> factorize(u64 n) {
    vector<u64> factorization;
    do {
        u64 d = find_factor(n);
        factorization.push_back(d);
        n /= d;
    } while (d != 1);
    return factorization;
}
```

每去掉一个因子，问题都会显著变小，因此完整分解的最坏运行时间就等于一次 `find_factor` 调用的最坏运行时间。

对许多分解算法（包括本节介绍的那些）而言，运行时间取决于较小的那个素因子。因此，为构造最坏输入，我们使用*半素数*（semiprime）：两个大小同阶的素数 $p \le q$ 的乘积。我们生成 $k$ 位半素数的方式，是取两个随机的 $\lfloor k / 2 \rfloor$ 位素数相乘。

由于其中一些算法天然是随机化的，我们也容忍一个较小（<1%）的假阴性错误率（即 `find_factor` 在 $n$ 为合数时仍返回 `1`）；这个错误率其实可以几乎无性能代价地降到接近于零。

### 试除法 {#trial-division}

<!--

Trial division was first described by Fibonacci in 1202. Although it was probably known to animals. Perhaps some animals can factor? The scientific priority probably belongs to dinosaurs or ancient fish trying to divvy stuff up.

0.056024

-->

最基本的方法，就是把每个小于 $n$ 的整数都拿来试除一次：

```c++
u64 find_factor(u64 n) {
    for (u64 d = 2; d < n; d++)
        if (n % d == 0)
            return d;
    return 1;
}
```

可以注意到：若 $n$ 能被某个 $d < \sqrt n$ 整除，则它也能被 $\frac{n}{d} > \sqrt n$ 整除，无须单独检查后者。这让我们可以提前终止试除，只检查不超过 $\sqrt n$ 的候选因子：

```c++
u64 find_factor(u64 n) {
    for (u64 d = 2; d * d <= n; d++)
        if (n % d == 0)
            return d;
    return 1;
}
```

在我们的基准测试中，$n$ 是半素数，且我们总能找到较小的那个因子，因此 $O(n)$ 和 $O(\sqrt n)$ 两种实现的表现完全相同，都能每秒分解约 2k 个 30 位数——而分解单个 60 位数则要花整整 20 秒。

### 查找表 {#lookup-table}

如今，你只需在 Linux 终端或 Google 搜索框里输入 `factor 57`，就能得到任意数的分解。但在计算机发明之前，更实用的做法是使用*分解表*（factorization table）：一种包含前 $N$ 个数的分解的专门书籍。

我们也可以用同样的思路，[在编译期间](/hpc/compilation/precalc/)计算这些查找表。为节省空间，可以只存每个数的最小因子。由于最小因子不超过 $\sqrt n$，对 16 位整数我们只需每数一字节：

```c++
template <int N = (1<<16)>
struct Precalc {
    unsigned char divisor[N];

    constexpr Precalc() : divisor{} {
        for (int i = 0; i < N; i++)
            divisor[i] = 1;
        for (int i = 2; i * i < N; i++)
            if (divisor[i] == 1)
                for (int k = i * i; k < N; k += i)
                    divisor[k] = i;
    }
};

constexpr Precalc P{};

u64 find_factor(u64 n) {
    return P.divisor[n];
}
```

用这个方法，我们可以每秒处理 3M 个 16 位整数，尽管对更大的数它多半会[变慢](../cpu-cache/bandwidth/)。计算并存储前 $2^{16}$ 个数的最小因子只需几毫秒和 64KB 内存，但它对更大的输入无法很好地扩展。

### 轮式分解 {#wheel-factorization}

为了节省纸张，计算机时代之前的分解表通常排除能被 $2$ 和 $5$ 整除的数，使表的体积缩减为原来的 ½ × ⅘ = 0.4。在十进制下，你可以很快判断一个数能否被 $2$ 或 $5$ 整除（看末位数字），并不断地把 $n$ 除以 $2$ 或 $5$，直到除不动为止，最终落到分解表中的某个条目上。

我们可以对试除法施以类似的技巧：先检查数是否能被 $2$ 整除，然后只考虑奇数因子：

```c++
u64 find_factor(u64 n) {
    if (n % 2 == 0)
        return 2;
    for (u64 d = 3; d * d <= n; d += 2)
        if (n % d == 0)
            return d;
    return 1;
}
```

需要执行的除法少了 50%，这个算法也因此快了一倍。

这个方法还可以推广：如果数不能被 $3$ 整除，我们也可以跳过所有 $3$ 的倍数，其他因子同理。问题在于，随着要排除的素数增多，只遍历不被它们整除的数就没那么直观了，因为这些数的分布不规则——除非素数个数很少。

例如，若考虑 $2$、$3$、$5$，那么在前 $90$ 个数中，我们只需检查：

```center
(1,) 7, 11, 13, 17, 19, 23, 29,
31, 37, 41, 43, 47, 49, 53, 59,
61, 67, 71, 73, 77, 79, 83, 89…
```

你可以发现一个规律：这个序列每 $30$ 个数循环一次。这不奇怪，因为只需看一个数模 $2 \times 3 \times 5 = 30$ 的余数，就能判断它能否被 $2$、$3$ 或 $5$ 整除。这意味着我们只需检查 $8$ 个具有特定余数的数（每 $30$ 个一组），性能也按相应比例提升：

```c++
u64 find_factor(u64 n) {
    for (u64 d : {2, 3, 5})
        if (n % d == 0)
            return d;
    u64 offsets[] = {0, 4, 6, 10, 12, 16, 22, 24};
    for (u64 d = 7; d * d <= n; d += 30) {
        for (u64 offset : offsets) {
            u64 x = d + offset;
            if (n % x == 0)
                return x;
        }
    }
    return 1;
}
```

不出所料，它比朴素的试除法快 $\frac{30}{8} = 3.75$ 倍，每秒能处理约 7.6k 个 30 位数。纳入更多素数还能继续提升性能，但收益是递减的：新增一个素数 $p$ 只让迭代次数减少 $\frac{1}{p}$，却让跳过表（skip-list）的大小增至 $p$ 倍，需要成比例增加的内存。

### 预计算素数 {#precomputed-primes}

如果在轮式分解中不断增加素数的个数，最终会排除所有合数、只检查素因子。到了这一步，我们不再需要那个偏移量数组，而只需要一个素数数组：

```c++
const int N = (1 << 16);

struct Precalc {
    u16 primes[6542]; // # of primes under N=2^16

    constexpr Precalc() : primes{} {
        bool marked[N] = {};
        int n_primes = 0;

        for (int i = 2; i < N; i++) {
            if (!marked[i]) {
                primes[n_primes++] = i;
                for (int j = 2 * i; j < N; j += i)
                    marked[j] = true;
            }
        }
    }
};

constexpr Precalc P{};

u64 find_factor(u64 n) {
    for (u16 p : P.primes)
        if (n % p == 0)
            return p;
    return 1;
}
```

这个方法让我们每秒能处理近 20k 个 30 位整数，但对更大的（64 位）数就无能为力了——除非它们恰有小（$< 2^{16}$）因子。

注意这其实是一个渐进意义上的优化：$O(\frac{n}{\ln n})$ 个素数存在于前 $n$ 个数之中，因此该算法执行 $O(\frac{\sqrt n}{\ln \sqrt n})$ 次操作，而轮式分解只消去一个很大但恒定的比例的因子。如果把它扩展到 64 位数并预计算 $2^{32}$ 以内的所有素数（存储它们需要几百 MB 内存），相对加速比会增长到 $\frac{\ln \sqrt{n^2}}{\ln \sqrt n} = 2 \cdot \frac{1/2}{1/2} \cdot \frac{\ln n}{\ln n} = 2$ 倍。

包括这一种在内的所有试除法变体，瓶颈都在整数除法的速度上；如果我们事先知道除数、并允许一些额外的预计算，除法是可以被[优化](/hpc/arithmetic/division/)的。在我们的场景下，适合使用 [Lemire 除法判断](/hpc/arithmetic/division/#lemire-reduction)：

```c++
// ...precomputation is the same as before,
// but we store the reciprocal instead of the prime number itself
u64 magic[6542];
// for each prime i:
magic[n_primes++] = u64(-1) / i + 1;

u64 find_factor(u64 n) {
    for (u64 m : P.magic)
        if (m * n < m)
            return u64(-1) / m + 1;
    return 1;
}
```

这让算法快了约 18 倍：我们现在每秒能分解 **约 350k** 个 30 位数，这实际上是我们在该数域上最高效的算法。虽然用 [SIMD](/hpc/simd) 并行地执行这些判断多半还能再快一些，我们就到此为止，转而尝试另一种渐进意义上更优的做法。

### Pollard rho 算法 {#pollards-rho-algorithm}

<!--

Consider this weird code snippet:

```c++
u64 find_factor(u64 n) {
    while (true) {
        if (u64 g = gcd(randint(2, n - 1), n); g != 1)
            return g;
    }
}
```

It also searches for a factor, but it does so by repeatedly trying to compute the [GCD](../gcd) of $n$ and its random remainder, which would yield a valid divisor of $n$ if this remainder is not coprime with it. Surprisingly, this algorithm is not *that* terrible: it needs expected $O(\sqrt n)$ iterations in the worst case (times $\log n$ from GCD) because on each trial, it can hit not only $p$ or $q = \frac{n}{p}$, but also $\frac{n}{p} + \frac{n}{q} = O(\sqrt n)$ of their multiples.

By itself, this algorithm is just an esoteric way of computing factorization, but can be made useful. If, instead of random numbers, we apply this $\gcd$ trick to a particular number sequence, we get a $O(n^\frac{1}{4})$ approach known as Pollard rho algorithm.

Apart from this trick, Pollard rho algorithm relies on a consequence from the Birthday paradox: we need to add $O(\sqrt{n})$ random numbers from $1$ to $n$ to a set until we get a collision. 

-->

Pollard rho 是一个随机化的 $O(\sqrt[4]{n})$ 整数分解算法，它利用了[生日悖论](https://en.wikipedia.org/wiki/Birthday_problem)：

> 只需抽取 $d = \Theta(\sqrt{n})$ 个介于 $1$ 与 $n$ 之间的随机数，就能以很高的概率得到一次碰撞。

其原理是：加入的 $d$ 个元素中，每一个都有 $\frac{d}{n}$ 的概率与已有元素碰撞，因此碰撞次数的期望是 $\frac{d^2}{n}$。若 $d$ 渐进地小于 $\sqrt n$，这个比值随 $n \to \infty$ 趋于零；否则趋于无穷。

考虑某个函数 $f(x)$，它取一个余数 $x \in [0, n)$，并按一种从数论角度看近乎随机的方式把它映射到 $n$ 的另一个余数。具体地，我们将使用 $f(x) = x^2 + 1 \bmod n$，它对我们的用途而言足够随机。

现在，考虑一张图，其中每个数-顶点 $x$ 都有一条指向 $f(x)$ 的边。这样的图称为*函数图*（functional graph）。在函数图中，任何元素的“轨迹”——从该元素出发、沿边不断走下去的路径——最终都会绕成环（因为顶点集合有限，走着走着必然会走到一个已经访问过的顶点）。

![元素的轨迹形似希腊字母 ρ（rho），算法即因此得名](/en/hpc/algorithms/img/rho.jpg)

考虑某个特定元素 $x_0$ 的轨迹：

$$
x_0, \; f(x_0), \; f(f(x_0)), \; \ldots
$$

我们对该序列的每个元素都模去 $p$——$n$ 的最小素因子——得到一个新序列。

**引理.** 这个取模后的序列在进入循环之前的期望长度是 $O(\sqrt[4]{n})$。

**证明：** 由于 $p$ 是最小的因子，$p \leq \sqrt n$。每走一条新边，本质上就是生成一个 $0$ 到 $p$ 之间的随机数（我们把 $f$ 当作一个“确定性地随机”的函数）。生日悖论告诉我们，只需生成 $O(\sqrt p) = O(\sqrt[4]{n})$ 个数就会发生碰撞，从而进入循环。

虽然我们并不知道 $p$，这个模 $p$ 的序列只是想象出来的，但只要在其中找到一个环——即找到 $i$ 和 $j$ 满足

$$
f^i(x_0) \equiv f^j(x_0) \pmod p
$$

——我们就能随之求出 $p$ 本身：

$$
p = \gcd(|f^i(x_0) - f^j(x_0)|, n)
$$

算法本身要做的就是用这个 GCD 技巧配合 Floyd 的“[龟兔赛跑](https://en.wikipedia.org/wiki/Cycle_detection#Floyd's_tortoise_and_hare)”算法找出这个环和 $p$：我们维护两个指针 $i$ 和 $j = 2i$，并检查

$$
\gcd(|f^i(x_0) - f^j(x_0)|, n) \neq 1
$$

这等价于比较 $f^i(x_0)$ 和 $f^j(x_0)$ 模 $p$ 是否相等。由于 $j$（兔子）的步进速度是 $i$（乌龟）的两倍，两者的距离每轮迭代增加 $1$，最终会等于（或成为倍数于）环长，此时 $i$ 和 $j$ 指向相同的元素。而正如半页之前我们所证明的，到达一个环只需 $O(\sqrt[4]{n})$ 轮迭代：

```c++
u64 f(u64 x, u64 mod) {
    return ((u128) x * x + 1) % mod;
}

u64 diff(u64 a, u64 b) {
    // a and b are unsigned and so is their difference, so we can't just call abs(a - b)
    return a > b ? a - b : b - a;
}

const u64 SEED = 42;

u64 find_factor(u64 n) {
    u64 x = SEED, y = SEED, g = 1;
    while (g == 1) {
        x = f(f(x, n), n); // advance x twice
        y = f(y, n);       // advance y once
        g = gcd(diff(x, y));
    }
    return g;
}
```

> **译者注**：原文此行写作 `g = gcd(diff(x, y));`，缺少参数 `n`，应为 `g = gcd(diff(x, y), n);` 的笔误（对照下文 Pollard-Brent 一节的实现可知）；上文代码块与原文保持一致，未予改动。

它每秒只能处理约 25k 个 30 位数——比用快速除法技巧逐个检查素数慢了几乎 15 倍——但对 60 位数，它完胜所有 $\tilde{O}(\sqrt n)$ 算法，每秒能分解约 90 个。

### Pollard-Brent 算法 {#pollard-brent-algorithm}

Floyd 找环算法有一个问题：它移动迭代器的次数超过了必要——较慢的迭代器至少会把一半的顶点多访问一次。

解决它的一种办法是记住快迭代器访问过的值 $x_i$，并每两轮迭代用 $x_i$ 与 $x_{\lfloor i / 2 \rfloor}$ 的差计算一次 GCD。但也可以不耗额外内存、换一种原理实现：乌龟不必每轮都动，而是当迭代编号到达 2 的幂时，被重置为快迭代器当前的值。这样既能省下额外的迭代，又仍能用同样的 GCD 技巧在每轮比较 $x_i$ 和 $x_{2^{\lfloor \log_2 i \rfloor}}$：

```c++
u64 find_factor(u64 n) {
    u64 x = SEED;
    
    for (int l = 256; l < (1 << 20); l *= 2) {
        u64 y = x;
        for (int i = 0; i < l; i++) {
            x = f(x, n);
            if (u64 g = gcd(diff(x, y), n); g != 1)
                return g;
        }
    }

    return 1;
}
```

注意我们还给迭代次数设了上限，好让算法在有限时间内结束，并在 $n$ 恰好是素数时返回 `1`。

这一改动其实*并没有*提升性能，反而让算法慢了约 1.5 倍，这大概与 $x$ 已经过期（stale）有关。它把大部分时间花在计算 GCD 而非推进迭代器上——事实上，正因如此，该算法目前的时间复杂度是 $O(\sqrt[4]{n} \log n)$。

与其[优化 GCD 本身](../gcd)，我们不如减少它的调用次数。利用这样一个事实：若 $a$ 和 $b$ 中有一个含有因子 $p$，那么 $a \cdot b \bmod n$ 也含有它；于是不必分别计算 $\gcd(a, n)$ 和 $\gcd(b, n)$，而是计算 $\gcd(a \cdot b \bmod n, n)$。这样一来，我们可以把 GCD 的计算按每组 $M = O(\log n)$ 个分组，从而把 $\log n$ 从渐进复杂度中去掉：

```c++
const int M = 1024;

u64 find_factor(u64 n) {
    u64 x = SEED;
    
    for (int l = M; l < (1 << 20); l *= 2) {
        u64 y = x, p = 1;
        for (int i = 0; i < l; i += M) {
            for (int j = 0; j < M; j++) {
                y = f(y, n);
                p = (u128) p * diff(x, y) % n;
            }
            if (u64 g = gcd(p, n); g != 1)
                return g;
        }
    }

    return 1;
}
```

现在它每秒能执行 425 次分解，瓶颈在取模的速度上。

### 优化取模 {#optimizing-the-modulo}

最后一步是应用[蒙哥马利乘法](/hpc/number-theory/montgomery/)。由于模数是常数，我们可以把所有计算——推进迭代器、乘法、乃至计算 GCD——都搬到约减很便宜的蒙哥马利空间中进行：

```c++
struct Montgomery {
    u64 n, nr;
    
    Montgomery(u64 n) : n(n) {
        nr = 1;
        for (int i = 0; i < 6; i++)
            nr *= 2 - n * nr;
    }

    u64 reduce(u128 x) const {
        u64 q = u64(x) * nr;
        u64 m = ((u128) q * n) >> 64;
        return (x >> 64) + n - m;
    }

    u64 multiply(u64 x, u64 y) {
        return reduce((u128) x * y);
    }
};

u64 f(u64 x, u64 a, Montgomery m) {
    return m.multiply(x, x) + a;
}

const int M = 1024;

u64 find_factor(u64 n, u64 x0 = 2, u64 a = 1) {
    Montgomery m(n);
    u64 x = SEED;
    
    for (int l = M; l < (1 << 20); l *= 2) {
        u64 y = x, p = 1;
        for (int i = 0; i < l; i += M) {
            for (int j = 0; j < M; j++) {
                x = f(x, m);
                p = m.multiply(p, diff(x, y));
            }
            if (u64 g = gcd(p, n); g != 1)
                return g;
        }
    }

    return 1;
}
```

这个实现每秒能处理约 3k 个 60 位数，比 [PARI](https://pari.math.u-bordeaux.fr/) / [SageMath 的 `factor`](https://doc.sagemath.org/html/en/reference/structure/sage/structure/factorization.html) / `cat semiprimes.txt | time factor` 所测得的快约 3 倍。

### 进一步改进 {#further-improvements}

**优化.** 我们的 Pollard 算法实现仍有很大的优化空间：

- 我们或许可以使用更好的找环算法，利用图是随机的这一事实。例如，在前几轮迭代内就进入环的可能性很小（既然绕环之前，路径上每个顶点都是独立选取的，环长与入环前的路径长在期望上应当相等），所以大可以先让迭代器空跑一段时间，再开始用 GCD 技巧进行试验。
- 我们目前的瓶颈在推进迭代器上（蒙哥马利乘法的延迟远高于其倒数吞吐量），在等待它完成的间隙里，我们完全可以用先前的值做不止一次试验。
- 如果让算法的 $p$ 个实例以不同种子并行运行、其中一个找到答案即停止，总耗时就会快 $\sqrt p$ 倍（推理类似于生日悖论；试着自己证一证）。为此并不需要多个核：还有大量未被利用的[指令级并行](/hpc/pipelining/)可用，我们可以在同一线程上并发运行两三个相同的操作，或者用 [SIMD](/hpc/simd) 指令并行执行 4 或 8 次乘法。

再快 3 倍、达到约 10k/秒的吞吐量，我不会感到意外。如果你[实现](https://github.com/sslotin/amh-code/tree/main/factor)了其中一些想法，请[告诉我](http://sereja.me/)。

<!-- Another observation: the length of the "tail" and the cycle is equal in expectation, since when we loop around, we choose any vertex of the path we walked independently. How to optimize for the *average* case is unclear. -->

**错误.** 实际实现中还需要处理的另一个方面是可能的错误。我们目前的实现对 60 位数有 0.7% 的错误率，数越小错误率越高。这些错误有三个主要来源：

- 单纯没找到环（算法天然是随机的，不保证一定能找到）。此时需要做一次素性测试，并酌情重新开始。
- 变量 `p` 变成零（因为 $p$ 和 $q$ 都可能乘进乘积里）。随着输入变小或常量 `M` 增大，这会越来越容易发生。此时要么重启整个过程，要么（更好的做法）回滚最后 $M$ 轮迭代，逐个重新试验。
- 蒙哥马利乘法中的溢出。我们目前的实现对溢出的处理相当粗放，若 $n$ 很大，就需要添加更多 `x > mod ? x - mod : x` 之类的语句来处理溢出。

**更大的数.** 如果用我们之前实现的算法排除掉小数和含有小素因子的数，上述问题就不那么重要了。一般而言，最优策略应取决于数的大小：

- 小于 $2^{16}$：用查找表；
- 小于 $2^{32}$：用预计算素数表加快速整除判断；
- 小于约 $2^{64}$：用带蒙哥马利乘法的 Pollard rho 算法；
- 小于 $10^{50}$：改用 [Lenstra 椭圆曲线分解](https://en.wikipedia.org/wiki/Lenstra_elliptic-curve_factorization)；
- 小于 $10^{100}$：改用[二次筛法](https://en.wikipedia.org/wiki/Quadratic_sieve)；
- 大于 $10^{100}$：改用[一般数域筛法](https://en.wikipedia.org/wiki/General_number_field_sieve)。

<!-- Requiring about 100KB of memory. 6542 * 8 -->

最后三种方法与我们前面的做法大相径庭，需要深得多的数论知识，它们值得拥有自己的一篇文章（或者一整门大学课程）。
