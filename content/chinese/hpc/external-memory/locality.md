---
title: 空间与时间局部性
weight: 8
draft: true
---

<!--

In some environments, the programmer has no direct control over caching. Moreover, sometimes we don't even know the high-level characteristics of the cache hierarchy, such as the memory size of each layer, the block size, the strategy used for cache eviction, or even the number of cache layers.

-->

要从内存操作的角度精确评估一个算法的性能，我们需要考虑缓存系统的多项特征：缓存层数、每层的[内存与块大小](../hierarchy)、每层所使用的确切[驱逐策略](../policies)，有时甚至还有[内存分页](../virtual)机制的细节。

在算法设计的早期阶段，把这些细枝末节抽象掉大有裨益。与其计算理论上的缓存命中率，用更定性的术语来推理缓存性能，往往更有意义。

<!--

In some environments, the programmer has no direct control over caching. Moreover, sometimes we don't even know the high-level characteristics of the cache hierarchy, such as the memory size of each layer, the block size, the strategy used for cache eviction, or even the number of cache layers.

In this article, we continue designing algorithms for the external memory model and address the problem of assessing I/O performance when some details of the cache system are unknown.

-->

在这个语境下，我们可以主要从两个维度来谈论缓存复用的程度：

- *时间局部性*（temporal locality）指在一段相对较短的时间内重复访问同一批数据，使得数据在两次请求之间大概率仍留在缓存里。
- *空间局部性*（spatial locality）指使用内存位置上彼此相近的元素，使得它们大概率会在同一个内存块中被一起取回。

换句话说，时间局部性说的是"同一个内存位置很可能很快再次被请求"，而空间局部性说的是"旁边的位置很可能紧接着就被请求"。

在本节中，我们会做几个案例研究，展示这些高层概念如何助力实际的优化。

### 深度优先 vs. 广度优先 {#depth-first-vs-breadth-first}

考虑一个像归并排序这样的分治算法。实现它有两种途径：

- 可以递归地实现，即"深度优先"，这也是通常的实现方式：排序左半边，排序右半边，然后归并两个结果。
- 也可以迭代地实现，即"广度优先"：先做最底下的一"层"，遍历整个数据集，把奇数位置的元素与偶数位置的元素比较；然后把第 1、2 个元素与第 3、4 个合并，把第 5、6 个与第 7、8 个合并，以此类推。

第二种做法看起来更繁琐，但更快——因为递归总是慢的，对吧？

一般来说，递归确实[很慢](/hpc/architecture/functions)，但对这个以及许多类似的分治算法而言，情况并非如此。迭代式做法的优势在于只做顺序 I/O，但递归式做法的时间局部性要好得多：一旦某个段完全装进了缓存，在递归所有更低的层里它都会留在那里，之后的访问时间也就更好。

事实上，由于只需分裂 $O(\log \frac{N}{M})$ 次就能做到这一点，我们总共只需读取 $O(\frac{N}{B} \log \frac{N}{M})$ 个块；而在迭代式做法里，无论如何，整个数组都要从头到尾读上 $O(\log N)$ 次。这带来了 $O(\frac{\log N}{\log N - \log M})$ 的加速比，最高可达一个数量级。

实践中，递归仍会带来一些开销，因此使用混合算法是有意义的：不必一路下探到基础情形，而是在递归的低层切换到迭代式的代码。

### 动态规划 {#dynamic-programming}

类似的推理也可以应用到动态规划算法的实现上，但会得出相反的结论。考虑经典的*背包问题*：给定 $N$ 个代价 $c_i$ 为正整数的物品，请选出一个总代价不超过给定常数 $W$ 的子集，使其总代价最大。

解法是引入*状态* $f[n, w]$，对应于不超过 $w$ 的最大总代价，且只使用前 $n$ 个物品。这些值可以以每表项 $O(1)$ 的时间计算：考虑取或不取第 $n$ 个物品，并利用动态规划先前的状态做出最优决策。

Python 有个方便的 `lru_cache` 装饰器，可以用记忆化递归来实现它：

```python
@lru_cache
def f(n, w):
    # check if we have no items to choose
    if n == 0:
        return 0
    
    # check if we can't pick the last item (note zero-based indexing)
    if c[n - 1] > w:
        return f(n - 1, w)
    
    # otherwise, we can either pick the last item or not
    return max(f(n - 1, w), c[n - 1] + f(n - 1, w - c[n - 1]))
```

计算 $f[N, W]$ 时，递归可能访问多达 $O(N \cdot W)$ 个不同的状态，这在渐近意义上是高效的，现实中却相当慢。即使把 Python 递归的开销、以及 LRU 缓存运转所需的全部[哈希表查询](../policies/#implementing-caching)都抹平，它依然慢，因为在执行过程的大部分时间里，它都在做随机 I/O。

我们可以换一种做法：为动态规划创建一个二维数组，并把递归替换成一个漂亮的嵌套循环，像这样：

```cpp
int f[N + 1][W + 1] = {0}; // this zero-fills the array

for (int n = 1; n <= N; n++)
    for (int w = 0; w <= W; w++)
        f[n][w] = c[n - 1] > w ?
                  f[n - 1][w] :
                  max(f[n - 1][k], c[n - 1] + f[n - 1][w - c[n - 1]]);
```

> **译者注**：上式中的 `f[n - 1][k]` 应为 `f[n - 1][w]`（原文笔误，否则代码无法编译）。

注意，我们计算下一层时只用到动态规划的上一层。这意味着，只要能把一层装进缓存，我们在外部存储器中就只需写入 $O(\frac{N \cdot W}{B})$ 个块。

不仅如此，如果我们只需要答案本身，就其实不必保存整个二维数组，只留最后一层就够了。这样，只需 $O(W)$ 的内存：维护一个含 $W$ 个值的单一数组即可。为了简化代码，我们可以稍微改变这个动态规划的语义，让它存储一个二值：用已考虑过的物品能否恰好凑出总和 $w$。这样的动态规划算起来更快：

```cpp
bool f[W + 1] = {0};
f[0] = 1;
for (int n = 0; n < N; n++)
    for (int x = W - c[n]; x >= 0; x--)
        f[x + c[n]] |= f[x];
```

顺带一提，既然它现在只用简单的按位操作，就还可以用 `bitset` 进一步优化：

```cpp
std::bitset<W + 1> b;
b[0] = 1;
for (int n = 0; n < N; n++)
    b |= b << c[n];
```

出人意料的是，这里仍有改进的空间，我们稍后会再回到这个问题。

### 稀疏表 {#sparse-table}

*稀疏表*（sparse table）是一种*静态*数据结构，常用于解决*静态 RMQ*问题，也用于一般性地计算任何类似的幂等区间归约。它可以形式化地定义为一个大小为 $\log n \times n$ 的二维数组：

$$
t[k][i] = \min \{ a_i, a_{i+1}, \ldots, a_{i+2^k-1} \}
$$

用大白话说：我们把每个长度为 2 的幂的段上的最小值都存起来。

这样的数组可以用来在常数时间内计算任意段上的最小值，因为对每个段，我们总能找到两个可能重叠的、长度为同一个 2 的幂的段，它们的并集恰好就是整个段。

![](/en/hpc/external-memory/img/sparse-table.png)

这意味着，我们只需取这两个预计算出的最小值中较小的一个作为答案：

```cpp
int rmq(int l, int r) { // half-interval [l; r)
    int t = __lg(r - l);
    return min(mn[t][l], mn[t][r - (1 << t)]);
}
```

`__lg` 函数是 GCC 提供的一个内建函数，计算一个数的二进制对数并向下取整。它内部使用 `clz`（"count leading zeros"，统计前导零）指令，再用 32（对 32 位整数而言）减去该计数，因此只需几个周期。

我在这篇文章里提起它，是因为它有多种可选的构建方式，内存操作效率各不相同。一般来说，稀疏表可以按动态规划的方式以 $O(n \log n)$ 时间构建：按 $i$ 递增或 $k$ 递增的顺序迭代，并应用以下恒等式：

$$
t[k][i] = \min(t[k-1][i], t[k-1][i+2^{k-1}])
$$

现在有两个设计抉择要做：对数规模的 $k$ 应该作为第一维还是第二维，以及是先遍历 $k$ 再遍历 $i$，还是反过来。这意味着共有 $2×2=4$ 种构建方式，而下面是最优的那一种：

```cpp
int mn[logn][maxn];

memcpy(mn[0], a, sizeof a);

for (int l = 0; l < logn - 1; l++)
    for (int i = 0; i + (2 << l) <= n; i++)
        mn[l + 1][i] = min(mn[l][i], mn[l][i + (1 << l)]);
```

这是内存布局与迭代顺序的全部组合中，唯一能产生漂亮的线性扫描的一种，速度约快 3 倍。作为练习，考虑其他三种变体，并想想*为什么*它们更慢。

### 结构体数组 vs. 数组结构体 {#array-of-structs-vs-struct-of-arrays}

假设你要实现一棵二叉树，并把它的各个字段分开存进几个数组，像这样：

```cpp
int left_child[maxn], right_child[maxn], key[maxn], size[maxn];
```

这种把每个字段与其他字段分开存放的内存布局，称为*数组结构体*（struct-of-arrays，SoA）。在大多数情况下，实现树的操作时，你访问一个结点后，紧接着就会访问它的全部或大部分内部数据。如果这些字段分开存放，就意味着它们位于不同的内存块中。倘若被请求的字段里有一些恰好在缓存里、另一些不在，你还是得等最慢的那个被取回来。

相反，如果改用*结构体数组*（array-of-structs，AoS）来存放，所需的块读取大约能减少到原来的 1/4，因为结点的全部数据都存放在同一个块里，一次便能取回：

```cpp
struct Node {
    int left_child, right_child, key, size;
};

Node t[maxn];
```

对数据结构来说，AoS 布局通常更受青睐，但 SoA 也有很好的用武之地：它虽然不利于查找，却远比后者适合线性扫描。

这种设计上的差异在数据处理应用中很重要。例如，数据库可以分为*行式*与*列式*（columnar，也称 column-oriented）：

- *行式*（row-oriented）存储格式适用于需要在大型数据集中查找少量对象、和/或获取它们全部或大部分字段的场合。例子：PostgreSQL、MongoDB。
- *列式*存储格式用于大数据处理与分析，那里你反正要把所有数据扫一遍来计算某些统计量。例子：ClickHouse、Hbase。

列式格式还有一个额外的优点：不同字段存放在互不相同的外部存储器区域中，因此可以只读取需要的那些字段。
