---
title: "[草稿]中断与系统调用"
weight: 9
draft: true
---

```asm
global _start

section .text

_start:
  mov rax, 1        ; write(
  mov rdi, 1        ;   STDOUT_FILENO,
  mov rsi, msg      ;   "Hello, world!\n",
  mov rdx, msglen   ;   sizeof("Hello, world!\n")
  syscall           ; );

  mov rax, 60       ; exit(
  mov rdi, 0        ;   EXIT_SUCCESS
  syscall           ; );

section .rodata
  msg: db "Hello, world!", 10
  msglen: equ $ - msg
```

中断（interrupt）的代价很高。它们不应该出现在正常的执行路径上。异常（exception）。

执行系统调用（system call）会带来一些开销，因此通常会尽量避免。例如，所有的 I/O 通常都会经过缓冲，这样你发给操作系统的就是单独一块——比如说 4KB——的数据。
