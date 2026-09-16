---
title: "[草稿]线程"
weight: 2
draft: true
---

线程（thread）是轻量级的进程，它与其他线程共享代码段、数据段，以及打开的文件和信号之类的操作系统资源。但和进程一样，线程拥有自己的程序计数器（program counter，PC）、一组寄存器和一段栈空间。

```cpp
#include <iostream>
using namespace std;

void print(int a[], int sz)
{
  for (int i = 0; i < sz; i++) cout << a[i] << " ";
  cout << endl;
}
 
void merge(int a[], const int low, const int mid, const int high)
{
  int *temp = new int[high-low+1];
        
  int left = low;
  int right = mid+1;
  int current = 0;
  // Merges the two arrays into temp[] 
  while(left <= mid && right <= high) {
    if(a[left] <= a[right]) {
      temp[current] = a[left];
      left++;
    }
    else { // if right element is smaller that the left
      temp[current] = a[right];  
      right++;
    }
    current++;
  }

  // Completes the array 

        // Extreme example a = 1, 2, 3 || 4, 5, 6
        // The temp array has already been filled with 1, 2, 3, 
        // So, the right side of array a will be used to fill temp.
  if(left > mid) { 
    for(int i=right; i <= high;i++) {
      temp[current] = a[i];
      current++;
    }
  }
        // Extreme example a = 6, 5, 4 || 3, 2, 1
        // The temp array has already been filled with 1, 2, 3
        // So, the left side of array a will be used to fill temp.
  else {  
    for(int i=left; i <= mid; i++) {
      temp[current] = a[i];
      current++;
    }
  }
  // into the original array
  for(int i=0; i<=high-low;i++) {
                a[i+low] = temp[i];
  }
  delete[] temp;
}
 
void merge_sort(int a[], const int low, const int high)
{
  if(low >= high) return;
  int mid = (low+high)/2;
  merge_sort(a, low, mid);  //left half
  merge_sort(a, mid+1, high);  //right half
  merge(a, low, mid, high);  //merge them
}
 
int main()
{        
  int a[] = {38, 27, 43, 3, 9, 82, 10};
  int arraySize = sizeof(a)/sizeof(int);

  print(a, arraySize);

  merge_sort(a, 0, (arraySize-1) );   

  print(a, arraySize);  
  return 0;
}
```

线程仍由操作系统管理。它们只是一种更轻量的构造，而且彼此之间还能共享内存。

## 线程与进程的对比 {#threads-vs-processes}

一个重要的区分，是语言层面的线程、操作系统的线程与硬件线程之间的区别。

```python
import logging
import threading
import time

def thread_function(name):
    logging.info("Thread %s: starting", name)
    time.sleep(2)
    logging.info("Thread %s: finishing", name)

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    logging.info("Main    : before creating thread")
    x = threading.Thread(target=thread_function, args=(1,))
    logging.info("Main    : before running thread")
    x.start()
    logging.info("Main    : wait for the thread to finish")
    # x.join()
    logging.info("Main    : all done")
```

有些语言不支持硬件线程。例如 Python 有个叫全局解释器锁（Global Interpreter Lock，GIL）的东西，它阻止任意两个线程同时执行。这是为了简化并发。Python（以及其他单线程语言）的应对办法是改为创建进程：

```python
# example with processes
```
