---
title: 汇编语言
weight: 1
draft: true
---

CPU 由*机器语言*控制——它就是一串二进制编码的指令，每条指令指明

- 指令编号（叫*操作码*，opcode），
- 它的*操作数*是什么（如果有），
- 以及*结果*存到哪里（如果会产生结果）。

机器语言的一种对人类友好得多的表现形式叫*汇编语言*：用助记符指代机器码指令，用符号名指代寄存器和其他存储位置。

直接上手，这是在 Arm 汇编里把两个数相加（`*c = *a + *b`）的方法：

```nasm
; *a = x0, *b = x1, *c = x2
ldr w0, [x0]    ; load 4 bytes from wherever x0 points into w0
ldr w1, [x1]    ; load 4 bytes from wherever x1 points into w1
add w0, w0, w1  ; add w0 with w1 and save the result to w0
str w0, [x2]    ; write contents of w0 to wherever x2 points
```

同样的操作，x86 汇编是这样的：

```nasm
; *a = rsi, *b = rdi, *c = rdx
mov eax, DWORD PTR [rsi]  ; load 4 bytes from wherever rsi points into eax
add eax, DWORD PTR [rdi]  ; add whatever is stored at rdi to eax
mov DWORD PTR [rdx], eax  ; write contents of eax to wherever rdx points
```

汇编非常"简单"，意思是它没有多少语法结构，跟高级编程语言比不了。从上面的例子可以观察到：

- 程序就是一条指令的序列，每条指令写成名字后跟数量不定的操作数。
- `[reg]` 语法用来"解引用"寄存器里存的指针；在 x86 上还要加尺寸前缀（这里的 `DWORD` 表示 32 位）。
- `;` 是行注释，类似其他语言里的 `#` 和 `//`。

汇编是一门极简语言，因为它必须如此。它尽可能贴近机器语言，直到机器码与汇编几乎一一对应。事实上，你可以把任何编译好的程序通过一个叫*反汇编*（disassembly）[^disassembly] 的过程还原成汇编形式——尽管注释这类非本质信息不会保留。

[^disassembly]: 在 Linux 上，反汇编一个编译好的程序可以执行 `objdump -d {path-to-binary}`。

注意，上面两段代码不只是语法不同。两者都是编译器优化后的代码，但 Arm 版本用了 4 条指令，x86 版本只用 3 条。`add eax, [rdi]` 这条指令就是所谓的*融合指令*（fused instruction），一条指令同时完成读取和相加——这是 [CISC](../isa#risc-vs-cisc) 路线的福利之一。

两种架构之间的差异远不止这一处，所以从现在起到全书结束，我们只提供 x86 的例子——这大概是多数读者要优化的平台——尽管介绍的许多概念与架构无关。

### 指令与寄存器 {#instructions-and-registers}

出于历史原因，大多数汇编语言的指令助记符都极其简短。在过去人们手写汇编、反复输入同一批常用指令的年代，少敲一个字符就离疯掉远一步。

比如 `mov` 是 "store/load a word"，`inc` 是 "increment by 1"，`mul` 是 "multiply"，`idiv` 是 "integer division"。可以[在 x86 参考手册](https://www.felixcloutier.com/x86/)里按名字查指令的描述，不过大多数指令干的就是你以为它们干的事。

大多数指令把结果写进第一个操作数，而这个操作数也可以参与运算，就像之前 `add eax, [rdi]` 的例子。操作数可以是寄存器、常量或内存位置。

**寄存器**的名字是 `rax`、`rbx`、`rcx`、`rdx`、`rdi`、`rsi`、`rbp`、`rsp` 以及 `r8`–`r15`，共 16 个。"字母系"的名字来自历史：`rax` 是 "accumulator"（累加器），`rcx` 是 "counter"（计数器），`rdx` 是 "data"（数据），等等——当然，它们并不只能干这些。

还有 32 位、16 位和 8 位的寄存器，名字相近（`rax` → `eax` → `ax` → `al`）。它们并非完全独立，而是*别名*（aliased）关系：`rax` 的低 32 位就是 `eax`，`eax` 的低 16 位就是 `ax`，依此类推。这是为了省晶片面积同时保持兼容，也是编译型语言里基本类型转换通常零开销的原因。

以上只是*通用*寄存器，除[少数例外](../functions)外你可以在大多数指令里随意使用。还有一组专用于[浮点运算](/hpc/arithmetic/float)的寄存器、一组用在[向量扩展](/hpc/simd)里的超宽寄存器，以及几个[控制流](../loops)需要的特殊寄存器——到时候再说。

**常量**就是整数或浮点数值：`42`、`0x2a`、`3.14`、`6.02e23`。它们更常被叫作*立即数*（immediate values），因为它们直接嵌在机器码里。由于会显著增加指令编码的复杂度，有些指令不支持立即数，或只允许固定的子集；某些情况下你得先把常量加载进寄存器再用。

除了数值，还有 `hello`、`world\n` 这样的字符串常量，有自己的一小套操作——但那是汇编语言里比较冷门的角落，这里不展开。

### 移动数据 {#moving-data}

有些指令的助记符相同，但操作数类型不同，此时它们被视为不同的指令——因为实际执行的操作略有差异，耗时也不同。`mov` 就是个鲜活的例子：它有大约 20 种形式，都与搬数据有关：在内存和寄存器之间，或两个寄存器之间。尽管名字叫 "move"，它并不把值*移动*进寄存器，而是*复制*，保留原值。

在两个寄存器之间复制数据时，`mov` 实际上在内部执行*寄存器重命名*（register renaming）——告知 CPU：寄存器 X 引用的值其实存在寄存器 Y 里——除了读取和译码指令本身，不产生任何额外延迟。同理，交换两个寄存器的 `xchg` 指令也不花什么代价。

正如上面融合的 `add` 所示，并非每次内存操作都要用 `mov`：一些算术指令本身就支持把内存位置当操作数。

<!--

Some operations are fused like `add r m` or `inc m` (this is one of the rare instructions that doesn't use any register values as operands).

When address is used,

Mirroring

-->

### 寻址模式 {#addressing-modes}

内存寻址用 `[]` 运算符，但它能做的不只是把寄存器里的值重解释为内存位置。地址操作数在语法上最多接受 4 个参数：

```
SIZE PTR [base + index * scale + displacement]
```

其中 `displacement` 必须是整数常量，`scale` 只能取 2、4 或 8。它计算指针 `base + index * scale + displacement` 然后解引用。

<!-- You can use them in any order: the assembler will figure it out. -->

使用复杂寻址比直接解引用指针[至多多花一个周期](/hpc/cpu-cache/pointers)，当你有一个结构体数组、想加载其中第 $i$ 个元素的某个字段时，它会很有用。

寻址运算符前面要加尺寸说明符，指明需要多少位数据：

- `BYTE` 8 位
- `WORD` 16 位
- `DWORD` 32 位
- `QWORD` 64 位

还有更少见的 `TBYTE`（[80 位](/hpc/arithmetic/float)），以及对应 [128、256、512 位](/hpc/simd)的 `XMMWORD`、`YMMWORD`、`ZMMWORD`。这些类型不必大写，但多数编译器就是大写输出的。

地址计算本身常常就有用：`lea`（"load effective address"）指令用一个周期算出操作数的内存地址并存进寄存器，不做任何真正的内存操作。它的本职是计算内存地址，但也常被当作算术技巧——替代一次乘法加两次加法——比如可以用它乘以 3、5、9。

它还经常顶替 `add`：如果你想把结果放到别处，`add` 只能工作在两寄存器的 `a += b` 模式，而 `lea` 能写 `a = b + c`（甚至 `a = b + c + d`，只要其中一个是常量），省去单独的 `mov`。

### 另一套语法 {#alternative-syntax}

实际上有很多*汇编器*（把汇编变成机器码的程序），各自有不同的汇编语言，但 x86 只有两套语法被广泛使用。人们习惯以当年使用它们、并对那个时代的编程有支配性影响的两家公司来称呼：

- *AT&T 语法*，所有 Linux 工具的默认选择。
- *Intel 语法*，默认嘛，就是 Intel 在用的。

这两套语法有时也分别叫 *GAS* 和 *NASM*，来自使用它们的两款主要汇编器（*GNU Assembler* 和 *Netwide Assembler*）。

本章用的是 Intel 语法，全书也会优先沿用。作为对比，同一个 `*c = *a + *b` 例子在 AT&T 汇编里是这样的：

```asm
movl (%rsi), %eax
addl (%rdi), %eax
movl %eax, (%rdx)
```

主要差异总结如下：

1. *最后一个*操作数是目的。
2. 寄存器和常量分别要加 `%` 和 `$` 前缀（例如 `addl $1, %rdx` 把 `rdx` 加 1）。
3. 内存寻址写成 `displacement(%base, %index, scale)`。
4. `;` 和 `#` 都能用作行注释，`/* */` 可用作块注释。

最重要的，AT&T 语法里指令名要加"后缀"（`addq`、`movl`、`cmpq` 等），用来指明操作多大的操作数：

- `b` = byte（8 位）
- `w` = word（16 位）
- `l` = long（32 位整数或 64 位浮点）
- `q` = quad（64 位）
- `s` = single（32 位浮点）
- `t` = ten bytes（80 位浮点）

Intel 语法里这些信息从操作数推断（这也是为什么你需要指明指针的大小）。

多数产生或消费 x86 汇编的工具两种语法都支持，挑喜欢的用就行，不用纠结。
