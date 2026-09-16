---
title: 内建函数与向量类型
aliases: [/hpc/simd/x86-simd]
weight: 1
draft: true
---

使用 SIMD 最底层的方式是直接使用汇编向量指令——它们与各自的标量等价指令毫无区别——但我们不打算这样做。相反，我们将使用映射到这些指令的*内建函数*（intrinsic），现代 C/C++ 编译器都提供它们。

本节我们过一遍它们的基本语法，而在本章余下部分，我们将大量使用它们来做一些真正有趣的事情。

## 准备工作 {#setup}

要使用 x86 内建函数，我们需要做一些基础准备。

首先，需要确定硬件支持哪些扩展。在 Linux 上，你可以执行 `cat /proc/cpuinfo`；在其他平台上，你最好去 [WikiChip](https://en.wikichip.org/wiki/WikiChip)，用 CPU 的名称在那里查询。无论哪种方式，都应该有一个 `flags` 小节，列出所有受支持的向量扩展的代码。

还有一条专门的 [CPUID](https://en.wikipedia.org/wiki/CPUID) 汇编指令，可以查询 CPU 的各种信息，包括对特定向量扩展的支持。它主要用于在运行时获取这类信息，避免为每种微架构分发一个单独的二进制文件。它的输出信息以特性掩码的形式非常紧凑地返回，因此编译器提供了一些内建方法来解读它。下面是一个例子：

```c++
#include <iostream>
using namespace std;

int main() {
    cout << __builtin_cpu_supports("sse") << endl;
    cout << __builtin_cpu_supports("sse2") << endl;
    cout << __builtin_cpu_supports("avx") << endl;
    cout << __builtin_cpu_supports("avx2") << endl;
    cout << __builtin_cpu_supports("avx512f") << endl;

    return 0;
}
```

其次，我们需要包含一个头文件，里面有我们需要的那部分内建函数。类似 GCC 中的 `<bits/stdc++.h>`，有一个 `<x86intrin.h>` 头文件包含了所有内建函数，所以我们直接用它就行。

最后，我们需要[告诉编译器](/hpc/compilation/flags)目标 CPU 确实支持这些扩展。这既可以用 `#pragma GCC target(...)`（就像[我们之前做的那样](../)），也可以用编译器选项中的 `-march=...` 标志。如果你在同一台机器上编译并运行代码，可以设置 `-march=native` 来自动检测微架构。

在后续所有代码示例中，都假定它们以这几行开头：

```c++
#pragma GCC target("avx2")
#pragma GCC optimize("O3")

#include <x86intrin.h>
#include <bits/stdc++.h>

using namespace std;
```

本章将聚焦于 AVX2 及此前的 SIMD 扩展，它们应该可用于 95% 的台式机和服务器；不过这里的一般原理同样适用于 AVX512、Arm Neon 及其他 SIMD 架构。

### SIMD 寄存器 {#simd-registers}

SIMD 扩展之间最显著的区别是对更宽寄存器的支持：

- SSE（1999 年）加入了 16 个 128 位寄存器，名为 `xmm0` 到 `xmm15`。
- AVX（2011 年）加入了 16 个 256 位寄存器，名为 `ymm0` 到 `ymm15`。
- AVX512（2017 年）加入[^mask]了 16 个 512 位寄存器，名为 `zmm0` 到 `zmm15`。

[^mask]: AVX512 还加入了 8 个所谓*掩码寄存器*，名为 `k0` 到 `k7`，用于数据的掩码与混合操作。我们不会讲它们，而且将主要使用 AVX2 及更早的标准。

你可以从命名，以及 512 位已经占满一整个缓存行这个事实猜到，x86 的设计者近期内并不打算添加更宽的寄存器。

C/C++ 编译器实现了专门的*向量类型*，用来指代存储在这些寄存器中的数据：

- 128 位的 `__m128`、`__m128d` 和 `__m128i` 类型，分别用于单精度浮点、双精度浮点和各种整数数据；
- 256 位的 `__m256`、`__m256d`、`__m256i`；
- 512 位的 `__m512`、`__m512d`、`__m512i`。

寄存器本身可以存放任何类型的数据：这些类型只用于类型检查。你可以像平常转换其他任何类型那样，把一个向量变量转换成另一种向量类型，而且不会带来任何开销。

### SIMD 内建函数 {#simd-intrinsics}

*内建函数*（intrinsic）就是对这些向量数据类型做某种操作的 C 风格函数，通常只是简单地调用对应的汇编指令。

举个例子，下面这个循环使用 AVX 内建函数把两个由 64 位浮点数组成的数组相加：

```c++
double a[100], b[100], c[100];

// iterate in blocks of 4,
// because that's how many doubles can fit into a 256-bit register
for (int i = 0; i < 100; i += 4) {
    // load two 256-bit segments into registers
    __m256d x = _mm256_loadu_pd(&a[i]);
    __m256d y = _mm256_loadu_pd(&b[i]);

    // add 4+4 64-bit numbers together
    __m256d z = _mm256_add_pd(x, y);

    // write the 256-bit result into memory, starting with c[i]
    _mm256_storeu_pd(&c[i], z);
}
```

使用 SIMD 的主要难题在于把数据整理成适合装入寄存器的、连续的固定大小块。在上面的代码中，如果数组长度不能被块大小整除，一般来说就会有问题。对此有两种常见的解决方案：

1. 我们可以"越界"一步，对最后一个不完整的段也照常迭代。为了确保不会因为试图读写不属于我们的内存区域而段错误，需要把数组填充到最近的块大小倍数（通常用某种"中性"元素，比如零）。
2. 少做一次迭代，在末尾写一个小循环，用普通方式（标量操作）处理余下的部分。

人类偏好方案 1，因为它更简单、代码更少；编译器偏好方案 2，因为它们实在没有别的合法选择。

### 指令参考 {#instruction-references}

大多数 SIMD 内建函数遵循类似于 `_mm<size>_<action>_<type>` 的命名约定，并对应一条同名的汇编指令。一旦你熟悉了汇编的命名习惯，它们就变得不言自明，尽管有时候这些名字看起来确实像是猫在键盘上踩出来的（解释一下这个：[punpcklqdq](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#ig_expand=3037,3009,4870,4870,4872,4875,833,879,874,849,848,6715,4845,6046,3853,288,6570,6527,6527,90,7307,6385,5993,2692,6946,6949,5456,6938,5456,1021,3007,514,518,4875,7253,7183,3892,5135,5260,5259,6385,3915,4027,3873,7401&techs=AVX,AVX2&text=punpcklqdq)）。

再举几个例子，让你找到感觉：

- `_mm_add_epi16`：把两个由 16 位*扩展打包整数*（extended packed integer）组成的 128 位向量相加，说白了就是 `short`。
- `_mm256_acos_pd`：对 4 个*打包双精度数*逐元素计算 $\arccos$。
- `_mm256_broadcast_sd`：把一个内存位置上的 `double` 广播（复制）到结果向量的全部 4 个元素。
- `_mm256_ceil_pd`：把 4 个 `double` 分别向上取整到最近的整数。
- `_mm256_cmpeq_epi32`：比较 8+8 个打包 `int`，返回一个掩码，其中相等的位置为全 1。
- `_mm256_blendv_ps`：根据掩码从两个向量中选取元素。

你可能已经猜到，内建函数的组合数量极其庞大；除此之外，有些指令还带立即数——因此它们的内建函数要求编译期常量参数：例如，浮点比较指令[有 32 种不同的修饰符](https://stackoverflow.com/questions/16988199/how-to-choose-avx-compare-predicate-variants)。

出于某种原因，有些操作本身与寄存器中存放的数据类型无关，却只接受特定的向量类型（通常是 32 位浮点数）——你只能先转换过去、用完再转换回来。为了简化本章的示例，我们将主要使用 256 位 AVX2 寄存器中的 32 位整数（`epi32`）。

一份非常有用的 x86 SIMD 内建函数参考资料是 [Intel Intrinsics Guide](https://software.intel.com/sites/landingpage/IntrinsicsGuide/)，它按类别和扩展分组，提供描述、伪代码、对应的汇编指令，以及它们在 Intel 各微架构上的延迟和吞吐量。你可能会想把那个页面加入书签。

当你知道某条具体指令存在、只想查一下它的名字或性能信息时，Intel 的参考很有用。当你不知道它是否存在时，这份[速查表](https://db.in.tum.de/~finis/x86%20intrinsics%20cheat%20sheet%20v1.0.pdf)可能更合适。

**指令选择。** 注意，编译器不一定选用你指定的那条指令。与[我们之前讨论过的](/hpc/analyzing-performance/assembly)标量 `c = a + b` 类似，也存在融合的向量加法指令，因此编译器不再是每个循环周期用 2+1+1=4 条指令，而是[把上面的代码改写](https://godbolt.org/z/dMz8E5Ye8)成每块 3 条指令，像这样：

```nasm
vmovapd ymm1, YMMWORD PTR a[rax]
vaddpd  ymm0, ymm1, YMMWORD PTR b[rax]
vmovapd YMMWORD PTR c[rax], ymm0
```

有时候——虽然相当少见——这种编译器干预会把事情搞糟，所以[查看一下汇编](/hpc/compilation/stages)、仔细检查生成的向量指令（它们通常以"v"开头）永远是个好主意。

另外，有些内建函数并不对应单条指令，而是对应一小段指令序列，算是一种便利的捷径：[广播与提取](../moving#register-aliasing)就是典型的例子。

<!--

For example, the group of `extract` intrinsics that are used to get individual elements out of vectors: e g., `_mm256_extract_epi32(x, 0)` returns the first element out of 8-integer vector. t is quite slow (~5 cycles) to move data between "normal" and SIMD registers in general.

-->

### GCC 向量扩展 {#gcc-vector-extensions}

如果你觉得 C 内建函数的设计很糟糕，你不是一个人。我花过几百个小时写 SIMD 代码、读 Intel Intrinsics Guide，但仍然记不住该输入 `_mm256` 还是 `__m256`。

内建函数不仅难用，而且既不可移植也难维护。在好的软件里，你不会想为每种 CPU 维护不同的过程：你会想只用一种与架构无关的方式把它实现一遍。

有一天，GNU 项目的编译器工程师们也这么想，于是开发出一种定义你自己的向量类型的方法，用起来更像数组，并重载了一些运算符来匹配相关指令。

在 GCC 中，你可以这样定义一个由 8 个整数打包成 256 位（32 字节）寄存器的向量：

```c++
typedef int v8si __attribute__ (( vector_size(32) ));
// type ^   ^ typename          size in bytes ^ 
```

不幸的是，这不是 C 或 C++ 标准的一部分，所以不同的编译器使用不同的语法。

这里有个约定俗成的命名惯例，就是把元素的数量和类型包含在类型名里：在上面的例子中，我们定义的是"8 个有符号整数组成的向量"。但你想取任何名字都行，比如 `vec`、`reg` 或随便什么。你唯一不想做的就是把它命名为 `vector`，因为与 `std::vector` 的混淆会带来无穷无尽的麻烦。

使用这些类型的主要优势在于，很多操作你可以直接用普通的 C++ 运算符，而不必去查对应的内建函数。

```c++
v4si a = {1, 2, 3, 5};
v4si b = {8, 13, 21, 34};

v4si c = a + b;

for (int i = 0; i < 4; i++)
    printf("%d\n", c[i]);

c *= 2; // multiply by scalar

for (int i = 0; i < 4; i++)
    printf("%d\n", c[i]);
```

有了向量类型，我们可以大大简化之前用内建函数实现的"a + b"循环：

```c++
typedef double v4d __attribute__ (( vector_size(32) ));
v4d a[100/4], b[100/4], c[100/4];

for (int i = 0; i < 100/4; i++)
    c[i] = a[i] + b[i];
```

可以看到，与内建函数带来的噩梦相比，向量扩展干净得多。它们的缺点是，有些我们想做的事情无法用原生 C++ 结构表达，所以仍然需要内建函数。幸运的是，这不是一道单选题，因为向量类型支持与 `_mm` 类型之间的零开销双向转换：

```c++
v8f x;
int mask = _mm256_movemask_ps((__m256) x)
```

还有许多面向不同语言的第三方库，提供类似的编写可移植 SIMD 代码的能力，并且也实现了一些额外的功能，总之用起来比内建函数和内建向量类型都更舒服。C++ 方面著名的例子有 [Highway](https://github.com/google/highway)、[Expressive Vector Engine](https://github.com/jfalcou/eve)、[Vector Class Library](https://github.com/vectorclass/version2) 和 [xsimd](https://github.com/xtensor-stack/xsimd)。

推荐使用一个成熟的 SIMD 库，它能极大改善开发体验。不过在本书中，我们将尽量贴近硬件，主要直接使用内建函数，偶尔为了简洁在可以用的时候切换到向量扩展。
