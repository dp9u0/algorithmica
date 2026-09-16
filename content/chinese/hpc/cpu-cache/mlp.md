---
title: 内存级并行
weight: 5
draft: true
---

内存请求可以在时间上重叠：在等待一个读请求完成的同时，你可以再发出另外几个请求，它们会与前者并发执行。这就是[线性迭代](../bandwidth)远快于[指针追逐](../latency)的主要原因：CPU 知道它接下来要取哪些内存位置，并提前很久就发出内存请求。

并发内存操作的数量很大但有限，且因内存类型而异。在设计算法、尤其是数据结构时，你可能想知道这个数字，因为它限定了你的计算所能达到的并行度。

要在理论上求出特定内存类型的这个极限，可以用它的延迟（取回一条缓存行的时间）乘以它的带宽（每秒取回的缓存行数），得到平均在途的内存操作数：

![](/en/hpc/cpu-cache/img/latency-bandwidth.svg)

L1/L2 缓存的延迟很小，所以不需要一条长长的挂起请求流水线，但更大的内存类型可以维持多达 25-40 个并发读操作。

### 直接实验 {#direct-experiment}

让我们试着更直接地测量可用的内存级并行（memory-level parallelism）：修改指针追逐基准测试，不再绕着一个环走，而是并行地绕 $D$ 个独立的环走：

```c++
const int M = N / D;
int p[M], q[D][M];

for (int d = 0; d < D; d++) {
    iota(p, p + M, 0);
    random_shuffle(p, p + M);
    k[d] = p[M - 1];
    for (int i = 0; i < M; i++)
        k[d] = q[d][k[d]] = p[i];
}

for (int i = 0; i < M; i++)
    for (int d = 0; d < D; d++)
        k[d] = q[d][k[d]];
```

把环长总和固定在几个选定的规模上，尝试不同的 $D$，得到略有差异的结果：

![](/en/hpc/cpu-cache/img/permutation-mlp.svg)

L2 缓存的运行受限于 ~6 个并发操作，与预测一致；但更大的内存类型都在 13 到 17 之间封顶。你没法利用更多的内存车道（lane），因为会对逻辑寄存器产生争用。当车道数少于寄存器数时，每条车道只需发出一条读指令：

```nasm
dec     edx
movsx   rdi, DWORD PTR q[0+rdi*4]
movsx   rsi, DWORD PTR q[1048576+rsi*4]
movsx   rcx, DWORD PTR q[2097152+rcx*4]
movsx   rax, DWORD PTR q[3145728+rax*4]
jne     .L9
```

但当车道数超过 ~15 时，你就得动用临时的内存存储：

```nasm
mov     edx, DWORD PTR q[0+rdx*4]
mov     DWORD PTR [rbp-128+rax*4], edx
```

你并不总能达到内存并行度的最大可能水平，但对大多数应用来说，十来个并发请求已经绰绰有余。
