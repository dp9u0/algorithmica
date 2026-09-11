---
title: 情境性优化
weight: 3
draft: true
---

<!--

Generally, you always want to specify the exact platform you are running and turn on `-O3`, but other optimizations, like the ones discussed [in the previous section](../assembly), are far more situational and require some input from the programmer.

-->

`-O2` 和 `-O3` 启用的大多数编译器优化都有保证：要么提升性能，至少也不会严重损害。那些没被 `-O3` 收录的优化，要么不符合严格的标准合规性，要么高度依赖具体场景，需要程序员补充输入才能判断使用它们是否划算。

来讨论其中最常用的几个——本书前面也都讲过。

### 循环展开 {#loop-unrolling}

[循环展开](/hpc/architecture/loops#loop-unrolling)默认关闭，除非循环的迭代次数是编译期已知的小常数——这种情况下循环会被替换成一段完全无跳转的重复指令序列。可以用 `-funroll-loops` 标志全局启用，它会展开所有迭代次数能在编译期确定、或进入循环时就能确定的循环。

也可以用 pragma 针对特定循环：

```c++
#pragma GCC unroll 4
for (int i = 0; i < n; i++) {
    // ...
}
```

循环展开会增大二进制体积，运行可能变快也可能不变快。不要狂热地使用它。

### 函数内联 {#function-inlining}

[内联](/hpc/architecture/functions#inlining)最好交给编译器决定，但你可以用 `inline` 关键字施加影响：

```c++
inline int square(int x) {
    return x * x;
}
```

不过，如果编译器认为潜在的性能收益不值当，这个提示可能被忽略。加上 `always_inline` 属性可以强制内联：

```c++
#define FORCE_INLINE inline __attribute__((always_inline))
```

还有 `-finline-limit=n` 选项，可以为被内联函数的体积（按指令数计）设定具体阈值。Clang 里的等价选项是 `-inline-threshold`。

### 分支的可能性 {#likeliness-of-branches}

分支的[可能性](/hpc/architecture/layout#unequal-branches)可以用 `if` 和 `switch` 中的 `[[likely]]`、`[[unlikely]]` 属性来提示：

```c++
int factorial(int n) {
    if (n > 1) [[likely]]
        return n * factorial(n - 1);
    else [[unlikely]]
        return 1;
}
```

这是个 C++20 才出现的新特性。在那之前，有各编译器专属的 intrinsic，用法类似地包裹条件表达式。老版本 GCC 里的同一个例子：

```c++
int factorial(int n) {
    if (__builtin_expect(n > 1, 1))
        return n * factorial(n - 1);
    else
        return 1;
}
```

<!--

What it usually does is it swaps the branches so that the more likely one goes immediately after jump (recall that "don't jump" branch is taken by default). The performance gain is usually rather small, because for most hot spots hardware branch prediction works just fine.
-->

还有许多类似的场合需要你给编译器指个方向，等它们更切题时我们再讲。

### 剖析引导优化 {#profile-guided-optimization}

往源代码里加这些元数据很繁琐。哪怕不用加这些，人们本来就已经讨厌写 C++ 了。

而且某些优化到底有没有益处，并不总是显而易见。要决定是否重排分支、内联函数、展开循环，我们需要这些问题的答案：

- 这个分支多久被走一次？
- 这个函数多久被调用一次？
- 这个循环平均迭代多少次？

幸运的是，有一种办法能自动提供这些真实世界的信息。

*剖析引导优化*（profile-guided optimization，PGO，也被叫作"pogo"，因为发音更省事也更好玩）是一种利用[剖析数据](/hpc/profiling)来超越纯静态分析所能达到的性能的技术。概括地说，它先在程序中感兴趣的点上加计时器和计数器，编译并在真实数据上运行，然后再次编译——这次把测试运行得到的额外信息提供给编译器。

整个过程由现代编译器自动化。例如，`-fprofile-generate` 标志会让 GCC 给程序插装剖析代码：

```
g++ -fprofile-generate [other flags] source.cc -o binary
```

运行程序——输入最好尽可能接近真实用例——之后会生成一堆 `*.gcda` 文件，其中包含测试运行的日志数据；接着我们可以重新构建程序，这次加上 `-fprofile-use` 标志：

```
g++ -fprofile-use [other flags] source.cc -o binary
```

对大型代码库，它通常能带来 10-20% 的性能提升，因此性能关键项目的构建流程普遍包含这一步。这也给了我们更多理由去打磨扎实的基准测试代码。

<!--

We will study how profiling works more deeply in the [next chapter](../../profiling).

-->
