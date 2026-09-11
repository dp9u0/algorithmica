---
title: 循环与条件
weight: 2
---

来看一个稍微复杂点的例子：

```nasm
loop:
    add  edx, DWORD PTR [rax]
    add  rax, 4
    cmp  rax, rcx
    jne  loop
```

它计算一个 32 位整数数组的和，正如一个简单的 `for` 循环所做的那样。

循环的"主体"是 `add edx, DWORD PTR [rax]`：这条指令从迭代器 `rax` 指向的位置加载数据，加到累加器 `edx` 上。接着用 `add rax, 4` 把迭代器前移 4 字节。然后，发生了一件稍微复杂的事。

### 跳转

汇编没有 if、for、函数这些高级语言的控制流结构。它有的是 `goto`——在底层编程的世界里叫"跳转"（jump）。

**跳转**把指令指针移到操作数指定的位置。这个位置可以是内存里的绝对地址、相对当前地址的偏移，甚至是[运行时计算出来的](../indirect)。为了免去直接管理这些地址的头痛，你可以在任意指令前放一个以 `:` 结尾的字符串作为标记（label），转换成机器码时它会被替换成这条指令的相对地址。

标记可以是任意字符串，但编译器并不发挥创意，[通常](https://godbolt.org/z/T45x8GKa5)直接用源码行号，或函数名加签名来命名。

**无条件**跳转 `jmp` 只能用来实现 `while (true)` 式的死循环，或者把程序的各个部分拼起来；真正的控制流靠一族**条件**跳转。

你大概会以为这些条件是在某处算好的 `bool` 值、再作为操作数传给条件跳转——毕竟编程语言里就是这么干的。但硬件不是这样实现的。条件操作使用一个特殊的 `FLAGS` 寄存器，需要先执行执行某种检查的指令来填充它。

在我们的例子里，`cmp rax, rcx` 把迭代器 `rax` 与数组末尾指针 `rcx` 作比较。这会更新 `FLAGS` 寄存器，然后 `jne loop` 就能使用它：查其中某一位来判断两个值是否相等，进而要么跳回开头，要么继续执行下一条指令——循环就此结束。

### 循环展开

关于上面的循环，你可能已经注意到：每处理一个元素都有很大的开销。每个周期只有一条指令是有用的，另外 3 条都在递增迭代器、判断是否做完。

我们能做的是把迭代分组*展开*（unroll）循环——等价于在 C 里写成：

```c++
for (int i = 0; i < n; i += 4) {
    s += a[i];
    s += a[i + 1];
    s += a[i + 2];
    s += a[i + 3];
}
```

在汇编里则是这样：

```nasm
loop:
    add  edx, [rax]
    add  edx, [rax+4]
    add  edx, [rax+8]
    add  edx, [rax+12]
    add  rax, 16
    cmp  rax, rsi
    jne  loop
```

现在 4 条有用的指令只需 3 条循环控制指令（效率从 $\frac{1}{4}$ 提升到 $\frac{4}{7}$），继续展开可以把开销压到几乎为零。

实践中，展开循环并不总是性能必需的，因为现代处理器并不真的逐条执行指令，而是维护一个[待执行指令队列](/hpc/pipelining)，让两个独立的操作并发执行、互不等待。

我们的例子正是如此：展开带来的真实加速不会是四倍，因为递增计数器和判断是否结束的操作与循环体相互独立，可以被调度成与循环体并发。不过，[让编译器](/hpc/compilation/situational)做一定程度的展开仍然可能有益。

### 另一种做法

条件跳转不一定非要显式使用 `cmp` 之类的指令。许多其他指令会读取或修改 `FLAGS` 寄存器，有时是作为启用可选异常检查的副产品。

例如 `add` 总会设置一组标志位：结果是否为零、是否为负、是否发生上溢或下溢，等等。利用这个机制，编译器经常生成这样的循环：

```nasm
    mov  rax, -100  ; replace 100 with the array size
loop:
    add  edx, DWORD PTR [rax + 100 + rcx]
    add  rax, 4
    jnz  loop       ; checks if the result is zero
```

这段代码对人来说更难读，但重复部分少了一条指令，而这一条可能切实影响性能。

<!--

### A More Complex Example

Let's do a more complicated example.

```c++
int collatz(int n) {
    int cnt = 0;
    while (n != 1) {
        cnt++;
        if (n & 2 == 1)
            n = 3 * n + 1;
        else
            n = n / 2;
    }
    return cnt;
}
```

It is a notoriously difficult math problem that seems ridiculously simple.

Make use of [lea instruction](../assembly).

E.g., if you want to make a computational experiment [Collatz conjecture](https://en.wikipedia.org/wiki/Collatz_conjecture), you may use `lea rax, [rax + rax * 2 + 1]`, and then try to `sar` it.

Another way is to check add.

Eliminating branching. Or at least making it easier for the compiler to predict which instructions are going to be executed next.

tzcnt

cmov

Need to somehow link it to branchless programming and layout article. We now have 3 places introducing the concept.

Many other operations set something in the `FLAGS` register. For example, add often. It is useful to, and then decrement or increment it to save on instruction. Like a while loop:

```
while (n--) {
    // ...
}
```

There is an important "conditional move" operation.

-->
