# dcc
DCC (Dex-to-C Compiler) is method-based aot compiler that can translate DEX code to C code.

## 安装
以下是ubuntu 18.04 环境下的安装配置步骤,如果某些环节已经配置过,如JDK,可跳过.
+ 下载代码
```
git clone https://github.com/amimo/dcc.git
```
+ 安装项目依赖
```
cd dcc
pip3 install -r requirements.txt
wget -O tools/apktool.jar https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.4.0.jar
```
+ 安装配置安卓开发环境(NDK r17+, SDK)
```
export PATH=path/to/ndk:$PATH
```
+ 安装JDK
```
sudo apt-get install openjdk-8-jdk
```

## 测试demo
+ 修改测试demo项目local.properties,配置正确的ndk.dir,sdk.dir路径
```
vi tests/demo-java/local.properties
vi tests/demo-c/local.properties
```
+ 编译demo-java
```
cd tests/demo-java
./gradlew assembleDebug
```
+ 将dex编译到c,生成的c代码输出到demo-c的src/main目录下
```
cd dcc
python3.6 dcc.py tests/demo-java/app/build/outputs/apk/debug/app-debug.apk --source-dir=tests/demo-c/app/src/main/ --no-build
```
+ 编译c demo
```
cd tests/demo-c
./gradlew assembleDebug
```
如果一切顺利,"tests/demo-c/app/build/outputs/apk/debug/app-debug.apk"就是最终生成的apk,安装到手机并运行,看是否会崩溃.

## 使用dcc加固app
首先在app代码合适的位置,如Application的onCreate,添加加载so库代码,并重新生成apk
```
try {
    System.loadLibrary("nc");
} catch (UnsatisfiedLinkError e) {
    e.printStackTrace();
}
```

dcc使用简单的黑白名单机制过滤需要编译或禁止编译的函数.
修改filter.txt,使用正则表达式配置需要处理的函数.默认编译Activity.onCreate,和测试demo中的所有函数.
```
vi filter.txt
```

使用如下命令加固app.apk
```
python3.6 dcc.py your_app.apk -o out.apk
```
对于我们的demo-java就是
```
python3.6 dcc.py tests/demo-java/app/build/outputs/apk/debug/app-debug.apk -o out.apk
```
该命令会生成两个文件out.apk和project-source.zip.其中out.apk已经使用testkey签名的加固app,可以直接安装;
project-source.zip是个jni工程,里面包含我们编译出来的c代码,解压出来后可以直接使用ndk编译.

## 注意
+ 这是我个人研究项目,当前还未经过大量测试,请谨慎用于线上项目!
+ 编译出来的C代码使用JNI跟Java虚拟机交互,有可能会对性能产生非常严重的影响,请谨慎选择加固函数!

## 参考资源
+ [DAD](https://github.com/androguard/androguard/tree/master/androguard/decompiler/dad)
