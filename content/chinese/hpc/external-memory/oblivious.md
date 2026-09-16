---
title: 缓存无关算法
weight: 7
draft: true
---

在[外部存储器模型](../model)的语境下，高效算法有两类：

- *缓存感知*（cache-aware）算法：在 $B$ 和 $M$ *已知*的情况下高效。
- *缓存无关*（cache-oblivious）算法：对*任意*的 $B$ 和 $M$ 都高效。

例如，[外部归并排序](../sorting)是缓存感知而非缓存无关的算法：我们需要知道系统的内存特征——具体来说就是可用内存与块大小之比——才能为 $k$ 路归并排序选出正确的 $k$。

缓存无关算法令人感兴趣之处在于，它们会自动对缓存层级中的所有内存层级都达到最优，而不只是对专门调优过的那一层。本文考察它们在矩阵计算中的一些应用。

## 矩阵转置 {#matrix-transposition}

假设有一个方阵 $A$，大小为 $N \times N$，我们要对它转置。按定义直译的朴素做法大致是这样：

```cpp
for (int i = 0; i < n; i++)
    for (int j = 0; j < i; j++)
        swap(a[j * N + i], a[i * N + j]);
```

这里我们用单个指向内存区域开头的指针代替二维数组，以便更明确地展现它的内存操作。

这段代码的 I/O 复杂度是 $O(N^2)$，因为写入不是顺序的。如果你试着交换两个迭代变量，读写的情况会对调过来，但结果（依旧）一样。

### 算法 {#algorithm}

*缓存无关*算法依赖如下这个分块矩阵恒等式：

$$
\begin{pmatrix}
A & B \\
C & D
\end{pmatrix}^T=
\begin{pmatrix}
A^T & C^T \\
B^T & D^T
\end{pmatrix}
$$

它让我们可以用分治法递归地求解这个问题：

1. 把输入矩阵划分成 4 个更小的矩阵。
2. 递归地转置每一个。
3. 交换位于角落的结果矩阵，完成合并。

在矩阵上实现分治比在数组上麻烦一些，但主要思路相同。我们不想显式地复制子矩阵，而是想使用指向它们的"视图"；并且在数据开始装得进 L1 缓存时切换回朴素方法（如果事先不知道 L1 的大小，就选个像 $32 \times 32$ 这样的小值）。我们还需要小心处理 $n$ 为奇数、从而无法把矩阵均分成 4 块的情形。

```cpp
void transpose(int *a, int n, int N) {
    if (n <= 32) {
        for (int i = 0; i < n; i++)
            for (int j = 0; j < i; j++)
                swap(a[i * N + j], a[j * N + i]);
    } else {
        int k = n / 2;

        transpose(a, k, N);
        transpose(a + k, k, N);
        transpose(a + k * N, k, N);
        transpose(a + k * N + k, k, N);
        
        for (int i = 0; i < k; i++)
            for (int j = 0; j < k; j++)
                swap(a[i * N + (j + k)], a[(i + k) * N + j]);
        
        if (n & 1)
            for (int i = 0; i < n - 1; i++)
                swap(a[i * N + n - 1], a[(n - 1) * N + i]);
    }
}
```

该算法的 I/O 复杂度是 $O(\frac{N^2}{B})$，因为每个合并阶段我们只需触及大约一半的内存块，这意味着问题在每个阶段都在变小。

把这份代码推广到非方阵的一般情形，就留作读者的练习。

## 矩阵乘法 {#matrix-multiplication}

接下来考虑一个稍微复杂些的东西：矩阵乘法。

$$
C_{ij} = \sum_k A_{ik} B_{kj}
$$

朴素算法就是把定义直接翻译成代码：

```cpp
// don't forget to initialize c[][] with zeroes
for (int i = 0; i < n; i++)
    for (int j = 0; j < n; j++)
        for (int k = 0; k < n; k++)
            c[i * n + j] += a[i * n + k] * b[k * n + j];
```

它总共需要访问 $O(N^3)$ 个块，因为每一次标量乘法都需要一次单独的块读取。

一个众所周知的优化是先把 $B$ 转置：

```cpp
for (int i = 0; i < n; i++)
    for (int j = 0; j < i; j++)
        swap(b[j][i], b[i][j])
// ^ or use our faster transpose from before

for (int i = 0; i < n; i++)
    for (int j = 0; j < n; j++)
        for (int k = 0; k < n; k++)
            c[i * n + j] += a[i * n + k] * b[j * n + k]; // <- note the indices
```

无论转置是朴素地完成，还是用我们此前开发的更快的缓存无关方法完成，把其中一个矩阵转置之后的矩阵乘法都可以做到 $O(N^3/B + N^2)$，因为所有内存访问现在都是顺序的了。

看起来我们没法做得更好，但事实证明可以。

### 算法 {#algorithm-1}

缓存无关矩阵乘法本质上依赖与转置相同的技巧：我们需要不断划分数据，直到它装得进最低一层缓存（即 $N^2 \leq M$）。对矩阵乘法来说，这相当于使用下面这个公式：

$$
\begin{pmatrix}
A_{11} & A_{12} \\
A_{21} & A_{22} \\
\end{pmatrix} \begin{pmatrix}
B_{11} & B_{12} \\
B_{21} & B_{22} \\
\end{pmatrix} = \begin{pmatrix}
A_{11} B_{11} + A_{12} B_{21} & A_{11} B_{12} + A_{12} B_{22}\\
A_{21} B_{11} + A_{22} B_{21} & A_{21} B_{12} + A_{22} B_{22}\\
\end{pmatrix}
$$

不过实现起来要更难一些，因为我们现在总共有 8 次递归的矩阵乘法：

```cpp
void matmul(const float *a, const float *b, float *c, int n, int N) {
    if (n <= 32) {
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                for (int k = 0; k < n; k++)
                    c[i * N + j] += a[i * N + k] * b[k * N + j];
    } else {
        int k = n / 2;

        // c11 = a11 b11 + a12 b21
        matmul(a,     b,         c, k, N);
        matmul(a + k, b + k * N, c, k, N);
        
        // c12 = a11 b12 + a12 b22
        matmul(a,     b + k,         c + k, k, N);
        matmul(a + k, b + k * N + k, c + k, k, N);
        
        // c21 = a21 b11 + a22 b21
        matmul(a + k * N,     b,         c + k * N, k, N);
        matmul(a + k * N + k, b + k * N, c + k * N, k, N);
        
        // c22 = a21 b12 + a22 b22
        mul(a + k * N,     b + k,         c + k * N + k, k, N);
        mul(a + k * N + k, b + k * N + k, c + k * N + k, k, N);

        if (n & 1) {
            for (int i = 0; i < n; i++)
                for (int j = 0; j < n; j++)
                    for (int k = (i < n - 1 && j < n - 1) ? n - 1 : 0; k < n; k++)
                        c[i * N + j] += a[i * N + k] * b[k * N + j];
        }
    }
}
```

由于这里还有许多其他因素在起作用，我们不会对这份实现跑基准测试，而是只在外部存储器模型中对它做理论性能分析。

### 分析 {#analysis}

算法的算术复杂度保持不变，因为递推式

$$
T(N) = 8 \cdot T(N/2) + \Theta(N^2)
$$

的解是 $T(N) = \Theta(N^3)$。

看起来我们还没"治"住任何东西，但来考虑一下它的 I/O 复杂度：

$$
T(N) = \begin{cases}
O(\frac{N^2}{B}) & N \leq \sqrt M & \text{(we only need to read it)} \\
8 \cdot T(N/2) + O(\frac{N^2}{B}) & \text{otherwise}
\end{cases}
$$

这个递推式由 $O((\frac{N}{\sqrt M})^3)$ 个基础情形主导，于是总复杂度是

$$
T(N) = O\left(\frac{(\sqrt{M})^2}{B} \cdot \left(\frac{N}{\sqrt M}\right)^3\right) = O\left(\frac{N^3}{B\sqrt{M}}\right)
$$

这比单纯的 $O(\frac{N^3}{B})$ 要好，而且好不少。

### Strassen 算法 {#strassen-algorithm}

与 Karatsuba 算法的精神相似，矩阵乘法可以分解为一种涉及 7 次 $\frac{n}{2}$ 规模矩阵乘法的形式，而主定理告诉我们，这样的分治算法耗时 $O(n^{\log_2 7}) \approx O(n^{2.81})$，在外部存储器模型中也有相似的渐近复杂度。

这项被称为 Strassen 算法的技术，同样把每个矩阵分成 4 块：

$$
\begin{pmatrix}
C_{11} & C_{12} \\
C_{21} & C_{22} \\
\end{pmatrix}
=\begin{pmatrix}
A_{11} & A_{12} \\
A_{21} & A_{22} \\
\end{pmatrix}
\begin{pmatrix}
B_{11} & B_{12} \\
B_{21} & B_{22} \\
\end{pmatrix}
$$

但它随后会计算这 $\frac{N}{2} \times \frac{N}{2}$ 矩阵的若干中间乘积，再把它们组合起来得到矩阵 $C$：

$$
\begin{aligned}
   M_1 &= (A_{11} + A_{22})(B_{11} + B_{22})   & C_{11} &= M_1 + M_4 - M_5 + M_7
\\ M_2 &= (A_{21} + A_{22}) B_{11}             & C_{12} &= M_3 + M_5
\\ M_3 &= A_{11} (B_{21} - B_{22})             & C_{21} &= M_2 + M_4
\\ M_4 &= A_{22} (B_{21} - B_{11})             & C_{22} &= M_1 - M_2 + M_3 + M_6
\\ M_5 &= (A_{11} + A_{12}) B_{22}
\\ M_6 &= (A_{21} - A_{11}) (B_{11} + B_{12})
\\ M_7 &= (A_{12} - A_{22}) (B_{21} + B_{22})
\end{aligned}
$$

你要是愿意，可以用简单的代入法验证这些公式。

据我所知，主流的优化线性代数库都没有采用 Strassen 算法，不过确实有一些原型实现，对大于 2000 左右的矩阵是高效的。

这项技术已经实实在在地被多次扩展，通过考虑更多子矩阵乘积，把渐近复杂度进一步压低。截至 2020 年，当前的世界纪录是 $O(n^{2.3728596})$。能否在 $O(n^2)$、或至少 $O(n^2 \log^k n)$ 的时间内完成矩阵乘法，仍是一个悬而未决的问题。

## 延伸阅读 {#further-reading}

想要一个扎实的理论视角，可以读一读 Erik Demaine 的 [Cache-Oblivious Algorithms and Data Structures](https://erikdemaine.org/papers/BRICS2002/paper.pdf)。
