---
title: 吞吐量计算
weight: 4
draft: true
---

优化*延迟*与优化*吞吐量*通常是两码事：

- 优化数据结构查询、一次性的小程序或分支密集的算法时，你需要[查指令的延迟](../tables)，在脑中构建出计算的执行图，然后试着重排它，让关键路径更短。<!-- [Binary GCD](/hpc/algorithms/gcd) is a good example of that. -->
- 优化热点循环和大数据集算法时，你需要查各指令的吞吐量，数清每条指令每次迭代用了几回，找出谁是瓶颈，然后重构循环，让瓶颈指令出现得更少。

后一条建议只适用于*数据并行*的循环，即每次迭代都与上一次完全无关。若相邻迭代之间存在依赖，就可能因[数据冒险](../hazards)产生流水线停顿——下一次迭代得等上一次完成。

### 示例

来看一个简单的例子——数组求和是怎么算的：

```c++
int s = 0;

for (int i = 0; i < n; i++)
    s += a[i];
```

暂且假设：编译器没有[向量化](/hpc/simd)这个循环，[内存带宽](/hpc/cpu-cache/bandwidth)不成问题，而且循环已经[展开](/hpc/architecture/loops)，维护循环变量的额外开销为零。此时计算就变得非常简单：

```c++
int s = 0;
s += a[0];
s += a[1];
s += a[2];
s += a[3];
// ...
```

这能算多快？恰好每元素一个周期——因为每次迭代都得花一个周期用 `add` 往 `s` 里加一个值。内存读取的延迟无关紧要，因为 CPU 可以提前发起它。

但还能更快。在我的 CPU（Zen 2）上，`add` 的*吞吐量*[^throughput]是 2，也就是说理论上每周期可以执行两条。可眼下做不到：当 `s` 正被用来累加第 $i$ 个元素时，至少一个周期内它不能再去累加第 $(i+1)$ 个。

[^throughput]: 寄存器-寄存器版 `add` 的吞吐量是 4，但由于它的第二个操作数要从内存读取，瓶颈落在内存版 `mov` 的吞吐量上，Zen 2 上是 2。

解决办法是用*两个*累加器，把奇数元素和偶数元素分开加：

```c++
int s0 = 0, s1 = 0;
s0 += a[0];
s1 += a[1];
s0 += a[2];
s1 += a[3];
// ...
int s = s0 + s1;
```

现在我们的超标量 CPU 可以同时执行这两个"线程"，计算中也不复存在限制吞吐量的关键路径。

<!--

By the virtue of out-of-order execution

-->

### 一般情况

如果一条指令延迟为 $x$、吞吐量为 $y$，那要用 $x \cdot y$ 个累加器才能喂饱它。这也意味着需要 $x \cdot y$ 个逻辑寄存器来保存它们的值——这是 CPU 设计中的重要考量，它限制了高延迟指令可用的执行单元数量上限。

这项技术主要用于 [SIMD](/hpc/simd)，很少用在标量代码里。你可以把上面的代码[推广](/hpc/simd/reduction)，算求和及其他归约时比编译器还快。

一般来说，优化循环时，你真正想喂饱的只有一个或少数几个*执行端口*（execution port），循环其余部分都是围绕它们设计的。由于不同指令可能使用不同的端口组合，哪个端口会被挤爆并不总是显而易见。这种时候，[机器码分析器](/hpc/profiling/mca)对找出小段汇编循环的瓶颈非常有帮助。

<!--

Compilers don't always produce the optimal code.

This only applies to the variables that you have to preserve between iterations. You can "fire and forget" instructions that compute temporary values as much as you want.

Memory operations may have [very high latencies](/hpc/cpu-cache/latency), but you don't need hundreds or registers for them because  because they are bottlenecked for different reasons.

But they are bottlenecked for different reasons.

You still need to imaging execution graph, but now loop it around. In most cases, there is one instruction that is the bottleneck.

This is different. For single-invocation procedures you essentially want to minimize the latency on the critical data path. For stuff that gets called in a loop, you need to maximize throughput.

Bandwidth is the rate at which data can be read or stored. For the purpose of designing algorithms, a more important characteristic is the bandwidth-latency product which basically tells how many cache lines you can request while waiting for the first one without queueing up. It is around 5 or more on most systems. This is like having friends whom you can send for beers asynchronously.

In the previous version, we have an inherently sequential chain of operations in the innermost loop. We accumulate the minimum in variable v by a sequence of min operations. There is no way to start the second operation before we know the result of the first operation; there is no room for parallelism here:

The result will be clearly the same, but we are calculating the operations in a different order. In essence, we split the work in two independent parts, calculating the minimum of odd elements and the minimum of even elements, and finally combining the results. If we calculate the odd minimum v0 and even minimum v1 in an interleaved manner, as shown above, we will have more opportunities for parallelism. For example, the 1st and 2nd operation could be calculated simultaneously in parallel (or they could be executed in a pipelined fashion in the same execution unit). Once these results are available, the 3rd and 4th operation could be calculated simultaneously in parallel, etc. We could potentially obtain a speedup of a factor of 2 here, and naturally the same idea could be extended to calculating, e.g., 4 minimums in an interleaved fashion.

Instruction-level parallelism is automatic Now that we know how to reorganize calculations so that there is potential for parallelism, we will need to know how to realize the potential. For example, if we have these two operations in the C++ code, how do we tell the computer that the operations can be safely executed in parallel?

The delightful answer is that it happens completely automatically, there is nothing we need to do (and nothing we can do)!

-->
