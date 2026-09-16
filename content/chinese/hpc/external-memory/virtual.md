---
title: 虚拟内存
weight: 2
draft: true
---

早期的操作系统给予每个进程随意读写任何内存区域的自由，包括分配给其他进程的区域。这种做法虽然保持了简单，也带来了一些问题：

- 如果某个进程有 bug，或者干脆就是恶意的呢？如何在阻止它修改分配给其他进程的内存的同时，仍然保留通过内存进行进程间通信的可能？
- 内存碎片化怎么处理？假设我们有 4MB 内存：进程 A 为自己分配了开头的 1MB，接着进程 B 申请了接下来的 2MB，然后 A 终止并释放了它的内存；此时进程 C 来了，请求一块连续的 2MB 区域——却得不到，因为只剩下两块互不相连的 1MB。重启进程 B，或者想个办法把它停下来、把它全部的数据和指针都挪动 1MB，看起来都不是什么好办法。
- 如何访问非 RAM 类型的内存？插上一个闪存盘，要怎么从里面读出某个特定的文件？

这些问题对于 GPU 这类专用计算机系统并不那么关键——在那上面你通常一次只解决一个任务，并且对计算过程有完全的掌控；但对现代多任务操作系统来说，它们绝对至关重要——而操作系统用一种叫做*虚拟内存*（virtual memory）的技术解决了所有这些问题。

### 内存分页 {#memory-paging}

虚拟内存给每个进程一种它完全掌控着一整段连续内存区域的印象，而这段区域在现实中可能映射到物理内存的多个较小块上——这里的物理内存既包括主存（RAM），也包括外部存储器（HDD、SSD）。

![](/en/hpc/external-memory/img/virtual-memory.jpg)

为实现这一点，内存地址空间被划分成*页*（page，通常大小为 4KB），页是程序向操作系统申请内存的基本单位。内存系统维护着一种特殊的硬件数据结构，叫做*页表*（page table），其中保存着虚拟页地址到物理页地址的映射。当进程使用它的虚拟内存地址访问数据时，内存系统会算出它所在的页号（把地址右移 $12$ 位，前提是页大小为 $4096=2^{12}$），在页表中查出该页的物理地址，再把读或写请求转发到数据实际存放的位置。

由于地址转换要对每个内存请求都做一遍，而内存页本身的数量又可能很大（例如 16G RAM / 4K 页大小 = 4M 页），地址转换本身就成了一个棘手的问题。加速它的一种办法，是为页表本身配备一种专用缓存，称为*转译后备缓冲区*（translation lookaside buffer，TLB）；另一种办法是[增大页的大小](/hpc/cpu-cache/paging)，以降低粒度为代价，换取内存页总数的减少。

<!--

When it doesn't hit, you essentially pay double the cost of a memory access. For this reason, some operating systems have support for larger pages (~2MB).

For performance, the data structures are implemented in hardware, embedded in the CPU.
Each overlooking each memory access.
Modern operating systems give every process the impression that it is working with large, contiguous section of memory, called *virtual memory*. Physically, the memory allocated to each process may be dispersed across different areas of physical memory, or may have been moved to another type of storage such as SSD or HDD.

-->

### 映射外部存储器 {#mapping-external-memory}

虚拟内存机制还让相当透明地使用外部存储器成为可能。现代操作系统支持[内存映射](https://en.wikipedia.org/wiki/Mmap)，它让你可以打开一个文件，把它的内容当作就在主存中一样使用：

```c++
// open a file containing 1024 random integers for reading and writing
int fd = open("input.bin", O_RDWR);
// map it into memory      size  allow reads and writes  write changes back to the file
int* data = (int*) mmap(0, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
// sort it like if it was a normal integer array
std::sort(data, data + 1024);
// changes are eventually propagated to the file
```

这里我们映射的是一个 4K 的文件，它整个落在单独一个内存页上；但当我们打开更大的文件时，对它的读取会等到我们请求某个特定页时才惰性地进行，写入则会被缓冲起来，由操作系统择机提交到文件系统（通常是在程序终止时，或系统耗尽 RAM 时）。

有一种技术与内存映射工作原理相同、意图却正好相反，那就是*交换文件*（swap file）：当真正的 RAM 不够用时，它让操作系统自动把 SSD 或 HDD 的一部分当作主存的扩展来用。这让耗尽内存的系统不至于崩溃，只是体验一场可怕的减速。

主存与外部存储器这种无缝的整合，实质上是把 RAM 变成了外部存储器的"L4 缓存"——从算法设计的角度看，这是思考二者关系的一种便捷方式。
