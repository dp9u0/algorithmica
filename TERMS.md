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

| English | 中文 | 来源 |
|---|---|---|
| undefined behavior | 未定义行为 | ch04 |
| intermediate representation (IR) | 中间表示 | ch04 |
| design-by-contract | 按契约设计 | ch04 |
| aliasing | 别名 | ch04 |
| attribute | 属性 | ch04 |
| benchmarking | 基准测试 | ch05 |
| stop-the-world | "停下来观察" | ch05 |
| IPC (instructions per cycle) | IPC（每周期指令数） | ch05 |

## 待收录

（各章 finish 时在此追加新术语；定期评审后提升进上面的表）
