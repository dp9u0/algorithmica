---
title: 二分查找
weight: 1
draft: true
---

<!-- mention interpolation search and radix trees? -->

虽然提升面向用户的应用程序的速度是性能工程的终极目标，但人们并不会真的为数据库里 5-10% 的提升而兴奋。没错，这正是软件工程师拿工资干的活，但这类优化往往过于繁琐、过于依赖具体系统，很难直接推广到其他软件上。

相反，性能工程最精彩的展示是对教科书算法的多倍优化：那种人人都知道、并且认为它简单到根本不会想到要去优化的算法。这类优化既简单又有启发性，而且完全可以被借鉴到别处。并且它们出人意料地并不罕见。

<!-- Yet, with remarkable periodicity, these can be optimized to ridiculous levels of performance. -->

在本节中，我们聚焦于一个这样的基础算法——*二分查找*（binary search）——并实现它的两个变体，依问题规模不同，它们比 `std::lower_bound` 最快可达 4 倍，而代码只有不到 15 行。

第一个算法通过去除[分支](/hpc/pipelining/branching)来达成这一点，第二个算法还进一步优化了内存布局以获得更好的[缓存系统](/hpc/cpu-cache)性能。严格来说，后者因此失去了作为 `std::lower_bound` 即插即用替代品的资格，因为它需要先对数组元素做一次重排才能开始回答查询——但我想不出有什么场景是你拿到了一个有序数组、却负担不起线性时间的预处理。

<!--

- *Branchless binary search* that is up to 3x faster on *small* arrays and can act as a drop-in replacement to `std::lower_bound`.
- *Eytzinger binary search* that rearranges the elements of a sorted array in a cache-friendly way of is also 3x faster on small arrays and 2x faster on large arrays.

-->

照例先声明环境：CPU 是 [Zen 2](https://www.7-cpu.com/cpu/Zen2.html)，内存是 [DDR4-2666](/hpc/cpu-cache/)，默认使用的编译器是 Clang 10。你的机器上的性能可能有所不同，所以我强烈建议你亲自去[测一测](https://godbolt.org/z/14rd5Pnve)。

<!--

It performs slightly worse on array sizes that fit lower layers of cache, but in low-bandwidth environments it can be up to 3x faster (or 7x faster than `std::lower_bound`). GCC sucked on all benchmarks, so we will mostly be using Clang (10.0). The CPU is a Zen 2, although the results should be transferrable to other platforms, including most Arm-based chips.

The CPU is a Zen 2, and as always, the results are a bit architecture dependant, although the results should be transferrable to other platforms, including most Arm-based chips.

This is a large article, which will turn into a multi-hour read. If you feel comfortable reading [intrinsic](/hpc/simd/intrinsics)-heavy code without any context whatsoever, you can skim through the first four implementation and jump straight to the last section.

Build up understanding gradually, but you can skip them.

-->

## 二分查找 {#binary-search}

<!--

For our benchmark, we create an array of random integers of size `n` and sort it. Then, each implementations can do some preprocessing:

```c++
void prepare(int *a, int n);
int lower_bound(int x);
```

Already sorted array `t` of size `n`.

We are going ot create an array named `a` into array named `t`.

-->

下面是在一个含 `n` 个整数的有序数组 `t` 中查找第一个不小于 `x` 的元素的标准写法，任何一本计算机科学入门教材里都能找到：

```c++
int lower_bound(int x) {
    int l = 0, r = n - 1;
    while (l < r) {
        int m = (l + r) / 2;
        if (t[m] >= x)
            r = m;
        else
            l = m + 1;
    }
    return t[l];
}
```

<!-- We maintain the indices of first and the last element that may be the answer, compare the element the middle to the key `x`, and then shrink the search interval by half depending how the comparison went. Beautiful in its simplicity. -->

找出查找区间的中间元素，与 `x` 比较，把区间缩小一半。美就美在它的简洁。

`std::lower_bound` 采用的方法类似，只不过它需要更通用，以支持非随机访问迭代器的容器，因此它使用的是第一个元素和查找区间的长度，而不是区间的两端。为此，[Clang](https://github.com/llvm-mirror/libcxx/blob/78d6a7767ed57b50122a161b91f59f19c9bd0d19/include/algorithm#L4169) 和 [GCC](https://github.com/gcc-mirror/gcc/blob/d9375e490072d1aae73a93949aa158fcd2a27018/libstdc%2B%2B-v3/include/bits/stl_algobase.h#L1023) 的实现都用了这么一个元编程怪物：

```c++
template <class _Compare, class _ForwardIterator, class _Tp>
_LIBCPP_CONSTEXPR_AFTER_CXX17 _ForwardIterator
__lower_bound(_ForwardIterator __first, _ForwardIterator __last, const _Tp& __value_, _Compare __comp)
{
    typedef typename iterator_traits<_ForwardIterator>::difference_type difference_type;
    difference_type __len = _VSTD::distance(__first, __last);
    while (__len != 0)
    {
        difference_type __l2 = _VSTD::__half_positive(__len);
        _ForwardIterator __m = __first;
        _VSTD::advance(__m, __l2);
        if (__comp(*__m, __value_))
        {
            __first = ++__m;
            __len -= __l2 + 1;
        }
        else
            __len = __l2;
    }
    return __first;
}
```

如果编译器成功地去除了这些抽象，它编译出的机器码与手写版本大致相同，平均延迟也大致一样，并且[不出所料地](/hpc/cpu-cache/latency)随数组规模增长：

![](/en/hpc/data-structures/img/search-std.svg)

由于大多数人不会手写二分查找，我们将使用 Clang 的 `std::lower_bound` 作为基准。

### 瓶颈 {#the-bottleneck}

在跳到优化后的实现之前，我们先简要讨论一下二分查找到底为什么慢。

如果你用 [perf](/hpc/profiling/events) 跑 `std::lower_bound`，你会看到它大部分时间花在一条[条件跳转](/hpc/architecture/loops)指令上：

```nasm
       │35:   mov    %rax,%rdx
  0.52 │      sar    %rdx
  0.33 │      lea    (%rsi,%rdx,4),%rcx
  4.30 │      cmp    (%rcx),%edi
 65.39 │    ↓ jle    b0
  0.07 │      sub    %rdx,%rax
  9.32 │      lea    0x4(%rcx),%rsi
  0.06 │      dec    %rax
  1.37 │      test   %rax,%rax
  1.11 │    ↑ jg     35
```

这个[流水线停顿](/hpc/)阻止了查找继续推进，它主要由两个[因素](/hpc/pipelining/hazards)造成：

- 我们遭遇了*控制冒险*（control hazard），因为有一个[分支](/hpc/pipelining/branching)是无法预测的（查询和键是独立随机抽取的），处理器每次[分支预测失败](/hpc/pipelining/branching)都要停顿 10-15 个周期来冲刷流水线并重新填满。
- 我们遭遇了*数据冒险*（data hazard），因为我们必须等待前一个比较完成，而这个比较又在等待它的一个操作数从内存中取回——根据它所在的位置，这[可能花费](/hpc/cpu-cache/latency) 0 到 300 个周期不等。

现在，让我们尝试逐个消除这些障碍。

## 去除分支 {#removing-branches}

我们可以用[谓词化](/hpc/pipelining/branchless)来替代分支。为了让任务更简单，我们可以采用 STL 的做法，改用第一个元素和查找区间长度（而不是它的首尾两个元素）来重写这个循环：

```c++
int lower_bound(int x) {
    int *base = t, len = n;
    while (len > 1) {
        int half = len / 2;
        if (base[half - 1] < x) {
            base += half;
            len = len - half;
        } else {
            len = half;
        }
    }
    return *base;
}
```

注意，每次迭代中 `len` 本质上只是被减半，然后根据比较结果向上或向下取整。这个条件更新看起来没必要；为了避免它，我们可以直接规定它总是向上取整：

```c++
int lower_bound(int x) {
    int *base = t, len = n;
    while (len > 1) {
        int half = len / 2;
        if (base[half - 1] < x)
            base += half;
        len -= half; // = ceil(len / 2)
    }
    return *base;
}
```

这样，我们每次迭代只需要用一条[条件传送](/hpc/pipelining/branchless/)更新查找区间的第一个元素，并把区间长度减半：

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

<!-- pre-compute base pointer for next iteration? -->

注意，这个循环并不总是与标准二分查找等价。由于它总是对查找区间长度*向上*取整，它访问的元素略有不同，可能比所需的比较多做一次。除了简化每次迭代的计算之外，它还使得迭代次数在数组规模固定时是常数，从而完全消除了分支预测失败。

正如谓词化的典型情况，这个技巧对编译器优化非常脆弱——取决于编译器以及函数如何被调用，它可能仍然留下一个分支，或者生成次优的代码。它在 Clang 10 上工作正常，在小数组上带来 2.5-3 倍的提升：

<!-- todo: update numbers -->

![](/en/hpc/data-structures/img/search-branchless.svg)

一个有趣的细节是它在大数组上表现更差。这看起来很奇怪：总延迟由 RAM 延迟主导，而它执行的内存访问与标准二分查找大致相同，所以性能应该大致相同甚至略好。

你真正需要问的问题不是为什么无分支的实现更差，而是为什么有分支的版本更好。原因在于有分支时，CPU 可以对某个分支进行[推测](/hpc/pipelining/branching/)，在还没确认它正确之前就开始取回左孩子或右孩子的键——这实际上起到了隐式[预取](/hpc/cpu-cache/prefetching)的作用。

对于无分支的实现，这不会发生，因为 `cmov` 被当作普通指令对待，分支预测器不会试图窥探它的操作数来预言未来。为了补偿这一点，我们可以在软件中显式请求左右两个子键来进行预取：

```c++
int lower_bound(int x) {
    int *base = t, len = n;
    while (len > 1) {
        int half = len / 2;
        len -= half;
        __builtin_prefetch(&base[len / 2 - 1]);
        __builtin_prefetch(&base[half + len / 2 - 1]);
        base += (base[half - 1] < x) * half;
    }
    return *base;
}
```

<!-- todo: rerun this too -->

加上预取后，大数组上的性能变得大致相同：

![](/en/hpc/data-structures/img/search-branchless-prefetch.svg)

曲线仍然增长得更快，因为有分支的版本还会预取"孙节点"、"曾孙节点"等等——尽管随着预测越来越不可能正确，每次新推测读取的收益也呈指数级递减。

无分支的版本同样可以向前多取几层，但所需的预取次数也会指数级增长。因此，我们将尝试一种不同的方法来优化内存操作。

## 优化内存布局 {#optimizing-the-layout}

二分查找过程中执行的内存请求构成一个非常特定的访问模式：

![](/en/hpc/data-structures/img/binary-search.png)

每次请求的元素有多大概率已在缓存中？它们的[数据局部性](/hpc/external-memory/locality/)有多好？

- *空间局部性*（spatial locality）对最后 3 到 4 次请求来说似乎还行，它们很可能在同一个[缓存行](/hpc/cpu-cache/cache-lines)上——但之前所有的请求都需要巨大的内存跳转。
- *时间局部性*（temporal locality）对头十几次请求来说似乎还行——这么长度的比较序列并没有多少种，所以我们会一遍又一遍地与同样的中间元素比较，而这些元素很可能已在缓存中。

为了说明第二类缓存共享有多重要，让我们试着在每次迭代时，从查找区间的元素中随机挑选一个元素作为比较对象，而不是选中间那个：

```c++
int lower_bound(int x) {
    int l = 0, r = n - 1;
    while (l < r) {
        int m = l + rand() % (r - l);
        if (t[m] >= x)
            r = m;
        else
            l = m + 1;
    }
    return t[l];
}
```

[理论上](#appendix-random-binary-search)，这个随机化二分查找预期的比较次数比普通版本多 30-40%，但在真实的计算机上，大数组的运行时间变成了约 6 倍：

![](/en/hpc/data-structures/img/search-random.svg)

这不仅仅是 `rand()` 调用慢造成的。你可以清楚地看到 L2-L3 边界上的那个点，在那里内存延迟的代价超过了随机数生成和[取模](/hpc/arithmetic/division)。性能退化是因为所有被取到的元素都不太可能在缓存里，而不只是其中一小部分后缀。

另一个潜在的负面效应是[缓存相联度](/hpc/cpu-cache/associativity)。如果数组规模是某个较大的 2 的幂的倍数，那么这些"热"元素的下标也会被某些较大的 2 的幂整除，从而映射到同一个缓存行上，互相挤出去。例如，在规模为 $2^{20}$ 的数组上二分查找每次查询约需 360ns，而在规模为 $(2^{20} + 123)$ 的数组上约需 300ns——相差 20%。有[一些办法](https://en.wikipedia.org/wiki/Fibonacci_search_technique)可以解决这个问题，但为了不在更重要的事情上分心，我们直接忽略它：我们使用的所有数组规模都取 $\lfloor 1.17^k \rfloor$（$k$ 为整数）的形式，这样任何缓存副作用都不太可能发生。

我们的内存布局真正的问题在于它没有最高效地利用时间局部性，因为它把热元素和冷元素分组在了一起。例如，元素 $\lfloor n/2 \rfloor$ 是每次查询一开始就要请求的，但它很可能和 $\lfloor n/2 \rfloor + 1$ 存在同一个缓存行里，而我们几乎从不请求后者。

<!--  (sometimes literally never — if it is the first element in a search range of three, and it is indeed the lower bound, we just compare against the middle and deduce it has to be the first element without ever even fetching it) — this is not true -->

下面这张热力图可视化了一个 31 元素数组的期望比较频率：

![](/en/hpc/data-structures/img/binary-heat.png)

所以，理想情况下我们想要一种内存布局：热元素和热元素分组在一起，冷元素和冷元素分组在一起。而只要用一种更缓存友好的方式给元素重新编号、重排整个数组，我们就能做到这一点。我们要用的这种编号法其实已经有五百年历史了，而且你很可能早就认识它。

### Eytzinger 布局 {#eytzinger-layout}

**Michaël Eytzinger** 是一位 16 世纪的奥地利贵族，以谱牒学方面的工作闻名，尤其是被称为 *ahnentafel*（德语"祖先表"）的祖先编号系统。

那个年代血统非常重要，但把这类数据写下来成本很高。*Ahnentafel* 能够紧凑地展示一个人的家谱，而不用画谱系图浪费额外空间。

它按照固定的上升顺序列出一个人的直系祖先。首先，此人自己被列为 1 号，然后递归地，对每个编号为 $k$ 的人，其父亲列为 $2k$，母亲列为 $(2k+1)$。

下面是[保罗一世](https://en.wikipedia.org/wiki/Paul_I_of_Russia)的例子，他是[彼得大帝](https://en.wikipedia.org/wiki/Peter_the_Great)的曾孙：

1. 保罗一世
2. 彼得三世（保罗之父）
3. [叶卡捷琳娜二世](https://en.wikipedia.org/wiki/Catherine_the_Great)（保罗之母）
4. 卡尔·弗里德里希（彼得之父，保罗的祖父）
5. 安娜·彼得罗芙娜（彼得之母，保罗的祖母）
6. 克里斯蒂安·奥古斯特（叶卡捷琳娜之父，保罗的外祖父）
7. 约翰娜·伊丽莎白（叶卡捷琳娜之母，保罗的外祖母）

除了紧凑之外，它还有一些很好的性质，比如所有偶数号的人都是男性，所有奇数号的人（可能除了 1 号）都是女性。只凭后代们的性别，也能推算出某位祖先的编号。例如，彼得大帝的血缘线是保罗一世 → 彼得三世 → 安娜·彼得罗芙娜 → 彼得大帝，所以他的编号应是 $((1 \times 2) \times 2 + 1) \times 2 = 10$。

**在计算机科学中**，这种编号被广泛用于堆、线段树和其他二叉树结构的隐式（无指针）实现——只不过它存储的不是人名，而是底层数组的元素。

把这种布局应用到二分查找上是这样子的：

![注意这棵树略微不平衡（因为最后一层是连续填充的）](/en/hpc/data-structures/img/eytzinger.png)

在这种布局中查找时，我们只需从数组的第一个元素开始，然后每次迭代根据比较结果跳到 $2 k$ 或 $(2k + 1)$：

![](/en/hpc/data-structures/img/eytzinger-search.png)

你立刻就能看出它的时间局部性更好（而且实际上是理论最优的），因为越靠近树根的元素越靠近数组开头，因此越有可能直接从缓存中取到。

![](/en/hpc/data-structures/img/eytzinger-heat.png)

另一种理解方式是：我们先把所有偶数下标的元素写到新数组的末尾，再把剩下的元素中偶数下标的写到它们前面，依此类推，直到把树根放在第一个位置。

### 构建 {#construction}

要构造 Eytzinger 数组，我们可以做 $O(\log n)$ 次这种奇偶[过滤](/hpc/simd/shuffling/#permutations-and-lookup-tables)——或许这反而是最快的做法——但为了简洁，我们改为通过遍历原搜索树来构建它：

```c++
int a[n], t[n + 1]; // the original sorted array and the eytzinger array we build
//              ^ we need one element more because of one-based indexing

void eytzinger(int k = 1) {
    static int i = 0; // <- careful running it on multiple arrays
    if (k <= n) {
        eytzinger(2 * k);
        t[k] = a[i++];
        eytzinger(2 * k + 1);
    }
}
```

这个函数取当前节点编号 `k`，递归地写出查找区间中部左侧的所有元素，写出当前我们要比较的元素，然后再递归写出右侧的所有元素。它看起来有点复杂，但要说服自己它是正确的，你只需要三个观察：

- 它恰好写出 `n` 个元素，因为对 `1` 到 `n` 的每个 `k`，`if` 的函数体只进入一次。
- 它写出的元素在原数组中是顺序的，因为它每次都递增 `i` 指针。
- 当我们写节点 `k` 上的元素时，它左侧的所有元素都已写完（恰好 `i` 个）。

尽管是递归的，它实际上相当快，因为所有的内存读取都是顺序的，而内存写入同一时刻只涉及 $O(\log n)$ 个不同的内存块。不过，维护这种重排无论在逻辑上还是计算上都更难：向有序数组插入一个元素只需把它的某个后缀右移一位，而 Eytzinger 数组实际上几乎需要从头重建。

注意，这个遍历及所得的重排与朴素二分查找的"树"并不完全等价：例如左子树可能比右子树大——最大可达两倍——但这无关紧要，因为两种做法的树深都是同样的 $\lceil \log_2 n \rceil$。

还要注意，Eytzinger 数组是从 1 开始编号的——这一点对后面的性能很重要。你可以在第 0 个元素里放一个"下界不存在"时希望返回的值（类似于 `std::lower_bound` 的 `a.end()`）。

### 搜索的实现 {#search-implementation}

现在我们可以只用下标来下降这个数组：从 $k=1$ 开始，需要往左走就执行 $k := 2k$，需要往右走就执行 $k := 2k + 1$。我们甚至不再需要存储和重新计算查找边界。这种简洁性也让我们得以去掉分支：

```c++
int k = 1;
while (k <= n)
    k = 2 * k + (t[k] < x);
```

唯一的问题出现在需要还原结果元素的下标时，因为 $k$ 并不直接指向它。看这个例子（对应的树已在上面列出）：

<!--

    array:  0 1 2 3 4 5 6 7 8 9                           
eytzinger:  6 3 7 1 5 8 9 0 2 4                           
1st range:  -------------------  k := 1                    
2nd range:  -------------        k := 2*k     = 2   (6 ≥ 3)
3rd range:  -------              k := 2*k     = 4   (3 ≥ 3)
4th range:      ---              k := 2*k + 1 = 9   (1 < 3)
5th range:        -              k := 2*k + 1 = 19  (2 < 3)

-->

<pre class='center-pre'>
    array:  0 1 2 3 4 5 6 7 8 9                            
eytzinger:  <u>6</u> <u>3</u> 7 <u>1</u> 5 8 9 0 <u>2</u> 4                            
1st range:  ------------?------  k := 2*k     = 2   (6 ≥ 3)
2nd range:  ------?------        k := 2*k     = 4   (3 ≥ 3)
3rd range:  --?----              k := 2*k + 1 = 9   (1 < 3)
4th range:      ?--              k := 2*k + 1 = 19  (2 < 3)
5th range:        !                                        
</pre>

<!-- do we need the last comparison? -->

这里我们在 $[0, …, 9]$ 的数组中查询 $x=3$ 的下界。我们依次与 $6$、$3$、$1$、$2$ 比较，往左、左、右、右走，最后得到 $k = 19$，它甚至不是一个合法的数组下标。

诀窍在于注意到：除非答案就是数组的最后一个元素，否则我们在某一步必然会拿 $x$ 与它比较，而当我们得知它不小于 $x$ 之后，我们会恰好往左走一次，然后一路往右直到叶子（因为我们之后只会拿 $x$ 与更小的元素比较）。因此，要还原答案，我们只需要"取消"若干次右转，然后再多取消一次。

这可以用一个优雅的方式完成：观察到右转被记录在 $k$ 的二进制表示中，表现为 1 比特，所以我们只需要找出二进制表示末尾连续 1 的个数，然后把 $k$ 右移恰好这个数加一比特。为此，我们可以先把数取反（`~k`）再调用"找第一个 1"指令：

```c++
int lower_bound(int x) {
    int k = 1;
    while (k <= n)
        k = 2 * k + (t[k] < x);
    k >>= __builtin_ffs(~k);
    return t[k];
}
```

我们运行它，然后……呃，看起来并没有*那么*好：

![](/en/hpc/data-structures/img/search-eytzinger.svg)

它在较小数组上的延迟与无分支二分查找持平——这并不奇怪，因为它就只有两行代码——但它更早开始起飞。原因是 Eytzinger 二分查找得不到空间局部性的好处：我们比较的最后 3-4 个元素不再位于同一缓存行，必须分别取回。

如果你想得更深一点，可能会反驳说时间局部性的改善应该能补偿这一点。之前，一个缓存行里只有大约 $\frac{1}{16}$ 的部分被用来存放一个热元素，而现在整行都被用上了，所以有效缓存容量大了 16 倍，能够多覆盖 $\log_2 16 = 4$ 层最初的请求。

但如果再想深一层，你就会明白这不足以补偿。缓存住另外 15 个元素并非完全无用，而且硬件预取器还可能把我们请求的相邻缓存行也取回来。如果这是我们最后的请求之一，那么接下来要读的东西很可能已经在缓存里了。所以实际上，最后 6-7 次访问都可能在缓存里，而不是 3-4 次。

看起来我们干了一件彻头彻尾的蠢事，换成了这种布局，但有一个办法能让它物有所值。

### 预取 {#prefetching}

为了隐藏内存延迟，我们可以使用软件预取，类似于无分支二分查找中的做法。但与其对左右两个子节点分别发出两条预取指令，我们可以注意到它们在 Eytzinger 数组中是相邻的：一个下标是 $2 k$，另一个是 $(2k + 1)$，所以它们很可能在同一缓存行上，一条指令就够了。

这个观察还可以延伸到节点 $k$ 的孙节点——它们也是顺序存储的：

```
2 * 2 * k           = 4 * k
2 * 2 * k + 1       = 4 * k + 1
2 * (2 * k + 1)     = 4 * k + 2
2 * (2 * k + 1) + 1 = 4 * k + 3
```

<!--

\begin{aligned}
   2 \cdot 2 \cdot k       &= 4 \cdot k
\\ 2 \cdot 2 \cdot k + 1   &= 4 \cdot k + 1
\\ 2 \cdot (2 \cdot k) + 1 &= 4 \cdot k + 2
\\ 2 \cdot (2 \cdot k + 1) + 1 &= 4 \cdot k + 3
\end{aligned}

-->

它们的缓存行同样可以用一条指令取回。有意思……那如果我们继续下去，不取直接孩子，而是把能塞进一个缓存行的后代尽可能多地一次取走呢？那就是 $\frac{64}{4} = 16$ 个元素，我们的曾曾孙，下标从 $16k$ 到 $(16k + 15)$。

现在，如果我们只预取这 16 个元素中的一个，很可能只能拿到其中一部分而不是全部，因为它们可能跨越缓存行边界。我们可以预取第一个*和*最后一个元素，但要想只用一次内存请求就搞定，需要注意到第一个元素的下标 $16k$ 能被 $16$ 整除，所以它的内存地址等于数组基地址加上某个能被 $16 \cdot 4 = 64$（缓存行大小）整除的数。如果数组本身从缓存行边界开始，那么这 $16$ 个曾曾孙元素就保证位于同一个缓存行上，而这正是我们需要的。

因此，我们只需要把数组[对齐](/hpc/cpu-cache/alignment)：

```c++
t = (int*) std::aligned_alloc(64, 4 * (n + 1));
```

然后每次迭代预取下标为 $16 k$ 的元素：

```c++
int lower_bound(int x) {
    int k = 1;
    while (k <= n) {
        __builtin_prefetch(t + k * 16);
        k = 2 * k + (t[k] < x);
    }
    k >>= __builtin_ffs(~k);
    return t[k];
}
```

大数组上的性能比上一版提升 3-4 倍，比 `std::lower_bound` 提升约 2 倍。只多两行代码，不错了：

![](/en/hpc/data-structures/img/search-eytzinger-prefetch.svg)

本质上，我们在这里做的是通过向前预取四步、重叠多个内存请求来隐藏延迟。理论上，如果计算开销可以忽略，我们应该能得到约 4 倍加速，但现实中得到的加速要温和一些。

我们也可以试着预取得比四步更远，而且甚至不必为此多用一条预取指令：可以只请求第一个缓存行，靠硬件去预取它的邻居。这个技巧能否提升实际性能取决于硬件：

```c++
__builtin_prefetch(t + k * 32);
```

另外要注意，最后几次预取请求其实并不需要，而且实际上它们甚至可能落在程序分配的内存区域之外。在大多数现代 CPU 上，无效的预取指令会被转化为空操作，所以这不是问题，但在某些平台上这可能导致变慢，所以比如把最后约 4 次迭代从循环里拆出来单独处理、试图去掉它们，可能是值得的。

这种预取技术让我们能提前读四个元素，但它并非真正免费——我们实际上是用额外的内存[带宽](/hpc/cpu-cache/bandwidth)换取了更低的[延迟](/hpc/cpu-cache/latency)。如果你同时在多个硬件线程上运行多个实例，或者后台有任何其他访存密集型的计算，它会显著[影响](/hpc/cpu-cache/sharing)基准测试性能。

但我们还能做得更好。与其每次取四条缓存行，我们可以取*少*四倍的缓存行。[下一节](../s-tree)将探讨这个方法。

<!--

But that was a small detour. Let's get back to optimizing for *large* arrays.

[Part 2](https://algorithmica.org/en/b-tree) explores efficient implementation of implicit static B-trees in bandwidth-constrained environment.

-->

### 去除最后一个分支 {#removing-the-last-branch}

最后一点收尾工作：你注意到 Eytzinger 查找曲线的颠簸了吗？这不是随机噪声——放大看看：

![](/en/hpc/data-structures/img/search-eytzinger-small.svg)

对于形如 $1.5 \cdot 2^k$ 的数组规模，延迟要高出约 10ns。这些是循环自身的分支预测失败——准确说是最后一次分支。当数组规模离 2 的幂较远时，循环会执行 $\lfloor \log_2 n \rfloor$ 次还是 $\lfloor \log_2 n \rfloor + 1$ 次迭代很难预测，所以我们有 50% 的概率恰好遭受一次分支预测失败。

一种解决办法是用无穷大把数组填充到最接近的 2 的幂，但这浪费内存。作为替代，我们干脆去掉那最后一个分支：总是执行恒定的最少迭代次数，然后用谓词化可选地与某个哑元素多做最后一次比较——保证它小于 $x$，从而这次比较会被取消：

```c++
t[0] = -1; // an element that is less than x
iters = std::__lg(n + 1);

int lower_bound(int x) {
    int k = 1;

    for (int i = 0; i < iters; i++)
        k = 2 * k + (t[k] < x);

    int *loc = (k <= n ? t + k : t);
    k = 2 * k + (*loc < x);

    k >>= __builtin_ffs(~k);

    return t[k];
}
```

曲线现在变平滑了，在小数组上只比无分支二分查找慢几个周期：

![](/en/hpc/data-structures/img/search-eytzinger-branchless.svg)

有趣的是，现在 GCC 没能把分支替换成 `cmov`，而 Clang 做到了。一比一。

### 附录：随机二分查找 {#appendix-random-binary-search}

顺便说一句，求出随机二分查找精确的期望比较次数本身就是一道相当有趣的数学题。建议先自己试试！

*算法性地*计算它的方法是动态规划。记 $f_n$ 为在长度为 $n$ 的查找区间中查找随机下界的期望比较次数，它就能由上一个 $f_n$ 出发、考虑所有 $(n - 1)$ 种切分方式来算出：

$$
f_n = \sum_{l = 1}^{n - 1} \frac{1}{n-1} \cdot \left( f_l \cdot \frac{l}{n} + f_{n - l} \cdot \frac{n - l}{n} \right) + 1
$$

直接套用这个公式得到一个 $O(n^2)$ 的算法，但我们可以像这样重排求和式来优化它：

$$
\begin{aligned}
f_n &= \sum_{i = 1}^{n - 1} \frac{ f_i \cdot i + f_{n - i} \cdot (n - i) }{ n \cdot (n - 1) } + 1
\\  &= \frac{2}{n \cdot (n - 1)} \cdot \sum_{i = 1}^{n - 1} f_i \cdot i + 1
\end{aligned}
$$

要更新 $f_n$，我们只需要算出 $f_i \cdot i$ 对所有 $i < n$ 的总和。为此，引入两个新变量：

$$
g_n = f_n \cdot n,
\;\;
s_n = \sum_{i=1}^{n} g_n
$$

现在它们可以依次计算如下：

$$
\begin{aligned}
g_n &= f_n \cdot n
     = \frac{2}{n-1} \cdot \sum_{i = 1}^{n - 1} g_i + n
     = \frac{2}{n - 1} \cdot s_{n - 1} + n
\\ s_n &= s_{n - 1} + g_n
\end{aligned}
$$

这样我们得到一个 $O(n)$ 的算法，但还可以做得更好。把 $g_n$ 代入 $s_n$ 的更新公式：

$$
\begin{aligned}
s_n &= s_{n - 1} + \frac{2}{n - 1} \cdot s_{n - 1} + n
\\  &= (1 + \frac{2}{n - 1}) \cdot s_{n - 1} + n
\\  &= \frac{n + 1}{n - 1} \cdot s_{n - 1} + n
\end{aligned}
$$

<!-- todo: can we simplify the proof and get rid of r? -->

下一个技巧更复杂一点。我们这样定义 $r_n$：

$$
\begin{aligned}
r_n &= \frac{s_n}{n}
\\  &= \frac{1}{n} \cdot \left(\frac{n + 1}{n - 1} \cdot s_{n - 1} + n\right)
\\  &= \frac{n + 1}{n} \cdot \frac{s_{n - 1}}{n - 1} + 1
\\  &= \left(1 + \frac{1}{n}\right) \cdot r_{n - 1} + 1
\end{aligned}
$$

可以把它代回之前得到的 $g_n$ 公式：

$$
g_n = \frac{2}{n - 1} \cdot s_{n - 1} + n = 2 \cdot r_{n - 1} + n
$$

回想 $g_n = f_n \cdot n$，我们就能把 $r_{n - 1}$ 用 $f_n$ 表出：

$$
f_n \cdot n = 2 \cdot r_{n - 1} + n
\implies
r_{n - 1} = \frac{(f_n - 1) \cdot n}{2}
$$

最后一步。我们刚刚把 $r_n$ 用 $r_{n - 1}$ 表出，又把 $r_{n - 1}$ 用 $f_n$ 表出。这让我们能把 $f_{n + 1}$ 用 $f_n$ 表出：

$$
\begin{aligned}
&&\quad r_n &= \left(1 + \frac{1}{n}\right) \cdot r_{n - 1} + 1
\\ &\Rightarrow & \frac{(f_{n + 1} - 1) \cdot (n + 1)}{2} &= \left(1 + \frac{1}{n}\right) \cdot \frac{(f_n - 1) \cdot n}{2} + 1
\\ &&&= \frac{n + 1}{2} \cdot (f_n - 1) + 1
\\ &\Rightarrow & (f_{n + 1} - 1) &= (f_{n} - 1) + \frac{2}{n + 1}
\\ &\Rightarrow &f_{n + 1} &= f_{n} + \frac{2}{n + 1}
\\ &\Rightarrow &f_{n} &= f_{n - 1} + \frac{2}{n}
\\ &\Rightarrow &f_{n} &= \sum_{k = 2}^{n} \frac{2}{k}
\end{aligned}
$$

最后的表达式是[调和级数](https://en.wikipedia.org/wiki/Harmonic_series_(mathematics))的两倍，而众所周知它近似于 $\ln n$（当 $n \to \infty$ 时）。因此，随机二分查找比普通版本多执行 $\frac{2 \ln n}{\log_2 n} = 2 \ln 2 \approx 1.386$ 倍的比较。

### 致谢 {#acknowledgements}

本文大致基于 Paul-Virak Khuong 和 Pat Morin 的 "[Array Layouts for Comparison-Based Searching](https://arxiv.org/pdf/1509.05053.pdf)"。这篇论文长达 46 页，更详细地讨论了这些方法以及许多其他（不那么成功的）方法。我强烈推荐也去读一读——这是我最喜欢的性能工程论文之一。

感谢 Marshall Lochbaum 为随机二分查找[提供](https://github.com/algorithmica-org/algorithmica/issues/57)了证明。我自己是绝对证不出来的。

另外，这些可爱的布局可视化图是很久以前我从某个博客上偷来的，但我不记得那个博客的名字和图片的许可证了，反向图片搜索也找不到它们了。如果你不告我，谢谢你了，不知名的恩人！
