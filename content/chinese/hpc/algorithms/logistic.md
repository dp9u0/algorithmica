---
title: "[草稿]优化逻辑回归"
weight: 5
draft: true
---

在机器学习中，逻辑回归（logistic regression）或许是最流行的黑盒分类方法。

比方说，我们想把 $28 \times 28$ 的黑白手写数字图片分到 10 个类别（0..9）之一：

![一些加拿大学生在答题卡上写下的数字构成了 MNIST 数据集](/en/hpc/arithmetic/img/mnist.png)

从计算的角度看，它是这样工作的。如果我们要把 $n$ 维数据分到 $m$ 个类别之一，就先把输入向量乘以一个 $n \times m$ 的参数矩阵，然后对输出的 $m$ 元素向量应用一个特殊的 "softmax" 函数：

$$
softmax(x)\_k = \frac{e^{x_k}}{\sum_i^m e_{x_i}}
$$

换句话说，这个函数所做的事情是计算输入向量的逐元素指数，然后对其归一化，使各元素之和为 1。由于输出是加起来等于 1 的 $m$ 个正数，它可以被当作样本属于各个类别的概率分布。然后我们可以查看概率最高的预测，把它当作模型的答案。

我们观察一个大的样本数据集并拟合参数矩阵，让尽可能多的样本得到正确答案。拟合的具体做法我们不会深入展开；而一旦拟合完成，我们需要对它做*推理*（inference），也就是喂给它新数据、得到预测。

这基本上就是一个性能工程师需要了解的关于机器学习的全部。目前我们只关心计算层面的问题。

```c++
float w[10][28*28];
// 796 x 10
int predict(float a) {
    float s[10] = {0};

    for (int k = 0; k < 10; k++)
        for (int i = 0; i < 28*28; i++)
            s[k] += a[i] * w[k][i];

    // there is not problem with calculating exponent of small numbers,
    // but exponent of large numbers may overflow
    int mx = *std::max_element(s, s + 10);
    float sumexp = 0;
    for (int i = 0; i < 10; i++) {
        s[i] = exp(s[i] - mx);
        sumexp += s[i];
    }

    int argmax = 0;
    
    for (int i = 0; i < 10; i++) {
        s[i] /= sumexp;
        if (s[i] > s[argmax])
            argmax = i;
    }

    return argmax;
}
```

这段代码并不太值得优化，毕竟总共也就 ~1 万次操作，但我们的用例可能更大。例如，神经网络与此并无本质不同：它们只是使用更长的变换链，而不只是矩阵乘法后接一个 softmax。

它也可能出现在热点路径上。例如，国际象棋程序使用类似的模型来评估局面的价值（获胜概率）。顺便说一句，"1-3-3-5-9" 这类启发式方法就是这么来的：你可以在由大量棋局组成的数据集上训练逻辑回归——把这些棋局转换成子力数量差——得到的权重就会是那个样子。其他游戏中的计分也是类似的原理。

我们能注意到的第一件事是：其实并不需要实现 softmax，因为可以注意到最大的 logit（pre-softmax 的那些数是这么称呼的）在 softmax 之后仍然是最大的，所以只需要在矩阵乘法之后取 argmax。

没有任何头脑清醒的人会用 C++ 训练 ML 模型。

### 量化 {#quantization}

机器学习是既不需要动态范围也不需要精度的场景之一。机器学习的全部意义就在于学习对数据的小扰动稳健的函数。输入数据本来就是带噪声的，那我们的计算为什么不能带噪声？何况，误差应当会相互抵消。我们还可以强制让矩阵参数落在某个特定的范围内。

使用更低的精度有两个好处：

1. 取数据花费的时间更少。
2. 我们可以使用把更多值打包到一起的 SIMD 指令。

```c++
char w[10][28*28];

int predict(char a) {
    short max = 0, argmax = 0;

    for (int k = 0; k < 10; k++) {
        short s = 0;
        for (int i = 0; i < 28*28; i++)
            s += a[i] * w[k][i];
        if (s > max)
            s = 0, argmax = k;
    }

    return argmax;
}
```
