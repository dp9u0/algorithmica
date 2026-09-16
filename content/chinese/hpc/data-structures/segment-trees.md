---
title: 线段树
weight: 4
draft: true
---

从[优化](../s-tree)[二分查找](../binary-search)中学到的经验可以应用到范围广泛的数据结构上。

在这篇文章中，我们不再去优化 STL 里的某个东西，而是聚焦于*线段树*（segment tree）——一种对大多数*正常*程序员、甚至大多数计算机科学研究者[^tcs]来说可能都很陌生的结构，但它凭借速度和实现的简洁性在编程竞赛中被[极其广泛地](https://www.google.com/search?q=segment+tree+site%3Acodeforces.com&newwindow=1&sxsrf=APq-WBuTupSOnSn9JNEHhaqtmv0Uq0eogQ%3A1645969931499&ei=C4IbYrb2HYibrgS9t6qgDQ&ved=0ahUKEwj2p8_og6D2AhWIjYsKHb2bCtQQ4dUDCA4&uact=5&oq=segment+tree+site%3Acodeforces.com&gs_lcp=Cgdnd3Mtd2l6EAM6BwgAEEcQsAM6BwgAELADEEM6BAgjECc6BAgAEEM6BQgAEIAEOgYIABAWEB46BQghEKABSgQIQRgASgQIRhgAUMkFWLUjYOgkaANwAXgAgAHzAYgB9A-SAQYxNS41LjGYAQCgAQHIAQrAAQE&sclient=gws-wiz)使用。

[^tcs]: 线段树在理论计算机科学文献中很少被提及，因为它相对新颖（约 2000 年发明）、大多不做任何[其他二叉树](https://en.wikipedia.org/wiki/Tree_(data_structure))做不到的事，而且*渐进地*看也不更快——尽管在实践中，它常常在速度上大胜。

（如果你已经了解背景，可以直接跳到[最后一节](#wide-segment-trees)看新东西：比树状数组快 4 到 12 倍的*宽线段树*。）

### 动态前缀和 {#dynamic-prefix-sum}

<!--

This is a long article, and to make it less long, we will mostly be focusing on its simplest application -->

线段树很酷，能做很多不同的事情，但在本文中我们聚焦于它最简单的非平凡应用——*动态前缀和问题*（dynamic prefix sum）：

```cpp
void add(int k, int x); // react to a[k] += x (zero-based indexing)
int sum(int k);         // return the sum of the first k elements (from 0 to k - 1)
```

由于必须支持两种类型的查询，我们的优化问题变成了多维的，最优解取决于查询的分布。例如，如果一种查询极其罕见，我们就可以只为另一种优化，这相对容易：

- 如果我们只在乎*更新数组*的成本，就原样存储数组，在每次 `sum` 查询时直接[计算求和](/hpc/simd/reduction)。
- 如果我们只在乎*前缀和查询*的成本，就把前缀和预先备好，每次更新时[从头完整重算](/hpc/algorithms/prefix)。

这两种做法都在一种查询上做 $O(1)$ 的工作，但在另一种上要做 $O(n)$ 的工作。当两类查询的频率相差不大时，我们可以牺牲一些一方的性能换取另一方性能的提升。线段树让你做的正是这件事：达到两类查询都是 $O(\log n)$ 工作量的平衡点。

### 线段树的结构 {#segment-tree-structure}

线段树背后的主要思想是：

- 计算整个数组的和，把它记在某个地方；
- 把数组分成两半，计算两半各自的和，也把它们记下来；
- 再把这些半分成两半，在其上计算总共四个和，也记下来；
- ……如此继续，直到递归地到达长度为一的段。

这些计算出来的子段和可以在逻辑上表示为一棵二叉树——这就是我们所说的*线段树*：

![一棵线段树，sum(11) 与 add(10) 查询涉及的节点被高亮](/en/hpc/data-structures/img/segtree-path.png)

线段树有一些很好的性质：

- 如果底层数组有 $n$ 个元素，线段树恰好有 $(2n - 1)$ 个节点——$n$ 个叶子和 $(n - 1)$ 个内部节点——因为每个内部节点把一个段一分为二，而只需要 $(n - 1)$ 个这样的节点就能完全分割原来的 $[0, n-1]$ 区间。
- 树高是 $\Theta(\log n)$：从树根开始的每一层，节点数大致翻倍，它们的段长大致减半。
- 每个段都能拆成 $O(\log n)$ 个互不相交、对应线段树节点的段：每一层最多取两个。

当 $n$ 不是 2 的幂时，并非所有层都被完全填满——最后一层可能不完整——但这些性质依然成立。第一条性质让我们可以只用 $O(n)$ 的内存存储树，后两条让我们能用 $O(\log n)$ 时间解决问题：

- `add(k, x)` 查询的处理方式是把值 `x` 加到所有段包含元素 `k` 的节点上，而我们刚刚确认了这样的节点只有 $O(\log n)$ 个。
- `sum(k)` 查询的处理方式是找出共同构成前缀 `[0, k)` 的所有节点、把它们存储的值加起来——而我们也确认过它们至多 $O(\log n)$ 个。

但这仍是理论。我们稍后会看到，实现这个数据结构的方法多得惊人。

<!--

Note that by the same logic that each prefix can be covered by $O(\log n)$ nodes, each possible segment can also be covered by $O(\log n)$ nodes: you just possibly need at most two of them on each level. This lets us compute sums on any segment, although in this article we are not going to do it, instead reducing it to computing two prefix sums (from the right border, and the subtracting the prefix sum on the left border).

This is a general idea. Many different implementations possible, which we will explore one by one in this article.

Segment trees are built recursively: build a tree for left and right halves and merge results to get root.

Depending on the relative frequencies of the query types, the optimal solution may differ.

One way to do this is through a trick commonly called *square root decomposition*: we split the array (of size $n$) into blocks of approximately $\sqrt n$ elements,

sqrt

Enable [hugepages](/hpc/cpu-cache/paging) system-wide and forget about it.

Most of examples in this section are about optimizing some algorithms that are either included in standard library or take under 10 lines of code to implement naively, but we will start off with a bit more obscure example.

There are many things segment trees can do. Persistent structures, computational geometry. But for most of this article, we will focus on the dynamic (as opposed to static) prefix sum problem.

Segment trees are used for windowing queries or range queries in general, either by themselves or as part of a larger algorithm.

Functional programming, e.g., for implementing persistent arrays and derived structures.

-->

### 基于指针的实现 {#pointer-based-implementation}

实现线段树最直白的方式，是把我们需要的一切都显式地存在节点里：包括数组段的边界、和，以及指向孩子的指针。

如果我们在上"面向对象入门"课，我们会像这样递归地实现线段树：

```c++
struct segtree {
    int lb, rb;                         // the range this node is responsible for 
    int s = 0;                          // the sum of elements [lb, rb)
    segtree *l = nullptr, *r = nullptr; // pointers to its children

    segtree(int lb, int rb) : lb(lb), rb(rb) {
        if (lb + 1 < rb) { // if the node is not a leaf, create children
            int m = (lb + rb) / 2;
            l = new segtree(lb, m);
            r = new segtree(m, rb);
        }
    }

    void add(int k, int x) { /* react to a[k] += x */ }
    int sum(int k) { /* compute the sum of the first k elements */ }
};
```

如果需要在已有数组上建树，我们会把构造函数改写成这样：

```c++
if (lb + 1 == rb) {
    s = a[lb]; // the node is a leaf -- its sum is just the element a[lb]
} else {
    int t = (lb + rb) / 2;
    l = new segtree(lb, t);
    r = new segtree(t, rb);
    s = l->s + r->s; // we can use the sums of children that we've just calculated
}
```

构建时间对我们没有太大意义，所以为了减轻思维负担，后续所有实现都假定数组是零初始化的。

现在实现 `add`：沿树下坡直到叶子节点，途中把增量加到 `s` 字段上：

```c++
void add(int k, int x) {
    s += x;
    if (l != nullptr) { // check whether it is a leaf node
        if (k < l->rb)
            l->add(k, x);
        else
            r->add(k, x);
    }
}
```

<!--

We can do largely the same with the prefix sum query, adding the sum stored in the left node each time we go right:

-->

要计算一个段上的和，可以检查查询是完全覆盖了当前段、还是与它完全不相交——是的话直接返回这个节点的结果。如果两者都不是，就把查询递归地传给孩子，让它们自己想办法：

```c++
int sum(int lq, int rq) {
    if (rb <= lq && rb <= rq) // if we're fully inside the query, return the sum
        return s;
    if (rq <= lb || lq >= rb) // if we don't intersect with the query, return zero
        return 0;
    return l->sum(lq, rq) + r->sum(lq, rq);
}
```

这个函数总共访问 $O(\log n)$ 个节点，因为它只在一个段与查询部分相交时才产生孩子递归，而这样的段至多 $O(\log n)$ 个。

对*前缀和*来说，这些检查可以简化，因为查询的左边界总是零：

```c++
int sum(int k) {
    if (rb <= k)
        return s;
    if (lb >= k)
        return 0;
    return l->sum(k) + r->sum(k);
}
```

由于我们有两类查询，也就有两张图可看：

![](/en/hpc/data-structures/img/segtree-pointers.svg)

这个面向对象的实现在软件工程实践层面相当不错，但有几个方面让它在性能层面非常糟糕：

- 两个查询实现都用[递归](/hpc/architecture/functions)——尽管 `add` 查询可以被尾调用优化。
- 两个查询实现都用不可预测的[分支](/hpc/pipelining/branching)，让 CPU 流水线停顿。
- 节点存了额外的元数据。这个结构占 $4+4+4+8+8=28$ 字节，出于[内存对齐](/hpc/cpu-cache/alignment)的原因被填充到 32 字节，而真正必要的只有存整数和的 4 字节。
- 最重要的是，我们在做大量的[指针追逐](/hpc/cpu-cache/latency)：必须先取回指向孩子的指针才能下降进去，尽管仅凭查询本身就能提前推断出我们需要的段。

指针追逐比其他所有问题都严重几个数量级——要消除它，就得去掉指针，让结构成为*隐式*的。

### 隐式线段树 {#implicit-segment-trees}

线段树是一种二叉树，所以可以用 [Eytzinger 布局](../binary-search#eytzinger-layout)把节点存进一个大数组，用下标运算代替显式指针来导航。

更正式地，我们把节点 $1$ 定义为树根，持有整个数组 $[0, n)$ 的和。然后，对每个节点 $v$（对应区间 $[l, r]$），我们定义：

- 节点 $2v$ 是它的左孩子，对应区间 $[l, \lfloor \frac{l+r}{2} \rfloor)$；
- 节点 $(2v+1)$ 是它的右孩子，对应区间 $[\lfloor \frac{l+r}{2} \rfloor, r)$。

当 $n$ 是 2 的幂时，这个布局把整棵树装得很整齐：

![隐式线段树的内存布局，同一查询路径被高亮](/en/hpc/data-structures/img/segtree-layout.png)

然而当 $n$ 不是 2 的幂时，布局就不再紧凑：尽管无论如何分割段，我们都恰好有 $(2n - 1)$ 个节点，它们却不再能完美映射到 $[1, 2n)$ 区间。

例如，考虑在规模为 $17 = 2^4 + 1$ 的线段树中下降到最右边的叶子会发生什么：

- 我们从编号 $1$ 的树根开始，它代表区间 $[0, 16]$，
- 我们走到节点 $3 = 2 \times 1 + 1$，代表区间 $[8, 16]$，
- 我们走到节点 $7 = 2 \times 2 + 1$，代表区间 $[12, 16]$，
- 我们走到节点 $15 = 2 \times 7 + 1$，代表区间 $[14, 16]$，
- 我们走到节点 $31 = 2 \times 15 + 1$，代表区间 $[15, 16]$，
- 最后到达节点 $63 = 2 \times 31 + 1$，代表区间 $[16, 16]$。

> **译者注**：原文上面一行写作 "7 = 2 × 2 + 1"，按上下文应为 "7 = 2 × 3 + 1"（节点 7 是节点 3 的右孩子），疑为笔误；译文按原文保留。

所以，由于 $63 > 2 \times 17 - 1 = 33$，布局里存在一些空洞，但树的结构不变，树高仍然是 $O(\log n)$。目前我们可以无视这个问题，直接分配一个更大的数组来存节点——可以证明最右叶子的下标从不超过 $4n$，所以分配那么多单元总是够的：

```c++
int t[4 * N]; // contains the node sums
```

现在实现 `add`：写一个类似的递归函数，但用下标运算代替指针。由于节点里也不再存段的边界，我们需要在每次递归调用时重算它们并作为参数传递：

```c++
void add(int k, int x, int v = 1, int l = 0, int r = N) {
    t[v] += x;
    if (l + 1 < r) {
        int m = (l + r) / 2;
        if (k < m)
            add(k, x, 2 * v, l, m);
        else
            add(k, x, 2 * v + 1, m, r);
    }
}
```

前缀和查询的实现大体相同：

```c++
int sum(int k, int v = 1, int l = 0, int r = N) {
    if (l >= k)
        return 0;
    if (r <= k)
        return t[v];
    int m = (l + r) / 2;
    return sum(k, 2 * v, l, m)
         + sum(k, 2 * v + 1, m, r);
}
```

在递归函数里传递五个变量看起来很笨拙，但性能收益显然值得：

![](/en/hpc/data-structures/img/segtree-topdown.svg)

除了需要的内存少得多（有利于装进 CPU 缓存）之外，这个实现的主要优点是现在可以利用[内存级并行](/hpc/cpu-cache/mlp)，并行取回我们需要的节点，显著改善两种查询的运行时间。

要进一步提升性能，我们可以：

- 手工优化下标运算（例如注意到不管怎样都要把 `v` 乘以 `2`），
- 用显式的二进制移位代替除以二（因为[编译器并不总能自己做到](/hpc/compilation/contracts/#arithmetic)），
- 以及最重要的，摆脱[递归](/hpc/architecture/functions)，把实现完全改成迭代的。

`add` 是尾递归且没有返回值，容易变成单个 `while` 循环：

```c++
void add(int k, int x) {
    int v = 1, l = 0, r = N;
    while (l + 1 < r) {
        t[v] += x;
        v <<= 1;
        int m = (l + r) >> 1;
        if (k < m)
            r = m;
        else
            l = m, v++;
    }
    t[v] += x;
}
```

对 `sum` 查询做同样的事稍难一些，因为它有两个递归调用。关键技巧是注意到：发起这两个调用时，其中之一必然立即终止，因为 `k` 只可能在其中一半里，所以可以在下降之前先检查这个条件：

```c++
int sum(int k) {
    int v = 1, l = 0, r = N, s = 0;
    while (true) {
        int m = (l + r) >> 1;
        v <<= 1;
        if (k >= m) {
            s += t[v++];
            if (k == m)
                break;
            l = m;
        } else {
            r = m;
        }
    }
    return s;
}
```

这对更新查询的性能改善不大（因为它本来是尾递归的，编译器已经做过类似的优化），但前缀和查询在所有问题规模上的运行时间都大致减半：

![](/en/hpc/data-structures/img/segtree-iterative.svg)

这个实现仍有一些问题：我们用了至多两倍于必要的内存，有代价高的[分支](/hpc/pipelining/branching)，还得在每次迭代时维护和重算数组边界。要摆脱这些问题，需要稍微换个思路。

### 自底向上的实现 {#bottom-up-implementation}

让我们改变隐式线段树布局的定义。不再依赖父到子的关系，而是先强行把所有叶子节点编号到 $[n, 2n)$ 区间，然后递归地定义节点 $k$ 的父节点为节点 $\lfloor \frac{k}{2} \rfloor$。

这个结构与之前大体相同：你仍然可以把任何节点编号除以二到达树根（节点 $1$），每个节点仍然至多有两个孩子 $2k$ 和 $(2k + 1)$，因为其他任何数除以二向下取整都会得到不同的父编号。我们得到的优势是强制最后一层连续、从 $n$ 开始，于是可以使用一半大小的数组：

```c++
int t[2 * N];
```

当 $n$ 是 2 的幂时，树的结构与之前完全相同，实现查询时我们可以利用这种自底向上的方式，从第 $k$ 个叶子节点（直接编号为 $N + k$）开始上溯到树根：

```c++
void add(int k, int x) {
    k += N;
    while (k != 0) {
        t[k] += x;
        k >>= 1;
    }
}
```

要计算 $[l, r)$ 子段上的和，可以维护指向首个和末个待累加元素的指针，加入节点时相应地增／减它们，直到两者汇聚到同一节点（即它们的最近公共祖先）后停止：

```c++
int sum(int l, int r) {
    l += N;
    r += N - 1;
    int s = 0;
    while (l <= r) {
        if ( l & 1) s += t[l++]; // l is a right child: add it and move to a cousin
        if (~r & 1) s += t[r--]; // r is a left child: add it and move to a cousin
        l >>= 1, r >>= 1;
    }
    return s;
}
```

出人意料的是，即使 $n$ 不是 2 的幂，这两个查询也都能正确工作。要理解为什么，考虑一棵 13 元素的线段树：

![](/en/hpc/data-structures/img/segtree-permuted.png)

最后一层的第一个下标总是 2 的幂，但当数组规模不是 2 的幂时，叶子元素的一部分前缀被回绕到了树的右侧。神奇的是，这一事实并不妨碍我们的实现：

- `add` 查询仍然会更新它的父节点们，即使其中一些节点对应的是数组的某个前缀加某个后缀，而不是连续的子段。
- `sum` 查询仍然会算出正确子段上的和，即使 `l` 落在那段回绕的前缀上、逻辑上位于 `r` 的"右边"——因为 `l` 终会变成某层的最后一个节点并被递增，突然跳到下一层的第一个元素，之后只需在那段回绕部分加上恰好合适的节点就能正常继续（看图中变暗的节点）。

与自顶向下的方法相比，我们只用一半内存，也不必维护查询区间，代码因此更简单、也相应更快：

![](/en/hpc/data-structures/img/segtree-bottomup.svg)

跑基准测试时，我们用 `sum(l, r)` 过程计算一般子段的和，把 `l` 固定为 `0`。为了在前缀和查询上取得更高性能，我们想避免维护 `l`，只移动右边界：

```c++
int sum(int k) {
    int s = 0;
    k += N - 1;
    while (k != 0) {
        if (~k & 1) // if k is a right child
            s += t[k--];
        k = k >> 1;
    }
    return s;
}
```

相比之下，除非 $n$ 是 2 的幂，这个前缀和实现无法工作[^notpow2]——因为 `k` 可能落在回绕的那部分上，那样我们会把几乎整个数组加起来而不是一个小前缀。

[^notpow2]: **译者注**：原文本句写作 "doesn't work unless *n* is not a power of two"，按字面为"除非 n **不是** 2 的幂"，与上下文（`k` 落在回绕部分导致算错）矛盾，疑为笔误；正确含义应为"除非 n **是** 2 的幂"（即该实现只适用于 n 为 2 的幂的情形）。下一段的重排叶子正是为解除这一限制。

要让它在任意数组规模下工作，可以重排叶子，让它们在树的最后两层里处于从左到右的逻辑顺序。在上面的例子里，这意味着给所有叶子下标加 $3$，然后把最后三个叶子减去 $13$、上移一层。

一般情况下，可以用谓词化在几个周期内完成：

```c++
const int last_layer = 1 << __lg(2 * N - 1);

// calculate the index of the leaf k
int leaf(int k) {
    k += last_layer;
    k -= (k >= 2 * N) * N;
    return k;
}
```

实现查询时，只需调用 `leaf` 函数获得正确的叶子下标：

```c++
void add(int k, int x) {
    k = leaf(k);
    while (k != 0) {
        t[k] += x;
        k >>= 1;
    }
}

int sum(int k) {
    k = leaf(k - 1);
    int s = 0;
    while (k != 0) {
        if (~k & 1)
            s += t[k--];
        k >>= 1;
    }
    return s;
}
```

最后一处点睛：把 `s += t[k--]` 这一行换成[谓词化](/hpc/pipelining/branchless)，就能让实现无分支（除了最后一个分支——循环条件仍然要检查）：

```c++
int sum(int k) {
    k = leaf(k - 1);
    int s = 0;
    while (k != 0) {
        s += (~k & 1) ? t[k] : 0; // will be replaced with a cmov
        k = (k - 1) >> 1;
    }
    return s;
}
```

合起来，这些优化让前缀和查询快了很多：

![](/en/hpc/data-structures/img/segtree-branchless.svg)

注意，前缀和查询延迟的凸起从 $2^{19}$ 开始而不是 L3 缓存边界的 $2^{20}$。这是因为我们仍存储 $2n$ 个整数，而且无论是否会把它加进 `s`，都会取回 `t[k]`。这两个问题其实都能解决。

### 树状数组 {#fenwick-trees}

隐式结构很棒：它们避免了指针追逐、允许并行访问所有相关节点，而且因为不在节点里存元数据而占用更少空间。比隐式结构更好的是*简洁*（succinct）结构：它们只需要存储该结构的信息论最小空间，只用 $O(1)$ 的额外内存。

要让线段树变得简洁，需要审视节点里存储的值、寻找冗余——即可以从其他值推出来的值——并把它们去掉。一个入手点是注意到：在前缀和的每一种实现里，我们从未用过存在右孩子里的和——因此，对前缀和计算而言，这样的节点是冗余的：

<!--

One way to do this is to use the fact that for every node $v$ with children $l$ and $r$, we have $s_v = s_l + s_r$, so we only need to store two of these values, and we can in "triangle" $(l, v, r)$

For any node $p$, its sum $s_p$ equals to the sum $(s_l + s_r)$ stored in its children nodes. Therefore, for any such "triangle" of nodes, we only need to store any two of $s_p$, $s_l$, or $s_r$, and we can restore the other one from the $s_p = s_l + s_r$ identity.

-->

![](/en/hpc/data-structures/img/segtree-succinct.png)

*树状数组*（Fenwick tree），也叫*二叉索引树*（binary indexed tree）——很快你就会明白为什么——就是这样一种线段树：它利用上述考量去掉了所有*右*孩子，实质上移除了每一层里的每第二个节点，使节点总数与底层数组相同。

```c++
int t[N + 1]; // +1 because we use use one-based indexing
```

为了紧凑地存放这些段和，树状数组抛弃了 Eytzinger 布局：在线段树最后一层会成为叶子的每个元素 $k$ 的位置上，它存放的是其第一个未被移除的祖先的和。例如：

- 元素 $7$ 存放 $[0, 7]$ 区间上的和（$282$），
- 元素 $9$ 存放 $[8, 9]$ 区间上的和（$-86$），
- 元素 $10$ 存放 $[10, 10]$ 区间上的和（$-52$，即元素本身）。

对给定的元素 $k$（更准确说是左边界；右边界永远是元素 $k$ 本身），如何比模拟沿树下降更快地算出这个区间？事实证明，当树的规模是 2 的幂且我们从 1 开始编号时，有一个聪明的位技巧——直接去掉下标的最低有效位：

- 元素 $7 + 1 = 8 = 1000_2$ 的左边界是 $0000_2 = 0$，
- 元素 $9 + 1 = 10 = 1010_2$ 的左边界是 $1000_2 = 8$，
- 元素 $10 + 1 = 11 = 1011_2$ 的左边界是 $1010_2 = 10$。

要取一个整数的最后一个置位比特，可以用这个过程：

```c++
int lowbit(int x) {
    return x & -x;
}
```

这个技巧之所以有效，靠的是[补码](/hpc/arithmetic/integer)表示有符号数的方式。计算 `-x` 时，我们实际上是从某个大的 2 的幂中减去它：数的前缀翻转，末尾一段零保持不变，而唯一保持不变的置位比特就是最后那个置位比特——它将是 `x & -x` 中唯一存活的 1。例如：

```
+90 = 64 + 16 + 8 + 2 = (0)10110
-90 = 00000 - 10110   = (1)01010
    → (+90) & (-90)   = (0)00010
```

<!-- More formally, a Fenwick tree is defined as the array $t_i = \sum_{k=f(i)}^i a_k$ where $f$ is some function for which $f(i) \leq i$. If $f$ is the "remove last bit" function (`x -= x & -x`), then both query and update would only require updating $O(\log n)$ different $t$. -->

我们已经明确：树状数组就是一个大小为 `n` 的数组，其中每个元素 `k` 定义为原数组中从 `k - lowbit(k) + 1` 到 `k`（含）的元素之和。现在该实现一些查询了。

前缀和查询的实现很简单。`t[k]` 存着我们需要的和，除了前 `k - lowbit(k)` 个元素的部分，所以可以直接把它加进结果，然后跳到 `k - lowbit(k)`，如此继续直到数组开头：

```c++
int sum(int k) {
    int s = 0;
    for (; k != 0; k -= lowbit(k))
        s += t[k];
    return s;
}
```

<!-- In a segment tree, this is equivalent to starting at the leaf `k` and jumping straight to the first ancestor that is a left child: -->

由于我们不断从 `k` 中去掉最低的置位比特，也由于这个过程等价于访问线段树中同一串左孩子节点，每次 `sum` 查询至多触及 $O(\log n)$ 个节点：

![树状数组中一次前缀和查询的路径](/en/hpc/data-structures/img/fenwick-sum.png)

为了略微提升 `sum` 查询的性能，我们用 `k &= k - 1` 一步去掉最低位，它比 `k -= k & -k` 快一条指令：

```c++
int sum(int k) {
    int s = 0;
    for (; k != 0; k &= k - 1)
        s += t[k];
    return s;
}
```

与之前所有线段树实现不同，树状数组是一种"把子段上的和算成两个前缀和之差"反而更容易、更高效的结构：

```c++
// [l, r)
int sum (int l, int r) {
    return sum(r) - sum(l);
}
```

更新查询更好写，但更不直观。我们需要把值 `x` 加到叶子 `k` 的所有左孩子祖先节点上。这些节点的下标 `m` 大于 `k`，但 `m - lowbit(m) < k`，从而它们的区间包含 `k`。

所有这样的下标都要与 `k` 有共同前缀，然后在 `k` 为 `0` 的位置有一个 `1`，再跟一段零后缀，使得那个 `1` 在 `m - lowbit(m)` 中被抵消、结果小于 `k`。所有这样的下标可以这样迭代地生成：

```c++
void add(int k, int x) {
    for (k += 1; k <= N; k += k & -k)
        t[k] += x;
}
```

反复把最低的置位比特加到 `k` 上会让它"变得更偶"，把它抬升到线段树中下一个左孩子祖先：

![树状数组中一次更新查询的路径](/en/hpc/data-structures/img/fenwick-update.png)

现在，如果代码保持原样，即使 $n$ 不是 2 的幂它也能正确工作。这种情况下，树状数组不再等价于一棵规模为 $n$ 的线段树，而是等价于至多 $O(\log n)$ 棵 2 的幂规模的线段树组成的*森林*——如果你愿意这么想的话，也可以说是一棵用零填充到较大 2 的幂的单棵线段树。无论哪种看法，所有过程都仍然正确，因为它们从不触及 $[1, n]$ 范围之外的任何东西。

<!-- Sometimes people use `k -= k & -k` to iterate when processing the `sum` query, which makes this implementation delightfully symmetric. -->

树状数组的性能在更新查询上与优化后的自底向上线段树相近，在前缀和查询上略快：

![](/en/hpc/data-structures/img/segtree-fenwick.svg)

图上有个奇怪的地方。跨过 L3 缓存边界后，性能迅速起飞。这是一个[缓存相联度](/hpc/cpu-cache/associativity)效应：最常使用的单元的下标都能被较大的 2 的幂整除，于是它们被混叠到同一个缓存组里互相挤出去，实际上缩小了缓存容量。

消除这个效应的一个办法是在布局里插入"空洞"：

```c++
inline constexpr int hole(int k) {
    return k + (k >> 10);
}

int t[hole(N) + 1];

void add(int k, int x) {
    for (k += 1; k <= N; k += k & -k)
        t[hole(k)] += x;
}

int sum(int k) {
    int res = 0;
    for (; k != 0; k &= k - 1)
        res += t[hole(k)];
    return res;
}
```

计算 `hole` 函数不在迭代之间的关键路径上，所以它不引入任何显著开销，却完全消除了缓存相联度问题，在大数组上把延迟最多缩小 3 倍：

![](/en/hpc/data-structures/img/segtree-fenwick-holes.svg)

树状数组很快，但仍有一些小问题。与[二分查找](../binary-search)类似，它们内存访问的时间局部性不算好，因为访问稀少的元素与访问最频繁的元素分组在一起。树状数组还执行非常数次迭代、必须做循环结束检查，很可能造成一次分支预测失败——虽然只有一次。

大概还有可优化的地方，但我们到此为止，转向一个完全不同的方法——如果你了解 [S-tree](../s-tree)，多半已经猜到方向了。

### 宽线段树 {#wide-segment-trees}

主要思想是：既然内存系统反正要为我们取回完整的[缓存行](/hpc/cpu-cache/cache-lines)，那就让它装载尽可能多的、能帮我们更快处理查询的信息。对线段树来说，这意味着一个节点里存不止一个数据点。这样能降低树高，下降或上溯时执行的迭代次数更少：

![](/en/hpc/data-structures/img/segtree-wide.png)

我们把这种改动称为*宽（B 叉）线段树*（wide (B-ary) segment tree）。

要实现这个布局，可以沿用 [S+ 树](../s-tree#implicit-b-tree-1)中类似的基于 [constexpr](/hpc/compilation/precalc) 的方法：

```c++
const int b = 4, B = (1 << b); // cache line size (in integers, not bytes)

// the height of the tree over an n-element array 
constexpr int height(int n) {
    return (n <= B ? 1 : height(n / B) + 1);
}

// where the h-th layer starts
constexpr int offset(int h) {
    int s = 0, n = N;
    while (h--) {
        n = (n + B - 1) / B;
        s += n * B;
    }
    return s;
}

constexpr int H = height(N);
alignas(64) int t[offset(H)]; // an array for storing nodes
```

这样，我们把树高有效降低了约 $\frac{\log_B n}{\log_2 n} = \log_2 B$ 倍（$\sim4$ 倍，若 $B = 16$），但在节点内高效地执行操作变得不再平凡。对我们要解的问题，有两个主要选项：

1. 在每个节点存 $B$ 个*和*（对应它的 $B$ 个孩子各一个）。
2. 在每个节点存 $B$ 个*前缀和*（第 $i$ 个是前 $(i + 1)$ 个孩子的和）。

如果选第一个方案，`add` 查询与自底向上线段树大体相同，但 `sum` 查询每访问一个节点要加起至多 $B$ 个标量。如果选第二个方案，`sum` 查询变得平凡，但 `add` 查询每访问一个节点要给某个后缀加 `x`。

无论哪种，一个操作做 $O(\log_B n)$ 次运算、每节点只碰一个标量，另一个操作做 $O(B \cdot \log_B n)$ 次运算、每节点要碰至多 $B$ 个标量。不过我们可以用 [SIMD](/hpc/simd) 加速较慢的那个操作，而且由于 SIMD 指令集里没有快的[水平归约](/hpc/simd/reduction)，向量加向量却很容易，所以选第二个方案、在每个节点存前缀和。

这让 `sum` 查询变得极快、也极易实现：

```c++
int sum(int k) {
    int s = 0;
    for (int h = 0; h < H; h++)
        s += t[offset(h) + (k >> (h * b))];
    return s;
}
```

`add` 查询更复杂、也更慢。我们只需给节点的一个后缀加数，做法是把不该修改的位置[掩码掉](/hpc/simd/masking)。

我们可以预计算一个 $B \times B$ 数组，对应 $B$ 个掩码：对节点内 $B$ 个位置中的每一个，指明某个前缀和值是否需要更新：

```c++
struct Precalc {
    alignas(64) int mask[B][B];

    constexpr Precalc() : mask{} {
        for (int k = 0; k < B; k++)
            for (int i = 0; i < B; i++)
                mask[k][i] = (i > k ? -1 : 0);
    }
};

constexpr Precalc T;
```

除了这个掩码技巧，其余的计算简单到只用 [GCC 向量类型](/hpc/simd/intrinsics#gcc-vector-extensions)就能应付。处理 `add` 查询时，只需用这些掩码与广播的 `x` 值按位与，把它掩码化，再加到节点存储的值上：

```c++
typedef int vec __attribute__ (( vector_size(32) ));

constexpr int round(int k) {
    return k & ~(B - 1); // = k / B * B
}

void add(int k, int x) {
    vec v = x + vec{};
    for (int h = 0; h < H; h++) {
        auto a = (vec*) &t[offset(h) + round(k)];
        auto m = (vec*) T.mask[k % B];
        for (int i = 0; i < B / 8; i++)
            a[i] += v & m[i];
        k >>= b;
    }
}
```

与树状数组相比，这让 `sum` 查询快了 10 倍以上，`add` 查询最多快 4 倍：

![](/en/hpc/data-structures/img/segtree-simd.svg)

与 [S-tree](../s-tree) 不同，这个实现的块大小可以轻松更改（真的就是改一个字符）。不出所料，增大块大小时，更新时间也增加——我们要取回并处理更多缓存行——而 `sum` 查询时间下降，因为树高变小了：

![](/en/hpc/data-structures/img/segtree-simd-others.svg)

与 [S+ 树](../s-tree/#modifications-and-further-optimizations)类似，最优的内存布局可能有非均匀的块大小，取决于问题规模和查询分布，但我们不打算探索这个想法，优化就到这里。

<!-- Wide Fenwick trees make little sense. The speed of Fenwick trees comes from rapidly iterating over just the elements we need. -->

### 性能对比 {#comparisons}

与其他流行的线段树实现相比，宽线段树明显更快：

![](/en/hpc/data-structures/img/segtree-popular.svg)

相对加速达到了数量级的差距：

![](/en/hpc/data-structures/img/segtree-popular-relative.svg)

与最初的基于指针的实现相比，宽线段树在前缀和和更新查询上分别最快可达 200 倍和 40 倍——不过当数组足够大时，两种实现都变成纯访存受限，加速分别回落到 60 倍和 15 倍左右。

### 扩展与变体 {#modifications}

我们只聚焦了 32 位整数的前缀和问题——为了让这篇已经很长的文章稍短一点，也为了让与树状数组的对比公平——但宽线段树可以用于其他常见的区间操作，尽管用 SIMD 高效实现它们需要一些创造力。

*免责声明*：以下想法我一个都没实现过，所以其中一些可能有致命缺陷。

**其他数据类型**可以平凡地支持：改一下向量类型，如果大小不同，再改节点大小 $B$——这也会改变树高，进而改变两种查询的迭代总次数。

也可能更新和前缀和查询有不同的取值限制。例如，只有"$\pm 1$"的更新查询、并保证前缀和查询结果总能装进 32 位整数的情况并不少见。如果结果能装进 8 比特，我们直接用 8 位 `char`、块大小 $B=64$ 字节，让树高缩小 $\frac{\log_{16} n}{\log_{64} n} = \log_{16} 64 = 1.5$ 倍，两种查询成比例地变快。

遗憾的是一般情况下行不通，但当更新增量较小时我们仍有提速办法：可以*缓冲*更新查询。还是用"$\pm 1$"的例子，我们可以如愿让分支因子 $B=64$，每个节点存 $B$ 个 32 位整数、$B$ 个 8 位有符号字符，以及一个从 $127$ 开始、每次更新节点时递减的 8 位计数器。然后处理节点上的查询时：

- 对更新查询，把掩码化后的 8 位加减一向量加到 `char` 数组上，递减计数器；若它为零，就把 `char` 数组里的值[转换](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=3037,3009,4870,6715,4845,3853,288,6570,90,7307,5993,2692,6946,6949,5456,6938,5456,1021,3007,514,518,7253,7183,3892,5135,5260,3915,4027,3873,7401,4376,4229,151,2324,2310,2324,591,4075,3011,3009,6130,4875,6385,5259,6385,6250,1395,7253,6452,7492,4669,4669,7253,1039,1029,4669,4707,7253,7242,848,879,848,7251,4275,879,874,849,833,6046,7250,4870,4872,4875,849,849,5144,4875,4787,4787,4787,3016,3018,5227,7359,7335,7392,4787,5259,5230,5230,5223,5214,6438,5229,488,483,6527,6527,6554,1829,1829,1829&techs=AVX,AVX2&text=cvtepi8_)成 32 位整数、加进整数数组、把 `char` 数组清零、并把计数器重置回 127。
- 对前缀和查询，访问相同的节点，但把 `int` 和 `char` 的值*都*加进结果。

这个更新累积技巧能带来最高 1.5 倍的性能提升，代价是多用约 25% 的内存。

在 `add` 查询里放一个条件分支、并把 `char` 数组加进 `int` 数组是相当慢的，但因为我们每 127 次迭代才需要做一次，摊还意义上它不花我们什么。`sum` 查询的处理时间会增加，但不显著——因为它主要取决于最慢的读取而非迭代次数。

**一般区间查询**可以像树状数组那样支持：把区间 $[l, r)$ 分解为两个前缀和 $[0, r)$ 与 $[0, l)$ 之差。

这对加法以外的一些操作也适用（模素数乘法、异或等），但它们必须是*可逆的*：得有一种办法能从最终结果里快速"抵消"左侧前缀上的操作。

**不可逆操作**也可以支持，尽管它们仍需满足一些其他性质：

- 必须是*可结合的*（associative）：$(a \circ b) \circ c = a \circ (b \circ c)$。
- 必须有*单位元*（identity）：$a \circ e = e \circ a = a$。

（如果你是个学院派，这样的代数结构叫[幺半群](https://en.wikipedia.org/wiki/Monoid)。）

遗憾的是，操作不可逆时前缀和技巧就不奏效了，我们只能换回[方案一](#wide-segment-trees)，为每个段单独存这些操作的结果。这需要对查询做相当大的改动：

- 更新查询应该替换叶子上的一个标量，在叶子节点做一次[水平归约](/hpc/simd/reduction/#horizontal-summation)，然后继续向上，替换父节点的一个标量，如此继续。
- 区间归约查询应该分别对左右边界计算一个在各自路径上垂直归约所得值的向量，把这两个向量合并成一个，再水平归约返回最终答案。注意我们仍需要用掩码把查询区间之外的值替换成中性元，而且这次可能需要一些条件传送/混合，外加 $B \times B$ 的预计算掩码，或用两个掩码分别照顾查询的左右边界。

这让两种查询都慢了很多——尤其是归约——但仍应比自底向上线段树快。

**最小值**是个不错的例外：当元素的新值小于当前值时，更新查询可以更快一些——我们可以跳过水平归约，直接用标量过程更新 $\log_B n$ 个节点。

当这类更新占主导时这非常快，例如边多于顶点的稀疏图 Dijkstra 算法。对这个问题，宽线段树可以充当一个高效的固定全域最小堆。

**惰性传播**（lazy propagation）可以通过在节点里另存一个数组来存放延迟操作来实现。传播更新时需要自顶向下（把 `for` 循环方向反过来、用 `k >> (h * b)` 计算第 `h` 代祖先即可），[广播](/hpc/simd/moving/#broadcast)并重置当前节点父节点中存放的延迟操作值，再用 SIMD 把它施加到当前节点存储的所有值上。

一个小问题是某些操作需要知道段的长度：例如同时支持求和与批量赋值时。解决办法有：填充元素使每层各段大小一致、预计算段长存进节点，或者用谓词化检查问题节点（每层至多一个）。

<!--

**Persistent** trees

We mostly focused on the prefix sum problem, but this general structure can be used for other problems handled by segment trees:

- General sums and other reductions.
- Range minimum sum queries.
- Fixed-universe heaps.

Some more exotic applications, reliant on there being pointers, are expectedly harder. To implement dynamic trees, we could store the mapping between the node number and the tree in a hash table. For more complicated cases, such as whether wide segment trees can help in implementing persistent trees is an open question.

why b-ary Fenwick tree is not a good idea

-->

### 致谢 {#acknowledgements}

非常感谢 Giulio Ermanno Pibiri 参与这个案例研究的合作，它主要基于他与 Rossano Venturini 合著的 2020 年论文 "[Practical Trade-Offs for the Prefix-Sum Problem](https://arxiv.org/pdf/2006.14552.pdf)"。如果你对我们为求简洁而略过的细节感兴趣，强烈建议阅读原文。

<!-- It has some more detailed discussions, as well as some other implementations or branchless top-down segment tree and why b-ary Fenwick tree is not a good idea. Intermediate structures we've skipped here. -->

自底向上线段树的代码和一些想法改编自 Oleksandr Bacherikov 2015 年的博文 "[Efficient and easy segment trees](https://codeforces.com/blog/entry/18051)"。

