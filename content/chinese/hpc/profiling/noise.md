---
title: 获得准确的结果
weight: 10
draft: true
---

两个库算法实现各自维护着一套基准测试代码、又各自声称比对方快，这种局面并不罕见。这让所有相关的人都困惑，尤其是用户——他们总得想办法在两者之间做个选择。

这类情形通常并非出自作者的造假行为；他们对"更快"有着不同的定义，而事实上，只定义并使用单一的性能指标往往本身就是很有问题的。

### 测对东西

有很多因素会给基准测试引入偏差。

**数据集不同。** 有很多算法，其性能或多或少依赖于数据集的分布。要想定义例如什么是最快的排序、最短路或二分查找算法，你必须固定算法运行时所用的数据集。

这有时甚至适用于只处理单条输入的算法。例如，给 GCD 实现喂连续的数不是个好主意，因为这会让分支变得非常可预测：

```c++
// don't do this
int checksum = 0;

for (int a = 0; a < 1000; a++)
    for (int b = 0; b < 1000; b++)
        checksum ^= gcd(a, b);
```

然而，如果把同样的这些数随机打乱采样，分支预测就变得困难得多，基准测试也就更耗时——尽管处理的还是同一批输入，只是顺序变了：

```c++
int a[1000], b[1000];

for (int i = 0; i < 1000; i++)
    a[i] = rand() % 1000, b[i] = rand() % 1000;

int checksum = 0;

for (int t = 0; t < 1000; t++)
    for (int i = 0; i < 1000; i++)
        checksum += gcd(a[i], b[i]);
```


多数情况下，最合乎逻辑的选择是对数据做均匀随机采样，但许多真实应用的分布远非均匀，所以你不能只选定一种。总的来说，好的基准测试应该贴合具体应用，并使用尽可能代表你真实使用场景的数据集。

<!--

People report things they like to report and leave out the things they don't.

To put numbers in perspective, use statistics like "ns per query" or "cycles per byte" instead of wall clock whenever it is applicable. When you start to approach very high levels of performance, it makes sense to calculate what the theoretically maximal performance is and start thinking about your algorithm performance as a fraction of it.

Similar to how Americans report pre-tax salary, Americans use non-PPP-adjusted stats, attention-seeking startups report revenue instead of profit, performance engineers report the best version of benchmark if not stated otherwise.


This happens especially often for data structures, and in general for algorithms whose performance somehow depends on the dataset distribution.

-->

**多个目标。** 有些算法设计问题有不止一个关键目标。例如哈希表，除了高度依赖键的分布之外，还需要小心平衡：

- 内存用量，
- 添加查询的延迟，
- 正向成员查询的延迟，
- 负向成员查询的延迟。

要在多种哈希表实现之间做选择，唯一的办法是把多个变体实际放进应用里试。

**延迟 vs 吞吐量。** 人们经常忽视的另一个方面是：即便对单次查询而言，执行时间的定义也不止一种。

当你写下这样的代码：

```c++
for (int i = 0; i < N; i++)
    q[i] = rand();

int checksum = 0;

for (int i = 0; i < N; i++)
    checksum ^= lower_bound(q[i]);
```

然后对整段计时、再除以迭代次数时，你实际测量的是查询的*吞吐量*——单位时间内能处理多少次操作。这通常少于单独处理一次操作实际所需的时间，因为各次调用之间存在交错。

要测量真正的*延迟*，需要在各次调用之间引入依赖：

```c++
for (int i = 0; i < N; i++)
    checksum ^= lower_bound(checksum ^ q[i]);
```

对于可能出现流水线停顿的算法，这往往影响最大，比如比较有分支与无分支算法孰优孰劣时。

**冷缓存。** 偏差的另一个来源是*冷缓存*（cold cache）效应：内存读取在起初会更慢，因为所需的数据还不在缓存里。

解决办法是在开始测量前先做一次*预热运行*（warm-up run）：

```c++
// warm-up run

volatile checksum = 0;

for (int i = 0; i < N; i++)
    checksum ^= lower_bound(q[i]);


// actual run

clock_t start = clock();
checksum = 0;

for (int i = 0; i < N; i++)
    checksum ^= lower_bound(q[i]);
```

如果验证答案比单纯算个校验和更复杂，把预热运行与答案验证合在一起做有时也更方便。

**过度优化。** 有时基准测试干脆就是错的，因为编译器直接把被测代码优化没了。为了不让编译器偷工减料，你需要加上校验和，并把它们打印到某处，或者加上 `volatile` 限定符——它还能顺带阻止循环迭代之间的一切交错。

对于只写数据的算法，可以用 `__sync_synchronize()` 内建函数加一道内存栅栏，防止编译器把更新累积起来。

### 降低噪声

<!--

https://github.com/sosy-lab/benchexec

-->

我们前面描述的问题会给测量带来*偏差*（bias）：它们会稳定地让一个算法压过另一个。基准测试还有另外一类问题，它们造成的是不可预测的偏斜或纯粹随机的噪声，从而增大*方差*（variance）。

这类问题源自副作用和某种外部噪声，主要是吵闹的邻居进程和 CPU 频率调节：

- 如果被测的是计算受限型算法，用 `perf stat` 以周期为单位测性能：这样它就与时钟频率无关了，而频率波动通常是噪声的主要来源。
- 否则，把核心频率设成你预期的值，并确保没有东西干扰它。在 Linux 上可以用 `cpupower`（例如 `sudo cpupower frequency-set -g powersave` 设为最低频率，或 `sudo cpupower frequency-set -g ondemand` 启用睿频）。我用的是一个[顺手的 GNOME shell 扩展](https://extensions.gnome.org/extension/1082/cpufreq/)，上面有个专门的按钮做这件事。
- 如果条件允许，关掉超线程，把任务绑到特定的核心上。确保系统上没有别的任务在跑，断开网络，并且尽量别乱动鼠标。

噪声和偏差不可能完全消除。就连程序的名字都能影响它的速度：可执行文件的名字会进某个环境变量，环境变量会落到调用栈上，于是名字的长短会影响栈对齐，进而可能因为跨越缓存行或内存页边界而拖慢数据访问。

在指导优化时，尤其是把结果报告给别人时，把噪声考虑进去很重要。除非你预期的是 2 倍这种量级的改进，否则应把所有微基准测试都当作 A/B 测试来对待。

在笔记本上跑一个不到一秒的程序，性能出现 ±5% 的波动是完全正常的。所以，如果你想决定要不要保留一个潜在的 +1% 改进，就把它跑到统计显著为止——可以通过计算方差和 p 值来判断。

### 延伸阅读

有兴趣的读者可以看看 Dror Feitelson 汇总的这份[实验计算机科学资源列表](https://www.cs.huji.ac.il/w~feit/exp/related.html)，入门不妨从 Todd Mytkowicz 等人的"[Producing Wrong Data Without Doing Anything Obviously Wrong](http://eecs.northwestern.edu/~robby/courses/322-2013-spring/mytkowicz-wrong-data.pdf)"开始。

你也可以看看 Emery Berger 关于如何做统计学上严谨的性能评测的[这个精彩演讲](https://www.youtube.com/watch?v=r-TLSBdHe1A)。
