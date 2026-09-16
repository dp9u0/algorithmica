---
title: 模算术
weight: 1
draft: true
---

<!--

TODO: use it in binary exponentiation.

In this section, we are going to discuss some preliminaries before discussing more advanced topics.

we use the 1st of January, 1970 as the start of the "Unix era," and all time computations are usually done relative to that timestamp.

And the beautiful thing about it is that remainders are small and cyclic. Think the hour clock: after 12 there comes 1 again, so the number is always small.

![](../img/clock.gif)

-->

计算机通常把时间存储为自 1970 年 1 月 1 日——"Unix 纪元"的起点——以来经过的秒数，并在一切与时间有关的计算中使用这些时间戳。

我们人类同样以过去的某个时刻为基准来记录时间，而这个时刻通常带有政治或宗教意义。例如，在写作本文的时刻，距公元元年大约已经过去了 63882260594 秒——公元元年正是[公元 6 世纪东罗马帝国修士对耶稣基督诞生之日的最佳估计](https://en.wikipedia.org/wiki/Anno_Domini)。

但与计算机不同，我们并不总是需要*全部*这些信息。视手头任务而定，相关的部分可能只是"现在是下午 2 点，该去吃晚饭了"，或者"今天是星期四，所以 Subway 的当日三明治是意大利 BMT"。我们不用完整的时间戳，而是只用它的*余数*，其中恰好包含我们需要的信息：处理一两位数总比处理十一位数容易得多。

**问题。** 今天是星期四。整整一年后是星期几？

如果把一周的每一天从星期一开始用 $0$ 到 $6$ 编号，星期四的编号是 $3$。要知道一年之后是星期几，需要给它加上 $365$，再对 $7$ 取模。方便的是，$365 \bmod 7 = 1$，所以我们知道那会是星期五——除非赶上闰年（那样就是星期六）。

### 剩余 {#residues}

**定义。** 两个整数 $a$ 和 $b$，若 $m$ 整除它们的差，则称它们模 $m$ *同余*（congruent）：

$$
m \mid (a - b) \; \Longleftrightarrow \; a \equiv b \pmod m
$$

例如，一年中的第 42 天与第 161 天是同一个星期几，因为 $(161 - 42) = 119 = 17 \times 7$。

模 $m$ 同余是一种等价关系，它把所有整数划分成称为*剩余类*（residue）的等价类。模 $m$ 的每个剩余类可以由它的任意一个成员代表——不过我们通常使用该类中最小的非负整数（它等于余数 $x \bmod m$，对所有非负的 $x$ 成立）。

<!--

Equivalently, the *remainders* of their division by $m$ should be equal:

a \bmod m = b \bmod m

Here are a few example of how this can be useful.

-->

*模算术*（modular arithmetic）研究的正是这些剩余类组成的集合，它们是数论的基础。

**问题。** 设我们的"一周"现在有 $m$ 天，一年有 $a$ 天（不考虑闰年）。从现在起一整年、两整年、三整年……之后，总共会出现多少个不同的星期几？

为简单起见，假设今天是星期一，即初始的天数编号 $d_0$ 为零，每过一年它变为

$$
d_{k + 1} = (d_k + a) \bmod m
$$

$k$ 年之后，它将是

$$
d_k = k \cdot a \bmod m
$$

由于一周只有 $m$ 天，迟早会再次轮到星期一，天数编号的序列将会循环。不同天数（星期几）的个数就是这个循环的长度，所以我们需要找到最小的 $k$，使得

$$
k \cdot a \equiv 0 \pmod m
$$

首先，若 $a \equiv 0$，那将永远是星期一。现在考虑非平凡的情形 $a \not \equiv 0$：

- 对于七天的一周，$m = 7$ 是素数。不存在 $k$（小于 $m$ 的）使 $k \cdot a$ 被 $m$ 整除，因为按素数的定义，$m$ 不可能分解成这样一个乘积。所以，若 $m$ 为素数，我们会遍历全部 $m$ 个星期几。
- 若 $m$ 不是素数，但 $a$ 与它*互素*（coprime，即 $a$ 和 $m$ 没有公因数），答案仍然是 $m$，理由相同：$a$ 的因子并不能帮乘积更快地归零。
- 若 $a$ 和 $m$ 共享一些因子，则只能得到同样被这些因子整除的剩余。例如，若一周长 $m = 10$ 天，而一年有 $a = 42$ 天或任何偶数天，我们会遍历所有偶数的天数编号；若天数是 $5$ 的倍数，就只会在 $0$ 和 $5$ 之间振荡。其余情况下，我们会遍历全部 $10$ 个余数。

因此，一般地，答案是 $\frac{m}{\gcd(a, m)}$，其中 $\gcd(a, m)$ 是 $a$ 与 $m$ 的[最大公约数](/hpc/algorithms/gcd/)。

### 费马定理 {#fermats-theorem}

现在考虑，如果不是反复加一个数 $a$，而是反复乘以它，写出序列

$$
d_n = a^n \bmod m
$$

同样，由于剩余的个数有限，序列终将出现循环。但循环的长度会是多少？结果是，若 $m$ 为素数，它会遍历全部 $(m - 1)$ 个非零剩余。

**定理。** 对任意 $a$ 和素数 $p$：

$$
a^p \equiv a \pmod p
$$

**证明**。设 $P(x_1, x_2, \ldots, x_n) = \frac{k}{\prod (x_i!)}$ 为*多项式系数*（multinomial coefficient），即元素 $a_1^{x_1} a_2^{x_2} \ldots a_n^{x_n}$ 在 $(a_1 + a_2 + \ldots + a_n)^k$ 展开后出现的次数。那么：

$$
\begin{aligned}
a^p &= (\underbrace{1+1+\ldots+1+1}_\text{$a$ times})^p &
\\\ &= \sum_{x_1+x_2+\ldots+x_a = p} P(x_1, x_2, \ldots, x_a) & \text{(by definition)}
\\\ &= \sum_{x_1+x_2+\ldots+x_a = p} \frac{p!}{x_1! x_2! \ldots x_a!} & \text{(which terms will not be divisible by $p$?)}
\\\ &\equiv P(p, 0, \ldots, 0) + \ldots + P(0, 0, \ldots, p) & \text{(everything else will be canceled)}
\\\ &= a
\end{aligned}
$$

注意这只对素数 $p$ 成立。利用这一事实，我们可以比因数分解更快地检验一个数是否为素数：随机取一个数 $a$，计算 $a^{p} \bmod p$，检查它是否等于 $a$。

这称为*费马素性测试*（Fermat primality test），它是概率性的——只会返回"否"或"可能"——因为也可能 $a^p$ 恰好等于 $a$，尽管 $p$ 是合数；这种情况下需要换一个随机的 $a$ 重复测试，直到你对假阳性概率满意为止。

素性测试常用于生成大素数（供密码学用途）。大约有 $\frac{n}{\ln n}$ 个素数落在前 $n$ 个自然数之内（这个事实我们不予证明），且它们的分布大致均匀。只需从所需范围内随机取一个数，做一次素性检验，然后重复直到找到素数，平均需要 $O(\ln n)$ 次尝试。

费马测试的一类极坏输入是[卡迈克尔数](https://en.wikipedia.org/wiki/Carmichael_number)（Carmichael numbers）：它们是这样的合数 $n$——$a^{n-1} \equiv 1 \pmod n$ 对所有与之互素的 $a$ 都成立。但它们很[稀少](https://oeis.org/A002997)，随机撞上的概率很低。

### 模意义下的除法 {#modular-division}

对剩余实现大多数"普通"算术运算都很直接，只需注意整数溢出并记得取模：

```c++
c = (a + b) % m;
c = (a - b + m) % m;
c = a * b % m;
```

但除法有问题：不能对两个剩余直接相除。例如，$\frac{8}{2} = 4$，但

$$
\frac{8 \bmod 5}{2 \bmod 5} = \frac{3}{2} \neq 4
$$

要做模意义下的除法，我们需要找到一个"扮演"倒数 $\frac{1}{a} = a^{-1}$ 角色的元素，然后乘以它。这个元素称为*模乘法逆元*（modular multiplicative inverse）。当模数 $p$ 为素数时，费马定理可以帮我们找到它。把该同余式两边接连除以两次 $a$，得到：

$$
a^p \equiv a \implies a^{p-1} \equiv 1 \implies a^{p-2} \equiv a^{-1}
$$

因此，就乘法而言 $a^{p-2}$ 的作用就像 $a^{-1}$，这正是我们对 $a$ 的模逆元的要求。
