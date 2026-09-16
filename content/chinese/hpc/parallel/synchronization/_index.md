---
title: "[草稿]同步原语"
weight: 2
draft: true
---

考虑下面这个循环：

```cpp
int s = 0;

for (int i = 0; i < n; i++) {
    s += a[i];
}
```

我们可以像这样把它并行化：

```cpp
int s = 0;

#pragma omp parallel for
for (int i = 0; i < n; i++) {
    s += a[i];
}
```

这段代码用了 OpenMP，下一章会讲到它。眼下你只需要知道，它会创建若干*线程*（thread），并把工作均匀地分配给它们。你也可以用 C++ 的线程写出一个等价的函数。

问题
