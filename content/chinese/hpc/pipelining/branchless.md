---
title: 无分支编程
weight: 3
draft: true
---

正如[上一节](../branching)所确立的，CPU 无法有效预测的分支代价高昂——预测失败后要重新取指，可能造成长长的流水线停顿。本节讨论的是如何从一开始就消除分支。

### 谓词化

我们继续之前开始的那个案例——创建一个随机数数组，把其中小于 50 的元素全部加起来：

```c++
for (int i = 0; i < N; i++)
    a[i] = rand() % 100;

volatile int s;

for (int i = 0; i < N; i++)
    if (a[i] < 50)
        s += a[i];
```

我们的目标是消除 `if` 语句带来的分支。可以试着这样去掉它：

```c++
for (int i = 0; i < N; i++)
    s += (a[i] < 50) * a[i];
```

现在循环每个元素只需约 7 个周期，而不是原先的约 14 个。而且把 `50` 换成别的阈值，性能保持不变——它不依赖分支概率。

且慢……这里不是应该还有个分支吗？`(a[i] < 50)` 是怎么映射到汇编的？

汇编里没有布尔类型，也没有哪条指令能根据比较结果直接产出 1 或 0，但我们可以这样间接算出来：`(a[i] - 50) >> 31`。这个技巧利用了[整数的二进制表示](/hpc/arithmetic/integer)，具体来说：若表达式 `a[i] - 50` 为负（即 `a[i] < 50`），则结果的最高位会被置为 1，随后用右移把它提取出来。

```nasm
mov  ebx, eax   ; t = x
sub  ebx, 50    ; t -= 50
sar  ebx, 31    ; t >>= 31
imul  eax, ebx   ; x *= t
```

实现这一整套的另一种更绕的办法，是把符号位转成掩码，然后用按位 `and` 代替乘法：`((a[i] - 50) >> 31 - 1) & a[i]`。考虑到 `imul` 与其他指令不同、要花 3 个周期，这一替换能让整个序列快一个周期：

```nasm
mov  ebx, eax   ; t = x
sub  ebx, 50    ; t -= 50
sar  ebx, 31    ; t >>= 31
; imul  eax, ebx ; x *= t
sub  ebx, 1     ; t -= 1 (causing underflow if t = 0)
and  eax, ebx   ; x &= t
```

注意，从编译器的角度看，这个优化严格来说并不正确：对最低的 50 个可表示整数——即 $[-2^{31}, - 2^{31} + 49]$ 范围内的数——结果会因下溢而出错。我们知道所有数都在 0 到 100 之间，这种事不会发生，但编译器不知道。

但编译器实际上选择了另一条路。它没有采用这个算术技巧，而是用了一条特殊的 `cmov`（条件传送，"conditional move"）指令，根据条件来赋值（条件的计算与检查用的是标志寄存器，与跳转的做法相同）：

```nasm
mov     ebx, 0      ; cmov doesn't support immediate values, so we need a zero register
cmp     eax, 50
cmovge  eax, ebx    ; eax = (eax >= 50 ? eax : ebx=0)
```

所以上面的代码其实更接近于使用像这样的三元运算符：

```c++
for (int i = 0; i < N; i++)
    s += (a[i] < 50 ? a[i] : 0);
```

两种写法都会被编译器优化，生成如下汇编：

```nasm
    mov     eax, 0
    mov     ecx, -4000000
loop:
    mov     esi, dword ptr [rdx + a + 4000000]  ; load a[i]
    cmp     esi, 50
    cmovge  esi, eax                            ; esi = (esi >= 50 ? esi : eax=0)
    add     dword ptr [rsp + 12], esi           ; s += esi
    add     rdx, 4
    jnz     loop                                ; "iterate while rdx is not zero"
```

这一通用技术称为*谓词化*（predication），它大致等价于下面这个代数技巧：

$$
x = c \cdot a + (1 - c) \cdot b
$$

这样确实消除了分支，但代价是*两个*分支都得算，外加 `cmov` 本身。由于算">="分支分文不花，其性能恰好等于分支版本中["永远为真"的情形](../branching/#branch-prediction)。

### 谓词化何时划算

使用谓词化消除了[控制冒险](../hazards)，却引入了数据冒险。流水线停顿依然存在，只是更便宜：只需等 `cmov` 的结果揭晓，而不必在预测失败时冲刷整条流水线。

然而，很多情况下让带分支的代码保持原样反而更高效。当计算*两个*分支（而非只算*一个*）的开销超过潜在分支预测失败的惩罚时，就是如此。

在我们的例子中，当分支能以约 75% 以上的概率被预测时，带分支的代码胜出。

![](/en/hpc/pipelining/img/branchy-vs-branchless.svg)

编译器普遍把 75% 这个阈值当作是否使用 `cmov` 的启发式判据。不幸的是，这个概率在编译期通常是未知的，因此需要通过以下几种方式之一提供：

- 我们可以用[性能剖析引导优化](/hpc/compilation/situational/#profile-guided-optimization)，让它自行决定用不用谓词化。
- 我们可以用[倾向性属性](../branching#hinting-likeliness-of-branches)和[编译器特有的内建函数](/hpc/compilation/situational)来提示分支的倾向：GCC 的 `__builtin_expect_with_probability` 和 Clang 的 `__builtin_unpredictable`。
- 我们还可以用三元运算符或各种算术技巧改写带分支的代码——这相当于程序员与编译器之间某种隐式契约：代码既然这么写了，多半就是想无分支。

"正道"是用分支提示，可惜对它的支持并不到位。眼下，等到编译器后端决定 `cmov` 是否更划算时，[这些提示似乎已经丢失](https://bugs.llvm.org/show_bug.cgi?id=40027)。这方面[有一些进展](https://discourse.llvm.org/t/rfc-cmov-vs-branch-optimization/6040)，但当前还没有什么好办法能强迫编译器生成无分支代码，所以有时最好的指望就是手写一小段汇编。

<!--

Because this is very architecture-specific.

in the absence of branch likeliness hints

While any program that uses a ternary operator is equivalent to a program that uses an `if` statement

The codes seem equivalent. My guess is that the compiler doesn't know that `s + a[i]` does not cause integer overflow.

(The compiler can't optimize it because it's technically [not allowed to](/hpc/compilation/contracts): despite `y - x` being valid, `x - y` could over/underflow, causing undefined behavior. Although fully correct, I guess the compiler just doesn't date executing it.)

Branchless computing tricks like this one are especially important in all sorts of parallel algorithms.

The `cmov` variant doesn't care about probabilities of branches. It only wins if the branch probability if 75% chance, which usually is the heuristic threshold set in compilers.

This is a legal optimization, but I guess an implicit contract has evolved between application programmers and compiler engineers that if you write a ternary operator, then you kind of telling that it is likely going to be an unpredictable branch.

The general technique is called *branchless* or *branch-free* programming. Predication is the main tool of it, but there are more complicated ways.

-->

<!--

Let's do a few more examples as an exercise.

```c++
int max(int a, int b) {
    return (a > b) * a + (a <= b) * b;
}
```

```c++
int max(int a, int b) {
    return (a > b ? a : b);
}
```


```c++
int abs(int a, int b) {
    return max(diff, -diff);
}
```

```c++
int abs(int a, int b) {
    int diff = a - b;
    return (diff < 0 ? -diff : diff);
}
```

```c++
int abs(int a) {
    return (a > 0 ? a : -a);
}
```

```c++
int abs(int a) {
    int mask = a >> 31;
    a ^= mask;
    a -= mask;
    return a;
}
```

-->

### 更大的例子

**字符串。** 大致简化地说，一个 `std::string` 由两部分组成：一个指向以空字符结尾的 `char` 数组（即所谓"C 字符串"）的指针——数组分配在堆上某处——以及一个记录字符串长度的整数。

字符串最常见的取值是空串——这也是它的默认值。空串总得处理，惯用做法是把指针赋为 `nullptr`、长度赋为 `0`，然后在每个涉及字符串的过程开头检查指针是否为空、长度是否为零。

然而这需要一个额外的分支，代价不小（除非字符串绝大多数为空、或绝大多数非空）。要消掉这次检查、也就消掉这个分支，可以分配一个"零 C 字符串"——其实就是分配在某处的一个零字节——然后让所有空串都指向它。这样一来，所有针对空串的字符串操作都得读这个无用的零字节，但这仍比一次分支预测失败便宜得多。

**二分查找。** 标准的二分查找[可以写成](/hpc/data-structures/binary-search)无分支的版本，在小数组（能装进缓存）上比带分支的 `std::lower_bound` 快约 4 倍：

```c++
int lower_bound(int x) {
    int *base = t, len = n;
    while (len > 1) {
        int half = len / 2;
        base += (base[half - 1] < x) * half; // will be replaced with a "cmov"
        len -= half;
    }
    return *base;
}
```

除了更复杂之外，它还有个小缺点：比较次数可能更多（恒为 $\lceil \log_2 n \rceil$ 次，而不是 $\lfloor \log_2 n \rfloor$ 或 $\lceil \log_2 n \rceil$ 二者之一），而且无法对未来的内存读取做推测（这本相当于预取，所以在超大数组上会吃亏）。

一般而言，让数据结构无分支的办法是隐式或显式地*填充*（padding）它们，使其操作耗费恒定次数的迭代。更复杂的例子参见[该文](/hpc/data-structures/binary-search)。

<!--

The only downside of the branchless implementation is that it potentially does more memory reads: 

There are typically two ways to achieve this:

And in general, data structures can be "padded" to be made constant size or height.

That there are no substantial reasons why compilers can't do this on their own, but unfortunately this is just how it is right now.

-->

**数据并行编程。** 无分支编程对 [SIMD](/hpc/simd) 应用非常重要，因为 SIMD 压根就没有分支。

在我们的数组求和例子中，把累加器的 `volatile` 类型限定符去掉，编译器就能[向量化](/hpc/simd/auto-vectorization)这个循环：

```c++
/* volatile */ int s = 0;

for (int i = 0; i < N; i++)
    if (a[i] < 50)
        s += a[i];
```

现在每个元素只需约 0.3 个周期，主要[瓶颈在内存](/hpc/cpu-cache/bandwidth)。

编译器通常能向量化任何没有分支、迭代间也没有依赖的循环——以及少量偏离这一模式的特例，比如[归约](/hpc/simd/reduction)，或只含一个没有 else 的 if 的简单循环。更复杂情形的向量化是个非常不平凡的问题，可能要用到[掩码](/hpc/simd/masking)、[寄存器内置换](/hpc/simd/shuffling)等各种技术。

<!--

**Binary exponentiation.** However, when it is constant

When we can iterate in small batches, [autovectorization](/hpc/simd/autovectorization) speeds it up 13x.

-->
