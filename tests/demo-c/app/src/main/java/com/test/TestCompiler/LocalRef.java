package com.test.TestCompiler;

public class LocalRef {
    private static String foo(int a) {
        return String.valueOf(a);
    }

    private native static void DeleteLocalRef();
    public static void run() {
        DeleteLocalRef();
    }
}
