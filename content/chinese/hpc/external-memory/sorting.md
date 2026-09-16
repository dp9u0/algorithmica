---
title: 外部排序
weight: 4
draft: true
---

现在，让我们试着为新的[外部存储器模型](../model)设计一些真正有用的算法。本节的目标是逐步构建出更复杂的东西，并最终抵达*外部排序*及其有趣的应用。

这个算法将基于标准的归并排序，所以我们先来推导它的主要原语。

### 归并 {#merge}

**问题。**给定有序数组 $a$ 和 $b$，长度分别为 $N$ 和 $M$，产出一个有序数组 $c$，长度为 $N + M$，包含它们的全部元素。

归并有序数组的标准双指针技巧长这个样子：

```cpp
void merge(int *a, int *b, int *c, int n, int m) {
    int i = 0, j = 0;
    for (int k = 0; k < n + m; k++) {
        if (i < n && (j == m || a[i] < b[j]))
            c[k] = a[i++];
        else
            c[k] = b[j++];
    }
}
```

从内存操作的角度看，我们只是线性地读入 $a$ 和 $b$ 的全部元素、线性地写出 $c$ 的全部元素。由于这些读写可以被缓冲，它耗费 $SCAN(N+M)$ 次 I/O 操作。

到目前为止的例子都很简单，对它们的分析与 RAM 模型差别不大，只是要把最终答案除以块大小 $B$。但下面这个情形就不是这样了。

**$k$ 路归并。**考虑该算法的一个变体：我们要归并的不是两个数组，而是 $k$ 个总计大小为 $N$ 的数组——同样地，盯着 $k$ 个当前值，选出其中的最小者写入 $c$，并把其中一个迭代器前移一步。

在标准 RAM 模型中，渐近复杂度会乘上 $k$，因为每填一个新元素都要做 $O(k)$ 次比较。但在外部存储器模型中，由于我们在内存里做的任何事情都不花代价，只要 $(k+1)$ 个完整的块能同时放进内存，渐近复杂度就不会改变，也就是当 $k = O(\frac{M}{B})$ 时。

还记得我们引入计算模型时的[$M \gg B$ 假设](../model)吗？若有 $M \geq B^{1+ε}$（其中 $\epsilon > 0$），那么任何次多项式（sub-polynomial）数量的块都放得进内存，自然包括 $O(\frac{M}{B})$ 个。这个条件称为*高缓存假设*（tall cache assumption），许多其他外部存储器算法通常也要求它。

### 归并排序 {#merge-sorting}

标准归并排序算法的"常规"复杂度是 $O(N \log_2 N)$：在其 $O(\log_2 N)$ 个"层"的每一层，算法都需要把全部 $N$ 个元素整个过一遍，并以线性时间归并它们。

在外部存储器模型中，当我们读入一个大小为 $M$ 的块时，可以把它的元素"免费"排序，因为它们已经在内存里了。这样，我们可以把数组拆成 $O(\frac{N}{M})$ 个由连续元素组成的块，把各自排序作为基础步骤，然后再归并它们。

![](/en/hpc/external-memory/img/k-way.png)

这实际上意味着，就 I/O 操作而言，归并排序的前 $O(\log M)$ 层是免费的，只有 $O(\log_2 \frac{N}{M})$ 个非零代价的层，每层总共可以 $O(\frac{N}{B})$ IOPS 完成。于是总的 I/O 复杂度为

$$
O\left(\frac{N}{B} \log_2 \frac{N}{M}\right)
$$

这已经相当快了。如果我们有 1GB 内存和 10GB 数据，这实质上意味着，排序只需付出比单纯读入数据略多于 3 倍的努力。有趣的是，我们还能做得更好。

### $k$ 路归并排序 {#k-way-mergesort}

半页之前我们已经学到，在外部存储器模型中，归并 $k$ 个数组与归并两个数组一样轻松——代价只是把它们读进来。为什么不在排序里也用上这个事实呢？

我们还是像之前那样，在内存中对每个大小为 $M$ 的块排序；但在每个归并阶段，我们不再只把有序的块两两配对，而是在一次 $k$ 路归并中取内存装得下的尽可能多的块。这样，归并树的高度将大幅降低，而每一层仍能以 $O(\frac{N}{B})$ IOPS 完成。

一次能归并多少个有序数组？恰好 $k = \frac{M}{B}$ 个，因为每个数组都需要占一个块的内存。由于总层数将减少到 $\log_{\frac{M}{B}} \frac{N}{M}$，总复杂度也随之降为

$$
SORT(N) \stackrel{\text{def}}{=} O\left(\frac{N}{B} \log_{\frac{M}{B}} \frac{N}{M} \right)
$$

注意，在我们的例子里，有 10GB 数据、1GB 内存，而对 HDD 来说块大小约为 1MB。于是 $\frac{M}{B} = 1000$，$\frac{N}{M} = 10$，对数值小于 1（具体而言，$\log_{1000} 10 = \frac{1}{3}$）。当然，我们不可能比读入数组还快地完成排序，所以这项分析适用于数据集非常大、内存非常小和/或块非常大的情形——如今在现实中很少发生。

### 实际实现 {#practical-implementation}

在更现实的约束下，我们可以不用 $\log_{\frac{M}{B}} \frac{N}{M}$ 层，而只用两层：一层按 $M$ 个元素的块排序数据，另一层把它们全部一次性归并。这样，从 I/O 操作的角度看，我们只是把数据集整个过两遍。以 1GB 内存和 1MB 块大小计，这种方式可以排序高达 1TB 的数组。

下面是第一阶段在 C++ 中的样子。这个程序打开一个多 GB 的、存放无序整数的二进制文件，按 256MB 的块读入，在内存中排序，然后把它们写回名为 `part-000.bin`、`part-001.bin`、`part-002.bin` 等等的文件：

```cpp
const int B = (1<<20) / 4; // 1 MB blocks of integers
const int M = (1<<28) / 4; // available memory

FILE *input = fopen("input.bin", "rb");
std::vector<FILE*> parts;

while (true) {
    static int part[M]; // better delete it right after
    int n = fread(part, 4, M, input);

    if (n == 0)
        break;
    
    // sort a block in-memory
    std::sort(part, part + n);
    
    char fpart[sizeof "part-999.bin"];
    sprintf(fpart, "part-%03d.bin", parts.size());

    printf("Writing %d elements into %s...\n", n, fpart);

    FILE *file = fopen(fpart, "wb");
    fwrite(part, 4, n, file);
    fclose(file);
    
    file = fopen(fpart, "rb");
    parts.push_back(file);
}

fclose(input);
```

剩下的就是把它们归并到一起了。现代 HDD 的带宽可以相当高，而待归并的部分可能很多，所以这一阶段的关注点并不只有 I/O 效率：归并 $k$ 个数组时，我们还需要一种比用 $O(k)$ 次比较找最小值更快的办法。我们可以做到以 $O(\log k)$ 的时间处理每个元素——只要为这 $k$ 个元素维护一个最小堆，其方式与堆排序几乎一模一样。

下面是实现。首先，我们需要一个堆（C++ 的 `priority_queue`）：

```c++
struct Pointer {
    int key, part; // the element itself and the number of its part

    bool operator<(const Pointer& other) const {
        return key > other.key; // std::priority_queue is a max-heap by default
    }
};

std::priority_queue<Pointer> q;
```

然后，我们需要分配并填充缓冲区：

```c++
const int nparts = parts.size();

auto buffers = new int[nparts][B]; // buffers for each part
int *l = new int[nparts],          // # of already processed buffer elements
    *r = new int[nparts];          // buffer size (in case it isn't full)

// now we add fill the buffer for each part and add their elements to the heap
for (int part = 0; part < nparts; part++) {
    l[part] = 1; // if the element is in the heap, we also consider it "processed"
    r[part] = fread(buffers[part], 4, B, parts[part]);
    q.push({buffers[part][0], part});
}
```

现在，我们只需要从堆中把元素弹出到结果文件里，直到堆为空，并小心地成批读写元素：

```cpp
FILE *output = fopen("output.bin", "w");

int outbuffer[B]; // the output buffer
int buffered = 0; // number of elements in it

while (!q.empty()) {
    auto [key, part] = q.top();
    q.pop();

    // write the minimum to the output buffer
    outbuffer[buffered++] = key;
    // check if it needs to be committed to the file
    if (buffered == B) {
        fwrite(outbuffer, 4, B, output);
        buffered = 0;
    }

    // fetch a new block of that part if needed
    if (l[part] == r[part]) {
        r[part] = fread(buffers[part], 4, B, parts[part]);
        l[part] = 0;
    }

    // read a new element from that part unless we've already processed all of it
    if (l[part] < r[part]) {
        q.push({buffers[part][l[part]], part});
        l[part]++;
    }
}

// write what's left of the output buffer
fwrite(outbuffer, 4, buffered, output);

//clean up
delete[] buffers;
for (FILE *file : parts)
    fclose(file);
fclose(output);
```

这个实现既谈不上特别高效，看上去也不怎么安全（嗯，它基本上就是纯 C），但作为如何使用底层内存 API 的教学示例，它是不错的。

### 连接 {#joining}

排序主要不是拿来单独使用的，而是作为其他操作的中间步骤。外部排序的一个重要现实用例是连接（即 SQL 里的 join），用于数据库和其他数据处理应用。

**问题。**给定两个元组列表 $(x_i, a_{x_i})$ 与 $(y_i, b_{y_i})$，输出一个列表 $(k, a_{x_k}, b_{y_k})$，使得 $x_k = y_k$。

最优解是先对两个列表排序，然后用标准的双指针技巧归并它们。这里的 I/O 复杂度与排序相同；而如果数组已经有序，则只需 $O(\frac{N}{B})$。这就是为什么大多数数据处理应用（数据库、MapReduce 系统）喜欢让它们的表至少保持部分有序。

**其他方法。**注意，以上分析只在外部存储器的设定下适用——也就是说，当你没有足够的内存把整个数据集读进来时。在现实世界中，别的方法可能更快。

其中最简单的恐怕是*哈希连接*（hash join），它大致是这样：

```python
def join(a, b):
    d = dict(a)
    for x, y in b:
        if x in d:
            yield d[x]
```

在外部存储器中，用哈希表连接两个列表是不可行的，因为那将涉及 $O(M)$ 次块读取，而每次只用到其中一个元素。

> **译者注**：按本章记号，`M` 是内部存储器的大小；这里的块读取次数应取决于数据规模（约 `O(N)` 量级），原文的 `O(M)` 疑为笔误。"不可行"这一结论不受影响。

另一种方法是使用替代性的排序算法，例如基数排序。特别地，只要有足够的内存为所有可能的键维护缓冲区，基数排序可以用 $O(\frac{N}{B} \cdot w)$ 次块读取完成；在键较小而数据集较大的情形下，它可能更快。
