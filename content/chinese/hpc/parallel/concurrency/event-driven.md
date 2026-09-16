---
title: "[草稿]事件驱动并发"
weight: 4
draft: true
---

你可能在 JavaScript 里见过它。这类语言有一个不断运转的事件循环（event loop）。它们也只用单个线程，因为所有阻塞操作基本都是 I/O。

```js
var callback = function() {
    console.log("Button clicked")
}

document.getElementById('someButton').addEventListener("click", callback)
```

事件驱动的环境通常是单线程的，靠把请求"分片"（sharding）来获得多线程的效果。

## Actor 模型 {#actor-model}

一种更泛化的思路被称为*Actor 模型*（actor model）。

它在 JVM 世界非常流行。

```scala
import akka.actor.Actor
import akka.actor.ActorSystem
import akka.actor.Props

class HelloActor extends Actor {
  def receive = {
    case "hello" => println("hello back at you")
    case _       => println("huh?")
  }
}

object Main extends App {
  val system = ActorSystem("HelloSystem")
  // default Actor constructor
  val helloActor = system.actorOf(Props[HelloActor], name = "helloactor")
  helloActor ! "hello"
  helloActor ! "buenos dias"
}
```

使用消息代理（message broker）的一个非常重要的优点是，你可以把通信解耦，还能把 actor 搬到另一个网络节点上，从而实现分布式计算。
