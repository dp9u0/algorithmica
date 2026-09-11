---
title: 现代硬件
weight: 1
ignoreIndexing: true
---

1960 年代超级计算机的主要缺点不在于慢——相对而言它们并不慢——而在于它们体型巨大、使用复杂、昂贵到只有超级大国的政府才买得起。体积正是昂贵的原因：它们需要大量定制元件，得由拿着电气工程高等学位的人在宏观世界里极其小心地组装，这样的流程无法规模化量产。

转折点是*微芯片*（microchip）的发明——单个微小的完整电路——它革新了整个行业，堪称 20 世纪最重要的发明。1965 年价值数百万美元的一柜计算机，到 1975 年可以塞进一片[4mm × 4mm 的硅片](https://en.wikipedia.org/wiki/MOS_Technology_6502)[^size]，花 25 美元就能买到。可负担性的这一飞跃在随后十年引发了家用计算机革命，Apple II、Atari 2600、Commodore 64 和 IBM PC 等计算机走进了大众生活。

[^size]: 实际 CPU 的尺寸大约在厘米量级，这是为了功耗管理、散热，以及能把它插上主板而不骂骂咧咧。

### 微芯片是怎样造出来的 {#how-microchips-are-made}

微芯片是用一种叫[光刻](https://en.wikipedia.org/wiki/Photolithography)的工艺"印"在晶硅片上的，大致包括：

1. 生长并切割出[极纯净的硅晶体](https://en.wikipedia.org/wiki/Wafer_(electronics))，
2. 覆盖一层[光子打上去会溶解的物质](https://en.wikipedia.org/wiki/Photoresist)，
3. 按预定图案用光子轰击，
4. 化学[蚀刻](https://en.wikipedia.org/wiki/Etching_(microfabrication))掉暴露出来的部分，
5. 清除剩余的光刻胶，

……然后再花上几个月做掉剩下的 40–50 道工序，一枚 CPU 才算完成。

![](/en/hpc/complexity/img/lithography.png)

现在来看"用光子轰击"这一步。我们可以用一组透镜把图案投影到小得多的区域上，等效于制造出一个具备全部所需特性的微型电路。靠这个办法，1970 年代的光学就能在指甲盖大小的面积上塞进几千个晶体管，这给微芯片带来了宏观世界计算机所不具备的几个关键优势：

- 更高的时钟频率（此前受限于光速）；
- 生产可规模化；
- 低得多的材料和功耗，对应低得多的单件成本。

除了这些立竿见影的好处，光刻还给出了一条清晰的性能提升路径：只要把透镜做得更强大，就能以相对小的代价造出更小但功能等价的器件。

### 登纳德缩放 {#dennard-scaling}

想想把微芯片按比例缩小会发生什么。更小的电路按比例需要更少的材料，更小的晶体管翻转得更快（芯片里所有其他物理过程也随之加快），于是可以降低电压、提高时钟频率。

一个更细致的观察被称为*登纳德缩放*（Dennard scaling）：晶体管尺寸每缩小 30%

- 晶体管密度翻倍（$0.7^2 \approx 0.5$），
- 时钟速度提高 40%（$\frac{1}{0.7} \approx 1.4$），
- 而*功率密度*保持不变。

由于单件制造成本是面积的函数，使用成本又主要是电费[^power]，所以每一代"新工艺"的总成本大致不变，却拥有高 40% 的时钟和翻倍的晶体管——这些晶体管可以立刻派上用场，比如添加新指令或增大字长，以跟上内存芯片同样的微型化步伐。

[^power]: 一台满载服务器运行 2–3 年的电费，大致等于制造这颗芯片本身的花费。

由于设计上可以在能耗与性能之间做权衡，制造工艺本身的保真度——比如"180nm"或"65nm"，直接对应晶体管密度——成了 CPU 效率的招牌指标[^fidelity]。

[^fidelity]: 到了某个时候，随着摩尔定律开始放缓，芯片厂商不再按器件实际尺寸标注工艺——它现在更像一个营销术语。有个[特别委员会](https://en.wikipedia.org/wiki/International_Technology_Roadmap_for_Semiconductors)每两年开一次会，拿上一个节点的名字除以根号二，四舍五入到最近的整数，宣布这就是新节点的名字，然后喝掉大量的酒。"nm"已经不再是纳米的意思了。

在整个计算史的大部分时间里，光学微缩是性能提升背后的主引擎。英特尔前 CEO 戈登·摩尔在 1975 年预测：微处理器中的晶体管数量每两年翻一番。这个预测一直成立到今天，被称为*摩尔定律*。

![](/en/hpc/complexity/img/dennard.ppm)

登纳德缩放和摩尔定律都不是真正的物理定律，只是精明的工程师们做出的经验观察。它们注定会在某个时刻因为根本性的物理限制而停下来，最终的极限是硅原子的尺寸。事实上，登纳德缩放已经停了——因为功耗问题。

从热力学角度看，计算机只是一台把电能转化为热的高效装置。这些热最终必须被散掉，而从毫米尺度的晶片上能散出的功率有物理上限。以性能最大化为目标的计算机工程师，本质上就是选择一个尽可能高的时钟频率，让总功耗维持不变。晶体管变小，电容就变小，翻转所需的电压随之降低，反过来又允许提高时钟频率。

大约在 2005–2007 年，这条路线因为*漏电*（leakage）效应失效了：电路的特征尺寸小到一定程度，它们的磁场开始让邻近电路中的电子朝不该去的方向移动，造成无谓的发热和偶尔的比特翻转。

唯一的缓解办法是提高电压；而为了平衡功耗又得降低时钟频率，这使得随着晶体管密度增加，整个流程的收益越来越差。到了某个节点，时钟频率再也无法靠微缩来提升，微型化趋势开始放缓。

<!--

### Power Efficiency

It may come as a surprise, but the primary metric for modern CPUs is not the clock frequency, but rather "useful operations per joule," or, more practically put, "useful operations per dollar."

Thermodynamically, a computer is just a very efficient device for converting electrical power into heat. This heat eventually needs to be removed, and it's not straightforward to do when you are working with a millimeter-scale crystal. There are physical limits to how much power you can consume and then dissipate.

Historically, the three main variables guiding microchip designs are power, performance, and area (PPA), commonly defined in watts, hertz, and nanometers. Until ~2005, cost, which was mainly a function of area, and performance, used to be the most important criteria. But as battery-driven mobile devices started replacing PCs, power quickly and firmly moved up on top of the list, followed by cost and performance.

Leakage: interfering magnetic fields make electrons move in the directions they are not supposed to and cause unnecessary heating. It isn't bad by itself: to mitigate it you need to increase the voltage, and it won't flick any bits. But the problem is that the smaller a circuit is, the harder it is to cope with this by isolating the wires. So modern chips keep the clock frequency at a level that won't cause overheat, although physically there aren't other reasons why they shouldn't.

-->

### 现代计算 {#modern-computing}

登纳德缩放已经终结，但摩尔定律还没死。

时钟频率进入平台期，但晶体管数量仍在增长，于是可以造出新的*并行*硬件。CPU 设计不再追逐更快的周期，而是开始专注于在单个周期里做完更多有用的事；晶体管不再一味变小，而是开始改变形状。

其结果是体系结构越来越复杂，每个周期能做几十、几百乃至几千件不同的事。

![AMD Zen CPU 核心的裸片照片（约 14 亿个晶体管）](/en/hpc/complexity/img/die-shot.jpg)

下面这些利用更多可用晶体管的核心思路，正在推动近年来的计算机设计：

- 让指令的执行相互重叠，使 CPU 的不同部分都忙起来（流水线）；
- 不必等前一条指令完成就开始执行后面的操作（推测执行与乱序执行）；
- 增加多个执行单元，同时处理相互独立的操作（超标量处理器）；
- 增大机器字长，直至添加能对 128、256 或 512 位数据块分组执行同一操作的指令（[SIMD](/hpc/simd/)）；
- 在芯片上叠加[多级缓存](/hpc/cpu-cache/)以加快对 [RAM 和外存](/hpc/external-memory/)的访问（内存并不太遵循硅缩放定律）；
- 在一枚芯片上放置多个相同的核（并行计算、GPU）；
- 在一块主板上用多枚芯片、在一个数据中心里用大量廉价计算机（分布式计算）；
- 用定制硬件以更高的芯片利用率解决特定问题（ASIC、FPGA）。

对现代计算机来说，用"[把所有操作数一遍](../)"的方式预测算法性能已经不是略有偏差，而是会差出几个数量级。这呼唤新的计算模型，以及评估算法性能的新方法。

<!--

Pointer jumping and processing in most scripting languages: $10^7$
Branchy operations in native languages: $10^8$
Branchless scalar processing in native languages: $10^9$
Bandwidth-bound or complex SIMD applications: $10^{10}$
Linear algebra, single core: $10^{11}$
Typical desktop CPU: $10^{12}$
Typical mobile phone GPU: $10^{12}$
Typical integrated graphics card: $2 \cdot 10^{12}$
High-end gaming setups: $10^{13}$
Deep learning hardware: $10^{14}$
Deep learning full rigs: $10^{15}$
Being considered a supercomputer: $10^{16}$
Setups used to train LM neural networks: $5 \cdot 10^{17}$
Fugaku (#1): $2 \cdot 10^{18}$
Folding@home: $3 \cdot 10^{18}$

-->
