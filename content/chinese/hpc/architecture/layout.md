---
title: 机器码布局
weight: 10
draft: true
---

计算机工程师喜欢在头脑里把 [CPU 的流水线](/hpc/pipelining)分成两部分：*前端*（front-end）负责从内存取指令并译码，*后端*（back-end）负责调度并最终执行。性能瓶颈通常在执行阶段，因此本书的大部分精力会花在后端相关的优化上。

但有时也会反过来：前端喂给后端指令的速度不够快，后端吃不饱。原因有很多，归根结底都与机器码在内存中的布局方式有关，而且对性能的影响颇为玄学：删掉一段没用的代码、交换 "if" 的两个分支、甚至只改变函数声明的顺序，都可能让性能变好或变坏。

### CPU 前端 {#cpu-front-end}

在机器码被转换成指令、CPU 领会程序员的意图之前，它要先经过我们关心的两个重要阶段：*取指*（fetch）和*译码*（decode）。

在**取指**阶段，CPU 从主存加载一块固定大小的字节，其中包含若干条指令的二进制编码。在 x86 上这块的大小通常是 32 字节，不同机器可能有差异。一个重要的细节是这块必须[对齐](/hpc/cpu-cache/cache-lines)：块地址必须是自身大小的倍数（在我们这是 32B）。

<!-- todo: what happens when an instruction crosses the boundary? -->

接下来是**译码**阶段：CPU 查看这块字节，丢弃指令指针之前的一切，把剩下的切分成指令。机器指令用可变字节数编码：`inc rax` 这样简单又常用的指令只要 1 字节，而一些带编码常量和行为修改前缀的冷门指令可能多达 15 字节。所以一块 32 字节里可能译出数量不定的指令，但不会超过某个机器相关的上限，即*译码宽度*（decode width）。我的 CPU（[Zen 2](https://en.wikichip.org/wiki/amd/microarchitectures/zen_2)）的译码宽度是 4：每个周期最多译码 4 条指令、送入下一阶段。

各阶段以流水线方式工作：如果 CPU 能判断（或[预测](/hpc/pipelining/branching/)）下一块需要什么指令，取指阶段就不等当前块的最后一条指令译码完成，立刻加载下一块。

<!--

Decoded Stream Buffer (DSB)

Loop Stream Detector (LSD)

-->

### 代码对齐 {#code-alignment}

其他条件相同时，编译器通常偏好机器码更短的指令：这样一块 32B 取指块能装下更多指令，也缩小二进制体积。但有时反过来才更好，原因正是取指块必须对齐。

想象你需要执行一段指令序列，而它恰从某个 32B 对齐块的最后一个字节开始。第一条指令也许能无额外延迟地执行，但后续的就得再等一个周期做下一次取指。如果代码块对齐在 32B 边界上，最多 4 条指令就能被同时译码、并发执行（除非它们特别长或相互依赖）。

有鉴于此，编译器经常做一个看似有害的优化：它们有时偏爱机器码更长的指令，甚至插入什么都不做的哑指令[^nop]，只为让关键跳转位置对齐到合适的 2 的幂边界。

[^nop]: 这类指令叫空操作，即 NOP 指令。在 x86 上"官方认证"的什么都不做是 `xchg rax, rax`（寄存器与自己交换）：CPU 认得它，除译码阶段外不花额外周期。`nop` 简写映射到同一机器码。

在 GCC 里可以用 `-falign-labels=n` 指定具体的对齐策略；想更精细的话，可以把 `-labels` [换成](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) `-function`、`-loops` 或 `-jumps`。在 `-O2` 和 `-O3` 优化级别上它默认开启——不设定具体对齐值，此时用一个（通常合理的）机器相关默认值。

<!-- Having to decode a bunch of extra NOPs is usually not a problem. -->

### 指令缓存 {#instruction-cache}

指令的存储和取用大体使用与数据相同的[内存系统](/hpc/cpu-cache)，只是缓存的下层可能换成一块独立的*指令缓存*（总不能让一次随手的数据读取把正在处理它的代码踢出缓存吧）。

在以下情形中，指令缓存至关重要：

- 你不知道接下来要执行什么指令，需要以[低延迟](/hpc/cpu-cache/latency)取下一块；
- 或你正在执行一长串冗长但处理很快的指令，需要[高带宽](/hpc/cpu-cache/bandwidth)。

因此，对机器码庞大的程序，内存系统可能成为瓶颈。这一考虑限制了我们之前讨论过的若干优化技术的适用范围：

- [内联函数](../functions)并不总是最优：它减少代码共享、增大二进制体积，需要更多指令缓存。
- [展开循环](../loops)只在一定程度上有益，即使迭代次数在编译期已知：到某个程度，CPU 得同时从主存取指令和数据，很可能被内存带宽卡住。
- 巨大的[代码对齐](#code-alignment)增大二进制体积，同样需要更多指令缓存。相比缓存未命中、等待指令从主存取回，取指多花一个周期只是小代价。

另一个方面是，把频繁使用的指令序列放进相同的[缓存行](/hpc/cpu-cache/cache-lines)和[内存页](/hpc/cpu-cache/paging)能改善[缓存局部性](/hpc/external-memory/locality)。要提高指令缓存的利用率，应当让热代码挨着热代码、冷代码挨着冷代码，并尽量移除死（未使用的）代码。想深入这个方向的话，可以看看 Facebook 的[二进制优化与布局工具](https://engineering.fb.com/2018/06/19/data-infrastructure/accelerate-large-scale-applications-with-bolt/)（BOLT），它最近被[合并](https://github.com/llvm/llvm-project/commit/4c106cfdf7cf7eec861ad3983a3dd9a9e8f3a8ae)进了 LLVM。

### 不对称的分支 {#unequal-branches}

假设出于某种原因，你需要一个计算整数区间长度的辅助函数。它接受两个参数 $x$ 和 $y$，但为了方便，它对应的既可以是 $[x, y]$ 也可以是 $[y, x]$——取决于哪个非空。用朴素的 C 你大概会这么写：

```c++
int length(int x, int y) {
    if (x > y)
        return x - y;
    else
        return y - x;
}
```

在 x86 汇编里，它的实现方式多变得多，且对性能影响显著。先试着把这个 C 代码直接翻成汇编：

```nasm
length:
    cmp  edi, esi
    jle  less
    ; x > y
    sub  edi, esi
    mov  eax, edi
done:
    ret
less:
    ; x <= y
    sub  esi, edi
    mov  eax, esi
    jmp  done
```

C 代码看起来非常对称，汇编版本却不是。于是产生一个有趣的小怪癖：一个分支可以比另一个稍快——如果 `x > y`，CPU 只需执行 `cmp` 到 `ret` 之间的 5 条指令；只要函数是对齐的，它们能一次取完；而 `x <= y` 的情况则需要多两次跳转。

假定 `x > y` 的情况*不太可能*发生是合理的（谁会去算一个反向区间的长度呢？），更像一个几乎从不发生的异常。我们可以检测这种情况，直接交换 `x` 和 `y`：

```c++
int length(int x, int y) {
    if (x > y)
        swap(x, y);
    return y - x;
}
```

汇编会是这样——"只有 if 没有 else"的模式通常都长这样：

```nasm
length:
    cmp  edi, esi
    jle  normal     ; if x <= y, no swap is needed, and we can skip the xchg
    xchg edi, esi
normal:
    sub  esi, edi
    mov  eax, esi
    ret
```

指令总长从 8 降到 6。但对我们假设的情形它仍不算最优：如果认为 `x > y` 从不发生，那么加载那条永远不会执行的 `xchg edi, esi` 也是浪费。解决办法是把它挪出正常执行路径：

```nasm
length:
    cmp  edi, esi
    jg   swap
normal:
    sub  esi, edi
    mov  eax, esi
    ret
swap:
    xchg edi, esi
    jmp normal
```

这一技术在处理各种异常路径时都很好用；在高级语言里，你可以给编译器一个[提示](/hpc/compilation/situational)，说明某个分支比另一个更可能：

```c++
int length(int x, int y) {
    if (x > y) [[unlikely]]
        swap(x, y);
    return y - x;
}
```

这个优化只有在你确知某分支极少发生时才有益。如果不是这样，那么有比代码布局[更重要的因素](/hpc/pipelining/hazards)，它们促使编译器彻底避免分支——比如本例中用一个特殊的"条件传送"指令替代，大致对应三元表达式 `(x > y ? y - x : x - y)` 或调用 `abs(x - y)`：

```nasm
length:
    mov   edx, edi
    mov   eax, esi
    sub   edx, esi
    sub   eax, edi
    cmp   edi, esi
    cmovg eax, edx  ; "mov if edi > esi"
    ret
```

消除分支是个重要话题，我们将在[下一章花大量篇幅](/hpc/pipelining/branching)更详细地讨论它。

<!--

This architecture peculiarity

When you have branches in your code, there is a variability in how you can place their instruction sequences in the memory — and surprisingly, .

```nasm
length:
    mov   edx, edi
    mov   eax, esi
    sub   edx, esi
    sub   eax, edi
    cmp   edi, esi
    cmovg eax, edx  ; "mov if edi > esi"
    ret
```

Granted that `x > y` never or almost never happens, the branchy variant will be 2 instructions shorter.

https://godbolt.org/z/bb3a3ahdE

(The compiler can't optimize it because it's technically [not allowed to](/hpc/compilation/contracts): despite `y - x` being valid, `x - y` could over/underflow, causing undefined behavior. Although fully correct, I guess the compiler just doesn't date executing it.)

We will spend [much of the next chapter](/hpc/pipelining/branching) discussing it in more detail.

You don't have to decode the things you are not going to execute anyway.

In general, you want to, and put rarely executed code away — even in the case of if-without-else patterns.

-->
