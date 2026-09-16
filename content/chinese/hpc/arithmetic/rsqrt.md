---
title: 快速平方根倒数
weight: 4
draft: true
---

浮点数的平方根倒数 $\frac{1}{\sqrt x}$ 用于计算归一化向量（normalized vector），而后者被大量用于各种模拟场景，例如计算机图形学（比如确定入射角和反射角以模拟光照）。

$$
\hat{v} = \frac{\vec v}{\sqrt {v_x^2 + v_y^2 + v_z^2}}
$$

直接计算平方根倒数——先算平方根、再用 $1$ 除以它——极其缓慢，因为这两种运算即便有硬件实现也还是慢。

但有一个出奇好的近似算法，它利用了浮点数在内存中的存储方式。它好到甚至已经被[实现在硬件里](https://www.felixcloutier.com/x86/rsqrtps)，所以这个算法本身对软件工程师已不再有意义，但我们还是要把它的内在之美和巨大的教学价值走一遍。

除方法本身外，它的诞生史也相当有趣。它被归功于游戏工作室 *id Software*，后者在他们 1999 年的标志性游戏《雷神之锤 III 竞技场》（*Quake III Arena*）中使用了它——不过看起来，它是经由一条"我从一个家伙那儿学来，那家伙又从另一个家伙那儿学来"的链条到达那里的，而链条的尽头似乎是 William Kahan（就是那个负责 IEEE 754 和 Kahan 求和算法的人）。

2005 年前后，随着游戏源码发布，它在游戏开发圈子里流行起来。下面是[源码中的相关摘录](https://github.com/id-Software/Quake-III-Arena/blob/master/code/game/q_math.c#L552)，注释一并奉上：

```c++
float Q_rsqrt(float number) {
    long i;
    float x2, y;
    const float threehalfs = 1.5F;

    x2 = number * 0.5F;
    y  = number;
    i  = * ( long * ) &y;                       // evil floating point bit level hacking
    i  = 0x5f3759df - ( i >> 1 );               // what the fuck? 
    y  = * ( float * ) &i;
    y  = y * ( threehalfs - ( x2 * y * y ) );   // 1st iteration
//  y  = y * ( threehalfs - ( x2 * y * y ) );   // 2nd iteration, this can be removed

    return y;
}
```

我们会一步步走完它做了什么，但首先需要绕个小弯。

### 近似对数 {#approximate-logarithm}

在计算机（至少是买得起的计算器）成为日常用品之前，人们用对数表计算乘法及相关运算——查出 $a$ 和 $b$ 的对数，相加，再查结果的反对数。

$$
a \times b = 10^{\log a + \log b} = \log^{-1}(\log a + \log b)
$$

计算 $\frac{1}{\sqrt x}$ 时也可以用同样的技巧，依据恒等式：

$$
\log \frac{1}{\sqrt x} = - \frac{1}{2} \log x
$$

快速平方根倒数正是建立在这个恒等式之上，因此它需要非常快地算出 $x$ 的对数。结果表明，只需把一个 32 位 `float` 重新解读为整数，就能近似它。

[回忆一下](../float)，浮点数依次存储符号位（正值时为零，正是我们的情形）、指数 $e_x$ 和尾数 $m_x$，对应

$$
x = 2^{e_x} \cdot (1 + m_x)
$$

它的对数因此是

$$
\log_2 x = e_x + \log_2 (1 + m_x)
$$

既然 $m_x \in [0, 1)$，右边的对数可以近似为

$$
\log_2 (1 + m_x) \approx m_x
$$

这个近似在区间两端是精确的，但为了照顾平均情形，我们需要把它平移一个小常数 $\sigma$，于是

$$
\log_2 x = e_x + \log_2 (1 + m_x) \approx e_x + m_x + \sigma
$$

现在，心里揣着这个近似，定义 $L=2^{23}$（`float` 的尾数位数）和 $B=127$（指数偏置），当我们把 $x$ 的位模式重新解读为整数 $I_x$ 时，本质上得到

$$
\begin{aligned}
I_x &= L \cdot (e_x + B + m_x)
\\  &= L \cdot (e_x + m_x + \sigma +B-\sigma )
\\  &\approx L \cdot \log_2 (x) + L \cdot (B-\sigma )
\end{aligned}
$$

（整数乘以 $L=2^{23}$ 等价于左移 23 位。）

当你把 $\sigma$ 调到均方误差最小时，得到的是一个出奇精确的近似。

![把浮点数 $x$ 重新解读为整数（蓝）与它缩放平移后的对数（灰）的对比](/en/hpc/arithmetic/img/approx.svg)

现在，从近似式中反解出对数：

$$
\log_2 x \approx \frac{I_x}{L} - (B - \sigma)
$$

好。现在，我们刚才说到哪儿了？哦对，我们要算平方根倒数。

### 近似结果 {#approximating-the-result}

要计算 $y = \frac{1}{\sqrt x}$，可以利用恒等式 $\log_2 y = - \frac{1}{2} \log_2 x$：把它代入我们的近似公式，得到

$$
\frac{I_y}{L} - (B - \sigma)
\approx
- \frac{1}{2} ( \frac{I_x}{L} - (B - \sigma) )
$$

解出 $I_y$：

$$
I_y \approx \frac{3}{2} L (B - \sigma) - \frac{1}{2} I_x
$$

原来我们根本不需要计算对数：上面的公式就是一个常数减去 $x$ 的整数重解读值的一半。代码里写的是：

```cpp
i = * ( long * ) &y;
i = 0x5f3759df - ( i >> 1 );
```

第一行把 `y` 重新解读为整数，第二行把它代入公式，其中第一项就是幻数 $\frac{3}{2} L (B - \sigma) = \mathtt{0x5F3759DF}$，第二项用二进制移位代替除法来计算。

### 用牛顿法迭代 {#iterating-with-newtons-method}

接下来是几轮手写的牛顿法迭代，取 $f(y) = \frac{1}{y^2} - x$，初值非常棒。它的更新规则是

$$
f'(y) = - \frac{2}{y^3} \implies y_{i+1} = y_{i} (\frac{3}{2} - \frac{x}{2} y_i^2) = \frac{y_i (3 - x y_i^2)}{2}
$$

在代码里写作

```cpp
x2 = number * 0.5F;
y  = y * ( threehalfs - ( x2 * y * y ) );
```

初始近似好到只需一轮迭代就足够满足游戏开发的目的。它在第一轮迭代后就落在正确答案的 99.8% 以内，还可以继续迭代以提高精度——硬件里就是这么干的：[x86 的那条指令](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=3037,3009,5135,4870,4870,4872,4875,833,879,874,849,848,6715,4845,6046,3853,288,6570,6527,6527,90,7307,6385,5993&text=rsqrt&techs=AVX,AVX2)会做上几轮，并保证相对误差不超过 $1.5 \times 2^{-12}$。

### 延伸阅读 {#further-reading}

[维基百科：快速平方根倒数](https://en.wikipedia.org/wiki/Fast_inverse_square_root#Floating-point_representation)。
