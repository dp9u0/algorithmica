---
title: 统计剖析
weight: 2
draft: true
---

[插装](../instrumentation)是一种相当繁琐的剖析方式，尤其是当你关注的是程序中多个细小的片段时。即便工具能把它部分自动化，由于其固有的开销，它依然帮不上你收集精细的统计数据。

另一种侵入性更小的剖析方法是按随机间隔中断程序的执行，看看指令指针停在哪里。指针停在每个函数代码块中的次数，大致正比于执行这些函数所花的总时间。用这个方法还能得到一些其他有用的信息，比如通过检查[调用栈](/hpc/architecture/functions)弄清哪些函数调用了哪些函数。

原则上，你大可以用 `gdb` 跑一个程序、隔三差五按一下 `ctrl+c` 来做到这一点，但现代 CPU 和操作系统为这类剖析提供了专门的工具。

### 硬件事件 {#hardware-events}

硬件*性能计数器*（performance counter）是内置于微处理器中的特殊寄存器，能存储某些硬件相关活动的计数。在微芯片上添加它们很便宜，因为它们本质上就是连着一根激活线的二进制计数器。

每个性能计数器连接到电路中的一大片子集，可以配置成在某个特定硬件事件发生时递增，比如一次分支预测失败或一次缓存未命中。你可以在程序开始时将计数器清零，运行程序，最后输出其存储的值——它就等于整个执行过程中该事件被触发的精确次数。

你还可以在多个事件之间多路复用来同时追踪它们：也就是按均匀的时间间隔停下程序，重新配置计数器。这种情况下结果就不是精确值，而是统计近似。这里有个微妙之处：它的精度无法靠单纯提高采样频率来改善，因为那会过分拖累性能、进而扭曲分布；所以要收集多项统计，就得让程序运行更长的时间。

总体而言，事件驱动的统计剖析通常是诊断性能问题最有效也最简单的方式。

### 用 perf 剖析 {#profiling-with-perf}

依赖上述事件采样技术的性能分析工具称为*统计剖析器*（statistical profiler）。这类工具很多，但本书主要使用的是 [perf](https://perf.wiki.kernel.org/)，它是随 Linux 内核发布的统计剖析器。在非 Linux 系统上，你可以用 Intel 的 [VTune](https://software.intel.com/content/www/us/en/develop/tools/oneapi/components/vtune-profiler.html#gs.cuc0ks)，就我们的用途而言它提供大致相同的功能。它免费可用，但属于专有软件，而且社区版许可证每 90 天要续期一次；而 perf 则是货真价实的自由软件（free as in freedom）。

Perf 是一个命令行应用，基于程序的实时执行生成报告。它不需要源码，能剖析的应用范围极广，甚至包括涉及多进程和操作系统交互的程序。

为了讲解，我写了一个小程序：创建一个含一百万个随机整数的数组，对其排序，然后在上面做一百万次二分查找：

```c++
void setup() {
    for (int i = 0; i < n; i++)
        a[i] = rand();
    std::sort(a, a + n);
}

int query() {
    int checksum = 0;
    for (int i = 0; i < n; i++) {
        int idx = std::lower_bound(a, a + n, rand()) - a;
        checksum += idx;
    }
    return checksum;
}
```

编译之后（`g++ -O3 -march=native example.cc -o run`），我们可以用 `perf stat ./run` 运行它，输出其执行期间基本性能事件的计数：

```yaml
 Performance counter stats for './run':

        646.07 msec task-clock:u               # 0.997 CPUs utilized          
             0      context-switches:u         # 0.000 K/sec                  
             0      cpu-migrations:u           # 0.000 K/sec                  
         1,096      page-faults:u              # 0.002 M/sec                  
   852,125,255      cycles:u                   # 1.319 GHz (83.35%)
    28,475,954      stalled-cycles-frontend:u  # 3.34% frontend cycles idle (83.30%)
    10,460,937      stalled-cycles-backend:u   # 1.23% backend cycles idle (83.28%)
   479,175,388      instructions:u             # 0.56  insn per cycle         
                                               # 0.06  stalled cycles per insn (83.28%)
   122,705,572      branches:u                 # 189.925 M/sec (83.32%)
    19,229,451      branch-misses:u            # 15.67% of all branches (83.47%)

   0.647801770 seconds time elapsed
   0.647278000 seconds user
   0.000000000 seconds sys
```

可以看到，执行耗时 0.53 秒，也就是在有效时钟频率 1.32 GHz 下花了 852M 个周期，其间执行了 479M 条指令。还有 122.7M 次分支，其中 15.7% 预测失败。

> **译者注**：原文此处写"0.53 秒"，但上方 perf 输出显示的实测耗时为 0.648 秒（852M 周期 ÷ 1.32 GHz ≈ 0.646 秒），0.53 疑为作者早期示例数据残留的笔误。

你可以用 `perf list` 列出所有支持的事件，然后用 `-e` 选项指定你想要的具体事件列表。例如，诊断二分查找时，我们主要关心缓存未命中：

```yaml
> perf stat -e cache-references,cache-misses ./run

91,002,054      cache-references:u                                          
44,991,746      cache-misses:u      # 49.440 % of all cache refs
```

就其本身而言，`perf stat` 只是为整个程序设置好性能计数器。它能告诉你分支预测失败的总次数，但不会告诉你它们发生在*哪里*，更不会告诉你*为什么*发生。

要尝试我们前面讨论过的那种"停下来观察"（stop-the-world）的方法，需要用 `perf record <cmd>`，它会记录剖析数据并转储为一个 `perf.data` 文件，然后调用 `perf report` 来查看。我强烈建议你亲自去试一试，因为最后那个命令是交互式的、花花绿绿的；不过对于眼下没法动手的人，我会尽力把它描述清楚。

调用 `perf report` 时，它首先显示一个类似 `top` 的交互式报告，告诉你哪些函数各花了多少时间：

```
Overhead  Command  Shared Object        Symbol
  63.08%  run      run                  [.] query
  24.98%  run      run                  [.] std::__introsort_loop<...>
   5.02%  run      libc-2.33.so         [.] __random
   3.43%  run      run                  [.] setup
   1.95%  run      libc-2.33.so         [.] __random_r
   0.80%  run      libc-2.33.so         [.] rand
```

注意，对每个函数列出的只是它的*自身开销*（overhead）而非总运行时间（例如 `setup` 包含 `std::__introsort_loop`，但只有它自己的开销被计为 3.43%）。有一些工具可以从 perf 报告构建[火焰图](https://www.brendangregg.com/flamegraphs.html)，让报告更清晰。你还需要考虑可能的内联——`std::lower_bound` 在这里显然就是被内联了。Perf 还会追踪共享库（如 `libc`），以及一般而言任何其他派生出的进程：只要你愿意，你可以用 perf 启动一个网页浏览器，看看它内部在发生什么。

接下来，你可以"放大"查看其中任何一个函数，除其他内容外，它还能给你展示带热力图的反汇编。例如，下面是 `query` 的汇编：

```asm
       │20: → call   rand@plt
       │      mov    %r12,%rsi
       │      mov    %eax,%edi
       │      mov    $0xf4240,%eax
       │      nop    
       │30:   test   %rax,%rax
  4.57 │    ↓ jle    52
       │35:   mov    %rax,%rdx
  0.52 │      sar    %rdx
  0.33 │      lea    (%rsi,%rdx,4),%rcx
  4.30 │      cmp    (%rcx),%edi
 65.39 │    ↓ jle    b0
  0.07 │      sub    %rdx,%rax
  9.32 │      lea    0x4(%rcx),%rsi
  0.06 │      dec    %rax
  1.37 │      test   %rax,%rax
  1.11 │    ↑ jg     35
       │52:   sub    %r12,%rsi
  2.22 │      sar    $0x2,%rsi
  0.33 │      add    %esi,%ebp
  0.20 │      dec    %ebx
       │    ↑ jne    20
```

左列是指令指针停在某一行上的次数占比。可以看到，我们把约 65% 的时间花在了那条跳转指令上——因为它前面是一个比较运算，说明控制流在那里等待这次比较的结果出炉。

由于[流水线](/hpc/pipelining)和乱序执行之类的复杂机制，"现在"在现代 CPU 上并不是一个定义明确的概念，所以这些数据略有偏差，因为指令指针会往前漂移一点点。指令级的数据仍然有用，但到了单个周期的层面，我们就得换用[更精确的工具](../simulation)了。

<!-- flame graphs -->
