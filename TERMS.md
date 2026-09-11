# 术语表（TERMS）

翻译术语先例的唯一事实源（取代"grep 已译章节"）。章节会话在**阶段 0 先查本表**，表里没有再 grep 已译章节；**finish 时把本章新术语**按格式补进"待收录"或核心表。发现与表冲突的既有译法 → 报 ISSUES.md，不要自行改别章。

约定：术语在每章**首次出现**时括注原文，如"缓存行（cache line）"；同章内保持一致。

## 核心术语（全书统一）

已验证各章实际用词一致（2026-09-11，覆盖 ch01–05）：

| English | 中文 | 备注 |
|---|---|---|
| pipeline | 流水线 | |
| branch prediction | 分支预测 | |
| speculative execution | **推测执行** | 勿用"预测执行"（与分支预测的"预测"区分） |
| out-of-order execution | 乱序执行 | |
| superscalar | 超标量 | |
| pipeline hazard | 流水线冒险 | 教材标准译法（数据/控制/结构冒险） |
| branchless | 无分支 | |
| latency | 延迟 | |
| throughput | 吞吐量 | |
| bandwidth | 带宽 | |
| cache line | 缓存行 | |
| vectorization | 向量化 | |
| loop unrolling | 循环展开 | |
| inlining | 内联 | |
| dependency chain | 依赖链 | |
| register renaming | 寄存器重命名 | |
| instruction set architecture (ISA) | 指令集架构 | |
| fetch / decode | 取指 / 译码 | CPU 前端两阶段 |
| decode width | 译码宽度 | |
| fused instruction | 融合指令 | |
| calling convention | 调用约定 | |
| stack frame | 栈帧 | |
| stack overflow | 栈溢出 | |
| tail recursion / tail call elimination | 尾递归 / 尾调用消除 | |
| computed jump | 计算跳转 | |
| branch table | 分支表 | |
| virtual method table | 虚方法表 | |
| dynamic dispatch | 动态派发 | |
| asymptotic complexity | 渐进复杂度 | |
| Dennard scaling | 登纳德缩放 | |
| Moore's law | 摩尔定律 | |
| photolithography | 光刻 | |
| bounds checking | 边界检查 | ch04 |

## 各章已用（ch03–05 会话的先例，供后续章节沿用）

**ch03（pipelining）**：

| English | 中文 |
|---|---|
| structural / data / control hazard | 结构 / 数据 / 控制冒险 |
| pipeline stall | 流水线停顿 |
| bubble | 气泡 |
| branch misprediction | 分支预测失败 |
| predication | 谓词化（勿译"预测"） |
| reciprocal throughput | 倒数吞吐量（Agner 术语） |
| block reciprocal throughput | 块倒数吞吐量 |
| instruction tables | 指令表 |
| cycles per instruction (CPI) | 每指令周期数 |
| execution unit / execution port | 执行单元 / 执行端口 |
| critical path | 关键路径 |
| accumulator | 累加器 |
| front-end / back-end | 前端 / 后端 |
| write-back | 写回 |
| micro-operation | 微操作 |
| conditional move (cmov) | 条件传送 |
| masking | 掩码 |
| reduction | 归约 |
| data-parallel | 数据并行 |
| cold cache | **冷缓存**（ch09 将大量使用） |
| cold start（基准测试语境） | **冷启动**（与 cold cache 区分） |
| warm-up run | 预热运行 |
| in-register permutation | 寄存器内置换 |
| flags register | 标志寄存器 |
| padding | 填充 |

**ch04（compilation）**：

| English | 中文 |
|---|---|
| profile-guided optimization (PGO) | 剖析引导优化 |
| corner case | 角落情况 |
| sanitizer | 消毒器 |
| implementation-defined | 由实现定义 |
| object file | 目标文件 |
| link-time optimization (LTO) | 链接时优化 |
| interprocedural optimization | 过程间优化 |
| header-only library | 仅头文件库 |
| contract programming | 契约编程 |
| dead code elimination | 死代码消除 |
| precondition / postcondition | 前置条件 / 后置条件 |
| static / shared library | 静态库 / 共享库 |
| microarchitecture | 微架构 |
| multiversioned function | 多版本函数 |
| lookup table | 查找表 |

**ch05（profiling）**：

| English | 中文 |
|---|---|
| profiler / profiling | 剖析器 / 剖析 |
| instrumentation | 插装（勿用"插桩"） |
| statistical profiler | 统计剖析器 |
| performance counter | 性能计数器 |
| hardware event | 硬件事件 |
| dispatch width | 发射宽度（≠ decode width 译码宽度） |
| memory fence | 内存栅栏 |
| intrinsic | 内建函数 |
| bias / variance | 偏差 / 方差 |
| membership query | 成员查询 |

机器码分析器（machine code analyzer）、算术逻辑单元（ALU）已入核心表语义，两章一致。

## 待收录

（各章 finish 时在此追加新术语；定期评审后提升进上面的表）
