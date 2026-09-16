---
title: 快速幂
weight: 2
draft: true
---

在模算术（以及整个计算代数）中，经常需要把一个数自乘到 $n$ 次幂——用于做[模意义下的除法](../modular/#modular-division)、执行[素性测试](../modular/#fermats-theorem)或计算一些组合数值——而且你通常希望花费少于 $\Theta(n)$ 次运算来算出它。

*快速幂*（binary exponentiation），也称*平方求幂*（exponentiation by squaring），是一种计算 $n$ 次幂时只需 $O(\log n)$ 次乘法的方法，它依赖以下观察：

$$
\begin{aligned}
    a^{2k}       &= (a^k)^2
\\  a^{2k + 1}   &= (a^k)^2 \cdot a
\end{aligned}
$$

要计算 $a^n$，可以递归地计算 $a^{\lfloor n / 2 \rfloor}$，将其平方，再视情况乘上 $a$（$n$ 为奇数时才需要），对应如下的递推式：

$$
a^n = f(a, n) = \begin{cases}
   1,               && n = 0
\\ f(a, \frac{n}{2})^2,     && 2 \mid n
\\ f(a, n - 1) \cdot a, && 2 \nmid n
\end{cases}
$$

由于每两次递归转移 $n$ 至少减半，这个递推的深度和乘法总次数至多为 $O(\log n)$。

### 递归实现 {#recursive-implementation}

既然已有递推式，很自然地把算法实现成一个按情形匹配的递归函数：

```c++
const int M = 1e9 + 7; // modulo
typedef unsigned long long u64;

u64 binpow(u64 a, u64 n) {
    if (n == 0)
        return 1;
    if (n % 2 == 1)
        return binpow(a, n - 1) * a % M;
    else {
        u64 b = binpow(a, n / 2);
        return b * b % M;
    }
}
```

在我们的基准测试中，取 $n = m - 2$，这样算出的就是 $a$ 模 $m$ 的[乘法逆元](../modular/#modular-division)：

```c++
u64 inverse(u64 a) {
    return binpow(a, M - 2);
}
```

我们取 $m = 10^9+7$。这是竞赛编程里常用的模数值，用于在组合问题中计算校验和——因为它是素数（可用快速幂求逆元），足够大，做加法不会溢出 `int`，做乘法不会溢出 `long long`，而且敲起来就是简单的 `1e9 + 7`。

由于我们在代码中把它用作编译期常量，编译器可以[用乘法替代取模](/hpc/arithmetic/division/)来优化它（即使它不是编译期常量，手工算一次魔数再用它们做快速约减也仍然更便宜）。

执行路径——以及相应的运行时间——取决于 $n$ 的值。对这个特定的 $n$，基准实现每次调用约需 330ns。由于递归会引入一些[开销](/hpc/architecture/functions/)，把实现展开成迭代过程是合理的。

### 迭代实现 {#iterative-implementation}

$a^n$ 的结果可以表示为 $a$ 的若干个 2 的幂的乘积——这些幂对应 $n$ 的二进制表示中的那些 1。例如，若 $n = 42 = 32 + 8 + 2$，则

$$
a^{42} = a^{32+8+2} = a^{32} \cdot a^8 \cdot a^2 
$$

要计算这个乘积，我们可以遍历 $n$ 的各个二进制位，同时维护两个变量：$a^{2^k}$ 的值，以及考虑完最低 $k$ 位（$n$ 的）之后的当前乘积。每一步中，我们把当前乘积乘上 $a^{2^k}$——只要第 $k$ 位（$n$ 的）为 1；无论该位为何，都将 $a^k$ 平方，得到将在下一轮迭代中使用的 $a^{2^k \cdot 2} = a^{2^{k+1}}$。

```c++
u64 binpow(u64 a, u64 n) {
    u64 r = 1;
    
    while (n) {
        if (n & 1)
            r = res * a % M;
        a = a * a % M;
        n >>= 1;
    }
    
    return r;
}
```

迭代实现每次调用约需 180ns。繁重的计算是相同的；改进主要来自依赖链的缩短：`a = a * a % M` 需要完成后循环才能继续，而现在它可以与 `r = res * a % M` 并发执行。

> **译者注**：原文代码中此行写作 `r = res * a % M`，其中 `res` 未定义，应为 `r = r * a % M` 的笔误；上文代码块与原文保持一致，未予改动。

性能还受益于 $n$ 是常量：这让[所有分支都变得可预测](/hpc/pipelining/branching/)，也让调度器提前知道接下来要执行什么。不过编译器没有利用这一点，没有展开 `while(n) n >>= 1` 循环。我们可以把它改写成固定执行 30 次迭代的 `for` 循环：

```c++
u64 inverse(u64 a) {
    u64 r = 1;
    
    #pragma GCC unroll(30)
    for (int l = 0; l < 30; l++) {
        if ( (M - 2) >> l & 1 )
            r = r * a % M;
        a = a * a % M;
    }

    return r;
}
```

这迫使编译器只生成我们需要的指令，再省下 10ns，使总运行时间约为 170ns。

注意，性能不仅取决于 $n$ 的二进制长度，还取决于二进制 1 的个数。若 $n$ 为 $2^{30}$，耗时会少大约 20ns，因为不必执行任何不在路径上的乘法。
