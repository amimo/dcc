package com.test.TestCompiler;/*
 * Copyright (C) 2008 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import java.util.HashMap;
import java.util.Map;

/**
 * Try different kinds of method calls.
 */
public class MethodCall extends MethodCallBase {
    MethodCall() {
        super();
        System.out.println("  MethodCall ctor");
    }

    /* overridden method */
    native int tryThing();

    native void testInterface();
   /* do-nothing private instance method */
    private void directly() {}

    /*
     * Function with many arguments.
     */
    static native void manyArgs(int a0, long a1, int a2, long a3, int a4, long a5,
                         int a6, int a7, double a8, float a9, double a10, short a11, int a12,
                         char a13, int a14, int a15, byte a16, boolean a17, int a18, int a19,
                         long a20, long a21, int a22, int a23, int a24, int a25, int a26,
                         String[][] a27, String[] a28, String a29);
    public native static void run();
}

class MethodCallBase {
    MethodCallBase() {
        System.out.println("  MethodCallBase ctor");
    }
    int tryThing() {
        return 7;
    }
}
