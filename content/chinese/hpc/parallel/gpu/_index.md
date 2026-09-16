---
title: "[草稿]GPU 编程"
weight: 5
draft: true
---

这是一个以 HTML 渲染的 Jupyter notebook。如果你想直接在这里做练习，在 [Colab]() 中打开，或者[下载]()后在本地编辑。前一种情况下，你需要完成一个小小的闯关任务，安装 CUDA 和它的 Python 绑定 PyCuda。在 Debian 系的机器上，下面这些大概就够了：
* `apt-get install nvidia-cuda-dev nvidia-cuda-toolkit`
* `pip install pycuda`

前置知识：Python 和 C 的基础知识、基础算法，以及大体上计算机是怎么工作的。

## 摩尔定律的微妙之处 {#subtlties-of-the-moores-law}

下面这张图大致描绘了 CPU 世界正在发生的事：

<img width='600px' src='https://www.karlrupp.net/wp-content/uploads/2015/06/35years.png'>

**摩尔定律**（Moore's law）是对这样一种现象的观察：微处理器中的晶体管数量大约每两年翻一番。这粗略地意味着性能也会跟着翻番。

可以看到，2005 年前后设计上出现了一次转向。

各个核心多少是相互独立的。

现代 GPU 出现于 2000 年代初。它们利用了自己所专注的那个特定领域。

核心的速度存在物理上的限制。

其中一条铁律：光速。你至少需要留出时间，让电磁波（它也是光）从主板的一侧传播到另一侧。

其中一些有

Google Colab 默认提供的免费 GPU [相当强大](https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/tesla-t4/t4-tensor-core-datasheet-951643.pdf)。作者完全不知道 Google 为什么这么做，但这真是太棒了。

## 为什么要多处理？ {#why-multiprocessing}

时钟频率——比如 Intel Core i7 可以达到。这给出了一个上界

有两种类型的

## 通用 GPU {#general-purpose-gpu}

曾有一段时间，对冲基金从游戏公司挖计算机图形学的人，看中的就是他们的计算能力。

有几种。

这就像 Windows 和 Linux 的情形一样。

我们会选用 CUDA，因为它更普及，尤其是在没人在乎的领域，比如深度学习。

## 异构计算 {#heterogineous-computing}

CUDA 编程涉及在两个不同的平台上并发地运行代码：一个带有一颗或多颗 CPU 的主机系统，以及一块或多块 GPU。

## 与 CPU 的差异 {#differences-from-cpus}

### 线程 {#threads}

CPU 上的线程通常是重量级的实体。操作系统必须把线程在 CPU 的执行通道上换入换出，以提供多线程能力。因此上下文切换（context switch）又慢又昂贵。

相比之下，GPU 上的线程极其轻量。在一个典型系统里，成千上万的线程排队等活——按每 32 个线程组成一个线程束（warp）。如果 GPU 必须等待某一个线程束，它就直接开始执行另一个线程束上的工作。由于所有活跃线程都分配有各自独立的寄存器，在 GPU 线程之间切换时不需要交换寄存器或其他状态。资源会一直分配给每个线程，直到它执行完毕。

简而言之，CPU 核心的设计目标是让每核同一时间运行的一两个线程的延迟最小，而 GPU 的设计目标是处理大量并发的轻量级线程，以最大化吞吐量。

### 内存 {#memory}

主机系统和设备各自拥有自己独立的物理内存。由于主机内存与设备内存之间隔着 PCI Express（PCIe）总线，主机内存中的数据偶尔需要经由总线传送到设备内存，反之亦然，如 What Runs on a CUDA-Enabled Device? 一节所述。

如果你照这样想，可以轻松丢掉 98% 的性能。

## 安装 PyCUDA {#installing-pycuda}

CUDA 有多种语言的版本可用。

不错的文档在这里：https://documen.tician.de/pycuda/index.html

如果你在 Colab 上，进入 Runtime -> Change runtime type -> Hardware accelerator，把它设为"GPU"。


```python
# you may want to clear the output of this cell after installation
from IPython.display import clear_output
 
# this might take a while
!pip install pycuda

clear_output()
```


```python
import numpy as np

from pycuda.compiler import SourceModule
import pycuda.driver as drv
import pycuda.autoinit
```

## 基础 {#the-basics}

让我们从一个简单的例子开始，然后再深入。

## 内核 {#kernels}

和 C 或 C++ 一样，只是你要用一些自定义的内建函数和说明符。

CUDA 与普通 C 几乎一样，只是你可以指定某些函数作为……来运行。视具体实现而定，工作流程如下：

你需要把你的计算机看作一台异构机器：有主机端数据，也有设备端数据。

* 把输入数据搬到设备内存。
* 在设备上执行一些计算。
* 把数据取回来。

事实上，内核（kernel）的运行是并发的——在内核运行完成之前，你的程序并不会阻塞。较新的设备甚至可以这样并发地运行多个内核，然后等待它们的结果。

## 著名的 $A + B$ 问题 {#the-famous-a-b-problem}

为了测试以及与主机端交互，我们会用 **NumPy** 包。如果你没有装，安装它：`pip install numpy`。

NumPy 是 Python 中做线性代数和数组操作的包。它用 C 编写、非常高效，但只在 CPU 上运行，所以我们将拿它当对拍的基准。


```python
# lets generate our test data: two float arrays filled with something random
a = numpy.random.randn(100).astype('float32')
b = numpy.random.randn(100).astype('float32')
# the type needs to be specified in this case, because randn's default type is float64, but CUDA knows nothing about it

# we need to create space where kernel should write its answers to
dest = numpy.zeros_like(a)

# this is the kernel itself
mod = SourceModule("""
    __global__ void add(float *dest, float *a, float *b) {
        const int i = threadIdx.x;
        dest[i] = a[i] + b[i];
    }
""")

# you need to specify the source code, and PyCUDA will compile it
add_kernel = mod.get_function("add")

add_kernel(
    drv.Out(dest),  # specifies that this memory should be accessible for writing
    drv.In(a),  # specifies this should be accessible for reading
    drv.In(b),
    block=(100,1,1)  # we'll talk about it in a minute
)

assert np.allclose(dest, a + b), 'WA'  # checks that these are equal
print('OK')
```


      File "<ipython-input-27-afc857479fe4>", line 19
        %%time
        ^
    SyntaxError: invalid syntax



### 内存管理 {#memory-management}

在 CUDA C 的 API 里，你需要显式地分配内存。所以说这其实挺好的。

还有一个 `drv.InOut` 函数，让内存既可读又可写，但本教程里我们不会用它，因为我们也需要测试自己的代码。

这里的大多数操作都是内存操作，所以在这里测性能没有意义。别担心，我们很快就会讲到更复杂的例子。

GPU 的操作非常特定。不过对 NVIDIA GPU 来说，管理这件事相当简单：显卡有*计算能力*（compute capability）等级（1.0、1.1、1.2、1.3、2.0 等等），在能力等级 $x$ 上加入的所有特性在之后的版本里也都可用。这些可以在运行时或编译时检查。

差异可以看这篇维基百科条目：https://en.wikipedia.org/wiki/CUDA#Version_features_and_specifications

## 同步 {#synchronization}

**归约**（reduction）是对整个数组进行的运算。

考虑下面这个问题：


## 动态规划 {#dynamic-programming}

考虑下面这个递推式：


```python
## Problem: dynamic programming
```

## 工作量与延迟 {#work-vs-latency}

现在我们要同时考虑工作量复杂度和步数复杂度了。

有些任务，尤其是密码学里的，无法并行化。但也有些可以。

## 在 $O(\log n)$ 时间内求数组之和 {#summing-arrays-in-olog-n-time}

假设我们想对数组执行某个满足结合律（即 $A*(B*C) = (A*B)*C$）的运算，数组有 $n$ 个元素。比如说，求和。

通常，我们会用一个简单的循环来做：

```c++
float s = 0;
for (int i = 0; i < n; i++) {
     s += a[i]; 
}
```

它的计算图长这样：

<img width='400px' src='https://www.elemarjr.com/wp-content/uploads/2018/03/sequential_sum.png'>

从工作量复杂度的角度这是最优的，但从步数复杂度的角度则不是：它是 $O(n)$。我们也许愿意接受工作量复杂度稍微差一点、但可以并行化的做法。

来试试这个分治（divide-and-conquer）的思路：

<img width='400px' src='https://www.elemarjr.com/wp-content/uploads/2018/03/parallel_sum.png'>

现在工作量复杂度仍是 $O(n)$（你实际需要的加法次数一模一样），但步数复杂度是 $O(\log n)$。

当你自顶向下展开递归时会发现，要得到每个需要的值，

<img width='400px' src='http://i.stack.imgur.com/Uehc3.png'>

## 归约小数组 {#reducing-small-arrays}


```python
a = numpy.random.randn(2048).astype('float32')

mod = SourceModule("""
    __global__ void sum(float *dest, float *a, float *b) {
        const int i = threadIdx.x;
        // for l from 0 to logn:
        //   __sync_threads()
        //   if the thread is active
        //     sum two elements into where they belong
        // a[0] should containt the needed sum
    }
""")

sum_kernel = mod.get_function("sum")

add_kernel(
    drv.InOut(a),
    block=(1024,1,1)
)

assert np.allclose(dest, a + b), 'WA'  # checks that these are equal
print('OK')
```

## 线程束与线程块 {#warps-and-thread-blocks}

线程被捆绑成 32 个一组。一组内的所有线程必须要么都在等待、要么都在执行同一个操作。这是由架构上的困难造成的。

<img width='300px' src='https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Block-thread.svg/1920px-Block-thread.svg.png'>

实际上你还可以用二维、三维索引做同样的事——挺奇怪的吧？

## 原子操作 {#atomics}

## 归约大数组 {#reducing-big-arrays}

## 归约超大数组 {#reducing-very-big-arrays}

现在，事情变难了。是时候讲讲 GPU 的并行到底是怎么运作的了.




```python

```

## 稠密矩阵乘法 {#dense-matrix-multiplication}

来看第一个真正值得用 GPU 的例子：矩阵乘法。

## 排序 {#sorting}

我们的最后一项（也是最难的）任务是实现排序。

你可能注意到，我们大部分时候都在鼓吹分治法。

确实如此。它们行得通。但我们现在还拿不出一个现成能用的算法。


```python
# we'll use a deep learning library for benchmarking because I'm not familiar with anything else 
import torch

a = torch.randn(10**8)
b = a.cuda()
```


```python
# this should run for ~15 secs
%time c = torch.sort(a)
%time c = torch.sort(b)
```


    CPU times: user 15.2 s, sys: 177 µs, total: 15.2 s
    Wall time: 15.2 s
    CPU times: user 274 ms, sys: 237 ms, total: 511 ms
    Wall time: 511 ms


于是，30 倍加速。这样我们就知道了要跟什么较量。


```python
b.sort()
```



    (tensor([-5.4567, -5.3551, -5.3288,  ...,  5.3529,  5.4484,  5.4486],
            device='cuda:0'),
     tensor([55083205,  8383169, 73705953,  ..., 79814161, 50474932, 27805828],
            device='cuda:0'))



排序算法有两类：数据驱动的。

第二类可以用排序网络（sorting network）来表示和分析。我们将用的是下面这个，它叫双调排序（bitonic sort）。

<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/BitonicSort.svg/1686px-BitonicSort.svg.png'>

它有 $O(\log n)$ 个阶段，这些阶段总共有 $1 + 2 + 3 + \ldots + \log n = O(\log^2 n$ 个无法并行、且要涉及数组每个元素的比较块。所以总的工作量复杂度是 $O(n \log^ n)$，而步数复杂度是 $O(\log^2 n)$，相当漂亮。

它实现起来其实没那么难。为了讲清楚，这里给一个慢速的递归 Python 实现：


```python
def bitonic_sort(a, up=False):
    if len(a) <= 1:
        return a
    else: 
        l = bitonic_sort(x[:len(a) // 2], True)
        r = bitonic_sort(x[len(a) // 2:], False)
        return bitonic_merge(first + second, up)

def bitonic_merge(a, up): 
    # assume input a is bitonic, and sorted list is returned 
    if len(a) == 1:
        return a
    else:
        bitonic_compare(a, up)
        l = bitonic_merge(a[:len(a) // 2], up)
        r = bitonic_merge(a[len(a) // 2:], up)
        return l + r

def bitonic_compare(a, up):
    dist = len(a) // 2
    for i in range(dist):  
        if (a[i] > a[i + dist]) == up:
            a[i], a[i + dist] = a[i + dist], x[i]  # this is how swap is done in Python
```


```python
bitonic_sort([57, 179, 42, 17, 300, 111])
```



    [300, 179, 111, 57, 42, 17]



```python
a = np.random.randn(10**8).astype('float32')
```


    ---------------------------------------------------------------------------

    NameError                                 Traceback (most recent call last)

    <ipython-input-27-58a927c14aae> in <module>()
    ----> 1 a = np.random.randn(10**8).astype('float32')
    
    NameError: name 'np' is not defined


## 为什么是 CUDA {#why-cuda}

其中大部分仍然适用。

再说一次，GPU 编程非常特殊。

SSE 与张量核心（tensor core）。

## 内核 {#kernels-1}

和 C 或 C++ 一样，只是你要用一些自定义的内建函数和说明符。

CUDA 与普通 C 几乎一样，只是你可以指定某些函数作为……来运行。视具体实现而定，工作流程如下：

你需要把你的计算机看作一台异构机器：有主机端数据，也有设备端数据。

* 把输入数据搬到设备内存。
* 在设备上执行一些计算。
* 把数据取回来。

事实上，内核的运行是并发的——在内核运行完成之前，你的程序并不会阻塞。较新的设备甚至可以这样并发地运行多个内核，然后等待它们的结果。

关于 GPU 你需要理解的是，它们为各自的应用做了极度的特化。

有为此准备的内建函数（intrinsic）。

如今，GPU 的很大一部分价值来自加密货币和深度学习。后者依赖两种特定的运算：用于线性层的矩阵乘法，以及用于计算机视觉中卷积层的卷积。

首先，他们引入了按每个 GPU 时钟周期执行的"乘加"（multiply-accumulate）运算（例如 `x += y * z`）。

Google 用的是张量处理单元（Tensor Processing Unit）。没人真正知道它们是怎么工作的（专有硬件，只租不卖）。

每个张量核心对 4x4 的小矩阵执行操作。每个张量核心每个 GPU 时钟能执行 1 次矩阵乘加操作。它把两个 4x4 的 fp16 矩阵相乘，并把乘积（fp32 矩阵，大小 4x4）加到累加器（同样是 fp32 的 4x4 矩阵）上。

每个时钟就能做这么多工作——

反正对深度学习来说，你也用不着比这更精确的东西。


它叫混合精度（mixed precision），因为输入矩阵是 fp16，而乘法结果和累加器是 fp32 矩阵。

更恰当的名字大概是"4x4 矩阵核心"，不过 NVIDIA 的市场团队决定用"张量核心"这个名字。

所以你看，这并不完全是公平的比较。

<img width='500px' src='https://static.seekingalpha.com/uploads/2018/8/11/275308-15340093003448672_origin.png'>

*<center>你需要把这张图稍微延长一点：去年 11 月，NVIDIA 的股价跟着比特币崩盘跌了 30%，所以我不会那么乐观</center>*

一路低到 int4（16 个取值，你没听错）

要写出高效的代码，你需要了解大量这类专门的细节。所以从零开始写库是个坏主意。

不管怎样，出于教学和娱乐的目的，今天我们要重新发明轮子，做一次矩阵乘法。

## 归约一个数组 {#reducing-an-array}

看起来很简单：你只需要。

可当你执行 `s += x` 时实际发生了什么？这并不是一个单一的操作。实际上，有四件事发生：

1. 把 $x$ 读入寄存器
2. 把 $s$ 读入寄存器
3. 计算 $s + x$
4. 把它写回 $s$ 最初所在的地方

两个线程可能交错地执行它。比如线程 A 可能拿到了 $s$，但一纳秒之后线程 B 会往这里写，而线程 A 并不知情，于是会把没有变化的值再写回去。



注：要用原子操作（atomics）来做这件事

对于较小的数据类型，它们是在硬件层面实现的，比那快得多。

std::atomic 就是为多线程环境中的原子操作而引入的。在多线程环境里，当两个线程操作同一个变量时，你必须格外小心，以避免竞态条件（race condition）。

## 内存类型 {#memory-types}

如果各种类型的设备内存来一场赛跑，名次会是这样：

寄存器宽度（= 机器字长）是 32 位，但它们也具备 64 位能力（否则就不可能有 4GB 以上的内存）。

* 第一名：**寄存器内存（register memory）**
  <br> 只有写入它的那个线程能看到这些数据。它们只在该线程的生命周期内有效。
* 第二名：**共享内存（shared memory）**
  <br> 由线程块内的所有线程共享。只在该块的生命周期内有效。这种内存允许线程之间通信（共享数据）。这正是为什么你应该
* 第三名：**常量内存（constant memory）**
  <br> 
* 第四名：纹理内存（texture memory）
* 并列垫底：局部内存（local memory）与全局内存（global memory）

现在你需要关心的是寄存器

眼下，你需要关心的是差别

访问全局内存需要几百个周期。

## 问题：稠密矩阵乘法 {#problem-dense-matrix-multiplication}

这些矩阵里很多其实是稀疏的。你可以拿社交网络图或网页图做点事情。

不错。但先让我们失望一下：
