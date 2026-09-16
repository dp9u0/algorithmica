---
title: "[草稿]纤程"
weight: 3
draft: true
---

*纤程*（fiber）是由语言自身实现的轻量级线程。它们的工作方式是随时接续执行。因此，语言必须维护自己的运行时。

```go
package main

import (
	"fmt"
	"time"
)

func say(s string) {
	for i := 0; i < 5; i++ {
		time.Sleep(100 * time.Millisecond)
		fmt.Println(s)
	}
}

func main() {
	go say("world")
	say("hello")
}
```

它们的工作原理是：语言维护一组线程，随时准备从各自上次停下的地方继续。这称为 N:M 调度（N:M scheduling）。

其他语言也有类似的运行时，比如 C++ 和 Rust 的。
