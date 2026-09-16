---
title: "[草稿]位操作"
weight: 7
draft: true
---

本文很大程度上基于 Sean Eron Anderson 的 [Bit Twiddling Hacks](https://graphics.stanford.edu/~seander/bithacks.html)。增加了一些方法，也删掉了一些因为已被硬件解决而不再需要的。这些技巧大多数已经由编译器完成优化。

在提供 `cmov` 的架构上，其中很多已经过时了。

这也可以当作一份练习。

## 基本操作 {#basic-operations}

`>>`

注意，算术移位（arithmetic shift）对负数移入 `1`，对正数移入 `0`。（不过这一点也可能是由实现定义的？）

对负数进行左移或右移在 C/C++ 中是未定义行为。

`<<`

做“循环左移”（rotate left）的 `rol` 指令

`__builtin_popcount` `popcnt` 返回 x 中值为 1 的位的个数。

`__builtin_parity` 返回 x 的*奇偶性*（parity，即 x 中 1 位的个数对 2 取模）。

这大概是为[错误检测](https://en.wikipedia.org/wiki/Parity_bit)而设的。

`__builtin_clrsb` 返回 x 中前导冗余符号位的个数，也就是最高有效位之后与它相同的那些位的个数。对 0 或其他值没有特殊情形。

`__builtin_ffs` 返回 x 的最低有效 1 位的下标加一；若 x 为零，则返回零。

`__builtin_clz` 返回从最高有效位位置起算的 x 中前导 0 位的个数。若 x 为 0，结果未定义

`__builtin_ctz` 返回从最低有效位位置起算的 x 中尾部 0 位的个数。若 x 为 0，结果未定义

`ctz`、`clz` -> `__lg`

## 技巧 {#recipes}

### 整数的符号 {#sign-of-an-integer}

`(x < 0)` 或 `x >> 31`

### 判断两个整数是否同号 {#check-if-two-integers-have-the-same-sign}

`x ^ z < 0`

### 整数的绝对值 {#absolute-value-of-an-integer}

提取符号位：`int mask = x >> 31`。对负数它将是 `1`，对正数是 `0`。

把它与最初的数异或：`x ^ mask`（依符号不同，这相当于加 1 或减 1）。

从第 2 步的结果中减去 `mask`：`(x ^ mask) - mask`

或者用 `(v + mask) ^ mask`，它做的是同一件事，只是反过来。

### 取最后一个 1 位 {#get-last-1-bit}

`x & -x`

### 去掉整数的最后一个 1 位 {#remove-the-last-1-bit-of-an-integer}

`x & (x - 1)`

### 判断是否为 2 的幂 {#checking-for-power-of-two}

`(x & (x - 1)) == 0`

注意 0 也会被当作 2 的幂。

### 位反转 {#reversing-bits}

Clang 有 `__builtin_bitreverse{8,16,32,64}`

```c++
int reverseBits(int x)
{
	unsigned int s = sizeof(x) * 8;
	T mask = ~T(0);
	while ((s >>= 1) > 0)
	{
		mask ^= mask << s;
		x = ((x >> s) & mask) | ((x << s) & ~mask);
	}
	return x;
}
```

### 用 XOR 交换两个数 {#swapping-numbers-with-xor}

这一个你多半听说过。

```c++
a ^= b;
b ^= a;
a ^= b;
```

但底层并不是这样执行的。有一条单独的 `xchng` 指令。

### 对 2 的幂取模 {#modulus-a-power-of-two}

若 `m = (1 << k)`，则 `x % m` 与 `x & (m - 1)` 相同。

## 掩码 {#masks}

掩码操作。

### 暴力枚举 {#brute-forcing}

你可以写成递归的（显然很慢）。也可以写成无分支的。

背包问题（knapsack problem）有一个 $O(2^n)$ 的暴力解法。

```c++
int ans = 0;
for (int mask = 0; mask < (1 << n); mask++) {
    int s = 0;
    for (int i = 0; i < n; i++)
        if (mask >> i & 1)
            s += a[i];
    if (s <= C)
        ans = max(ans, s);
}
```

### 所有子集的子集 {#subsets-of-all-subsets}

```c++
for (int submask = mask; submask != 0; submask = (submask - 1) & mask) {
    // ...
}
```

结果总枚举量是 $3^n$。每次迭代中，每个位都处于三种状态之一：不在 $m$ 中、尚不在 $s$ 中、同时在 $s$ 和 $m$ 中。由于总共有 $n$ 个位，最多有 $3^n$ 种不同的组合。
