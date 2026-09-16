---
title: 对齐与打包
weight: 8
draft: true
---

内存被划分成 64B 的[缓存行](../cache-lines)，这一事实使得操作跨越缓存行边界的数据字变得困难。当你需要取回某个基本类型（例如 32 位整数）时，你当然希望它落在单条缓存行内——一方面因为取回两条缓存行需要更多内存带宽，另一方面因为用硬件拼接结果要占用宝贵的晶体管面积。

这个方面深刻地影响着算法设计，也影响着编译器如何选择数据结构的内存布局。

### 对齐分配 {#aligned-allocation}

默认情况下，当你分配某个基本类型的数组时，可以保证所有元素的地址都是其大小的整数倍，这确保了它们只横跨单条缓存行。例如，可以保证 `int` 数组的第一个以及后续每个元素的地址都是 4 字节（`sizeof int`）的倍数。

有时候你需要保证这个最小对齐更高。例如，许多 [SIMD](/hpc/simd) 应用以 32 字节为单位读写数据，而这 32 字节属于同一条缓存行对性能[至关重要](/hpc/simd/moving)。这种情况下，可以在定义静态数组变量时使用 `alignas` 说明符：

```c++
alignas(32) float a[n];
```

要动态分配内存对齐的数组，可以使用 `std::aligned_alloc`，它接受对齐值和数组的字节大小，返回指向所分配内存的指针——就像 `new` 运算符那样：

```c++
void *a = std::aligned_alloc(32, 4 * n);
```

还可以把内存对齐到[比缓存行更大的尺寸](../paging)。唯一的限制是，`size` 参数必须是 `alignment` 的整数倍。

定义 `struct` 时也可以使用 `alignas` 说明符：

```c++
struct alignas(64) Data {
    // ...
};
```

每当分配 `Data` 的实例时，它都会位于缓存行的开头。缺点是结构体的有效大小会被向上取整到最近的 64 字节倍数。这是必须的，比方说这样在分配 `Data` 的数组时，不只是第一个元素对齐正确。

### 结构体对齐 {#structure-alignment}

当我们需要分配一组非同质的元素时——结构体正是这种情况——问题变得更复杂。与其玩俄罗斯方块式地重排 `struct` 的成员、试图让每个成员都落在单条缓存行内——这并不总能做到，因为结构体本身不必被放在缓存行的开头——大多数 C/C++ 编译器同样依赖内存对齐机制。

结构体对齐同样保证其所有成员基本类型（`char`、`int`、`float*` 等）的地址都是其大小的整数倍，这自动保证了每个成员只横跨一条缓存行。它是这样做到的：

- 在必要时用若干空白字节*填充*（padding）每个结构体成员，以满足下一个成员的对齐要求；
- 把结构体本身的对齐要求设为其成员类型对齐要求中的最大值，这样当分配该结构体类型的数组、或把它用作另一个结构的成员类型时，其所有基本类型的对齐要求都能得到满足。

为了更好地理解，考虑下面这个玩具例子：

```cpp
struct Data {
    char a;
    short b;
    int c;
    char d;
};
```

紧凑存放时，这个结构体每个实例共需 $1 + 2 + 4 + 1 = 8$ 字节，但即便假设整个结构体按 4 字节对齐（它最大的成员 `int`），也只有 `a` 没问题，`b`、`c` 和 `d` 都没有按大小对齐，可能跨越缓存行边界。

为了修复这一点，编译器插入一些无名成员，让每个后续成员获得正确的最小对齐：

```cpp
struct Data {
    char a;    // 1 byte
    char x[1]; // 1 byte for the following "short" to be aligned on a 2-byte boundary
    short b;   // 2 bytes
    int c;     // 4 bytes (largest member, setting the alignment of the whole structure)
    char d;    // 1 byte
    char y[3]; // 3 bytes to make total size of the structure 12 bytes (divisible by 4)
};

// sizeof(Data) = 12
// alignof(Data) = alignof(int) = sizeof(int) = 4
```

这有可能浪费空间，但省下大量 CPU 周期。这种权衡总体上是划算的，所以大多数编译器默认开启结构体对齐。

### 优化成员顺序 {#optimizing-member-order}

填充只会插在尚未对齐的成员之前或结构体的末尾。通过改变结构体中成员的排列顺序，可以改变所需的填充字节数和结构体的总大小。

在前面的例子中，我们可以像这样重排结构体成员：

```c++
struct Data {
    int c;
    short b;
    char a;
    char d;
};
```

现在，每个成员无需任何填充即已对齐，结构体的大小只有 8 字节。结构体的大小、进而其性能，竟然取决于成员定义的顺序——这看起来很蠢，但这是二进制兼容所要求的。

根据经验法则，把类型定义从最大数据类型排到最小——除非有一些奇怪的非 2 的幂的类型大小，比如 [10 字节](/hpc/arithmetic/ieee-754#float-formats)的 `long double`[^extended]，这个贪心算法保证有效。

[^extended]: 80 位的 `long double` 至少占 10 字节，但确切格式由编译器决定——例如，它可能填充到 12 或 16 字节以减少对齐问题（64 位 GCC 和 Clang 默认用 16 字节；你可以通过指定 `-mlong-double-64/80/128` 或 `-m96/128bit-long-double` [选项](https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html)之一来覆盖它）。

<!--

For example, if members are sorted by descending alignment requirements a minimal amount of padding is required. The minimal amount of padding required is always less than the largest alignment in the structure. Computing the maximum amount of padding required is more complicated, but is always less than the sum of the alignment requirements for all members minus twice the sum of the alignment requirements for the least aligned half of the structure members.


```c++
struct NodeF {
    int* i1;
    bool b1;
    int* i2;
    bool b2;
    int* i3;
    bool b3;
    int* i4;
    bool b4;
    int* i5;
    bool b5;
};
```

12x8 = 80 bytes.

```c++
struct NodeG {
    int* i1;
    int* i2;
    int* i3;
    int* i4;
    int* i5;
    bool b1;
    bool b2;
    bool b3;
    bool b4;
    bool b5;
};
```

-->

### 结构体打包 {#structure-packing}

如果你清楚自己在做什么，可以禁用结构体填充，把数据打包得尽可能紧。

你得请求编译器这么做，因为这样的功能既不属于 C 标准、也不属于 C++ 标准。在 GCC 和 Clang 中，这是用 `packed` 属性实现的：

```cpp
struct __attribute__ ((packed)) Data {
    long long a;
    bool b;
};
```

这让 `Data` 的实例只占 9 字节，而不是对齐所需的 16 字节，代价是读取其元素时可能要取回两条缓存行。

### 位域 {#bit-fields}

还可以把打包与*位域*（bit fields）配合使用，它允许你显式地以比特为单位固定某个成员的大小：

```cpp
struct __attribute__ ((packed)) Data {
    char a;     // 1 byte
    int b : 24; // 3 bytes
};
```

这个结构体打包时占 4 字节，填充时占 8 字节。成员的比特数不必是 8 的倍数，结构体的总大小也不必。在 `Data` 的数组中，当字节数不是整数时，相邻的元素会被"合并"。它还允许你设置超过基本类型的宽度，其作用相当于填充——不过过程中会抛出警告。

<!-- TODO: verify this -->

这个特性并不那么普及，因为 CPU 没有 3 字节算术之类的东西，加载时不得不做一些低效的逐字节转换：

```cpp
int load(char *p) {
    char x = p[0], y = p[1], z = p[2];
    return (x << 16) + (y << 8) + z;
}
```

当存在非整数字节时，开销还要更大——需要用移位加 and 掩码来处理。

这个过程可以这样优化：加载一个 4 字节的 `int`，然后用掩码丢弃其最高位。

```cpp
int load(int *p) {
    int x = *p;
    return x & ((1<<24) - 1);
}
```

编译器通常不这么做，因为严格来说这是不合法的：那第 4 个字节可能位于你不拥有的内存页上，所以即便你打算立刻丢弃它，操作系统也不会让你加载它。
