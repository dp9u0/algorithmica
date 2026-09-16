---
title: 搜索树
weight: 3
draft: true
---

在[上一篇文章](../s-tree)中，我们设计并实现了*静态* B 树来加速有序数组中的二分查找。在它的[最后一节](../s-tree/#as-a-dynamic-tree)里，我们简短讨论了如何在保留 [SIMD](/hpc/simd) 带来的性能收益的同时把它们变回*动态*的，并通过在 S+ 树的内部节点中添加和跟随显式指针验证了我们的预测。

在本文中，我们沿着这个思路设计一个功能最小化的整数键搜索树，在 `lower_bound` 和 `insert` 查询上分别取得对 `std::set` 最高 18 倍/8 倍、对 [`absl::btree`](https://abseil.io/blog/20190812-btree) 最高 7 倍/2 倍的加速（[评估数据](#evaluation)在此）——而且仍有充足的改进空间。

这个结构的内存开销对 32 位整数约为 30%，最终实现[不到 150 行 C++](https://github.com/sslotin/amh-code/blob/main/b-tree/btree-final.cc)。它可以容易地推广到其他算术类型和小／定长字符串，比如哈希值、国家代码和股票代码。

<!--

7-18x/3-8x speedup over `std::set` and 3-7x/1.5-2x

that we call *B− tree*

-->

## B− 树 {#b-tree}

不像其他案例研究中那样做小的渐进式改进，本文只实现一个数据结构，我们把它命名为 *B− 树*（B− tree）。它基于 [B+ 树](../s-tree/#b-tree-layout-1)，有几点小差异：

- B− 树的节点不存储指针或任何元数据（B+ 树的叶子节点会存一个指向下一个叶子的指针），内部节点孩子的指针除外。这让我们能把叶子节点里的键完美地铺在缓存行上。
- 我们把键 $i$ 定义为第 $i$ 个孩子的子树中的*最大*键，而不是第 $(i + 1)$ 个孩子的子树中的*最小*键。这让我们到达叶子之后不必再取任何其他节点（B+ 树中叶子节点里的键可能全部小于查找键，那样就得去下一个叶子取它的第一个元素）。

我们还使用 $B=32$ 的节点大小，比典型值小。它不是 $16$——那个对 [S+ 树最优](../s-tree/#modifications-and-further-optimizations)的值——的原因是：我们多了取回指针的额外开销，把树高降低约 20% 的收益超过了每节点多处理一倍元素的成本，而且这还能改善 `insert` 查询的运行时间，它平均每 $\frac{B}{2}$ 次插入就要执行一次代价高昂的节点分裂。

<!--

We will discuss other node sizes later.

This is needed simd to be efficient (we will discuss other node sizes later).

There is some overhead, so it makes sense to use more than one cache line.

Analogous to the B+ tree,

-->

### 内存布局 {#memory-layout}

虽然从软件工程的角度这可能不是最好的做法，但我们干脆把整棵树存进一个大的预分配数组，不区分叶子和内部节点：

```c++
const int R = 1e8;
alignas(64) int tree[R];
```

我们还预先把数组填满无穷大以简化实现：

```c++
for (int i = 0; i < R; i++)
    tree[i] = INT_MAX;
```

（一般而言，拿它与底层用 `new` 的 `std::set` 之类结构比较在技术上算作弊，但内存分配和初始化在这里都不是瓶颈，所以这对评估没有显著影响。）

两种类型的节点都按键排序顺序存储键，并以它第一个键在数组中的下标来标识：

- 叶子节点最多有 $(B - 1)$ 个键，但会用无穷大填充到 $B$ 个元素。
- 内部节点最多有 $(B - 2)$ 个键填充到 $B$ 个元素，以及最多 $(B - 1)$ 个孩子节点的下标，同样填充到 $B$ 个元素。

这些设计决策并非随意：

- 填充保证叶子节点恰好占 2 条缓存行，内部节点恰好占 4 条。
- 我们特意[用下标而不是指针](/hpc/cpu-cache/pointers/)，以节省缓存空间并让 SIMD 搬运它们更快。
  （下文中"指针"和"下标"会混用。）
- 我们把下标紧挨着键存放，尽管它们位于不同的缓存行上，因为[我们有自己的理由](/hpc/cpu-cache/aos-soa/)。
- 我们有意在叶子节点里"浪费"一个数组单元、在内部节点里"浪费" $2+1=3$ 个单元，因为节点分裂时需要它们存放临时结果。

初始时我们只有一个作为根的空叶子节点：

```c++
const int B = 32;

int root = 0;   // where the keys of the root start
int n_tree = B; // number of allocated array cells
int H = 1;      // current tree height
```

要"分配"一个新节点，只需把 `n_tree` 增加 $B$（叶子）或 $2 B$（内部节点）。

由于新节点只能由满节点分裂产生，除根以外的每个节点至少是半满的。这意味着每个整数元素需要 4 到 8 个字节（内部节点对这个数字的贡献约 $\frac{1}{16}$），前者对应顺序插入的情况，后者对应对抗性输入的情况。当查询均匀分布时，节点平均约 75% 满，折合约 5.2 字节每元素。

与基于指针的二叉树相比，B 树的内存效率非常高。例如 `std::set` 至少需要三个指针（左孩子、右孩子、父亲），仅此就花掉 $3 \times 8 = 24$ 字节，加上[结构填充](/hpc/cpu-cache/alignment/)的原因，存键和元信息至少还要 $8$ 字节。

### 搜索 {#searching}

超过 90% 的操作都是查询是非常常见的场景；即使不是这样，其他树操作通常也都要先定位一个键，所以我们从搜索的实现和优化开始。

实现 [S-tree](../s-tree/#optimization) 时，由于混合（blending）／打包（packs）指令工作方式的微妙之处，我们最终把键按重排过的顺序存放。对*动态树*问题，重排存放会让插入难实现得多，所以我们换一种思路。

在有序数组中找元素 `x` 将来所在的位置，另一种理解方式不是"第一个不小于 `x` 的元素的下标"，而是"小于 `x` 的元素的个数"。这个观察引出如下想法：把键与 `x` 比较，把向量掩码聚合成一个 32 位掩码（只要映射是双射，每个比特可以对应任意元素），然后对它调用 `popcnt`，返回小于 `x` 的元素个数。

这个技巧让我们无需任何混洗就能高效完成节点内搜索：

```c++
typedef __m256i reg;

reg cmp(reg x, int *node) {
    reg y = _mm256_load_si256((reg*) node);
    return _mm256_cmpgt_epi32(x, y);
}

// returns how many keys are less than x
unsigned rank32(reg x, int *node) {
    reg m1 = cmp(x, node);
    reg m2 = cmp(x, node + 8);
    reg m3 = cmp(x, node + 16);
    reg m4 = cmp(x, node + 24);

    // take lower 16 bits from m1/m3 and higher 16 bits from m2/m4
    m1 = _mm256_blend_epi16(m1, m2, 0b01010101);
    m3 = _mm256_blend_epi16(m3, m4, 0b01010101);
    m1 = _mm256_packs_epi16(m1, m3); // can also use blendv here, but packs is simpler

    unsigned mask = _mm256_movemask_epi8(m1);
    return __builtin_popcount(mask);    
}
```

注意，由于这个例程，我们必须用无穷大填充"键区域"，这让我们无法在被腾出的单元里存元数据（除非愿意在载入 SIMD 通道时多花几个周期把掩码之外的东西屏蔽掉）。

现在，实现 `lower_bound` 只需像 S+ 树那样下降树，只是在算出孩子编号后再取回指针：

```c++
int lower_bound(int _x) {
    unsigned k = root;
    reg x = _mm256_set1_epi32(_x);
    
    for (int h = 0; h < H - 1; h++) {
        unsigned i = rank32(x, &tree[k]);
        k = tree[k + B + i];
    }

    unsigned i = rank32(x, &tree[k]);

    return tree[k + i];
}
```

实现搜索很容易，也没有引入多少开销。难的是插入。

### 插入 {#insertion}

一方面，正确实现插入需要大量代码；另一方面，这些代码中的大部分执行得非常不频繁，所以我们不必太在意它的性能。大多数时候，我们要做的就是到达叶子节点（怎么到达已经解决了），然后向其中插入一个新键，把键的某个后缀右移一位。偶尔我们也需要分裂节点和／或更新一些祖先，但这相对罕见，所以先聚焦最常见的执行路径。

要向含 $(B - 1)$ 个有序元素的数组插入键，我们可以把它们载入向量寄存器，然后用[预计算](/hpc/compilation/precalc/)的掩码——它指明对给定的 `i` 哪些元素需要写入——把它们[掩码存储](/hpc/simd/masking)到右边一位的位置：

```c++
struct Precalc {
    alignas(64) int mask[B][B];

    constexpr Precalc() : mask{} {
        for (int i = 0; i < B; i++)
            for (int j = i; j < B - 1; j++)
                // everything from i to B - 2 inclusive needs to be moved
                mask[i][j] = -1;
    }
};

constexpr Precalc P;

void insert(int *node, int i, int x) {
    // need to iterate right-to-left to not overwrite the first element of the next lane
    for (int j = B - 8; j >= 0; j -= 8) {
        // load the keys
        reg t = _mm256_load_si256((reg*) &node[j]);
        // load the corresponding mask
        reg mask = _mm256_load_si256((reg*) &P.mask[i][j]);
        // mask-write them one position to the right
        _mm256_maskstore_epi32(&node[j + 1], mask, t);
    }
    node[i] = x; // finally, write the element itself
}
```

这个 [constexpr 魔法](/hpc/compilation/precalc/)是我们使用的唯一 C++ 语言特性。

还有其他做法，有些可能更高效，但我们暂时到此为止。

分裂节点时需要把一半的键移到另一个节点，所以再写一个这样的原语：

```c++
// move the second half of a node and fill it with infinities
void move(int *from, int *to) {
    const reg infs = _mm256_set1_epi32(INT_MAX);
    for (int i = 0; i < B / 2; i += 8) {
        reg t = _mm256_load_si256((reg*) &from[B / 2 + i]);
        _mm256_store_si256((reg*) &to[i], t);
        _mm256_store_si256((reg*) &from[B / 2 + i], infs);
    }
}
```

有了这两个向量函数，我们可以非常小心地实现插入了：

```c++
void insert(int _x) {
    // the beginning of the procedure is the same as in lower_bound,
    // except that we save the path in case we need to update some of our ancestors
    unsigned sk[10], si[10]; // k and i on each iteration
    //           ^------^ We assume that the tree height does not exceed 10
    //                    (which would require at least 16^10 elements)
    
    unsigned k = root;
    reg x = _mm256_set1_epi32(_x);

    for (int h = 0; h < H - 1; h++) {
        unsigned i = rank32(x, &tree[k]);

        // optionally update the key i right away
        tree[k + i] = (_x > tree[k + i] ? _x : tree[k + i]);
        sk[h] = k, si[h] = i; // and save the path
        
        k = tree[k + B + i];
    }

    unsigned i = rank32(x, &tree[k]);

    // we can start computing the is-full check before insertion completes
    bool filled  = (tree[k + B - 2] != INT_MAX);

    insert(tree + k, i, _x);

    if (filled) {
        // the node needs to be split, so we create a new leaf node
        move(tree + k, tree + n_tree);
        
        int v = tree[k + B / 2 - 1]; // new key to be inserted
        int p = n_tree;              // pointer to the newly created node
        
        n_tree += B;

        for (int h = H - 2; h >= 0; h--) {
            // ascend and repeat until we reach the root or find a the node is not split
            k = sk[h], i = si[h];

            filled = (tree[k + B - 3] != INT_MAX);

            // the node already has a correct key (the right one)
            //                  and a correct pointer (the left one)
            insert(tree + k,     i,     v);
            insert(tree + k + B, i + 1, p);
            
            if (!filled)
                return; // we're done

            // create a new internal node
            move(tree + k,     tree + n_tree);     // move keys
            move(tree + k + B, tree + n_tree + B); // move pointers

            v = tree[k + B / 2 - 1];
            tree[k + B / 2 - 1] = INT_MAX;

            p = n_tree;
            n_tree += 2 * B;
        }

        // if reach here, this means we've reached the root,
        // and it was split into two, so we need a new root
        tree[n_tree] = v;

        tree[n_tree + B] = root;
        tree[n_tree + B + 1] = p;

        root = n_tree;
        n_tree += 2 * B;
        H++;
    }
}
```

低效之处很多，但幸运的是 `if (filled)` 的函数体执行得非常不频繁——大约每 $\frac{B}{2}$ 次插入一次——而插入性能本来就不是我们的首要目标，所以就让它去了。

## 性能评估 {#evaluation}

我们只实现了 `insert` 和 `lower_bound`，所以测量也就是这两样。

我们希望评估花费的时间合理，所以基准测试是一个在两个步骤之间交替的循环：

- 用单次 `insert` 把结构规模从 $1.17^k$ 增长到 $1.17^{k+1}$，并测量所花的时间。
- 执行 $10^6$ 次随机 `lower_bound` 查询，并测量所花的时间。

我们从规模 $10^4$ 开始、到 $10^7$ 结束，总共约 $50$ 个数据点。两类查询的数据都在 $[0, 2^{30})$ 范围内均匀生成，且各阶段之间相互独立。由于数据生成过程允许重复键，我们对比的是 `std::multiset` 和 `absl::btree_multiset`[^absl]，不过为简洁仍称它们为 `std::set` 和 `absl::btree`。我们还在系统层面为这三者都启用了[大页](/hpc/cpu-cache/paging)。

[^absl]: 如果你也觉得只和 Abseil 的 B-tree 比不够有说服力，欢迎把你最喜欢的搜索树[加进](https://github.com/sslotin/amh-code/tree/main/b-tree)基准测试。

<!--

Keys are uniform, but we should not rely on that fact (e.g., using interpolation search).

It is common that >90% of operations are lookups. Optimizing searches is important because every other operation starts with locating a key.

I apologize to everyone else, but this is sort of your fault for not using a public benchmark.

-->

B− 树的性能与我们最初的预测相符——至少对查询是如此：

![](/en/hpc/data-structures/img/btree-absolute.svg)

相对加速随结构规模变化——对 STL 是 7-18 倍/3-8 倍，对 Abseil 是 3-7 倍/1.5-2 倍：

![](/en/hpc/data-structures/img/btree-relative.svg)

插入只比 `absl::btree`（全部用标量代码完成）快 1.5-2 倍。插入之所以*这么*慢，我最好的猜测是数据依赖：由于树节点可能变化，CPU 无法在上一次查询结束前开始处理下一次（两种查询的[真实延迟](../s-tree/#comparison-with-stdlower_bound)大致相等，约为 `lower_bound` 倒数吞吐量的 3 倍）。

![](/en/hpc/data-structures/img/btree-absl.svg)

结构规模小时，`lower_bound` 的[倒数吞吐量](../s-tree/#comparison-with-stdlower_bound)呈离散阶梯增长：只有根节点可访问时是 3.5ns，然后涨到 6.5ns（两个节点），再到 12ns（三个节点），然后撞上 L2 缓存（图上未画出）开始更平滑地增长，但树高每次增加时仍有明显的尖峰。

有趣的是，B− 树哪怕只存一个键时也胜过 `absl::btree`：后者要为[分支预测失败](/hpc/pipelining/branching/)停顿约 5ns，而 B− 树的搜索是完全无分支的。

### 可能的优化 {#possible-optimizations}

在我们以往的数据结构优化尝试中，把尽可能多的变量变成编译期常量帮了大忙：编译器可以把这些常量硬编码进机器码、简化算术、展开所有循环，替我们做许多好事。

如果我们的树高度恒定，这就完全不是问题，但它不是。不过它*大体上*是恒定的：高度很少变化，事实上在基准测试的约束下，最大高度也只有 6。

我们能做的是为若干不同的编译期常量高度预编译 `insert` 和 `lower_bound` 函数，随树增长在它们之间切换。地道的 C++ 做法是用虚函数，但我更喜欢显式的裸函数指针：

```c++
void (*insert_ptr)(int);
int (*lower_bound_ptr)(int);

void insert(int x) {
    insert_ptr(x);
}

int lower_bound(int x) {
    return lower_bound_ptr(x);
}
```

现在定义以树高为参数的模板函数，并在 `insert` 函数内树增长的那段代码里随树的生长切换指针：

```c++
template <int H>
void insert_impl(int _x) {
    // ...
}

template <int H>
void insert_impl(int _x) {
    // ...
    if (/* tree grows */) {
        // ...
        insert_ptr = &insert_impl<H + 1>;
        lower_bound_ptr = &lower_bound_impl<H + 1>;
    }
}

template <>
void insert_impl<10>(int x) {
    std::cerr << "This depth was not supposed to be reached" << std::endl;
    exit(1);
}
```

<!--

insert_ptr = &insert_impl<1>;
lower_bound_ptr = &lower_bound_impl<1>;

-->

我试过了，但没拿到任何性能提升，不过我仍对这个方法抱有厚望：编译器（理论上）可以消除 `sk` 和 `si`，彻底去掉临时存储，每样东西只读取和计算一次，大幅优化 `insert` 过程。

插入大概率还能靠更大的块大小来优化——节点分裂会变少——但代价是查询变慢。我们也可以给不同的层用不同的节点大小：叶子大概应该比内部节点大。

**另一个想法**是插入时把多余的键挪到兄弟节点，把节点分裂尽量往后拖。

这类改法中有一种广为人知，即 B* 树。它在当前节点满时把最后一个键挪到下一个节点，而当两个节点都满时，把它们一起分裂成三个 ⅔ 满的节点。这降低了内存开销（节点平均 ⅚ 满）并提高了扇出、降低了树高，对所有操作都有帮助。

这种技术甚至能推广到比如三变四的分裂，尽管进一步泛化会让 `insert` 变慢。

**还有一个想法**是去掉（一部分）指针。例如对很大的树，我们大概负担得起用一个覆盖 $16 \cdot 17$ 个元素左右的小 [S+ 树](../s-tree)作为树根，并在它不常变化的每次变化时从头重建。遗憾的是没法把它扩展到整棵树：我记得某处有篇论文说，动态结构若要完全隐式化，每个查询就得付出 $\Omega(\sqrt n)$ 的代价。

我们也可以尝试一些非树的数据结构，比如[跳表](https://en.wikipedia.org/wiki/Skip_list)。甚至有过一次[成功将它向量化的尝试](https://doublequan.github.io/)——尽管加速并不惊人。我对跳表本身能有多大改进不抱太大希望，尽管它在并发场景下也许能获得更高的总吞吐量。

### 其他操作 {#other-operations}

要*删除*一个键，同样可以先定位它，再用同样的掩码存储技巧把它从节点中移除。之后如果节点仍然至少半满，就完成了。否则，尝试从下一个兄弟借一个键：如果兄弟的键多于 $\frac{B}{2}$ 个，就把它的第一个键追加过来、把它的键整体左移一位。否则，当前节点和下一个节点的键都少于 $\frac{B}{2}$ 个，可以把它们合并，然后上溯到父节点迭代地删除那里的一个键。

另一件我们可能想实现的事是*迭代*。把 `l` 到 `r` 之间的键批量取出是非常常见的模式——比如数据库里 `SELECT abc ORDER BY xyz` 类型的查询——而 B+ 树通常会在数据层存指向下一个节点的指针以支持这种快速迭代。B− 树的节点小得多，这么做会遇到[指针追逐](/hpc/cpu-cache/latency/)问题。改为上溯到父节点、读出它的全部 $B$ 个指针可能更快，因为它消除了这个问题。因此，一个祖先栈（`insert` 里用到的 `sk` 和 `si` 数组）就可以充当迭代器，甚至可能比在节点里单独存指针更好。

`std::set` 的功能我们几乎都能容易地实现，但 B− 树与其他 B 树一样，因为指针稳定性的要求，极难成为 `std::set` 的即插即用替代品：指向元素的指针应当在元素未被删除时保持有效，而我们一直在分裂、合并节点，这很难做到。这不仅对搜索树是个大问题，对绝大多数数据结构都是：同时拥有指针稳定性和高性能几乎是不可能的。

<!--

Maybe if the C++ standard adds something like `std::set_with_unstable_pointers`

We can't store junk in keys.

-->

## 致谢 {#acknowledgements}

感谢来自 Google 的 [Danila Kutenin](https://danlark.org/) 就 B 树在 Abseil 中的适用性与使用进行的多次有意义的讨论。

<!-- One interesting use case is *rope*, also known as *cord*, which is used for wrapping strings in a tree to support mass operations. For example, editing a very large text file. Which is the topic. -->
