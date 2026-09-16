---
title: 整数除法
weight: 6
draft: true
---

与其他算术运算相比，除法在 x86 和计算机整体上的表现都很差。浮点除法和整数除法都以难于硬件实现而臭名昭著。电路在 ALU 里占很大空间，计算又有很多阶段，结果就是 `div` 及其兄弟姐妹们通常要花 10–20 个周期才能完成，数据类型越小时延越略低。

### x86 中的除法和取模 {#division-and-modulo-in-x86}

既然没人想为单独的取模运算把这一坨麻烦再复制一份，`div` 指令就身兼两职。要执行一次 32 位整数除法，你需要把被除数*专门*放进 `eax` 寄存器，然后以除数作为 `div` 的唯一操作数调用它。之后，商会存在 `eax` 里，余数会存在 `edx` 里。

唯一的小机关是：被除数其实需要存在*两个*寄存器 `eax` 和 `edx` 里——这套机制使 64 除 32、甚至 128 除 64 的除法成为可能，与[128 位乘法](../integer)的工作方式类似。执行寻常的 32 除 32 有符号除法时，我们需要把 `eax` 符号扩展到 64 位，把高半部分存进 `edx`：

```nasm
div(int, int):
    mov  eax, edi
    cdq
    idiv esi
    ret
```

无符号除法则只需把 `edx` 清零，免得它捣乱：

```nasm
div(unsigned, unsigned):
    mov  eax, edi
    xor  edx, edx
    div  esi
    ret
```

两种情形中，除了 `eax` 里的商，你都可以顺手拿到 `edx` 里的余数：

```nasm
mod(unsigned, unsigned):
    mov  eax, edi
    xor  edx, edx 
    div  esi
    mov  eax, edx
    ret
```

你还可以用 64 位整数去除一个 128 位整数（存在 `rdx:rax` 里）：

```nasm
div(u128, u64):
    ; a = rdi + rsi, b = rdx
    mov  rcx, rdx
    mov  rax, rdi
    mov  rdx, rsi
    div  edx 
    ret
```

被除数的高半部分必须小于除数，否则会发生溢出。由于这条限制，让编译器[自己](https://danlark.org/2020/06/14/128-bit-division/)生成这种代码很难：如果你用一个 [128 位整数类型](../integer)除以 64 位整数，编译器会用额外的检查把它层层包裹起来，而这些检查实际上可能是多余的。

### 除以常数 {#division-by-constants}

整数除法慢得令人心痛，即便完全由硬件实现也是如此，但当除数是常数时，某些情形下可以绕开它。一个众所周知的例子是除以 2 的幂，可以用一周期的二进制移位替代：[二进制 GCD 算法](/hpc/algorithms/gcd)是这一技艺的漂亮展示。

一般情况下，有几种灵巧的技巧能以一点预计算为代价用乘法替代除法。所有这些技巧都基于同一个想法。考虑用一个浮点数 $x$ 除以另一个浮点数 $y$、而 $y$ 事先已知的任务。我们可以计算一个常数

$$
d \approx y^{-1}
$$

然后在运行期间计算

$$
x / y = x \cdot y^{-1} \approx x \cdot d
$$

$\frac{1}{y}$ 的结果最多偏差 $\epsilon$，乘法 $x \cdot d$ 只会再加一个 $\epsilon$，因此总偏差最多 $2 \epsilon + \epsilon^2 = O(\epsilon)$，对浮点情形来说可以容忍。

<!--

For example, `double` has 53 mantissa bits and therefore a machine epsilon of $\frac{1}{53}$, , if we also make sure it is rounded the right way.

-->

### Barrett 规约 {#barrett-reduction}

如何把这个技巧推广到整数？计算 `int d = 1 / y` 看起来行不通，因为它就是零。我们所能做的最好的事，是把它表达成

$$
d = \frac{m}{2^s}
$$

然后找一个"幻数" $m$ 和一个二进制移位 $s$，使得对所有范围内的 `x` 都有 `x / y == (x * m) >> s`。

$$
  \lfloor x / y \rfloor
= \lfloor x \cdot y^{-1} \rfloor
= \lfloor x \cdot d \rfloor
= \lfloor x \cdot \frac{m}{2^s} \rfloor
$$

可以证明这样一对总是存在，而且编译器确实会自己执行这类优化。每逢遇到除以常数，它们就用一次乘法和一次二进制移位取而代之。下面是 `unsigned long long` 除以 $(10^9 + 7)$ 时生成的汇编：

```nasm
;  input (rdi): x
; output (rax): x mod (m=1e9+7)
mov    rax, rdi
movabs rdx, -8543223828751151131  ; load magic constant into a register
mul    rdx                        ; perform multiplication
mov    rax, rdx
shr    rax, 29                    ; binary shift of the result
```

这项技术称为 *Barrett 规约*（Barrett reduction），叫"规约"是因为它主要用于取模运算——借助下面这个公式，取模可以换成一次除法、一次乘法和一次减法：

$$
r = x - \lfloor x / y \rfloor \cdot y
$$

这种方法需要一些预计算，其中包括一次货真价实的除法。因此，只有当你执行的不是一次而是几次除法、且都用同一个常数除数时，它才划算。

### 为什么行得通 {#why-it-works}

为什么这样的 $m$ 和 $s$ 总是存在，以及怎么找到它们，都不太显然。但对固定的 $s$，直觉告诉我们 $m$ 应该尽可能接近 $2^s/y$，这样 $2^s$ 才能约掉。于是有两个自然的选择：$\lfloor 2^s/y \rfloor$ 和 $\lceil 2^s/y \rceil$。前者不行，因为如果你代入

$$
\Bigl \lfloor \frac{x \cdot \lfloor 2^s/y \rfloor}{2^s} \Bigr \rfloor
$$

那么对任何整数 $\frac{x}{y}$（$y$ 为奇数时），结果都会严格小于真值。这样就只剩另一种情形，$m = \lceil 2^s/y \rceil$。现在，试着推导计算结果的上下界：

$$
  \lfloor x / y \rfloor
= \Bigl \lfloor \frac{x \cdot m}{2^s} \Bigr \rfloor
= \Bigl \lfloor \frac{x \cdot \lceil  2^s /y \rceil}{2^s} \Bigr \rfloor
$$

先看 $m$ 的界：

$$
2^s / y
\le
\lceil 2^s / y \rceil
<
2^s / y + 1
$$

再看整个表达式：

$$
x / y - 1
<
\Bigl \lfloor \frac{x \cdot \lceil  2^s /y \rceil}{2^s} \Bigr \rfloor
<
x / y + x / 2^s
$$

可以看到结果落在大小为 $(1 + \frac{x}{2^s})$ 的某个区间里，而如果对所有可能的 $x / y$ 这个区间永远恰好包含一个整数，那么算法就保证给出正确答案。结果表明，我们总可以把 $s$ 设得足够高来实现这一点。

最坏的情况会是什么样？怎样选取 $x$ 和 $y$ 才能让区间 $(x/y - 1, x/y + x / 2^s)$ 里装下两个整数？可以看到整数比值行不通，因为左边界取不到；而假设 $x/2^s < 1$，区间里就只有 $x/y$ 自己。真正的最坏情况实际上是这样一种 $x/y$：它最接近 $1$ 却不超过它。对 $n$ 位整数而言，就是第二大的可能整数除以第一大的：

$$
\begin{aligned}
    x = 2^n - 2
\\  y = 2^n - 1
\end{aligned}
$$

此时下界是 $(\frac{2^n-2}{2^n-1} - 1)$，上界是 $(\frac{2^n-2}{2^n-1} + \frac{2^n-2}{2^s})$。左边界距离一个整数近到无以复加，整个区间的大小则是第二大的可能。而妙处在于：如果 $s \ge n$，这个区间里唯一的整数就是 $1$，于是算法永远会返回它。

### Lemire 规约 {#lemire-reduction}

Barrett 规约有点复杂，而且由于取模是间接计算的，它还生成了较长的指令序列。有一种新的（[2019](https://arxiv.org/pdf/1902.01961.pdf)）方法，更简单，在某些情形下算取模还更快。它还没有约定俗成的名字，我打算称之为 [Lemire](https://lemire.me/blog/) 规约。

主要想法如下。考虑某个整数分数的浮点表示：

$$
\frac{179}{6} = 11101.1101010101\ldots = 29\tfrac{5}{6} \approx 29.83
$$

我们怎么"解剖"它来取出需要的部分？

- 要得到整数部分（29），直接在小数点前取整或截断即可。
- 要得到小数部分（⅚），直接取小数点后面的东西。
- 要得到余数（5），用小数部分乘以除数。

现在，对 32 位整数，我们可以取 $s = 64$，看看"乘法加移位"方案里所做的计算：

$$
  \lfloor x / y \rfloor
= \Bigl \lfloor \frac{x \cdot m}{2^s} \Bigr \rfloor
= \Bigl \lfloor \frac{x \cdot \lceil  2^s /y \rceil}{2^s} \Bigr \rfloor
$$

我们在这里真正做的是：把 $x$ 乘以一个浮点常数（$x \cdot m$），然后把结果截断（$(\lfloor \frac{\cdot}{2^s} \rfloor)$）。

如果我们取的不是最高位而是最低位呢？那对应的就是小数部分——把它乘回 $y$ 再截断结果，得到的恰好是余数：

$$
r = \Bigl \lfloor \frac{ (x \cdot \lceil  2^s /y \rceil \bmod 2^s) \cdot y }{2^s} \Bigr \rfloor
$$

这完美可行，因为我们在这里做的事可以解读为区区三次级联的浮点乘法，总相对误差为 $O(\epsilon)$。既然 $\epsilon = O(\frac{1}{2^s})$ 而 $s = 2n$，误差永远小于一，因此结果是精确的。

```c++
uint32_t y;

uint64_t m = uint64_t(-1) / y + 1; // ceil(2^64 / y)

uint32_t mod(uint32_t x) {
    uint64_t lowbits = m * x;
    return ((__uint128_t) lowbits * y) >> 64; 
}

uint32_t div(uint32_t x) {
    return ((__uint128_t) m * x) >> 64;
}
```

我们还能检查 $x$ 能否被 $y$ 整除，只需一次乘法——依据是"除法的余数为零当且仅当小数部分（$m \cdot x$ 的低 64 位）不超过 $m$"这一事实（否则它乘回 $y$ 再右移 64 位后会变成一个非零数）：

```c++
bool is_divisible(uint32_t x) {
    return m * x < m;
}
```

这种方法唯一的缺点是：执行乘法需要四倍于原尺寸的整数类型，而其他规约方法用 double 就够了。

还有一种通过小心操纵中间结果的各半部分来计算 64×64 取模的办法；实现留作读者练习。

### 延伸阅读 {#further-reading}

想了解更通用的优化整数除法实现，参见 [libdivide](https://github.com/ridiculousfish/libdivide) 和 [GMP](https://gmplib.org/)。

也值得一读的是 [Hacker's Delight](https://www.amazon.com/Hackers-Delight-2nd-Henry-Warren/dp/0321842685)，它有一整章专门讲整数除法。
