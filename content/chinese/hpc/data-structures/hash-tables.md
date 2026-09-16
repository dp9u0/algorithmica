---
title: "[草稿]哈希表"
weight: 8
draft: true
---


## 哈希表 {#hash-tables}

![](https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Hash_table_3_1_1_0_1_0_0_SP.svg/2560px-Hash_table_3_1_1_0_1_0_0_SP.svg.png =500x)

----

### 链地址法 {#chaining}

![](https://upload.wikimedia.org/wikipedia/commons/d/d0/Hash_table_5_0_1_1_1_1_1_LL.svg =500x)

大量链表或可增长数组

----

### 开放寻址 {#open-addressing}

![](https://upload.wikimedia.org/wikipedia/commons/b/bf/Hash_table_5_0_1_1_1_1_0_SP.svg =500x)

固定数量的格子，和一个哈希函数 $f_i(x)$，它决定第 $i$ 步该去哪里查找

----

用循环数组实现：

```cpp
struct hashmap {
    const int size = (1<<24);
    int a[size] = {-1}, b[size];

    static inline int h(int x) { return (x^179)*7; }

    void add(int x, int y) {
        int k = h(x) % size;
        while (a[k] != -1 && a[k] != x)
            k = (k + 1) % size;
        a[k] = x, b[k] = y; 
    }

    int get(int x) {
        for (int k = h(x) % size; a[k] != -1; k = (k + 1) % size)
            if (a[k] == x)
                return b[k];
        return -1;
    }
};
```

渐进复杂度相同，但实际速度相差 2-3 倍

----

![](https://upload.wikimedia.org/wikipedia/commons/1/1c/Hash_table_average_insertion_time.png =500x)

唯一的缺点是你需要更频繁地对它重新哈希（rehash）
