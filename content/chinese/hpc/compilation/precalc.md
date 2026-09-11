---
title: 预计算
weight: 8
draft: true
---

当编译器能推断出某个变量不依赖任何用户提供的输入时，它可以在编译期算出这个值，把它作为常量嵌入生成的机器码。

这项优化对性能帮助很大，但它不是 C++ 标准的一部分，所以编译器并非*必须*这么做。当一次编译期计算要么难以实现、要么太耗时间时，编译器可能放弃这个机会。

### 常量表达式 {#constant-expressions}

想要更可靠的方案，现代 C++ 允许把函数标记为 `constexpr`；只要调用时传入的是常量，它的值保证在编译期计算：

```c++
constexpr int fibonacci(int n) {
    if (n <= 2)
        return 1;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

static_assert(fibonacci(10) == 55);
```

这类函数有一些限制，比如只能调用其他 `constexpr` 函数、不能做内存分配，但除此之外，它们"原样"执行。

注意，`constexpr` 函数虽然在运行时零开销，却会增加编译时间，所以多多少少还是要关心一下它们的效率，别把什么 NP 完全的问题塞进去：

```c++
constexpr int fibonacci(int n) {
    int a = 1, b = 1;
    while (n--) {
        int c = a + b;
        a = b;
        b = c;
    }
    return b;
}
```

早期 C++ 标准里的限制多得多，比如函数内不能有任何状态、只能依靠递归，整个过程写起来更像 Haskell 而不是 C++。从 C++17 起，你甚至可以用命令式风格计算静态数组，这适合预计算查找表：

```c++
struct Precalc {
    int isqrt[1000];

    constexpr Precalc() : isqrt{} {
        for (int i = 0; i < 1000; i++)
            isqrt[i] = int(sqrt(i));
    }
};

constexpr Precalc P;

static_assert(P.isqrt[42] == 6);
```

注意，调用 `constexpr` 函数时如果传入的不是常量，编译器可能在编译期计算它们，也可能不：

```c++
for (int i = 0; i < 100; i++)
    cout << fibonacci(i) << endl;
```

在这个例子里，尽管严格说我们执行的是常数次迭代、传给 `fibonacci` 的参数在编译期已知，但它们并不算严格意义上的编译期常量。这个循环优化不优化，全由编译器定夺——对重计算，它常常选择不优化。

<!--

### Code Generation

There are plenty of languages that support computing *data* during compile time, but none can produce efficient code at all times.

One huge example is generating lexers and parsers: which is usually done in.

For example, CUDA and OpenCL are mostly C, and have no support for metaprogramming.

At some point (and perhaps to this day), these languages had no way to unroll loops, so people would write a [jinja template](https://jinja.palletsprojects.com/en/3.0.x/), call the thing from Python, and then compile.

It is not uncommon to use a templating engine to generate code. For example, CUDA (a GPU programming language) has no loop unrolling

-->
