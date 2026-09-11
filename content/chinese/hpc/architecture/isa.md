---
title: 指令集架构
weight: -1
draft: true
---

作为软件工程师，我们对构建和使用抽象有着发自内心的热爱。

想想加载一个 URL 时发生了多少事情：你在键盘上敲字；按键以某种方式被操作系统检测到并发给浏览器；浏览器解析 URL 并请求操作系统发起网络访问；接着是 DNS、路由、TCP、HTTP 和 OSI 的其他各层；浏览器解析 HTML；JavaScript 施展魔法；页面的某种表示被送进 GPU 渲染；图像帧被发往显示器……而其中每一步大概还各自牵扯几十件更具体的事。

抽象帮我们把这一切复杂度压缩成一个单一的*接口*——它描述某个*模块*能做什么，而不规定具体实现。这带来双重好处：

- 工作在更高层模块上的工程师只需要知道（小得多的）接口。
- 工作在模块本身的工程师获得优化与重构实现的自由，只要遵守接口的*契约*。

硬件工程师同样热爱抽象。CPU 的抽象叫*指令集架构*（instruction set architecture，ISA），它从程序员的视角定义了一台计算机应该如何工作。与软件接口类似，它既让计算机工程师可以持续改进现有的 CPU 设计，也让它的使用者——也就是我们程序员——确信以前能工作的东西不会在新芯片上坏掉。

ISA 本质上定义了硬件应如何解释机器语言。除了指令及其二进制编码，ISA 还规定了寄存器的数量、大小与用途、内存模型以及输入/输出模型。与软件接口类似，ISA 也可以扩展：实际上它们经常被更新，多数时候以向后兼容的方式，添加新的、更专用的指令来提升性能。

### RISC 与 CISC

历史上曾有许多相互竞争的 ISA 在使用。但与[字符编码和即时通讯协议](https://xkcd.com/927/)不同，开发并维护一套完全独立的 ISA 代价高昂，所以主流 CPU 设计最终收敛到两个家族：

- **Arm** 芯片，几乎用于所有移动设备，以及其他类计算机设备：电视、智能冰箱、微波炉、[汽车自动驾驶](https://en.wikipedia.org/wiki/Tesla_Autopilot)等等。它们由同名的英国公司设计，也包括 Apple 和 Samsung 在内的一批电子厂商。
- **x86**[^x86] 芯片，几乎用于所有服务器和桌面机，但有几个著名的例外——Apple 的 M1 MacBook、AWS 的 Graviton 处理器，以及[当时世界最快的超级计算机](https://en.wikipedia.org/wiki/Fugaku_(supercomputer))——它们都用基于 Arm 的 CPU。x86 由 Intel 和 AMD 双寡头设计。

[^x86]: x86 的现代 64 位版本被称为 "AMD64"、"Intel 64"，或更中立的 "x86-64" / "x64"。Arm 类似的 64 位扩展叫 "AArch64" 或 "ARM64"。本书直接用朴素的 "x86" 和 "Arm"，均指 64 位版本。

两者的主要区别在于架构复杂度——这更像一种设计哲学，而不是什么严格定义的属性：

- Arm CPU 是*精简*指令集计算机（RISC）。它靠保持指令集小而高度优化来提升性能，不过一些不常用的操作得用包含多条指令的子程序来实现。
- x86 CPU 是*复杂*指令集计算机（CISC）。它靠添加大量专用指令来提升性能，其中一些在实际程序里可能很少用到。

RISC 设计的主要优势是芯片更简单更小，这意味着更低的制造成本和功耗。于是市场自然分化：Arm 统治了电池供电的通用设备，而把复杂的神经网络和伽罗瓦域计算留给服务器级、高度专用的 x86。

<!--

The two architectures are functionally similar, both sharing concepts such as pipelines, execution ports, and SIMD instructions, but since most readers are interested in optimizing applications for mainstream servers and desktops, we will mainly focus on x86 in this book.

-->
