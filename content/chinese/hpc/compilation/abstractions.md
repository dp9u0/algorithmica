---
title: "[草稿]非零开销的抽象"
weight: 7
draft: true
---

总体而言，抽象是好东西。用得好，它们能减少代码量，也减轻程序员的心智负担。

但抽象常常伴随着性能上的代价。使用共享库（shared library）时，你得额外花一些周期搬移数据，才能正确调用它的函数。调用虚方法（virtual method）时，你无法可靠预测接下来要执行的是哪段代码，实际上就吃到了一次分支预测失败。

C++ 和 Rust 这类语言大力宣扬*零开销*抽象（zero-cost abstraction）的理念——没有任何额外的运行时开销，而且至少在原则上能被编译器完全消除。但实践中，根本不存在零开销的抽象——编译器技术还没到那个水平。

**虚函数。**任何形式的运行时多态。

**边界检查。**不过编译器很擅长消除它们。

**一般来说，任何复杂的代码都算。**举个我个人很烦的例子：C++ 标准库的 `std::min`。它反复表现得比手写取最小值更差，原因在于它并非直接实现为 `return (a < b ? a : b)`，而是为了通用性用了变长初始化列表（variadic initializer list）和迭代器：

```cpp
template<typename _Tp> GLIBCXX14_CONSTEXPR inline _Tp min(initializer_list<_Tp> __l) {
    return *std::min_element(__l.begin(), __l.end());
}
```

把一个小程序改写得更直白、更贴近硬件，通常并不难。只要你开始一层层剥掉抽象，编译器终究会妥协。

面向对象语言、尤其是函数式语言，有一些像这样很难穿透的抽象。因此人们常常更愿意用接近 C 的风格、而非更高层的语言来编写性能关键的软件（解释器、运行时、数据库）。

大胡子 C/汇编程序员。

### 内存 {#memory}

指针追逐（pointer chasing）。

```c++
typedef vector< vector<int> > matrix;
matrix a(n, vector<int>(n, 0));

int val = a[i][j];
```

这样最多要慢两倍：你首先得取出

```c++
int a = new int[n * n];
memset(a, 0, 4 * n* n);

int val = a[i * n + j];
```

如果你实在想要一层抽象，可以写个包装：

```c++
template<typename T>
struct Matrix {
    int x, y, n, N;
    T* data;
    T* operator[](int i) { return data + (x + i) * N + y; }
};
```

例如，[缓存无关转置](/hpc/external-memory/oblivious)可以这样写：

```c++
Matrix<T> subset(int _x, int _y, int _n) { return {_n, _x, _y, N, data}; }

Matrix<T> transpose() {
    if (n <= 32) {
        for (int i = 0; i < n; i++)
            for (int j = 0; j < i; j++)
                swap((*this)[j][i], (*this)[i][j]);
    } else {
        auto A = subset(x, y, n / 2).transpose();
        auto B = subset(x + n / 2, y, n / 2).transpose();
        auto C = subset(x, y + n / 2, n / 2).transpose();
        auto D = subset(x + n / 2, y + n / 2, n / 2).transpose();
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                swap(B[i][j], C[i][j]);
    }

    return *this;
}
```

我个人更喜欢写底层代码，因为它更容易优化。

更整洁吗？我看未必。
