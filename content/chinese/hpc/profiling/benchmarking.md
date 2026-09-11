---
title: 基准测试
weight: 6
draft: true
---

大多数好的软件工程实践，都在以这样或那样的方式解决让*开发周期*更快的问题：你想更快地编译软件（构建系统），尽早抓到 bug（静态分析、持续集成），新版本一就绪就发布（持续部署），并且不失时机地回应用户反馈（敏捷开发）。

性能工程也不例外。如果你做得对，它也应该呈现为一个循环：

1. 运行程序并收集指标。
2. 找出瓶颈在哪里。
3. 消除瓶颈，回到第 1 步。

在本节中，我们将讨论基准测试（benchmarking），以及一些能让这个循环更短、帮你更快迭代的实用技巧。这些建议大多来自写这本书的过程，因此你可以在本书的[代码仓库](https://github.com/sslotin/ahm-code)里找到许多所述配置的真实例子。

### 在 C++ 内部做基准测试

写基准测试代码有好几种方法。也许最流行的一种是：把你想比较的多个同语言实现放进同一个文件，从 `main` 函数里分别调用它们，并在同一个源文件里算出你想要的全部指标。

这种方法的缺点是你要写很多样板代码，并且要为每个实现复制一遍，不过元编程可以部分抵消这一点。例如，当你对多个 [gcd](/hpc/algorithms/gcd) 实现做基准测试时，用下面这个高阶函数可以大幅精简基准测试代码：

```c++
const int N = 1e6, T = 1e9 / N;
int a[N], b[N];

void timeit(int (*f)(int, int)) {
    clock_t start = clock();

    int checksum = 0;

    for (int t = 0; t < T; t++)
        for (int i = 0; i < n; i++)
            checksum ^= f(a[i], b[i]);
    
    float seconds = float(clock() - start) / CLOCKS_PER_SEC;

    printf("checksum: %d\n", checksum);
    printf("%.2f ns per call\n", 1e9 * seconds / N / T);
}

int main() {
    for (int i = 0; i < N; i++)
        a[i] = rand(), b[i] = rand();
    
    timeit(std::gcd);
    timeit(my_gcd);
    timeit(my_another_gcd);
    // ...

    return 0;
}
```

这是一种开销非常低的方法，能让你运行更多实验、并从中[获得更准确的结果](../noise)。你仍然要做一些重复动作，但它们很大程度上可以由框架代劳，C++ 里最流行的选择是 [Google benchmark 库](https://github.com/google/benchmark)。有些编程语言还自带好用的基准测试工具：这里要特别提一下 [Python 的 timeit 函数](https://docs.python.org/3/library/timeit.html)和 [Julia 的 @benchmark 宏](https://github.com/JuliaCI/BenchmarkTools.jl)。

C 和 C++ 在执行速度上固然*高效*，但算不上最*高产*的语言，做数据分析时尤其如此。当你的算法依赖一些参数（比如输入规模），而且需要从每个实现身上收集不止一个数据点时，你会很想让基准测试代码与外部环境集成，并用别的工具来分析结果。

### 拆分实现

提升模块化和可复用性的一个办法是：把所有测试和分析代码与算法的具体实现分开，并且让不同的版本各自实现在单独的文件里、共享同一个接口。

在 C/C++ 中，你可以创建单个头文件（如 `gcd.hh`）存放函数接口，并把全部基准测试代码放在 `main` 里：

```c++
int gcd(int a, int b); // to be implemented

// for data structures, you also need to create a setup function
// (unless the same preprocessing step for all versions would suffice)

int main() {
    const int N = 1e6, T = 1e9 / N;
    int a[N], b[N];
    // careful: local arrays are allocated on the stack and may cause stack overflow
    // for large arrays, allocate with "new" or create a global array

    for (int i = 0; i < N; i++)
        a[i] = rand(), b[i] = rand();

    int checksum = 0;

    clock_t start = clock();

    for (int t = 0; t < T; t++)
        for (int i = 0; i < n; i++)
            checksum += gcd(a[i], b[i]);
    
    float seconds = float(clock() - start) / CLOCKS_PER_SEC;

    printf("%d\n", checksum);
    printf("%.2f ns per call\n", 1e9 * seconds / N / T);
    
    return 0;
}
```

然后为每个算法版本创建各自的实现文件（如 `v1.cc`、`v2.cc` 等等，或者起些贴切的名字），它们全都 include 那个唯一的头文件：

```c++
#include "gcd.hh"

int gcd(int a, int b) {
    if (b == 0)
        return a;
    else
        return gcd(b, a % b);
}
```

这么做的全部意义在于：从命令行直接对某个特定算法版本做基准测试，而不必动任何源码文件。为此，你可能还想把它可能有的参数暴露出来——比如从命令行参数里解析：

```c++
int main(int argc, char* argv[]) {
    int N = (argc > 1 ? atoi(argv[1]) : 1e6);
    const int T = 1e9 / N;

    // ...
}
```

另一种做法是使用 C 风格的全局宏定义，然后在编译时通过 `-D N=...` 标志传入：

```c++
#ifndef N
#define N 1000000
#endif

const int T = 1e9 / N;
```

这样你可以利用编译期常量，这对某些算法的性能可能大有好处；代价是每次想改参数都得重新构建程序，这会显著拉长在一组参数取值范围内收集指标所需的时间。

### Makefile

<!-- TODO -->

拆分源文件后，你就可以用带缓存的构建系统（例如 [Make](https://en.wikipedia.org/wiki/Make_(software))）来加速编译。

我在自己的项目间搬来搬去一直用的是这版 Makefile：

```c++
compile = g++ -std=c++17 -O3 -march=native -Wall

%: %.cc gcd.hh
	$(compile) $< -o $@ 

%.s: %.cc gcd.hh
	$(compile) -S -fverbose-asm $< -o $@

%.run: %
	@./$<

.PHONY: %.run
```

现在你可以用 `make example` 编译 `example.cc`，并用 `make example.run` 自动运行它。

你还可以在 Makefile 里加上计算统计数据的脚本，或者与 `perf stat` 调用结合，让剖析自动化。

### Jupyter Notebook

为了加速高层数据分析，你可以建一个 Jupyter notebook，把所有脚本放进去，画所有的图。

加一个对实现做基准测试的包装函数会很方便，它只返回一个标量结果：

```python
def bench(source, n=2**20):
    !make -s {source}
    if _exit_code != 0:
        raise Exception("Compilation failed")
    res = !./{source} {n} {q}
    duration = float(res[0].split()[0])
    return duration
```

然后就可以用它写出干净的分析代码：

```python
ns = list(int(1.17**k) for k in range(30, 60))
baseline = [bench('std_lower_bound', n=n) for n in ns]
results = [bench('my_binary_search', n=n) for n in ns]

# plotting relative speedup for different array sizes
import matplotlib.pyplot as plt

plt.plot(ns, [x / y for x, y in zip(baseline, results)])
plt.show()
```

这套流程一旦建立，你的迭代速度会快得多，可以把精力集中在优化算法本身。
