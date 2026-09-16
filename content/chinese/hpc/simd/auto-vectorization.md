---
title: 自动向量化与 SPMD
weight: 10
draft: true
---

SIMD 并行最常用于*易并行*（embarrassingly parallel）计算：那种你所做的只是对数组的所有元素施加某个逐元素函数、再把结果写到别处的计算。在这种场景下，你甚至不需要了解 SIMD 的原理：编译器完全有能力自己优化这样的循环——你只需要知道这种优化的存在，以及它通常能带来 5-10 倍的加速。

什么都不做、依赖自动向量化，实际上是使用 SIMD 最流行的方式。事实上，在很多情况下，甚至有人建议为了简单性和可维护性而坚持使用朴素的标量代码。

但往往连那些看起来很容易向量化的循环也不会被优化，原因出在一些技术细节上。[正如许多其他情形一样](/hpc/compilation/contracts)，编译器可能需要程序员提供一些额外的输入，因为程序员对问题的了解可能比静态分析能推断出来的多一点。

### 潜在的问题 {#potential-problems}

考虑我们[开头用过](../intrinsics/#simd-intrinsics)的"a + b"例子：

```c++
void sum(int *a, int *b, int *c, int n) {
    for (int i = 0; i < n; i++)
        c[i] = a[i] + b[i];
}
```

让我们设身处地站在编译器的角度，想想这个循环被向量化时可能出什么问题。

**数组大小。** 如果数组大小事先未知，那么它可能太小，向量化根本不划算。就算它足够大，我们也得为循环的余部插入一个额外的检查，用标量方式处理它，而这要付出一个分支的代价。

为了消除这些运行时检查，请使用编译期常量的数组大小，而且最好把数组填充到 SIMD 块大小的最近倍数。

**内存别名。** 即使数组大小的问题不存在，向量化这个循环也不总是技术上正确的。例如，数组 `a` 和 `c` 可能以开头只错开一个位置的方式相交——谁知道呢，也许程序员就是想用这种卷积的方式来计算斐波那契数列。在这种情况下，SIMD 块中的数据会相交，观察到的行为就会与标量情形不同。

当编译器无法证明这个函数不会用于相交的数组时，它只能生成两个实现版本——一个向量化的和一个"安全"的——并插入运行时检查在两者之间选择。为了避免这些检查，我们可以加上 `__restrict__` 关键字，告诉编译器我们保证没有内存被别名（alias）：

```cpp
void add(int * __restrict__ a, const int * __restrict__ b, int n) {
    for (int i = 0; i < n; i++)
        a[i] += b[i];
}
```

另一种方式是 SIMD 特有的"忽略向量依赖"pragma。这是告知编译器循环迭代之间没有依赖的一般方法：

```c++
#pragma GCC ivdep
for (int i = 0; i < n; i++)
    // ...
```

**对齐。** 编译器对这些数组的对齐情况同样一无所知，只能要么在向量化段开始前先处理这些数组开头的若干元素，要么冒着损失一些性能的风险使用[非对齐内存访问](../moving)。

为了帮编译器消除这种角落情况，我们可以对静态数组使用 `alignas` 说明符，并用 `std::assume_aligned` 函数标记指针是对齐的。

**检查向量化是否发生。** 无论哪种情况，检查编译器是否按你的意图向量化了循环都是有用的。你可以[把它编译成汇编](/hpc/compilation/stages)，寻找以"v"开头的指令块，或者加上 `-fopt-info-vec-optimized` 编译标志，让编译器指出自动向量化发生在哪里、用的是哪种 SIMD 宽度。如果把 `optimized` 换成 `missed` 或 `all`，你还可能得到它在其他地方没有向量化的原因。

还有[许多其他方式](https://software.intel.com/sites/default/files/m/4/8/8/2/a/31848-CompilerAutovectorizationGuide.pdf)可以告诉编译器我们的确切意图，但在特别复杂的情形下——比如循环内有大量分支或函数调用——不如直接下降一层抽象，手动向量化。

### SPMD {#spmd}

在自动向量化与手动使用 SIMD 内建函数之间，有一个漂亮的折中："单程序多数据"（SPMD）。这是一种计算模型，程序员写下的看上去是一段普通的串行程序，但它实际在硬件上并行地执行。

编程体验大体相同，也仍然存在"计算必须是数据并行的"这个根本限制，但 SPMD 确保无论编译器和目标 CPU 架构如何，向量化都会发生。它还允许计算自动并行到多个核心上，在某些情况下甚至可以卸载到其他类型的并行硬件上。

一些现代语言（[Julia](https://docs.julialang.org/en/v1/base/base/#Base.SimdLoop.@simd)）、多进程 API（[OpenMP](https://www.openmp.org/spec-html/5.0/openmpsu42.html)）和专门的编译器（Intel [ISPC](https://ispc.github.io/)）都支持 SPMD，但它最成功的舞台是 GPU 编程——那里的问题和硬件都是大规模并行的。

我们将在第二部分更深入地介绍这种计算模型

<!-- This approach is especially popular with [game developers](https://twitter.com/pbrubaker/status/1537041398037303296) because they need to support many platforms and have reliable performance, and also because it resembles the way graphics programming is done. -->
