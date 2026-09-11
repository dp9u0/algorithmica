// 2.3《循环与条件》实验：数组求和的三种写法，观察编译器如何变换循环
// 编译：clang -O2 -o loops loops.c && ./loops
// 看汇编：clang -O2 -S -o - loops.c | sed -n '/sum_naive:/,/cfi_endproc/p'
//
// 实测（Apple M5, clang -O2）：
// - naive 0.001s vs 手工展开 0.002s——朴素版反而更快（此时长在噪声边缘，以汇编为准）
// - clang 已自动完成文中全部三项技巧：每轮 16 元素展开、4 个独立向量累加器
//   （add.4s）、以及"倒计数+标志位副作用"的 Arm 形态（subs x11,x11,#16 + b.ne）
// - 教训：手写展开反而限制了编译器（4 个标量累加器 < clang 自选的 4 向量累加器）

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

// 写法一：书中的朴素循环（依赖链版）
int sum_naive(const int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++)
        s += a[i];
    return s;
}

// 写法二：手工多累加器（打破依赖链 + 手工展开，对应书中 2.3 的展开技巧）
int sum_unrolled(const int *a, int n) {
    int s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (int i = 0; i + 3 < n; i += 4) {
        s0 += a[i];
        s1 += a[i + 1];
        s2 += a[i + 2];
        s3 += a[i + 3];
    }
    int s = (s0 + s1) + (s2 + s3);
    for (int i = n & ~3; i < n; i++) s += a[i];
    return s;
}

int main() {
    int n = 4096;
    int *a = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++) a[i] = i;

    clock_t t0 = clock();
    int volatile sink = 0;
    for (int r = 0; r < 10000; r++) sink += sum_naive(a, n);
    double t1 = (double)(clock() - t0) / CLOCKS_PER_SEC;

    t0 = clock();
    for (int r = 0; r < 10000; r++) sink += sum_unrolled(a, n);
    double t2 = (double)(clock() - t0) / CLOCKS_PER_SEC;

    printf("naive:    %.3fs  (sum=%d)\n", t1, sum_naive(a, n));
    printf("unrolled: %.3fs  (sum=%d)\n", t2, sum_unrolled(a, n));
    printf("比值:     %.2fx\n", t1 / t2);
    return 0;
}
