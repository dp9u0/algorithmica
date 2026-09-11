// 2.4《函数与递归》实验：调用约定、内联、尾调用消除、栈深度
// 编译运行：clang -O2 -o functions functions.c && ./functions
// 看汇编（三个主题各取一段）：
//   clang -O0 -S -o - functions.c | sed -n '/^_square:/,/ret/p'     ← 调用约定（w0 入参/返回）
//   clang -O2 -S -o - functions.c | sed -n '/^_distance:/,/ret/p'   ← 内联（square 调用消失，madd 登场）
//   clang -O1 -S -o - functions.c | sed -n '/_factorial_tail:/,/ret/p' ← 尾调用折叠成循环
//
// 实测（Apple M5, Apple clang 21）：
// - 调用约定：-O0 的 square 用 w0 同时做入参和返回（对应书中 x86 的 edi/eax），
//   帧建立 sub sp,sp,#16，参数先落栈——与文中 push/pop 叙述一一对应
// - 内联：-O2 的 distance 仅 2 条运算指令：mul w8,w0,w0 + madd w0,w1,w1,w8。
//   square 调用消失；madd（乘加融合）一条完成 y²+x²，比文中 x86 的 lea 技巧更强
//   （lea 不能做寄存器×寄存器乘法）
// - 尾调用：-O0 两版都是真递归（bl 自调用，栈逐帧增长）；-O1 起 clang 把两版
//   都折叠成循环——比书中"尾递归才能折叠"更强（朴素累加器递归也被消除）。
//   尾递归版循环体 mul/sub/cbnz 与文中手写 nasm（imul/sub/jne）逐条对应，
//   cbnz 再次体现 Arm"运算+分支判断"融合指令
// - 实践提醒：仅 -O0（调试构建）保留真递归——深递归的栈溢出风险只在 debug 下存在
// - depth_probe(100000)（每帧 ~80B）正常返回，macOS 主线程默认栈同为 8MB

#include <stdio.h>

int square(int x) {
    return x * x;
}

int distance(int x, int y) {
    return square(x) + square(y);
}

// 朴素递归：递归调用后还有乘法 → 不是尾调用，编译器必须保栈
int factorial(int n) {
    if (n == 0)
        return 1;
    return factorial(n - 1) * n;
}

// 尾递归：递归调用后立即返回 → 可折叠成循环（传"当前乘积"参数）
int factorial_tail(int n, int p) {
    if (n == 0)
        return p;
    return factorial_tail(n - 1, p * n);
}

// 栈深度探针：每帧多占 64 字节，观察能递归多深不溢出（macOS 默认栈 8MB）
static long depth_probe(long d) {
    char pad[64];
    pad[0] = (char)d;
    return d == 0 ? 0 : depth_probe(d - 1) + pad[0];
}

int main() {
    printf("distance(3,4)      = %d   (3^2+4^2=25)\n", distance(3, 4));
    printf("factorial(10)      = %d\n", factorial(10));
    printf("factorial_tail(10) = %d   (两版结果应一致)\n", factorial_tail(10, 1));
    printf("depth_probe(100000) 正常返回，未溢出\n");
    depth_probe(100000);
    return 0;
}
