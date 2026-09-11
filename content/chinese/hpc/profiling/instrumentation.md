---
title: 插装
weight: 1
draft: true
---

<!-- pv in Linux, pipes -->

*插装*（instrumentation）是个把简单事情说复杂了的术语，意思就是往程序里插入计时器和其他追踪代码。最简单的例子是在类 Unix 系统里用 `time` 工具测量整个程序的执行时长。

更一般地，我们想知道的是程序的*哪些部分*需要优化。编译器和 IDE 自带一些能自动为指定函数计时的工具，但更稳妥的做法是动手 DIY，用语言提供的各种与时间交互的方法：

```cpp
clock_t start = clock();
do_something();
float seconds = float(clock() - start) / CLOCKS_PER_SEC;
printf("do_something() took %.4f", seconds);
```

这里有个细节：特别快的函数没法这样测，因为 `clock` 函数返回的时间戳精度是微秒（$10^{-6}$），而且它自身就要花上最多几百纳秒才能执行完。其他所有与时间相关的工具同样都至少只有微秒级粒度——在底层优化的世界里，这已经是永恒了。

要获得更高的精度，可以把函数放进循环里反复调用，把整个过程计时一次，再用总时间除以迭代次数：

```cpp
#include <stdio.h>
#include <time.h>

const int N = 1e6;

int main() {
    clock_t start = clock();

    for (int i = 0; i < N; i++)
        clock(); // benchmarking the clock function itself

    float duration = float(clock() - start) / CLOCKS_PER_SEC;
    printf("%.2fns per iteration\n", 1e9 * duration / N);

    return 0;
}
```

你还需要确保没有任何东西被缓存、被编译器优化掉，或受到诸如此类的副作用影响。这是个独立且高度复杂的话题，我们会在[本章末尾](../benchmarking)详细讨论。

### 事件采样

插装也可以用来收集其他类型的信息，从中可以获得关于某个具体算法性能的有用洞见。例如：

- 对于哈希函数，我们关心其输入的平均长度；
- 对于二叉树，我们在意它的大小和高度；
- 对于排序算法，我们想知道它做了多少次比较。

类似地，我们可以在代码里插入计数器来计算这些算法专属的统计量。

加计数器的缺点是引入开销，不过只要只对一小部分调用随机地进行统计，这个缺点几乎可以完全消除：

```c++
void query() {
    if (rand() % 100 == 0) {
        // update statistics
    }
    // main logic
}
```

如果采样率足够小，每次调用剩下的开销就只有随机数生成和一次条件判断。有趣的是，我们还能借助一点统计学魔法把它再优化一下。

从数学上讲，我们在这里做的事情是不断从[伯努利分布](https://en.wikipedia.org/wiki/Bernoulli_distribution)（$p$ 等于采样率）中采样，直到出现一次成功。还有另一个分布告诉我们需要多少次伯努利采样才能等到第一次成功，它叫[几何分布](https://en.wikipedia.org/wiki/Geometric_distribution)。我们可以改为从这个分布采样一次，把得到的值用作一个递减计数器：

```c++
void query() {
    static next_sample = geometric_distribution(sample_rate);
    if (next_sample--) {
        next_sample = geometric_distribution(sample_rate);
        // ...
    }
    // ...
}
```

这样我们就省去了每次调用都采样一个新随机数的需要，只在选择计算统计量时才重置计数器。

这类技巧常被大型项目里的库算法开发者使用，用来在不明显拖慢最终程序性能的前提下收集剖析数据。
