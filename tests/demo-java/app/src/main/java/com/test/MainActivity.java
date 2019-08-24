package com.test;

import android.app.Activity;
import android.os.Bundle;

import com.test.TestCompiler.Main;
import com.test.TestDCC.TestClassAnnotation;
import com.test.TestDCC.TestMethodAnnotation;

public class MainActivity extends Activity {
    static {
        try {
            System.loadLibrary("nc");
        } catch (UnsatisfiedLinkError e) {
            e.printStackTrace();
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        testCompiler();
        testDCC();
    }

    private int testCompiler() {
        Main.main(new String[] {null});
        return 0;
    }

    private void testDCC() {
        TestClassAnnotation.test();
        TestMethodAnnotation.test();
    }

}
