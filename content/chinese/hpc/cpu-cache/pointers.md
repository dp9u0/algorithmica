---
title: 指针的替代方案
weight: 10
draft: true
---

在[指针追逐基准测试](../latency)中，为了简单起见，我们用的不是真正的指针，而是相对于基地址的整数下标：

```c++
for (int i = 0; i < N; i++)
    k = q[k];
```

x86 上的[内存寻址运算符](/hpc/architecture/assembly#addressing-modes)与地址计算是融合的，所以 `k = q[k]` 这一行折叠成一条简短的指令，还在底层顺带完成了乘 4 和加法：

```nasm
mov rax, DWORD PTR q[0+rax*4]
```

虽然是完全融合的，这些额外的计算还是给内存操作添了一点延迟。L1 取数的延迟是 4 或 5 个周期——后者是我们需要执行复杂地址计算的情形。因此，排列基准测试测得每次跳转 3ns 即 6 个周期：读和地址计算 4+1，再加把结果挪到正确寄存器的 1 个。

### 指针 {#pointers}

如果把"假指针"——下标——换成真正的指针，我们可以让基准测试略微加快。

让"指向指针的指针的指针……"这类结构跑起来有一些语法上的麻烦，所以我们改为定义一个只包含指向自身类型的指针的结构体——大多数指针追逐本来就是这么工作的：

```cpp
struct node { node* ptr; };
```

现在我们随机地用指针填充数组，然后改为追逐它们：

```cpp
node* k = q + p[N - 1];

for (int i = 0; i < N; i++)
    k = k->ptr = q + p[i];

for (int i = 0; i < N; i++)
    k = k->ptr;
```

这段代码对放得进 L1 缓存的数组跑到了 2ns / 4 周期。为什么不是 4+1=5？因为 Zen 2 [有一个有趣的特性](https://www.agner.org/forum/viewtopic.php?t=41)，允许对刚刚按地址访问过的数据做零延迟复用，所以这里的"挪动"是透明的，总共省下两个周期。

遗憾的是，它在 64 位系统上有个问题：指针变成两倍大，与使用 32 位下标相比，数组会快得多地溢出缓存。延迟-规模图像左移了一个 2 的幂——正如它应该的那样：

![](/en/hpc/cpu-cache/img/permutation-p64.svg)

切换到 32 位模式可以缓解这个问题：

![](/en/hpc/cpu-cache/img/permutation-p32.svg)

要让它在本地跑起来，你得[费一番功夫](https://askubuntu.com/questions/91909/trouble-compiling-a-32-bit-binary-on-a-64-bit-machine)弄到 32 位库，但除此之外应该不会有什么问题——除非你需要与 64 位软件互操作，或者要访问超过 4G 的 RAM

### 位域 {#bit-fields}

在较大的问题规模上，性能瓶颈在内存而不是 CPU，这让我们可以尝试更奇怪的东西：用少于 4 字节来存放下标。这可以用[位域](../alignment#bit-fields)做到：

```cpp
struct __attribute__ ((packed)) node { int idx : 24; };
```

除了定义位域的结构体，你不需要做任何别的事——编译器自己会处理这个 3 字节整数：

```cpp
int k = p[N - 1];

for (int i = 0; i < N; i++) {
    k = q[k].idx = p[i];

for (int i = 0; i < N; i++) {
    k = q[k].idx;
```

这段代码在 L1 缓存上测得 6.5ns。还有改进空间，因为编译器默认选择的转换过程不是最优的。我们可以手动加载 4 字节整数再自己截断（还需要给 `q` 数组多加一个元素，确保那多出来的一个字节是我们自己的）：

```cpp
k = *((int*) (q + k));
k &= ((1<<24) - 1);
```

现在它跑 4ns，产生的图像如下：

![](/en/hpc/cpu-cache/img/permutation-bf-custom.svg)

如果放得足够近看（[这张图是 svg](/en/hpc/cpu-cache/img/permutation-bf-custom.svg)），你会看到在很小的数组上指针获胜；从 L2-L3 缓存边界附近开始，我们的自定义位域反超；而对非常大的数组则无所谓，因为我们反正命中不了缓存。

这不是能给你 5 倍提升的那种优化，但当其他所有资源都已榨尽时，它仍然值得一试。
