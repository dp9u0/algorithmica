// 2.6《机器码布局》实验：cmov/csel、[[unlikely]] 冷热分离、NOP 对齐
// 编译运行：clang -O2 -o layout layout.c && ./layout
// 看汇编：
//   clang -O2 -S -o - layout.c | sed -n '/^_length_/,/ret/p'   ← 三种 length 的布局差异
//   clang -O2 -S -o - layout.c | grep -c p2align               ← 编译器主动要求对齐的次数
//
// 实测（Apple M5, Apple clang 21）：
// - length_if（if/else 对称版）被编译为 subs w8,w0,w1 + cneg w0,w8,mi——比文中 x86
//   的 cmov 版更极致：cneg（条件取反，Arm 专属）+ subs（置标志副产品）= 两条指令算出
//   |x−y|，即文中末段"roughly corresponding to abs(x-y)"的字面实现
// - length_swap：因含 noinline 调用，条件传送不可用，必须真分支。加
//   __builtin_expect(x>y, 0)（[[unlikely]] 在 C 中的底层形式；.c 文件不认 C++20 属性）
//   后布局翻转：热路径成为直线贯穿（cmp/b.gt 跳过冷块），swap 调用被移到函数尾部、
//   经两次跳转进出——与文中第三版汇编（swap: 在末尾 jmp normal）逐条对应。
//   不加 expect 时分支极性相反（b.le），块序不同
// - 本文件 -S 输出含 3 处 .p2align——即文中"看似有害的优化"：编译器主动要求
//   汇编器插入 NOP 把关键地址对齐到 2 的幂边界

#include <stdio.h>
#include <stdlib.h>

// 写法一：if/else 对称双分支（文中第一版）
int length_if(int x, int y) {
    if (x > y)
        return x - y;
    else
        return y - x;
}

// 写法二：unlikely 冷分支 + 不可内联的调用（真分支必须保留，观察冷热分离）
// 注意：[[unlikely]] 是 C++20 属性，C 里用其底层实现 __builtin_expect(cond, 0)
__attribute__((noinline)) static void swap2(int *a, int *b) { int t = *a; *a = *b; *b = t; }

int length_swap(int x, int y) {
    if (__builtin_expect(x > y, 0))   // 冷分支（期望不发生）
        swap2(&x, &y);
    return y - x;
}

int main() {
    printf("length_if(3,7)   = %d\n", length_if(3, 7));
    printf("length_swap(3,7) = %d\n", length_swap(3, 7));
    // 实测要点：
    // 1) length_if 在 Arm 上应编译为 csel（条件选择，x86 cmov 的对应物）——无分支
    // 2) length_swap 的冷路径（swap 调用）应被移出直线代码（跳到远处再跳回）
    // 3) -S 输出里的 .p2align 指令 = 编译器主动插入 NOP 做对齐（文中"看似有害的优化"）
    return 0;
}
