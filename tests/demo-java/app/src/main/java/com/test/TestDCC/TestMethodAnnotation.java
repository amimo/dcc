package com.test.TestDCC;

import android.webkit.JavascriptInterface;

public class TestMethodAnnotation {
    @Dex2C
    @JavascriptInterface
    static public void test() {
    }

    static public void test(int i) {
    }
}
