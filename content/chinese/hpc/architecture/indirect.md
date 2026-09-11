---
title: 间接跳转
weight: 4
---

汇编的标记在汇编阶段被转换成地址（绝对或相对），然后编码进跳转指令。

你也可以跳到一个存在寄存器里的非恒定值，这叫*计算跳转*（computed jump）：

```nasm
jmp rax
```

它有一些与动态语言和更复杂控制流实现相关的有趣应用。

### 多路分支

如果你已经忘了 `switch` 语句是干什么的，这里有一个计算美国绩点（GPA）的小子程序：

```cpp
switch (grade) {
    case 'A':
        return 4.0;
        break;
    case 'B':
        return 3.0;
        break;
    case 'C':
        return 2.0;
        break;
    case 'D':
        return 1.0;
        break;
    case 'E':
    case 'F':
        return 0.0;
        break;
    default:
        return NAN;
}
```

我自己想不起上一次在非教学场景里用 switch 是什么时候了。一般而言，switch 语句等价于一串"if、else if、else if、else if……"，因此很多语言干脆没有它。尽管如此，这类控制流结构对实现解析器、解释器和其他状态机很重要——它们通常就是一个 `while (true)` 循环套一个 `switch (state)`。

当变量可能的取值范围由我们掌控时，可以用计算跳转玩下面这个技巧。不必做 $n$ 次条件分支，我们可以建一张*分支表*（branch table），存放各个可能跳转位置的指针/偏移，然后直接用取值在 $[0, n)$ 区间的 `state` 变量做下标。

当取值密集地挤在一起时（不一定严格连续，但表里留空位得划算），编译器会采用这个技术。它也可以用*computed goto* 显式实现：

```cpp
void weather_in_russia(int season) {
    static const void* table[] = {&&winter, &&spring, &&summer, &&fall};
    goto *table[season];

    winter:
        printf("Freezing\n");
        return;
    spring:
        printf("Dirty\n");
        return;
    summer:
        printf("Dry\n");
        return;
    fall:
        printf("Windy\n");
        return;
}
```

基于 switch 的代码对编译器来说并不总是好优化，所以在状态机的语境下，人们经常直接用 `goto`。`glibc` 里 I/O 相关的部分满是例子。

### 动态派发

间接跳转也是实现运行时多态的关键。

考虑那个老掉牙的例子：一个抽象类 `Animal` 带虚方法 `.speak()`，两个具体实现：会汪汪的 `Dog` 和会喵喵的 `Cat`：

```cpp
struct Animal {
    virtual void speak() { printf("<abstract animal sound>\n");}
};

struct Dog {
    void speak() override { printf("Bark\n"); }
};

struct Cat {
    void speak() override { printf("Meow\n"); }
};
```

我们想创建一个动物，并在不预知其类型的情况下调用 `.speak()` 方法——它应该设法调用正确的实现：

```c++
Dog sparkles;
Cat mittens;

Animal *catdog = (rand() & 1) ? &sparkles : &mittens;
catdog->speak();
```

实现这个行为有很多方式，C++ 用的是*虚方法表*（virtual method table）。

对 `Animal` 的所有具体实现，编译器把它们的全部方法（即指令序列）填充对齐，使每个类中的长度完全一致（在 `ret` 后面插一些[填充指令](../layout)），然后按顺序把它们写进指令内存的某处。接着它向结构体（即所有实例）添加一个*运行时类型信息*字段，本质上就是内存区域中的一个偏移，指向该类虚方法的正确实现。

发起虚方法调用时，这个偏移字段从结构体实例中取出，用它完成一次普通的函数调用——利用的是"每个派生类的所有方法和其他字段都有完全相同的偏移"这一事实。

当然，这带来一些开销：

- 出于与[分支预测失败](/hpc/pipelining)相同的流水线冲刷原因，你可能要多花 15 个周期左右。
- 编译器很可能无法内联这次函数调用。
- 类的大小增加若干字节（视实现而定）。
- 二进制体积本身也会增大一点。

因此，在性能关键的应用中，运行时多态通常是被回避的。
