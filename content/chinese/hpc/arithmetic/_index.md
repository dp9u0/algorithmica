---
title: 算术
weight: 6
draft: true
---

正如我们在书中反复展示的那样，熟悉指令集的阴暗角落（darker corner）可以非常有成效，尤其是对 [CISC](/hpc/architecture/isa) 平台而言——比如 x86，它目前有 [1000 到 4000 条左右](https://stefanheule.com/blog/how-many-x86-64-instructions-are-there-anyway/)不同的指令，具体取决于你怎么数。

这些指令大多与算术相关，而要高效地使用它们来优化算术运算，需要大量的知识、技能和创造力。因此，本章将讨论数字表示法及其在数值算法中的应用。

<!--

Knowing darker corners of the instruction set can be very fruitful, especially in the case of [CISC](/hpc/architecture/isa) platforms like x86, which currently has [somewhere between 1000 and 4000](https://stefanheule.com/blog/how-many-x86-64-instructions-are-there-anyway/) distinct instructions, depending on how you count.

In this chapter, we will discuss number representations and their use in numerical algorithms, as well as some core mathematical concepts in algebra and number theory that are often overlooked in computer science curricula.

-->
