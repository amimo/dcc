# 工作流程
```
Dex CFG -> SSA IR -> Type Inference -> Out-Of-SSA & CodeGen
```
## 构建Dex code的CFG
这步使用[androguard](https://github.com/androguard/androguard)完成,但是androguard生成的CFG并不能直接使用,考虑下面代码
```
v1 = ...;
v0_0 = 0;
try {
    if (v1 > 0) {
//BB1
        v0_1 = 1;
    } else {
//BB2
        v0_2 = 2;
    }
//BB3
    v0_3 = "sss";
} catch () {
//BB4
//v0_4 = phi(v0_1:BB1, v0_2:BB2, v0_3:BB3)
}
//BB5
bar(v0_4); //"sss"
```
最后一行中v0的值必定是"sss",但如果直接在androiguard的CFG上构建SSA IR, v0_1, v0_2的值通过catch块的phi传播到bar,导致bar读取到值不正确.
所以首先要对androguard生成的CFG进行改造:
+ 将会抛出异常的指令放到独立的基本块内
+ 对于不会抛出异常的基本块,不能给它添加catch后继

## SSA IR构建
构建SSA IR使用的是论文\<\<Simple and Efficient Construction of Static Single Assignment Form\>\>中的方法.

## Type Inference
类型推导有三个作用
1. 声明变量
2. 选用正确的JNI函数(GetXXXArrayElement,等)
3. 释放局部引用

我的做法是,如果在定义一个变量时明确知道其类型的,则直接将类型固定.如当前编译函数的参数,调用有返回值函数定义的变量,aget-byte等.
对于定义时类型未知的变量,通过其使用不断优化它的类型.

实现过程中还遇到一个坑,Dalvik指令中的常量是多态的,例如0,可以当作引用类型NULL,整型0,布尔类型的false.
为实现的简单,对于常量的每次使用,我都会生成一个新的SSA变量,这样每个SSA变量就都只有一个类型了.

## Out-Of-SSA & CodeGen
PHI消除使用的是\<\<Translating out of static single assignment form\>\>论文中的方法,即将TSSA转成CSSA,然后给PHI相关变量分配相同名字来消除PHI.

## 局部引用缓存和释放
当前使用全局和局部两级缓存策略缓存jclass, jmethodID, jfieldID解析结果.
全局缓存jclass会消耗全局引用(全局引用表也会溢出).
整个解析过程如下:
1. 查看当前函数是否已有缓存,如果已经缓存则可直接使用.
2. 局部没有缓存时,查看全局是否缓存,如有缓存,缓存结果到局部变量并返回结果.
3. 全局仍没有缓存时,请求Java虚拟机解析,缓存结果到全局和局部并返回结果.

为了避免局部引用表溢出(local reference table overflow),我们需要在引用不再被使用或没有使用时将其释放.
我能想到的判断方法有两种:

### 使用变量活跃分析
+ 当指令s运行之后,释放在s入口活跃,但出口不再活跃的引用:LiveIn(s) - LiveOut(s)
+ 控制流从A -> B时,释放A出口活跃,B入口不活跃的引用: LiveOut(A) - LiveIn(B)
+ 异常发生时 A -> LandingPad -> B,先释放异常处理中不会使用到的引用LiveOut(A) - LiveIn(LandingPad);
再释放异常处理B中不会使用到的引用LiveOut(LangindPad) - LiveIn(B)

使用这种方式生成的代码大概是这个样子的:
```
v1 = foo(v0);
env->DeleteLocalRef(v0);
```
### 引用被杀死时
考虑如下代码
```
v1 = foo(v0)
```
如果我们知道v1中保存的是引用,那么v1在该指令之后肯定不会再有使用,所有在运行这条指令之前把它释放掉.

使用这种方式生成的代码大概是这个样子的:
```
env->DeleteLocalRef(v1);
v1 = foo(v0);
```
我使用的是后一种方法.

## 异常处理
当程序运行到某处,有抛出异常时,会先跳转的指令s所属基本块A的LandingPad,在LandingPad中查找对应异常的异常处理catch块
如果有catch handler可以处理该异常,则跳转到该catch handler,否则跳转到UnwindBlock,开始进行回溯.