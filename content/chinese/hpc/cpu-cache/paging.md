---
title: 内存分页
weight: 12
draft: true
---

再一次[考虑](../associativity)跨步自增循环：

```cpp
const int N = (1 << 13);
int a[D * N];

for (int i = 0; i < D * N; i += D)
    a[i] += 1;
```

我们改变步长 $D$，并按比例增大数组，使总迭代次数 $N$ 保持不变。由于内存访问的总数也保持不变，对所有 $D \geq 16$，我们都应该恰好取回 $N$ 条缓存行——精确地说，是 $64 \cdot N = 2^6 \cdot 2^{13} = 2^{19}$ 字节。这不多不少正好放进 L2 缓存，与步长无关，吞吐量图像应该是平的。

这一次我们考察更大的 $D$ 值范围，一直到 1024。从 256 附近开始，图像明显不再平：

![](/en/hpc/cpu-cache/img/strides.svg)

这个反常同样源于缓存系统，尽管标准的 L1-L3 数据缓存与此毫无关系。罪魁祸首是[虚拟内存](/hpc/external-memory/virtual)，确切地说是*转译后备缓冲区*（translation lookaside buffer，TLB）——一种负责取回虚拟内存页物理地址的缓存。

在[我的 CPU](https://en.wikichip.org/wiki/amd/microarchitectures/zen_2) 上，TLB 有两级：

- L1 TLB 有 64 项，若页大小为 4K，它无需求助 L2 TLB 即可覆盖 $64 \times 4K = 512K$ 的活跃内存。
- L2 TLB 有 2048 项，无需求助页表即可覆盖 $2048 \times 4K = 8M$ 的内存。

当 $D$ 等于 256 时分配了多少内存？你猜对了：$8K \times 256 \times 4B = 8M$，恰好是 L2 TLB 能覆盖的极限。当 $D$ 超过它，一些请求开始被转到主页表，后者延迟大、吞吐量非常有限，把整个计算卡成了瓶颈。

### 改变页大小 {#changing-page-size}

8MB 的免减速内存看起来是个非常紧的限制。虽然我们无法改变硬件特性来解除它，但我们*可以*增大页的大小，从而减轻 TLB 容量受到的压力。

现代操作系统既允许我们全局设置页大小，也允许针对单次分配设置。CPU 只支持一组确定的页大小——比如我这颗可以用 4K 或 2M 的页。另一个典型的页大小是 1G——它通常只跟拥有数百 GB 内存的服务器级硬件有关。超过默认 4K 的页，在 Linux 上叫*大页*（huge pages），在 Windows 上叫*大页面*（large pages）。

在 Linux 上，有一个专门的系统文件管理大页的分配。下面是让内核在每次分配时都给你大页的方法：

```bash
$ echo always > /sys/kernel/mm/transparent_hugepage/enabled
```

像这样全局启用大页并不总是个好主意，因为它降低了内存粒度、抬高了进程内存消耗的下限——而有些环境里，进程数比空闲的兆字节数还多。所以，除了 `always` 和 `never`，那个文件里还有第三个选项：

```bash
$ cat /sys/kernel/mm/transparent_hugepage/enabled
always [madvise] never
```

`madvise` 是一个特殊的系统调用，让程序就"是否使用大页"给内核提建议，可以用来按需分配大页。如果它处于启用状态，你可以在 C++ 里这样用：

```c++
#include <sys/mman.h>

void *ptr = std::aligned_alloc(page_size, array_size);
madvise(ptr, array_size, MADV_HUGEPAGE);
```

只有当一块内存区域具有相应的对齐时，才能请求用大页来分配它。

Windows 有类似的功能。它的内存 API 把这两个函数合二为一：

```c++
#include "memoryapi.h"

void *ptr = VirtualAlloc(NULL, array_size,
                         MEM_RESERVE | MEM_COMMIT | MEM_LARGE_PAGES, PAGE_READWRITE);
```

无论哪种情况，`array_size` 都应当是 `page_size` 的倍数。

### 大页的影响 {#impact-of-huge-pages}

两种分配大页的方式都立即使曲线变平了：

![](/en/hpc/cpu-cache/img/strides-hugepages.svg)

启用大页还能把放不进 L2 缓存的数组的[延迟](../latency)改善多达 10-15%：

![](/en/hpc/cpu-cache/img/permutation-hugepages.svg)

总的来说，只要存在任何形式的稀疏读取，启用大页就是个好主意：它们通常会带来少许改善，而且（[几乎](../aos-soa)）从不损害性能。

话虽如此，能不依赖大页就别依赖，因为受硬件或计算环境的限制，大页并非总能用上。把数据访问在空间上聚拢还有[许多](../cache-lines)[其他](../prefetching)[理由](../aos-soa)，而这么做会自动解决分页问题。

<!--


virtually located, physically tagged

Actually, TLB misses may stall memory reads for the same reason. The TLB cache is called "lookaside" because the lookup can happen independently from normal data cache lookups. L1 and L2 caches on the other side are private to the core, and so they can store virtual addresses and be queried concurrently with TLB — after fetching a cache line, its tag is used to restore the physical address, which is then checked against the concurrently fetched TLB entry. This trick does not work for shared memory however, because their bandwidth is limited, and dispatching read queries there for no reason is not a good idea in general. So we can observe a similar effect in L3 and RAM reads when the page does not fit L1 TLB and L2 TLB respectively.

For sparse reads, it often makes sense to increase page size, which improves the latency.

Typical size of a page is 4KB, but it can be up to 1G or so for large databases, but enabling it by default is not a good idea as scenarios when we have a VPS with 256M or RAM and more than 256 processes are not uncommon.

Typical page sizes are 4K, 2M and 1G (e.g., allowing for 256K, 128M, 64G memory regions to be stored in a 64-entry L1 TLB respectively).


- There are other types of cache inside CPUs that are used for things other than data. The most important for us are *instruction cache* (I-cache), which is used to speed up the fetching of machine code from memory, and *translation lookaside buffer* (TLB), which is used to store physical locations of virtual memory pages, which is instrumental to the efficiency of virtual memory.

You can fetch this information for your architecture with `cpuid` command.

-->

