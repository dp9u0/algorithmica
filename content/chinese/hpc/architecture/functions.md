---
title: 函数与递归
weight: 3
draft: true
---

在汇编里"调用函数"就是[跳转](../loops)到它的开头，然后再跳回来。但这样一来两个重要的问题就出现了：

1. 如果调用者和被调用者把数据存在同一批寄存器里怎么办？
2. "回来"是回到哪里？

两个问题都能用同一个办法解决：在内存里划出一块专用位置，调用函数之前把返回所需的全部信息写进去。这块位置叫*栈*（stack）。

### 栈 {#the-stack}

硬件上的栈和软件里的栈工作方式一样，同样只用两个指针实现：

- *基指针*（base pointer）标记栈的起点，按惯例存在 `rbp`。
- *栈指针*（stack pointer）标记栈的最后一个元素，按惯例存在 `rsp`。

调用函数时，把所有局部变量压栈（其他场合也可以这么做，比如寄存器不够用的时候），再把当前指令指针压栈，然后跳到函数开头。函数退出时，读取栈顶存的指针、跳回去，再小心翼翼地把栈上存的变量读回各自的寄存器。

<!--

Function parameters and local variables are accessed by adding and subtracting, respectively, a constant offset from `ebp`.

ebp itself actually points to the previous frame's base pointer, which enables stack walking in a debugger and viewing other frames local variables to work. Fun things, such as stopping the program and seeing which functions are called by which.

push ebp      ; Preserve current frame pointer
mov ebp, esp  ; Create new frame pointer pointing to current stack top
sub esp, 20   ; allocate 20 bytes worth of locals on stack.

frame pointer omission optimization which you can enable will actually eliminate this and use ebp as another register and access locals directly off of esp, but this makes debugging a bit more difficult since the debugger can no longer directly access the stack frames of earlier function calls.

When a function starts, it executed a *function prologue*: saves the previous base pointer on the stack and sets `rbp = rsp`.

-->

这些都可以用常规的内存操作加跳转来实现，但由于使用频率极高，硬件专门提供了 4 条指令：

- `push` 把数据写到栈指针处，并递减栈指针。
- `pop` 从栈指针处读数据，并递增栈指针。
- `call` 把下一条指令的地址压到栈顶，然后跳到某个标记。
- `ret` 从栈顶读出返回地址并跳过去。

如果它们不是真正的硬件指令，你会叫它们"语法糖"——它们不过是下面这些两条指令组合的融合等价物：

```nasm
; "push rax"
sub rsp, 8
mov QWORD PTR[rsp], rax

; "pop rax"
mov rax, QWORD PTR[rsp]
add rsp, 8

; "call func"
push rip ; <- instruction pointer (although accessing it like that is probably illegal)
jmp func

; "ret"
pop  rcx ; <- choose any unused register
jmp rcx
```

`rbp` 和 `rsp` 之间的内存区域叫*栈帧*（stack frame），函数的局部变量通常就存放在这里。它在程序启动时预分配，如果压栈的数据超过其容量（Linux 上默认 8MB），就会遇到*栈溢出*（stack overflow）错误。由于现代操作系统在你读写地址空间之前并不真正分配内存页，你可以随意指定一个非常大的栈大小——它更像一个"最多能用多少"的上限，而不是每个程序都必须占用的固定量。

<!--

It is convenient to save the frame pointer `rbp` at the beginning of a function and replace it with `rsp` — this way, when leaving a function, you could just restore `rbp` and forget about all its local variables. This sequence is called *function prologue* and usually looks somewhat like that (which is often optimized away by the compiler):

```nasm
push rbp     ; preserve the current frame pointer
mov rbp, rsp ; create a new frame pointer pointing to the current top of the stack
sub rsp, 20  ; allocate 20 bytes worth of locals on stack
```

-->

<!--
The memory region dedicated for stack memory (called *stack frame*) is not any different from any other memory region. It is allocated on the start of the program. You could also do tricky stuff, such as

Functions execute a *prologue* which usually looks somewhat like that:

```nasm
push rbp     ; preserve the current frame pointer
mov rbp, rsp ; create a new frame pointer pointing to the current top of the stack
sub rsp, 20  ; allocate 20 bytes worth of locals on stack
```

Note that the data in the stack is written top-to-bottom. This is just a convention: it could be the other way around. When you need to "leave" a function or a visibility scope such as the body of an `if` or a `for`, you can just increase the stack pointer.

-->

### 调用约定 {#calling-conventions}

开发编译器和操作系统的人最终制定了如何编写和调用函数的[约定](https://wiki.osdev.org/Calling_Conventions)。这些约定成就了一些重要的[软件工程奇迹](/hpc/compilation/stages/)：把编译拆分成独立单元、复用已编译的库、甚至用不同的编程语言来写它们。

看下面这个 C 例子：

```c
int square(int x) {
    return x * x;
}

int distance(int x, int y) {
    return square(x) + square(y);
}
```

<!--

When compiled without any optimization flags, it produces the following assembly:

```nasm
square:
    push    rbp
    mov     rbp, rsp
    mov     DWORD PTR [rbp-4], edi
    mov     eax, DWORD PTR [rbp-4]
    imul    eax, eax
    pop     rbp
    ret
length:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 8
    mov     DWORD PTR [rbp-12], edi
    mov     DWORD PTR [rbp-16], esi
    mov     eax, DWORD PTR [rbp-12]
    mov     edi, eax
    call    square
    mov     ebx, eax
    mov     eax, DWORD PTR [rbp-16]
    mov     edi, eax
    call    square
    add     eax, ebx
    mov     rbx, QWORD PTR [rbp-8]
    leave
    ret
```
-->

按约定，函数应从 `rdi`、`rsi`、`rdx`、`rcx`、`r8`、`r9` 取参数（不够时其余走栈），把返回值放进 `rax`，然后返回。于是 `square` 这个简单的单参数函数可以这样实现：

```nasm
square:             ; x = edi, ret = eax
    imul edi, edi
    mov  eax, edi
    ret
```

每次从 `distance` 调用它，我们只需费点周折保护自己的局部变量：

```nasm
distance:           ; x = rdi/edi, y = rsi/esi, ret = rax/eax
    push rdi
    push rsi
    call square     ; eax = square(x)
    pop  rsi
    pop  rdi

    mov  ebx, eax   ; save x^2
    mov  rdi, rsi   ; move new x=y

    push rdi
    push rsi
    call square     ; eax = square(x=y)
    pop  rsi
    pop  rdi

    add  eax, ebx   ; x^2 + y^2
    ret
```

其中还有很多细节，但我们不深入了——这本书讲的是性能，而对付函数调用的最好办法其实是一开始就别调用。

### 内联 {#inlining}

对这样的小函数，数据进出栈会产生可观的额外开销。之所以必须这么做，是因为一般情况下你不知道被调用者会不会改写你存放局部变量的寄存器。但当你能看到 `square` 的代码时，这个问题就解了：把数据存进你确信不会被改动的寄存器即可。

```nasm
distance:
    call square
    mov  ebx, eax
    mov  edi, esi
    call square
    add  eax, ebx
    ret
```

这样好些了，但我们仍在隐式地访问栈内存：每次函数调用都要压入和弹出指令指针。在这种简单情况下，我们可以*内联*（inline）函数调用——把被调用者的代码缝进调用者，并解决寄存器冲突。对我们的例子：

```nasm
distance:
    imul edi, edi       ; edi = x^2
    imul esi, esi       ; esi = y^2
    add  edi, esi
    mov  eax, edi       ; there is no "add eax, edi, esi", so we need a separate mov
    ret
```

这已经相当接近优化编译器对这段代码的产出了——它们只是用 [lea 技巧](../assembly)让最终的机器码序列再短几个字节：

```nasm
distance:
    imul edi, edi       ; edi = x^2
    imul esi, esi       ; esi = y^2
    lea  eax, [rdi+rsi] ; eax = x^2 + y^2
    ret
```

在这类场景下，函数内联显然是划算的，编译器也大多[自动](/hpc/compilation/situational)这么做；但也有不划算的时候——我们[稍后](../layout)会讲。

### 尾调用消除 {#tail-call-elimination}

当被调用者不再调用其他函数、或至少调用不是递归的时候，内联是直接了当的。来看一个更复杂的例子。这是阶乘的递归计算：

```cpp
int factorial(int n) {
    if (n == 0)
        return 1;
    return factorial(n - 1) * n;
}
```

等价的汇编：

```nasm
; n = edi, ret = eax
factorial:
    test edi, edi   ; test if a value is zero
    jne  nonzero    ; (the machine code of "cmp rax, 0" would be one byte longer)
    mov  eax, 1     ; return 1
    ret
nonzero:
    push edi        ; save n to use later in multiplication
    sub  edi, 1
    call factorial  ; call f(n - 1)
    pop  edi
    imul eax, edi
    ret
```

如果函数是递归的，通常仍有可能通过重构让它"无调用"。当函数是*尾递归*（tail recursive）的时候就可以——即它在递归调用之后立即返回。由于调用之后不需要再做任何事，也就无需在栈上保存任何东西，递归调用可以安全地替换成一条跳到开头的跳转——实际上把函数变成了循环。

要让 `factorial` 尾递归，可以给它传一个"当前乘积"参数：

```cpp
int factorial(int n, int p = 1) {
    if (n == 0)
        return p;
    return factorial(n - 1, p * n);
}
```

于是这个函数可以轻松折叠成循环：

```nasm
; assuming n > 0
factorial:
    mov  eax, 1
loop:
    imul eax, edi
    sub  edi, 1
    jne  loop
    ret
```

递归可能慢的主要原因是它需要往栈里读写数据，而迭代和尾递归算法不用。这个概念在函数式编程中非常重要——那里没有循环，你能用的只有函数。没有尾调用消除，函数式程序的执行将需要多得多的时间和内存。
