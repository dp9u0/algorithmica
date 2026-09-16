---
title: "[草稿]读取十进制整数"
weight: 10
draft: true
---

我写了一种新的整数解析算法，比 scanf 快约 35 倍。

（不，这不是愚人节玩笑——尽管它听起来确实很荒谬。）

Zen 2 @ 2GHz。编译器为 Clang 13。

荒谬。

### Iostream {#iostream}

### Scanf {#scanf}

### 同步 {#syncronization}

### Getchar {#getchar}

### 缓冲 {#buffering}

### SIMD {#simd}

http://0x80.pl/notesen/2014-10-12-parsing-decimal-numbers-part-1-swar.html


### 串行 {#serial}

### 基于转置的方法 {#transpose-based-approach}

### 指令级并行 {#instruction-level-parallelism}


### 改进 {#modifications}

ILP 的收益不会那么大。

一个大大的星号：我们拿到的是整数，甚至还可以在它们之上执行其他解析算法。

每字节 1.75 个周期。

AVX-512 既得益于更大的 SIMD 通道（lane）尺寸，也得益于专门用于过滤的操作。

它占总时间的约 2%，但可以用专门的例程来优化。用任意数字填充缓冲区。

### 未来工作 {#future-work}

下次我们会讲*写*整数。

你可以像 rabin-karp 算法那样通过计算哈希来构造一个字符串搜索算法——尽管这事似乎没法做成一个*精确*算法。

## 致谢 {#acknowledgements}

http://0x80.pl/articles/simd-parsing-int-sequences.html

https://stackoverflow.com/questions/25622745/transpose-an-8x8-float-using-avx-avx2/25627536#25627536
