---
title: "[草稿]进程"
weight: 1
draft: true
---

在你需要的时候它工作得很好。

fork 系统调用用于创建新进程，新进程称为子进程（child process），它与发起 fork() 调用的进程（父进程，parent process）并发运行。新的子进程创建之后，两个进程都会执行紧跟在 fork() 系统调用之后的下一条指令。子进程使用与父进程相同的程序计数器（program counter）、相同的 CPU 寄存器，以及父进程中打开的相同文件。

它不接收参数，返回一个整数值。下面是 fork() 返回的不同取值。

```cpp
#include <stdio.h> 
#include <sys/types.h> 
#include <unistd.h> 
int main() { 
    // make two process which run same 
    // program after this instruction 
    fork(); 
  
    printf("Hello world!\n"); 
    return 0; 
} 
```

主要缺点是额外的开销。它由操作系统管理。当你需要这种粒度时，就会使用独立的进程。

fork 出来的进程既看不见、也无法修改彼此的内存空间。
