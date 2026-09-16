---
title: 扩展欧几里得算法
weight: 3
draft: true
---

[费马定理](../modular/#fermats-theorem) 让我们可以通过[快速幂](../exponentiation)在 $O(\log n)$ 次运算内计算模乘法逆元，但它只对素数模数有效。它有一个推广，即[欧拉定理](https://en.wikipedia.org/wiki/Euler%27s_theorem)：若 $m$ 与 $a$ 互素，则

$$
a^{\phi(m)} \equiv 1 \pmod m
$$

其中 $\phi(m)$ 是[欧拉函数](https://en.wikipedia.org/wiki/Euler%27s_totient_function)（Euler's totient function），定义为满足 $x < m$ 且与 $m$ 互素的正整数的个数。在 $m$ 为素数的特殊情形下，全部 $m - 1$ 个剩余都是互素的，$\phi(m) = m - 1$，便得到费马定理。

这让我们可以把 $a$ 的逆元算作 $a^{\phi(m) - 1}$——前提是已知 $\phi(m)$；但反过来，计算它并不快：通常需要先求出 $m$ 的[因数分解](/hpc/algorithms/factorization/)。还有一种更一般的方法，通过改造[欧几里得算法](/hpc/algorithms/gcd/)得到。

### 算法 {#algorithm}

*扩展欧几里得算法*（extended Euclidean algorithm）除了求出 $g = \gcd(a, b)$，还能找到整数 $x$ 和 $y$ 使得

$$
a \cdot x + b \cdot y = g
$$

把 $b$ 换成 $m$、$g$ 换成 $1$，它就解决了求模逆元的问题：

$$
a^{-1} \cdot a + k \cdot m = 1
$$

注意，若 $a$ 与 $m$ 不互素，则无解：$a$ 与 $m$ 的任何整数组合都不可能得出不是其最大公约数之倍数的数。

该算法同样是递归的：它算出系数 $x'$ 和 $y'$——对应 $\gcd(b, a \bmod b)$——再还原出原数对的解。若我们已有解 $(x', y')$（对应数对 $(b, a \bmod b)$），即

$$
b \cdot x' + (a \bmod b) \cdot y' = g
$$

那么，为了得到最初输入的解，可以把表达式 $(a \bmod b)$ 改写为 $(a - \lfloor \frac{a}{b} \rfloor \cdot b)$ 并代入上式：

$$
b \cdot x' + (a - \Big \lfloor \frac{a}{b} \Big \rfloor \cdot b) \cdot y' = g
$$

现在按 $a$ 和 $b$ 分组重排各项，得到

$$
a \cdot \underbrace{y'}_x + b \cdot \underbrace{(x' - \Big \lfloor \frac{a}{b} \Big \rfloor \cdot y')}_y = g
$$

与最初的表达式比较，可以推断：直接把 $a$ 和 $b$ 的系数取作最初的 $x$ 和 $y$ 即可。

### 实现 {#implementation}

我们把算法实现为递归函数。由于它的输出不是一个而是三个整数，我们按引用把系数传给它：

```c++
int gcd(int a, int b, int &x, int &y) {
    if (a == 0) {
        x = 0;
        y = 1;
        return b;
    }
    int x1, y1;
    int d = gcd(b % a, a, x1, y1);
    x = y1 - (b / a) * x1;
    y = x1;
    return d;
}
```

要求逆元，只需传入 $a$ 和 $m$，返回算法求出的系数 $x$。由于传入的是两个正数，两个系数必然一正一负（哪个是负的取决于迭代次数的奇偶），所以需要视情况检查 $x$ 是否为负，是则加上 $m$ 以得到正确的剩余：

```c++
int inverse(int a) {
    int x, y;
    gcd(a, M, x, y);
    if (x < 0)
        x += M;
    return x;
}
```

它耗时约 160ns——比用[快速幂](../exponentiation)求数的逆元快 10ns。想进一步优化，可以类似地把它改写成迭代版本——耗时 135ns：

```c++
int inverse(int a) {
    int b = M, x = 1, y = 0;
    while (a != 1) {
        y -= b / a * x;
        b %= a;
        swap(a, b);
        swap(x, y);
    }
    return x < 0 ? x + M : x;
}
```

注意，与快速幂不同，运行时间取决于 $a$ 的值。例如，对这个特定的 $m$（$10^9 + 7$），最坏输入恰好是 564400443，算法对其执行 37 次迭代，耗时 250ns。

**练习。** 试着把同样的技巧移植到[二进制 GCD](/hpc/algorithms/gcd/#binary-gcd) 上（不过除非你的优化水平比我高，否则不会有性能提升）。
