---
title: 二进制 GCD
weight: 1
draft: true
aliases: [/hpc/analyzing-performance/gcd]
---

在本节中，我们将推导出一个比 C++ 标准库中的实现快约 2 倍的 `gcd` 变体。

## 欧几里得算法 {#euclids-algorithm}

欧几里得算法解决的是求两个整数 $a$ 和 $b$ 的*最大公约数*（greatest common divisor，GCD）的问题，它定义为最大的数 $g$，且能同时整除 $a$ 与 $b$：

$$
\gcd(a, b) = \max_{g: \; g|a \, \land \, g | b} g
$$

你可能已经在某本计算机科学教材里学过这个算法，但我还是在这里概括一下。它基于以下公式（假设 $a > b$）：

$$
\gcd(a, b) = \begin{cases}
    a, & b = 0
\\ \gcd(b, a \bmod b), & b > 0
\end{cases}
$$

这个公式成立，因为若 $g = \gcd(a, b)$ 同时整除 $a$ 和 $b$，它也应整除 $(a \bmod b = a - k \cdot b)$；但任何更大的因子 $d$——只要它整除 $b$——都不能：$d > g$ 意味着 $d$ 无法整除 $a$，因而也不会整除 $(a - k \cdot b)$。

上面的公式本质上就是算法本身：直接递归地应用它即可；由于每一步都有一个参数严格减小，最终必然收敛到 $b = 0$ 的情形。

教材上多半还提到过，欧几里得算法的最坏输入——使总步数最多的输入——是相邻的斐波那契数；由于斐波那契数是指数增长的，该算法的最坏运行时间是对数级的。如果把*平均*运行时间定义为均匀分布整数对的期望步数，那么平均运行时间也是对数级的。[维基百科词条](https://en.wikipedia.org/wiki/Euclidean_algorithm)里还有一个颇为晦涩的推导，给出了更精确的 $0.84 \cdot \ln n$ 渐进估计。

![你可以在黄金比例的位置看到亮蓝色的线条](/en/hpc/algorithms/img/euclid.svg)

欧几里得算法有很多种实现方式。最简单的就是把定义直接翻译成代码：

```c++
int gcd(int a, int b) {
    if (b == 0)
        return a;
    else
        return gcd(b, a % b);
}
```

也可以把它改写得更紧凑一些：

```c++
int gcd(int a, int b) {
    return (b ? gcd(b, a % b) : a);
}
```

还可以改写成循环的形式，这更接近硬件实际执行的方式。不过它并不会更快，因为编译器很容易优化掉尾递归。

```c++
int gcd(int a, int b) {
    while (b > 0) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}
```

你甚至可以把循环体写成下面这个令人费解的单行语句——而且自 C++17 起，它编译时甚至不会触发未定义行为相关的警告：

```c++
int gcd(int a, int b) {
    while (b) b ^= a ^= b ^= a %= b;
    return a;
}
```

所有这些写法，以及 C++17 引入的 `std::gcd`，几乎都等价，[编译](https://godbolt.org/z/r8z5KcGqK)后在功能上都对应下面这个汇编循环：

```nasm
; a = eax, b = edx
loop:
    ; modulo in assembly:
    mov  r8d, edx
    cdq
    idiv r8d
    mov  eax, r8d
    ; (a and b are already swapped now)
    ; continue until b is zero:
    test edx, edx
    jne  loop
```

如果对它运行 [perf](/hpc/profiling/events)，你会发现约 90% 的时间都花在 `idiv` 那一行。这并不奇怪：通用[整数除法](/hpc/arithmetic/division)在包括 x86 在内的所有计算机上都出了名地慢。

但有一类除法在硬件上运行得很好：除以 2 的幂。

## 二进制 GCD {#binary-gcd}

*二进制 GCD 算法*（binary GCD algorithm）的发现时间与欧几里得算法大致相当，但地点却在文明世界的另一端——古代中国。1967 年，Josef Stein 重新发现了它，用于那些要么没有除法指令、要么除法指令极慢的计算机——那个年代的 CPU 在执行罕见或复杂的操作时花上成百上千个周期并不稀奇。

与欧几里得算法类似，它基于下面几条相似的观察：

1. $\gcd(0, b) = b$，对称地 $\gcd(a, 0) = a$；
2. $\gcd(2a, 2b) = 2 \cdot \gcd(a, b)$；
3. $\gcd(2a, b) = \gcd(a, b)$（当 $b$ 为奇数），对称地 $\gcd(a, b) = \gcd(a, 2b)$（当 $a$ 为奇数）；
4. $\gcd(a, b) = \gcd(|a − b|, \min(a, b))$（当 $a$ 和 $b$ 均为奇数）。

同样，算法本身也只是对这些恒等式的反复应用。

它的运行时间仍是对数级的，这一点甚至更容易证明：除最后一条外，每条恒等式中都有一个参数被除以 2；而在最后一条里，新的第一个参数是两个奇数之差的绝对值，必然是偶数，因此也会在下一轮迭代中被除以 2。

这个算法对我们来说尤其有趣的地方在于，它用到的算术运算只有二进制移位、比较和减法，而这些运算通常都只需一个周期。

### 实现 {#implementation}

这个算法没被写进教材的原因是：它再也无法用一个简单的单行语句实现了：

```c++
int gcd(int a, int b) {
    // base cases (1)
    if (a == 0) return b;
    if (b == 0) return a;
    if (a == b) return a;

    if (a % 2 == 0) {
        if (b % 2 == 0) // a is even, b is even (2)
            return 2 * gcd(a / 2, b / 2);
        else            // a is even, b is odd (3)
            return gcd(a / 2, b);
    } else {
        if (b % 2 == 0) // a is odd, b is even (3)
            return gcd(a, b / 2);
        else            // a is odd, b is odd (4)
            return gcd(std::abs(a - b), std::min(a, b));
    }
}
```

运行一下……结果很糟糕。与 `std::gcd` 的速度差距确实是 2 倍，只是方向反了。这主要是因为需要大量分支来区分各种情形。我们开始优化吧。

首先，把所有除以 2 的操作替换为除以所能整除的最高的 2 的幂。这可以用 `__builtin_ctz` 高效完成——它是现代 CPU 上可用的“数末尾零”（count trailing zeros）指令。原算法中每次要除以 2 时，改为调用这个函数，它会给出该数需要右移的确切位数。假设我们处理的是足够大的随机数，这预计能把迭代次数减少近一半，因为 $1 + \frac{1}{2} + \frac{1}{4} + \frac{1}{8} + \ldots \to 2$。

其次，可以注意到条件 2 现在只可能在一开始成立一次——因为其他每条恒等式都至少让其中一个数保持奇数。因此我们可以在开头单独处理这一情形，主循环中不再考虑它。

第三，可以注意到：进入条件 4 并应用其恒等式之后，$a$ 总是偶数而 $b$ 总是奇数，所以我们已经知道下一轮迭代会落入条件 3。这意味着我们其实可以立刻把 $a$ “去偶”，而这样做之后，下一轮迭代又会命中条件 4。也就是说，我们要么处于条件 4，要么以条件 1 终止，这就消除了分支的必要。

把这些想法结合起来，就得到下面的实现：

```c++
int gcd(int a, int b) {
    if (a == 0) return b;
    if (b == 0) return a;

    int az = __builtin_ctz(a);
    int bz = __builtin_ctz(b);
    int shift = std::min(az, bz);
    a >>= az, b >>= bz;
    
    while (a != 0) {
        int diff = a - b;
        b = std::min(a, b);
        a = std::abs(diff);
        a >>= __builtin_ctz(a);
    }
    
    return b << shift;
}
```

它运行耗时 116ns，而 `std::gcd` 需要 198ns。快了差不多两倍——也许我们还能把它优化到 100ns 以内？

为此我们需要再盯着[它的汇编代码](https://godbolt.org/z/nKKMe48cW)看一会儿，尤其是这一段：

```nasm
; a = edx, b = eax
loop:
    mov   ecx, edx
    sub   ecx, eax       ; diff = a - b
    cmp   eax, edx
    cmovg eax, edx       ; b = min(a, b)
    mov   edx, ecx
    neg   edx
    cmovs edx, ecx       ; a = max(diff, -diff) = abs(diff)
    tzcnt ecx, edx       ; az = __builtin_ctz(a)
    sarx  edx, edx, ecx  ; a >>= az
    test  edx, edx       ; a != 0?
    jne   loop
```

我们来画出这个循环的依赖图：

<!--
\node [draw, circle] (diff)  at (3, 10) {diff};
\node [draw, circle] (min)   at (1.5, 8.9) {min};
\node [draw, circle] (abs)   at (3, 8.9) {abs};
\node [draw, circle] (ctz)   at (3, 7.8) {ctz};
\node [draw, circle] (shift) at (3, 6.6) {shift};
\node [draw, circle] (test)  at (3, 5.3) {test};

\path [->] (diff) edge (abs);
\path [->] (abs) edge (ctz);
\path [->] (ctz) edge (shift);
\path [->, dashed] (min) edge [bend left] (diff);
\path [->, dotted] (shift) edge (test);
\path [->, dashed] (shift) edge [bend right=75] (diff);
\path [->, dashed] (shift) edge [bend left=25] (min);
-->

![](/en/hpc/algorithms/img/gcd-dependency1.png)

现代处理器可以并行执行多条指令，这本质上意味着这段计算的真正“开销”约等于其关键路径上各级延迟之和。在本例中，就是 `diff`、`abs`、`ctz` 和 `shift` 的延迟总和。

我们可以降低这段延迟，依据是：实际上仅凭 `diff = a - b` 就能算出 `ctz`，因为能被 $2^k$ 整除的[负数](../arithmetic/integer/#signed-integers)在其二进制表示的末尾同样有 $k$ 个零。这样就不必先等 `max(diff, -diff)` 算出来，得到的依赖图也更短，像这样：

<!--
\node [draw, circle] (diff)  at (3, 10) {diff};
\node [draw, circle] (min)   at (1.5, 8.9) {min};
\node [draw, circle] (abs)   at (4.5, 8.9) {abs};
\node [draw, circle] (ctz)   at (3, 8.9) {ctz};
\node [draw, circle] (shift) at (3, 7.8) {shift};
\node [draw, circle] (test)  at (5.6, 9.4) {test};

\path [->] (diff) edge (abs);
\path [->] (diff) edge (ctz);
\path [->] (ctz) edge (shift);
\path [->, dashed] (min) edge [bend left] (diff);
\path [->, dotted] (diff) edge (test);
\path [->, dashed] (shift) edge [bend left=25] (min);
\path [->, dashed] (abs) edge [bend left=25] (diff);
-->

![](/en/hpc/algorithms/img/gcd-dependency2.png)

希望想清楚最终代码的执行方式之后，你会少一些困惑：

```c++
int gcd(int a, int b) {
    if (a == 0) return b;
    if (b == 0) return a;

    int az = __builtin_ctz(a);
    int bz = __builtin_ctz(b);
    int shift = std::min(az, bz);
    b >>= bz;
    
    while (a != 0) {
        a >>= az;
        int diff = b - a;
        az = __builtin_ctz(diff);
        b = std::min(a, b);
        a = std::abs(diff);
    }
    
    return b << shift;
}
```

它运行耗时 91ns，已经足够好，就到此为止吧。

如果有人想通过手写汇编，或者尝试用查找表省掉最后几次迭代，再抠出几纳秒，请[告诉我](http://sereja.me/)。

### 致谢 {#acknowledgements}

主要的优化想法属于 Daniel Lemire 和 Ralph Corderoy，他们在 2013 年圣诞节假期里[闲得没事可做](https://lemire.me/blog/2013/12/26/fastest-way-to-compute-the-greatest-common-divisor/)。
