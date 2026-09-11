---
title: 契约编程
weight: 6
draft: true
---

在 Java 和 Rust 这类"安全"语言里，每种可能的操作、每种可能的输入，通常都有明确定义的行为。也有些东西是*欠定义*的，比如哈希表里键的顺序、`std::vector` 的增长因子，但这类通常只是留给实现自行决定的次要细节，为将来潜在的性能提升留出空间。

相比之下，C 和 C++ 把未定义行为（undefined behavior）的概念推向了另一个层次。某些操作在编译期或运行期都不会报错，但就是*不被允许*——这里存在程序员与编译器之间的一份*契约*：一旦发生未定义行为，编译器在"法律上"被允许做任何事，包括炸掉你的显示器、格式化你的硬盘。当然，编译器工程师对那些事没兴趣。相反，未定义行为被用来保证角落情况（corner case）的缺席，从而帮助优化。

### 未定义行为为何存在 {#why-undefined-behavior-exists}

引发未定义行为的行为分两大类：

- 几乎可以肯定是无心之失的操作，比如除以零、解引用空指针、读取未初始化的内存。这些你想在测试中尽早抓出来，所以崩溃或出现非确定行为，好过让它们总是执行返回零之类的固定兜底动作。

  你可以用*消毒器*（sanitizer）编译并运行程序，尽早捕获未定义行为。在 GCC 和 Clang 里，可以用 `-fsanitize=undefined` 标志，一些臭名昭著容易引发 UB 的操作会被插装，在运行时检测。

- 在不同平台上可观察行为略有差异的操作。例如，整数左移超过 31 位的结果是未定义的，因为执行该操作的指令在 Arm 和 x86 CPU 上的实现不同。如果把某一种行为标准化，为另一平台编译的所有程序就得多花几个周期检查这种边缘情况，所以最好留作未定义。

  有时，当某种平台特有行为存在正当用例时，可以不宣布它未定义，而是留作*由实现定义*（implementation-defined）。例如，[负整数](/hpc/arithmetic/integer)右移的结果取决于平台：移入的可能是 0 也可能是 1（比如 `11010110 = -42` 右移一位，可能得到 `01101011 = 107`，也可能得到 `11101011 = -21`，两种用例都很现实）。

把某件事指定为未定义而非由实现定义，同样有助于编译器优化。考虑有符号整数溢出的例子。在几乎所有体系结构上，[有符号整数](/hpc/arithmetic/integer)的溢出方式与无符号整数相同，`INT_MAX + 1 == INT_MIN`，然而按 C++ 标准，这是未定义行为。这完全是有意为之：如果禁止有符号整数溢出，那么对 `int` 而言 `(x + 1) > x` 保证恒为真；对 `unsigned int` 则不然，因为 `(x + 1)` 可能溢出。对有符号类型，这让编译器能把这类检查直接优化掉。

再看一个更自然出现的例子：以整数为控制变量的循环。现代 C++ 和 Rust 这类语言鼓励程序员用无符号整数（`size_t` / `usize`），而 C 程序员固执地继续用 `int`。要理解缘由，看下面这个 `for` 循环：

```cpp
for (unsigned int i = 0; i < n; i++) {
    // ...
}
```

这个循环执行多少次？严格说有两个合法答案：$n$ 和无穷——后者发生在 $n$ 超过 $2^{32}$ 时，$i$ 每 $2^{32}$ 次迭代就会归零一次。虽然前者多半是程序员的假设，但为了符合语言规范，编译器仍不得不插入额外的运行时检查、把两种情况都考虑进去，而这两者本应分别优化。换作 `int` 版本，则恰好执行 $n$ 次迭代，因为有符号溢出的可能性本身就被定义没了。

### 消除角落情况 {#removing-corner-cases}

"安全"的编程风格通常意味着大量运行时检查，但它们未必得以性能为代价。

例如，Rust 就以对数组及其他随机访问结构做边界检查（bounds checking）闻名。C++ STL 里，`vector` 和 `array` 有一个"不安全"的 `[]` 运算符和一个"安全"的 `.at()` 方法，后者的实现大致是这样：

```cpp
T at(size_t k) {
    if (k >= size())
        throw std::out_of_range("Array index exceeds its size");
    return _memory[k];
}
```

有意思的是，这些检查在运行时很少真正执行，因为编译器常常能在编译期证明每次访问都在界内。比如在 `for` 循环里从 1 迭代到数组长度、每步索引第 $i$ 个元素，不可能发生任何非法访问，于是边界检查可以被安全地优化掉。

### 假设 {#assumptions}

当编译器无法证明角落情况不存在、而*你*能证明时，可以借助未定义行为这一机制提供这条额外信息。

Clang 提供了一个好用的 `__builtin_assume` 函数，你可以放入一个保证为真的断言，编译器会在优化中利用这个假设。GCC 里用 `__builtin_unreachable` 也能达到同样效果：

```cpp
void assume(bool pred) {
    if (!pred)
        __builtin_unreachable();
}
```

例如，在上面的例子中把 `assume(k < vector.size())` 放在 `at` 之前，边界检查就会被优化掉。

把 `assume` 与 `assert`、`static_assert` 结合起来找 bug 也相当有用：同一个函数，可以在调试构建里用来检查前置条件，再在生产构建里用它提升性能。

<!--

```cpp
void assume(bool pred) {
    if (!pred)
        #ifdef
        __builtin_unreachable();
        #else
        exit(0); // ?
        #endif
}
```

-->

### 算术 {#arithmetic}

角落情况值得时刻放在心上，优化算术时尤其如此。

对[浮点算术](/hpc/arithmetic/float)，这不太成问题，因为可以用 `-ffast-math` 标志（`-Ofast` 也包含它）直接关掉严格标准合规。何况这几乎是必须的，否则编译器除了严格按源代码的顺序执行算术运算外，什么优化都做不了。

<!--

because even algebraically correct rearrangements result in slightly different rounding errors

-->

整数算术则不同，因为结果必须精确。考虑除以 2 的例子：

```cpp
unsigned div_unsigned(unsigned x) {
    return x / 2;
}
```

一个广为人知的优化是用一条右移指令（`x >> 1`）替代它：

```nasm
shr eax
```

这对所有*正*数当然正确，但一般情况呢？

```cpp
int div_signed(int x) {
    return x / 2;
}
```

如果 `x` 是负数，直接移就不对了——不管移入的是 0 还是符号位：

- 移入 0，会得到非负的结果（符号位是 0）。
- 移入符号位，舍入就会朝负无穷而不是朝零进行（`-5 / 2` 会等于 `-3` 而不是 `-2`）[^python]。

[^python]: 有趣的事实：在 Python 里，负数的整数除法不知为何会对结果向下取整，所以 `-5 // 2 = -3`，等价于 `-5 >> 1 = -3`。我怀疑 Guido van Rossum 当初设计这门语言时脑子里想的是不是这个优化，但从理论上说，一个含大量除以 2 运算的 [JIT 编译](/hpc/complexity/languages/#compiled-languages)的 Python 程序可能比对应的 C++ 程序还快。

因此，为处理一般情况，我们不得不插进一些"拐杖"让它能工作：

```nasm
mov  ebx, eax
shr  ebx, 31    ; extract the sign bit
add  eax, ebx   ; add 1 to the value if it is negative to ensure rounding towards zero
sar  eax        ; this one shifts in sign bits
```

当预期的只有正数情形时，也可以用 `assume` 机制排除 `x` 为负的可能，免去对这种角落情况的处理：

```cpp
int div_assume(int x) {
    assume(x >= 0);
    return x / 2;
}
```

不过在这个特定例子里，表达"只预期非负数"的最佳语法也许就是使用无符号整数类型。

正是因为这类细微之处，把中间函数里的代数式展开、亲手化简算术，往往比依赖编译器来做更有益。

### 内存别名 {#memory-aliasing}

编译器相当不擅长优化涉及内存读写的操作。原因常常是上下文不够，不足以保证优化的正确性。

考虑下面的例子：

```c++
void add(int *a, int *b, int n) {
    for (int i = 0; i < n; i++)
        a[i] += b[i];
}
```

由于循环的每次迭代相互独立，它可以并行执行并[向量化](/hpc/simd)。但严格说，真的可以吗？

如果数组 `a` 与 `b` 相交，就可能出问题。考虑 `b == a + 1` 的情形，即 `b` 只是从 `a` 的第二个元素开始的同一块内存的视图。这时下一个迭代依赖于上一个，唯一正确的做法是顺序执行循环。编译器不得不检查这种可能性，哪怕程序员明知它不会发生。

这就是 `const` 和 `restrict` 关键字存在的原因。前者约束我们不会通过该指针变量修改内存，后者则告诉编译器这块内存保证没有别名（alias）。

```cpp
void add(int * __restrict__ a, const int * __restrict__ b, int n) {
    for (int i = 0; i < n; i++)
        a[i] += b[i];
}
```

即便不考虑性能，这些关键字本身也值得使用，能起到自我说明的作用。

### C++ 契约 {#c-contracts}

契约编程是一种使用不多但非常强大的技术。

有一份进入后期阶段的提案，要以[契约属性](http://www.hellenico.gr/cpp/w/cpp/language/attributes/contract.html)（contract attributes）的形式把按契约设计（design-by-contract）加入 C++ 标准，功能上等价于我们手写的、依赖具体编译器的 `assume`：

```c++
T at(size_t k) [[ expects: k < n ]] {
    return _memory[k];
}
```

属性有 3 种——`expects`、`ensures`、`assert`——分别用于指定函数的前置条件、后置条件，以及可以放在程序任何地方的一般断言。

遗憾的是，这个令人兴奋的新特性[尚未最终标准化](https://www.reddit.com/r/cpp/comments/cmk7ek/what_happened_to_c20_contracts/)，更别说被主流 C++ 编译器实现了。但也许几年之后，我们就能这样写代码：

```c++
bool is_power_of_two(int m) {
    return m > 0 && (m & (m - 1) == 0);
}

int mod_power_of_two(int x, int m)
    [[ expects: x >= 0 ]]
    [[ expects: is_power_of_two(m) ]]
    [[ ensures r: r >= 0 && r < m ]]
{
    int r = x & (m - 1);
    [[ assert: r = x % m ]];
    return r;
}
```

其他面向性能的语言也有契约编程的某种形式，比如 [Rust](https://docs.rs/contracts/latest/contracts/) 和 [D](https://dlang.org/spec/contracts.html)。

一条与语言无关的通用建议：总是去[检查编译器产出的汇编](../stages)，如果它不是你期望的样子，就想一想可能是哪些角落情况在限制编译器优化。
