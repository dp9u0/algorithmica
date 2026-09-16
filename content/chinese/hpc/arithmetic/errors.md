---
title: 舍入误差
weight: 2
draft: true
---

硬件浮点数的舍入方式简单得出奇：当且仅当运算结果无法精确表示时才发生舍入，且默认被舍入到最近的可表示数字（平局时优先选择二进制表示以零结尾的那个）。

考虑下面这段代码：

```c++
float x = 0;
for (int i = 0; i < (1 << 25); i++)
    x++;
printf("%f\n", x);
```

它输出的不是 $2^{25} = 33554432$（数学上应有的结果），而是 $16777216 = 2^{24}$。为什么？

当我们反复递增一个浮点数 $x$ 时，最终会碰到一个临界点：数字变得如此之大，以至于 $(x + 1)$ 被舍入回 $x$ 本身。第一个这样的数字是 $2^{24}$（尾数位数加一），因为

$$2^{24} + 1 = 2^{24} \cdot 1.\underbrace{0\ldots0}_{\times 23} 1$$

它与 $2^{24}$ 和 $(2^{24} + 1)$ 的距离完全相等，但按上述平局裁决规则被舍入到 $2^{24}$。与此同时，所有比它小的数字的递增都能被精确表示，压根不会发生舍入。

### 舍入误差与运算顺序 {#rounding-errors-and-operation-order}

尽管代数上正确，浮点计算的结果仍可能依赖于运算顺序。

例如，加法和乘法在纯数学意义上满足交换律和结合律，但它们的舍入误差不满足：当我们有三个浮点变量 $x$、$y$、$z$ 时，$(x+y+z)$ 的结果取决于求和的顺序。同样的非交换性原则适用于大多数（乃至全部）其他浮点运算。

编译器不允许产生[不符合规范](/hpc/compilation/contracts/)的结果，所以这个恼人的细节禁用了一些涉及重排算术操作数的潜在优化。在 GCC 和 Clang 中你可以用 `-ffast-math` 标志关闭这种严格合规。如果加上它重新编译上面的代码片段，它会跑得[快得多](/hpc/simd/reduction)，而且碰巧输出正确结果 33554432（不过你要知道，编译器同样可能选了一条精度更低的计算路径）。

### 舍入模式 {#rounding-modes}

除了默认模式（也称"银行家舍入法"（Banker's rounding）），你还可以[设置](https://www.cplusplus.com/reference/cfenv/fesetround/)另外 4 种舍入逻辑：

- 舍入到最近值，完美平局时总是"远离"零方向舍入；
- 向上舍入（朝 $+∞$；负数结果因此朝零舍入）；
- 向下舍入（朝 $-∞$；负数结果因此朝远离零方向舍入）；
- 向零舍入（对二进制结果做截断）。

例如，如果在运行上面的循环之前调用 `fesetround(FE_UPWARD)`，输出的既不是 $2^{24}$，也不是 $2^{25}$，而是 $67108864 = 2^{26}$。这是因为：到达 $2^{24}$ 之后，$(x + 1)$ 开始舍入到下一个最近的可表示数字 $(x + 2)$，我们只用一半的时间就到达了 $2^{25}$；在那之后，$(x + 1)$ 向上舍入到 $(x+4)$，我们开始以四倍速前进。

替代舍入模式的用途之一是诊断数值不稳定性。如果算法的结果在"向正无穷舍入"和"向负无穷舍入"之间切换时变化显著，说明它容易受舍入误差影响。

这种检验往往优于"把全部计算切换到更低精度、看结果变化是否过大"的做法，因为默认的舍入到最近策略在足够的平均之下会收敛到正确的"期望"值：误差一半时间向上舍入，另一半时间向下舍入——从统计上讲，它们相互抵消。

### 度量误差 {#measuring-errors}

指望执行自然对数、平方根这类复杂计算的硬件给出这样的保证似乎有些出人意料，但事实就是如此：你被保证从所有运算中得到可能达到的最高精度。这使得分析舍入误差变得非常容易，我们稍后就会看到。

度量计算误差有两种自然的方式：

* 制造硬件或符合规范的精确软件的工程师关心的是*末位单位*（units in the last place，ulp），即用"精确实数值与实际计算结果之间能塞下多少个可表示数字"来衡量两个数字之间的距离。
* 研究数值算法的人关心的是*相对精度*，即近似误差的绝对值除以真实答案：$|\frac{v-v'}{v}|$。

无论哪种情况，分析误差的常规策略都是假设最坏情况并直接给出界。

如果你执行一次基本算术运算，那么可能发生的最坏情况就是结果被舍入到最近的可表示数字，意味着误差不超过 0.5 ulp。为了用同样的方式推理相对误差，我们可以定义一个数 $\epsilon$，称为*机器精度*（machine epsilon），等于 $1$ 与下一个可表示值之间的差（它应该等于 2 的负幂，幂次取决于尾数分到多少位）。

这意味着，如果在一次算术运算之后你得到结果 $x$，那么真实值就在区间

$$
[x \cdot (1-\epsilon),\; x \cdot (1 + \epsilon)]
$$

之中。在做基于浮点计算结果的离散"是/否"判断时，牢记误差的无处不在尤其重要。例如，下面是检查相等性的正确姿势：

```c++
const float eps = std::numeric_limits<float>::epsilon; // ~2^(-23)
bool eq(float a, float b) {
    return abs(a - b) <= eps;
}
```

`eps` 的取值应取决于应用场景：上面这个——`float` 的机器精度——只适用于不超过一次浮点运算的情形。

### 区间算术 {#interval-arithmetic}

如果一个算法的误差（无论成因）在计算过程中不会增长得过大，就称该算法是*数值稳定*（numerically stable）的。而这只有在问题本身是*良态*（well-conditioned）时才可能发生——即输入数据只变动一点点时，解也只变动一点点。

在分析数值算法时，采用实验物理学的同款方法往往很有用：不直接操作未知的真实值，而是操作它们可能所在的区间。

例如，考虑一个连续把某个变量乘以任意实数的运算链：

```cpp
float x = 1;
for (int i = 0; i < n; i++)
    x *= a[i];
```

第一次乘法之后，$x$ 的值相对于真实乘积的值以 $(1 + \epsilon)$ 为界；此后每多一次乘法，这个上界就再乘上一个 $(1 + \epsilon)$。由归纳法，$n$ 次乘法之后，计算出的值以 $(1 + \epsilon)^n = 1 + n \epsilon + O(\epsilon^2)$ 为界（下界类似）。

这意味着相对误差是 $O(n \epsilon)$，这还算可以接受，因为通常 $n \ll \frac{1}{\epsilon}$。

再看一个数值*不稳定*的计算的例子，考虑函数

$$
f(x, y) = x^2 - y^2
$$

假设 $x > y$，这个函数能返回的最大值大约是

$$
x^2 \cdot (1 + \epsilon) - y^2 \cdot (1 - \epsilon)
$$

对应的绝对误差为

$$
x^2 \cdot (1 + \epsilon) - y^2 \cdot (1 - \epsilon) - (x^2 - y^2) = (x^2 + y^2) \cdot \epsilon
$$

从而相对误差为

$$
\frac{x^2 + y^2}{x^2 - y^2} \cdot \epsilon
$$

如果 $x$ 和 $y$ 量级相近，误差将是 $O(\epsilon \cdot |x|)$。

在直接计算中，减法把平方运算的误差"放大"了。但改用下面的公式就能修复：

$$
f(x, y) = x^2 - y^2 = (x + y) \cdot (x - y)
$$

在这一版中，容易证明误差以 $\epsilon \cdot |x - y|$ 为界。它还更快，因为它需要 2 次加法和 1 次乘法：比原式多一次快速加法、少一次慢速乘法。

### Kahan 求和 {#kahan-summation}

从上一个例子可以看出，长长的运算链不是问题，把量级悬殊的数字相加减才是。处理这类问题的一般思路是：尽量让大数跟大数待在一起，小数跟小数待在一起。

考虑标准的求和算法：

```c++
float s = 0;
for (int i = 0; i < n; i++)
    s += a[i];
```

由于我们执行的是求和而非连乘，它的相对误差不再只是以 $O(\epsilon \cdot n)$ 为界，而是严重依赖于输入。

在最离谱的情形下，如果第一个值是 $2^{24}$ 而其余值都等于 $1$，那么和都将是 $2^{24}$——不管 $n$ 是多少——执行下面的代码并观察它干脆利落地打印两遍 $16777216 = 2^{24}$ 即可验证：

```cpp
const int n = (1<<24);
printf("%d\n", n);

float s = n;
for (int i = 0; i < n; i++)
    s += 1.0;

printf("%f\n", s);
```

这是因为 `float` 只有 23 个尾数位，于是 $2^{24} + 1$ 是第一个无法精确表示、必须向下舍入的整数，而这发生在我们每一次试图把 $1$ 加到 $s = 2^{24}$ 上的时候。误差的确是 $O(n \cdot \epsilon)$，但那是就绝对误差而言，不是相对误差：在上面的例子中它是 $2$，而如果最后一个数恰好是 $-2^{24}$，它会一路飘到无穷。

显而易见的解决办法是换成 `double` 这样更大的类型，但这算不上一种可扩展的方法。一种优雅的解法是把没能加进去的部分存到一个单独的变量里，再把它加到下一个变量上：

```c++
float s = 0, c = 0;
for (int i = 0; i < n; i++) {
    float y = a[i] - c; // c is zero on the first iteration
    float t = s + y;    // s may be big and y may be small, losing low-order bits of y
    c = (t - s) - y;    // (t - s) cancels high-order part of y
    s = t;
}
```

这一技巧称为 *Kahan 求和*（Kahan summation）。它的相对误差以 $2 \epsilon + O(n \epsilon^2)$ 为界：第一项来自最后一次求和，第二项则源于我们每一步都在处理小于机器精度的误差。

当然，一种不仅适用于数组求和的更通用的办法是切换到更精确的数据类型（如 `double`），这相当于把机器精度平方。更进一步，它还能（勉强算作）通过把两个 `double` 变量捆绑在一起来扩展：一个存值，另一个存它无法表示的误差，使它们共同表示值 $a+b$。这种方法称为 double-double 算术，还可以类似地推广出 quad-double 及更高精度的算术。

<!--

## Conversion to Decimal

It is unfortunate that humans evolved to have 10 fingers, because owing to this fact we ended up with a very clumsy number system.

Digit is actually also a anatomical term meaning either a finger or a toe

Six fingers on each hand would be more convenient, because it would be straightforward to divide numbers by 2, 3, 4 and 6. This numbering system was used by ancient Babylonians, and it is still the reason why we have 60 seconds in a minute, 24 hours in a day, 12 months and 6 cans of beer in a pack: you can perfectly divide items by low divisors.

Four fingers on each hand (like in The Simpsons) would give us a very convenient octal system where you can divide by powers of 2, although most people would not start appreciating it until invention of computers.

But here we are, and we have a problem of converting binary floating-point numbers to decimal numbers in scientific notation. But what does that even mean, exactly?

Note that some decimal numbers are not representable in finite form in binary. Here is a famous JavaScript joke (that you can reproduce by pressing F12 in your browser):

```
> 0.1
< 0.1
> 0.2
< 0.2
> 0.1+0.2
< 0.30000000000000004
```

Neither of them are exact, so JavaScript prints the shortest number that would be parsed back as the same number (reading numbers is defined similarly: it rounds to the closest representable number). The result of "0.3" and "0.1+0.2" is off by exactly one ULP, so it isn't printed as 0.3.

The way to approach any hard problem is to figure out how to solve some partial cases in then to figure out how to reduce the initial problem. Let's start with processing the sign bit: it's simple, just print "-" in front of a number in case it is 1. Next, we can check for special values.

Then, we can notice that some numbers are easy to print. If we have 23-bit mantissa and our exponent value is exactly 23, then we can reinterpret the mantissa as integer, add it to $2^23$ (the implicit 1) and then print it as we would print an integer. We can also do the same thing for small exponents, except that we would need to multiply that intermediate integer by a small power of two.

But what to do in general case, if the exponent value is either too large or too small? We can reduce the problem to the previous case by multiplying it by $\frac{10^a}{2^b}$ for some integers $a$ and $b$ with precise enough arithmetic so that the exponent is small.

Multiplying or dividing by 10 is the same as incrementing the exponent (the resulting one after the "e" in scientific notation, not the binary). The idea is to find a proper power of 10 so that the resulting number will have . We need to precalculate numbers of the form $\frac{10^a}{2^b}$ (since exponent is limited, there won't be many of them). To get the precalculated number, we need to look at the exponent (or possibly its neighbors).

The tricky part is the "shortest possible." It can be solved by printing digits one by one and trying to parse it back, but this would be too slow.

How many decimal digits do we need to print a `float`?

-->
