---
title: 静态 B 树
weight: 2
draft: true
---

本节是[上一节](../binary-search)的后续，在那里我们通过去除分支和改进内存布局优化了二分查找。这里我们同样在有序数组中查找，但这次不再局限于每次只取回和比较一个元素。

在本节中，我们把为二分查找开发的技术推广到*静态 B 树*（static B-tree），并用 [SIMD 指令](/hpc/simd)进一步加速。特别地，我们开发了两个新的隐式数据结构：

- [第一个](#b-tree-layout)基于 B 树的内存布局，依数组规模不同，它比 `std::lower_bound` 最快可达 8 倍，而占用的空间与原数组相同，只需要对元素做一次重排。
- [第二个](#b-tree-layout-1)基于 B+ 树的内存布局，比 `std::lower_bound` 最快可达 15 倍，而只多用 6-7% 的内存——如果我们能保留原来的有序数组，那就是 6-7% **的**内存。

为了与 B 树——那种带指针、每节点几百到几千个键、内部还有空洞的结构——区分开，我们把这两种特定的内存布局分别称为 *S 树*（S-tree）和 *S+ 树*（S+ tree）[^name]。

[^name]: [与 B 树类似](https://en.wikipedia.org/wiki/B-tree#Origin)，"关于 S-tree 里的 S 是什么意思，你想得越多，对 S-tree 的理解就越透彻。"

<!--

Similar to how the B in B-trees stands for many thing in We even have more claim to it than Bayer had on B-tree: it is succinct, static, simd, my name, my surname.

- *S-tree*: an approach based on the implicit (pointer-free) B-layout accelerated with SIMD operations to perform search efficiently while using less memory bandwidth and is ~8x faster on small arrays and 5x faster on large arrays.
- *S+ tree*: an approach similarly based on the B+ layout and achieves up to 15x faster for small arrays and ~7x faster on large arrays. Uses 6-7% of the array memory.

There is a an obscure data structure in computer vision.

The last two approaches use SIMD, which technically disqualifies it from being binary search. This is technically not a drop-in replacement, since it requires some preprocessing, but I can't recall a lot of scenarios where you obtain a sorted array but can't spend linear time on preprocessing.

-->

据我所知，这是对现有[方法](http://kaldewey.com/pubs/FAST__SIGMOD10.pdf)的显著改进。和之前一样，我们使用 Clang 10、面向 Zen 2 CPU，但这些性能提升应该能近似地迁移到大多数其他平台，包括 Arm 架构的芯片。如果你想在你的机器上测试，可以使用最终实现的[这个单文件基准程序](https://github.com/sslotin/amh-code/blob/main/binsearch/standalone.cc)。

这是一篇长文，由于它同时也是一个[教科书](/hpc/)式的案例研究，我们会出于教学目的渐进地改进算法。如果你已经是专家，习惯在几乎没有上下文的情况下阅读[内建函数](/hpc/simd/intrinsics)密集的代码，可以直接跳到[最终实现](#implicit-b-tree-1)。

## B 树布局 {#b-tree-layout}

B 树推广了二叉搜索树的概念，允许节点拥有多于两个的孩子。一个 $k$ 阶 B 树的节点不再只存一个键，而是可以容纳至多 $B = (k - 1)$ 个按键排序的键，以及至多 $k$ 个指向孩子节点的指针。第 $i$ 个孩子满足这样的性质：它子树中的所有键都位于父节点第 $(i - 1)$ 个键和第 $i$ 个键之间（如果这两个键存在）。

![一棵 4 阶 B 树](/en/hpc/data-structures/img/b-tree.jpg)

这种方法的主要优点是把树高降低 $\frac{\log_2 n}{\log_k n} = \frac{\log k}{\log 2} = \log_2 k$ 倍，而取回每个节点仍然只需大致相同的时间——只要它能塞进单个[内存块](/hpc/external-memory/hierarchy/)。

B 树最初主要是为管理磁盘数据库而设计的，在磁盘上随机取回一个字节的延迟与顺序读取下 1MB 数据的时间是可比的。对我们的用例，我们将使用 $B = 16$ 个元素——即 $64$ 字节，一个缓存行的大小——作为块大小，这使得树高和每次查询的总缓存行取回次数都比二分查找小 $\log_2 17 \approx 4$ 倍。

### 隐式 B 树 {#implicit-b-tree}

在 B 树节点里存储和取回指针会浪费宝贵的缓存空间、降低性能，但在插入和删除时改变树的结构又离不开它们。而当没有更新、树的结构是*静态*的时候，我们就可以去掉指针，使结构成为*隐式*的。

实现这一点的方法之一，是把 [Eytzinger 编号](../binary-search#eytzinger-layout)推广到 $(B + 1)$ 叉树：

- 根节点编号为 $0$。
- 节点 $k$ 有 $(B + 1)$ 个孩子节点，编号为 $\\{k \cdot (B + 1) + i + 1\\}$，$i \in [0, B]$。

这样，只需分配一个大二维键数组、靠下标运算来定位树中的孩子节点，我们就能只用 $O(1)$ 的额外内存：

```c++
const int B = 16;

int nblocks = (n + B - 1) / B;
int btree[nblocks][B];

int go(int k, int i) { return k * (B + 1) + i + 1; }
```

<!-- todo: exact height -->

这种编号自动使 B 树成为完全树或近似完全树，高度为 $\Theta(\log_{B + 1} n)$。如果初始数组长度不是 $B$ 的倍数，最后一个块会用该数据类型的最大值填充。

### 构建 {#construction}

我们可以用构建 Eytzinger 数组的相同方式来构建 B 树——遍历搜索树：

```c++
void build(int k = 0) {
    static int t = 0;
    if (k < nblocks) {
        for (int i = 0; i < B; i++) {
            build(go(k, i));
            btree[k][i] = (t < n ? a[t++] : INT_MAX);
        }
        build(go(k, B));
    }
}
```

它是正确的，因为初始数组的每个值都会被复制到结果数组中唯一的位置；树高是 $\Theta(\log_{B+1} n)$，因为每下降到一个孩子节点，$k$ 就乘以 $(B + 1)$。

注意，这种编号会造成轻微的不平衡：越靠左的孩子子树可能越大，不过这只对 $O(\log_{B+1} n)$ 个父节点成立。

### 查找 {#searches}

要找下界，我们需要取回节点里的 $B$ 个键，找出第一个键 $a_i$（不小于 $x$），下降到第 $i$ 个孩子——如此继续直到到达叶子节点。如何找出那个键有一定的自由度。例如，我们可以做一个只需 $O(\log B)$ 次迭代的微型内部二分查找，或者干脆按顺序逐个比较、$O(B)$ 时间内找到局部下界，期待循环能提早一点点退出。

但我们不打算这么做——因为我们有 [SIMD](/hpc/simd)。它与分支配合得不好，所以我们本质上要做的是：无论如何都与全部 $B$ 个元素比较，由这些比较结果算出一个位掩码，然后用 `ffs` 指令找到对应第一个不小于元素的比特：

```cpp
int mask = (1 << B);

for (int i = 0; i < B; i++)
    mask |= (btree[k][i] >= x) << i;

int i = __builtin_ffs(mask) - 1;
// now i is the number of the correct child node
```

遗憾的是，编译器还不够聪明，尚不能[自动向量化](/hpc/simd/auto-vectorization/)这段代码，所以我们得手工优化。在 AVX2 中，我们可以一次载入 8 个元素，将它们与查找键比较、产生一个[向量掩码](/hpc/simd/masking/)，再用 `movemask` 把标量掩码提取出来。下面是一个我们想做的事情的最小示意示例：

```center
       y = 4        17       65       103     
       x = 42       42       42       42      
   y ≥ x = 00000000 00000000 11111111 11111111
           ├┬┬┬─────┴────────┴────────┘       
movemask = 0011                               
           ┌─┘                                
     ffs = 3                                  
```

由于我们一次只能处理 8 个元素（块大小／缓存行大小的一半），必须把元素分成两组，再把两个 8 位掩码合并起来。为此，把条件换成 `x > y`、改算反过来的掩码会稍微容易一些：

```c++
typedef __m256i reg;

int cmp(reg x_vec, int* y_ptr) {
    reg y_vec = _mm256_load_si256((reg*) y_ptr); // load 8 sorted elements
    reg mask = _mm256_cmpgt_epi32(x_vec, y_vec); // compare against the key
    return _mm256_movemask_ps((__m256) mask);    // extract the 8-bit mask
}
```

现在，要处理整个块，我们需要调用它两次并合并掩码：

```c++
int mask = ~(
    cmp(x, &btree[k][0]) +
    (cmp(x, &btree[k][8]) << 8)
);
```

要沿树下降，我们对那个掩码用 `ffs` 得到正确的孩子编号，然后调用之前定义的 `go` 函数：

```c++
int i = __builtin_ffs(mask) - 1;
k = go(k, i);
```

最后要真正返回结果时，我们本想直接取回访问的最后一个节点里的 `btree[k][i]`，但问题是有时局部下界并不存在（$i \ge B$），因为 $x$ 恰好比节点里所有的键都大。理论上，我们可以像 [Eytzinger 二分查找](../binary-search/#search-implementation)那样，在算出最后下标*之后*还原正确的元素，但这次我们没有漂亮的位技巧可用，得做大量的[除以 17](/hpc/arithmetic/division) 的运算才能算出来，那会很慢，而且几乎肯定不值。

作为替代，我们可以记住下降过程中遇到的最后一个局部下界并返回它：

```c++
int lower_bound(int _x) {
    int k = 0, res = INT_MAX;
    reg x = _mm256_set1_epi32(_x);
    while (k < nblocks) {
        int mask = ~(
            cmp(x, &btree[k][0]) +
            (cmp(x, &btree[k][8]) << 8)
        );
        int i = __builtin_ffs(mask) - 1;
        if (i < B)
            res = btree[k][i];
        k = go(k, i);
    }
    return res;
}
```

这个实现的性能超过了之前所有的二分查找实现，而且幅度巨大：

![](/en/hpc/data-structures/img/search-btree.svg)

这已经非常好了——但我们还能进一步优化。

### 优化 {#optimization}

在其他一切之前，先让我们在[大页](/hpc/cpu-cache/paging)上为数组分配内存：

```c++
const int P = 1 << 21;                        // page size in bytes (2MB)
const int T = (64 * nblocks + P - 1) / P * P; // can only allocate whole number of pages
btree = (int(*)[16]) std::aligned_alloc(P, T);
madvise(btree, T, MADV_HUGEPAGE);
```

这稍稍改善了较大数组规模下的性能：

![](/en/hpc/data-structures/img/search-btree-hugepages.svg)

理想情况下，我们还需要为[之前所有的实现](../binary-search)都启用大页来保证比较公平，但这没那么重要，因为它们都有某种形式的预取来缓解这个问题。

安顿好这些，我们开始真正的优化。首先，我们要尽可能用编译期常量代替变量，因为这让编译器把它们嵌进机器码、展开循环、优化算术，免费替我们做各种好事。具体来说，我们想提前知道树高：

<!-- todo: maybe this can be computed simpler? -->

```c++
constexpr int height(int n) {
    // grow the tree until its size exceeds n elements
    int s = 0, // total size so far
        l = B, // size of the next layer
        h = 0; // height so far
    while (s + l - B < n) {
        s += l;
        l *= (B + 1);
        h++;
    }
    return h;
}

const int H = height(N);
```

<!--

```c++
constexpr std::pair<int, int> precalc(int n) {
    int s = 0, // total size
        l = B, // size of next layer
        h = 0; // height so far
    while (s + l - B < n) {
        s += l;
        l *= (B + 1);
        h++;
    }
    int r = (n - s + B - 1) / B; // remaining blocks on the last layer
    return {h, s / B + (r + B) / (B + 1) * (B + 1)};
}

const int [height, nblocks] = precalc(N);
```

-->

接下来，我们可以更快地在节点内找到局部下界。与其分别为两个 8 元素块各算一遍、再合并两个 8 位掩码，我们改用 [packs](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=3037,4870,6715,4845,3853,90,7307,5993,2692,6946,6949,5456,6938,5456,1021,3007,514,518,7253,7183,3892,5135,5260,3915,4027,3873,7401,4376,4229,151,2324,2310,2324,4075,6130,4875,6385,5259,6385,6250,1395,7253,6452,7492,4669,4669,7253,1039,1029,4669,4707,7253,7242,848,879,848,7251,4275,879,874,849,833,6046,7250,4870,4872,4875,849,849,5144,4875,4787,4787,4787,5227,7359,7335,7392,4787,5259,5230,5223,6438,488,483,6165,6570,6554,289,6792,6554,5230,6385,5260,5259,289,288,3037,3009,590,604,5230,5259,6554,6554,5259,6547,6554,3841,5214,5229,5260,5259,7335,5259,519,1029,515,3009,3009,3011,515,6527,652,6527,6554,288,3841,5230,5259,5230,5259,305,5259,591,633,633,5259,5230,5259,5259,3017,3018,3037,3018,3017,3016,3013,5144&text=_mm256_packs_epi32&techs=AVX,AVX2) 指令合并向量掩码，然后用 `movemask` 一次提取：

```c++
unsigned rank(reg x, int* y) {
    reg a = _mm256_load_si256((reg*) y);
    reg b = _mm256_load_si256((reg*) (y + 8));

    reg ca = _mm256_cmpgt_epi32(a, x);
    reg cb = _mm256_cmpgt_epi32(b, x);

    reg c = _mm256_packs_epi32(ca, cb);
    int mask = _mm256_movemask_epi8(c);

    // we need to divide the result by two because we call movemask_epi8 on 16-bit masks:
    return __tzcnt_u32(mask) >> 1;
}
```

这条指令把两个寄存器里存的 32 位整数转换为存进一个寄存器的 16 位整数——在我们的场景里，实际上就是把两个向量掩码接成一个。注意我们交换了比较的方向——这让我们最后不必再把掩码取反，但代价是一开始就要把查找键减去一[^float]才能保证正确（否则它算的是 `upper_bound`）。

[^float]: 如果你需要处理[浮点](/hpc/arithmetic/float)键，考虑一下 `upper_bound` 是否够用——因为如果你明确需要 `lower_bound`，那么把查找键减去一或机器精度都不行：你需要[取到前一个可表示的数](https://stackoverflow.com/questions/10160079/how-to-find-nearest-next-previous-double-value-numeric-limitsepsilon-for-give)。除了一些角落情况，这基本上意味着把它的比特重新解释为整数、减去一、再重新解释回浮点数（由于 [IEEE-754 浮点数](/hpc/arithmetic/ieee-754)在内存中的存储方式，这会魔法般地正确工作）。

问题是，这条指令会做一种奇怪的交错：结果按 `a1 b1 a2 b2` 的顺序写入，而不是我们想要的 `a1 a2 b1 b2`——很多 AVX2 指令都有这种毛病。要纠正它，需要对得到的向量做一次[置换](/hpc/simd/shuffling)，但与其在查询时做，不如在预处理时就把每个节点重排好：

```c++
void permute(int *node) {
    const reg perm = _mm256_setr_epi32(4, 5, 6, 7, 0, 1, 2, 3);
    reg* middle = (reg*) (node + 4);
    reg x = _mm256_loadu_si256(middle);
    x = _mm256_permutevar8x32_epi32(x, perm);
    _mm256_storeu_si256(middle, x);
}
```

现在只需在构建完节点后立刻调用 `permute(&btree[k])`。交换中间元素大概还有更快的办法，但我们就到此为止，预处理时间目前不重要。

这个新的 SIMD 例程明显更快，因为多出来的那条 `movemask` 很慢，而且合并两个掩码也要花不少指令。遗憾的是，元素被重排之后，我们就不能再直接做 `res = btree[k][i]` 的更新了。可以用一些位层面的技巧以 `i` 为参数解决这个问题，但查一个小的查找表更快，而且不需要新的分支：

```c++
const int translate[17] = {
    0, 1, 2, 3,
    8, 9, 10, 11,
    4, 5, 6, 7,
    12, 13, 14, 15,
    0
};

void update(int &res, int* node, unsigned i) {
    int val = node[translate[i]];
    res = (i < B ? val : res);
}
```

这个 `update` 过程要花一些时间，但它不在迭代之间的关键路径上，所以对实际性能影响不大。

把它们拼起来（并略去其他一些小优化）：

```c++
int lower_bound(int _x) {
    int k = 0, res = INT_MAX;
    reg x = _mm256_set1_epi32(_x - 1);
    for (int h = 0; h < H - 1; h++) {
        unsigned i = rank(x, &btree[k]);
        update(res, &btree[k], i);
        k = go(k, i);
    }
    // the last branch:
    if (k < nblocks) {
        unsigned i = rank(x, btree[k]);
        update(res, &btree[k], i);
    }
    return res;
}
```

所有这些工作为我们省下了 15-20% 左右：

![](/en/hpc/data-structures/img/search-btree-optimized.svg)

到目前为止还不算令人满足，但这些优化思路我们后面还会复用。

当前实现有两个主要问题：

- `update` 过程代价不小，尤其考虑到它很可能毫无用处：17 次里有 16 次，我们本可以直接从最后一个块取回结果。
- 我们执行的迭代次数非常数，造成与 [Eytzinger 二分查找](../binary-search/#removing-the-last-branch)类似的分支预测问题；这次你也能在图上看到，只是延迟颠簸的周期变成了 $2^4$。

要解决这些问题，我们需要把布局稍作改动。

## B+ 树布局 {#b-tree-layout-1}

大多数时候，人们说 B 树时其实指的是 *B+ 树*，它是 B 树的一个变体，区分两种节点：

- *内部节点*（internal node）存储至多 $B$ 个键和 $(B + 1)$ 个指向孩子节点的指针。第 $i$ 个键总是等于第 $(i + 1)$ 个孩子的子树中最小的键。
- *数据节点*（data node）或*叶子*（leaf）存储至多 $B$ 个键、指向下一个叶子的指针，以及（可选的）每个键关联的值——如果这个结构被当作键值映射使用的话。

这种做法的优点包括更快的查找时间（内部节点只存键）以及快速遍历一段连续条目的能力（沿着下一个叶子的指针走），但代价是一些内存开销：我们必须在内部节点里存键的副本。

![一棵 4 阶 B+ 树](/en/hpc/data-structures/img/bplus.png)

回到我们的用例，这种布局能帮我们解决上述两个问题：

- 我们最后下降进入的节点要么本身就有局部下界，要么局部下界就是下一个叶子的第一个键，所以不必在每次迭代都调用 `update`。
- 所有叶子的深度是相同的，因为 B+ 树是从根部向下生长而不是从叶子向上生长，这就免去了分支。 <!-- todo: elaborate on that -->

缺点是这个布局不是*简洁*（succinct）的：我们需要一些额外的内存来存内部节点——准确说是原数组规模的约 $\frac{1}{16}$——但性能提升远超这笔开销。

### 隐式 B+ 树 {#implicit-b-tree-1}

为了让指针运算更明确，我们将把整棵树存进一个一维数组。为了减少运行时的下标计算，我们把各层依次连续存放在这个数组里，用编译期算好的偏移量来寻址：第 `h` 层节点编号 `k` 的键从 `btree[offset(h) + k * B]` 开始，它的第 `i` 个孩子在 `btree[offset(h - 1) + (k * (B + 1) + i) * B]`。

要实现这一切，我们需要再多几个 `constexpr` 函数：

```c++
// number of B-element blocks in a layer with n keys
constexpr int blocks(int n) {
    return (n + B - 1) / B;
}

// number of keys on the layer previous to one with n keys
constexpr int prev_keys(int n) {
    return (blocks(n) + B) / (B + 1) * B;
}

// height of a balanced n-key B+ tree
constexpr int height(int n) {
    return (n <= B ? 1 : height(prev_keys(n)) + 1);
}

// where the layer h starts (layer 0 is the largest)
constexpr int offset(int h) {
    int k = 0, n = N;
    while (h--) {
        k += blocks(n) * B;
        n = prev_keys(n);
    }
    return k;
}

const int H = height(N);
const int S = offset(H); // the tree size is the offset of the (non-existent) layer H

int *btree; // the tree itself is stored in a single hugepage-aligned array of size S
```

注意，我们以逆序存放各层，但层内的节点以及节点内的数据仍然是从左到右的，而且层是自底向上编号的：叶子构成第 0 层，树根是第 `H - 1` 层。这些只是随意的决定——只是这样在代码里实现起来稍微容易一点。

### 构建 {#construction-1}

要从有序数组 `a` 构建这棵树，首先把它复制进第 0 层并用无穷大填充：

```c++
memcpy(btree, a, 4 * N);

for (int i = N; i < S; i++)
    btree[i] = INT_MAX;
```

现在逐层构建内部节点。对每个键，我们需要先下降到它的右边，然后一路向左直到叶子节点，再取它的第一个键——它就是子树里最小的键：

```c++
for (int h = 1; h < H; h++) {
    for (int i = 0; i < offset(h + 1) - offset(h); i++) {
        // i = k * B + j
        int k = i / B,
            j = i - k * B;
        k = k * (B + 1) + j + 1; // compare to the right of the key
        // and then always to the left
        for (int l = 0; l < h - 1; l++)
            k *= (B + 1);
        // pad the rest with infinities if the key doesn't exist 
        btree[offset(h) + i] = (k * B < N ? btree[k * B] : INT_MAX);
    }
}
```

最后一点收尾——我们需要重排内部节点里的键，以便更快地搜索它们：

```c++
for (int i = offset(1); i < S; i += B)
    permute(btree + i);
```

我们从 `offset(1)` 开始，特意不重排叶子节点，让数组保持原始的有序顺序。动机是：如果叶子里的键也被重排了，我们就得做 `update` 里那种复杂的下标翻译，而这在最后一步操作时恰好在关键路径上。所以仅仅这一层，我们换回原来的掩码合并式局部下界例程。

### 搜索 {#searching}

搜索过程比 B 树布局更简单了：我们不需要 `update`，只需执行固定次数的迭代——虽然最后一次需要特殊处理：

```c++
int lower_bound(int _x) {
    unsigned k = 0; // we assume k already multiplied by B to optimize pointer arithmetic
    reg x = _mm256_set1_epi32(_x - 1);
    for (int h = H - 1; h > 0; h--) {
        unsigned i = permuted_rank(x, btree + offset(h) + k);
        k = k * (B + 1) + i * B;
    }
    unsigned i = direct_rank(x, btree + k);
    return btree[k + i];
}
```

换到 B+ 布局的收益远超成本：S+ 树比优化后的 S-tree 快 1.5-3 倍：

![](/en/hpc/data-structures/img/search-bplus.svg)

图表高端处的尖峰是因为 L1 TLB 不够大：它有 64 个条目，所以最多能处理 64 × 2 = 128MB 的数据，而这恰好是存放 `2^25` 个整数所需的容量。S+ 树因为有约 7% 的内存开销，会更早一点撞上这个上限。

### 与 `std::lower_bound` 的比较 {#comparison-with-stdlower_bound}

从二分查找出发，我们已经走了很远：

![](/en/hpc/data-structures/img/search-all.svg)

在这个尺度下，看相对加速比更有意义：

![](/en/hpc/data-structures/img/search-relative.svg)

曲线开头的悬崖是因为 `std::lower_bound` 的运行时间随数组规模平滑增长，而 S+ 树的运行时间在局部是平坦的，只有在需要增加新的一层时才离散地跳一阶。

我们还没有讨论的一个重要注脚是：我们测量的其实不是真实延迟，而是*倒数吞吐量*（reciprocal throughput）——执行大量查询的总时间除以查询数：

```c++
clock_t start = clock();

for (int i = 0; i < m; i++)
    checksum ^= lower_bound(q[i]);

float seconds = float(clock() - start) / CLOCKS_PER_SEC;
printf("%.2f ns per query\n", 1e9 * seconds / m);
```

要测量*实际的*延迟，需要在循环迭代之间引入依赖，让下一次查询无法在上一次结束前开始：

```c++
int last = 0;

for (int i = 0; i < m; i++) {
    last = lower_bound(q[i] ^ last);
    checksum ^= last;
}
```

按真实延迟计，加速就没有那么惊人了：

![](/en/hpc/data-structures/img/search-relative-latency.svg)

S+ 树的性能提升很大一部分来自去除分支和最小化内存请求，这使得更多相邻查询的执行得以重叠——平均而言大约能重叠三个。

<!-- grouping requests together explicitly? -->

虽然除了可能搞 HFT 的人之外没人关心真实延迟，大家即使嘴上说"延迟"实际测的都是吞吐量，但在预估用户应用中可能的加速时，这个细微差别仍然需要考虑进去。

### 修改与进一步优化 {#modifications-and-further-optimizations}

<!--

Bloated:

```c++
void permute32(int *node) {
    // a b c d 1 2 3 4 -> (a c) (b d) (1 3) (2 4) -> (a c) (1 3) (b d) (2 4)
    reg x = _mm256_load_si256((reg*) (node + 8));
    reg y = _mm256_load_si256((reg*) (node + 16));
    _mm256_storeu_si256((reg*) (node + 8), y);
    _mm256_storeu_si256((reg*) (node + 16), x);
    permute16(node);
    permute16(node + 16);
}

unsigned permuted_rank32(reg x, int *node) {
    reg a = _mm256_load_si256((reg*) node);
    reg b = _mm256_load_si256((reg*) (node + 8));
    reg c = _mm256_load_si256((reg*) (node + 16));
    reg d = _mm256_load_si256((reg*) (node + 24));

    reg ca = _mm256_cmpgt_epi32(a, x);
    reg cb = _mm256_cmpgt_epi32(b, x);
    reg cc = _mm256_cmpgt_epi32(c, x);
    reg cd = _mm256_cmpgt_epi32(d, x);

    reg cab = _mm256_packs_epi32(ca, cb);
    reg ccd = _mm256_packs_epi32(cc, cd);
    reg cabcd = _mm256_packs_epi16(cab, ccd);
    unsigned mask = _mm256_movemask_epi8(cabcd);

    return __tzcnt_u32(mask);
}
```

```c++
unsigned rank32(reg x, int *node) {
    unsigned mask = cmp(x, node)
                  | (cmp(x, node + 8) << 8)
                  | (cmp(x, node + 16) << 16)
                  | (cmp(x, node + 24) << 24);
```

That's it. This implementation should outperform even the [state-of-the-art indexes](http://kaldewey.com/pubs/FAST__SIGMOD10.pdf) used in high-performance databases, though it's mostly due to the fact that data structures used in real databases have to support fast updates while we don't.

The problem has more dimensions.

-->

为了减少查询期间的内存访问次数，我们可以增大块大小。要在 32 元素节点（横跨两条缓存行、四个 AVX2 寄存器）中找局部下界，可以用一个[类似的技巧](https://github.com/sslotin/amh-code/blob/a74495a2c19dddc697f94221629c38fee09fa5ee/binsearch/bplus32.cc#L94)：用两条 `packs_epi32` 和一条 `packs_epi16` 合并掩码。

我们还可以试着更高效地利用缓存，方法是控制每一层在缓存层级中的驻留位置。做法是在查询期间把节点预取到[特定层级](/hpc/cpu-cache/prefetching/#software-prefetching)，并使用[非时间性读取](/hpc/cpu-cache/bandwidth/#bypassing-the-cache)。

我把这两个优化各实现了一版：一个块大小为 32，一个最后一次读取是非时间性的。它们并不能提升吞吐量：

![](/en/hpc/data-structures/img/search-bplus-other.svg)

……但确实降低了延迟：

![](/en/hpc/data-structures/img/search-latency-bplus.svg)

还有一些我尚未实现、但认为非常有前景的想法：

- 让块大小非均匀。动机是：拥有一层 32 元素层的减速，小于拥有两个独立层的减速。另外树根经常是不满的，所以也许有时它应该只有 8 个键甚至只有 1 个键。为给定的数组规模挑选最优的层配置，应该能抹平相对加速曲线上的尖峰，让它看起来更像自己的上包络。
  
  我知道怎么用代码生成来做，但我当时选择了一个更通用的方案，尝试用现代 C++ 的设施来[实现](https://github.com/sslotin/amh-code/blob/main/binsearch/bplus-adaptive.cc)，结果编译器没法以这种方式生成最优代码。
- 把节点与它的一两代后代（约 300 个节点／约 5k 个键）分组放在一起，让它们在内存中彼此靠近——精神上类似 [FAST](http://kaldewey.com/pubs/FAST__SIGMOD10.pdf) 所说的分层分块。这能减轻 TLB 缺失的严重程度，也可能改善延迟，因为内存控制器可以选择保持 [RAM 行缓冲区](/hpc/cpu-cache/aos-soa/#ram-specific-timings)开启，预期会有局部读取。
- 可选地在某些特定层使用预取。除了有 $\frac{1}{17}$ 的概率正好取到我们需要的节点之外，只要数据总线不忙，硬件预取器也可能顺带取回它的一些邻居。它同样具有与分块相同的 TLB 和行缓冲效应。

其他可能的小优化包括：

- 把最后一层的节点也重排——如果我们只需要下标而不需要值。
- 把各层的存放顺序反过来变成从左到右，让最上面的几层落在同一页上。
- 用汇编重写全部代码，因为编译器在指针运算上似乎很挣扎。
- 用[混合](/hpc/simd/masking)（blending）代替 `packs`：可以先把节点键做奇偶混洗（`[1 3 5 7] [2 4 6 8]`），与查找键比较，然后把第一个寄存器掩码的低 16 位与第二个的高 16 位混合。混合在许多架构上略快，而且交替使用打包与混合可能也有帮助，因为它们用的是不同的端口子集。（感谢 HackerNews 的 Const-me [提议](https://news.ycombinator.com/item?id=30381912)这一点。）
- 用 [popcount](/hpc/simd/shuffling/#shuffles-and-popcount) 代替 `tzcnt`：下标 `i` 等于小于 `x` 的键的个数，所以我们可以拿 `x` 与所有键比较，以任意方式合并向量掩码，调用 `maskmov`，再用 `popcnt` 数出置位的个数。这消除了对键存放顺序的要求，让我们能跳过重排步骤，也把这一过程用在最后一层上。
- 把键 $i$ 定义为第 $i$ 个孩子子树中的*最大*键，而不是第 $(i + 1)$ 个孩子子树中的*最小*键。正确性不变，但这保证了结果总存在我们访问的最后一个节点里（而不是下一个邻居节点的第一个元素），让我们能少取回一点缓存行。

注意，当前实现是特定于 AVX2 的，要适配其他平台可能需要一些不小的改动。把它移植到支持 AVX-512 的 Intel CPU 和支持 128 位 NEON 的 Arm CPU 上会很有意思，后者可能需要一些[技巧](https://github.com/WebAssembly/simd/issues/131)才能工作。

<!--

Mobile and some older CPUs only have 128-bit wide registers, and some high-end CPUs have 512-bit registers. and some computers even have different cache line size. NEON would require some [trickery](https://github.com/WebAssembly/simd/issues/131)

-->

有了这些优化，对某些平台，我不会惊讶于再看到 10-30% 的提升，以及大数组上对 `std::lower_bound` 超过 10 倍的加速。

### 作为动态树 {#as-a-dynamic-tree}

与 `std::set` 和其他基于指针的树相比，对比结果更加悬殊。在我们的基准测试中，我们插入相同的元素（不计插入耗时）并使用相同的下界查询，S+ 树最快可达 30 倍：

![](/en/hpc/data-structures/img/search-set-relative.svg)

这提示我们，或许可以用这个方法同样大幅改进*动态*搜索树。

为了验证这个假设，我为每个节点添加了一个 17 个下标的数组，指向它们的孩子应该在哪里，并用这个数组替代通常的隐式编号来下降树。这个数组独立于树本体，不对齐，甚至不在大页上——我们做的唯一优化是预取一个节点的第一个和最后一个指针。

我还把 [Abseil 的 B-tree](https://abseil.io/blog/20190812-btree) 加入了对比，它是我所知唯一被广泛使用的 B 树实现。它的表现只比 `std::lower_bound` 略好，而带指针的 S+ 树在大数组上快约 15 倍：

<!--

My next priorities is to adapt it to segment trees, which I know how to do, and to B-trees, which I don't exactly know how to do. But comparing to `std::set` hints that there may be up to 30x improvements:

`absl::btree_set`, the only widely-used B-tree implementation I know, is just slightly faster than binary search.

-->

![](/en/hpc/data-structures/img/search-set-relative-all.svg)

当然，这个对比并不公平，因为实现动态搜索树是一个维度更高的问题。

我们还需要实现更新操作，它不会那么高效，而且要为它牺牲一些扇出。但看起来实现一个快 10-20 倍的 `std::set`、快 3-5 倍的 `absl::btree_set` 仍然是可能的——取决于你怎么定义"快"——而这也是我们[接下来要尝试](../b-tree)做的事情之一。

<!--

A ~15x improvement is definitely worth it — and the memory overhead is not large, as we only need to store pointers (indices, actually) for internal nodes. It may be higher, because we need to fetch two separate memory blocks, or lower, because we need to handle updates somehow. Either way, this will be an interesting optimization problem.

though it's mostly due to the fact that data structures used in real databases have to support fast updates while we don't.

The problem has more dimensions.

-->

### 致谢 {#acknowledgements}

Cory Nelson 的这个 [StackOverflow 回答](https://stackoverflow.com/questions/20616605/using-simd-avx-sse-for-tree-traversal)是我重排 16 元素搜索技巧的出处。

<!--

I stole some pictures from blogs and I can't find the originals.

-->

