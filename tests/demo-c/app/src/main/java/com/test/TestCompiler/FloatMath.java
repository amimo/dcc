package com.test.TestCompiler;

/*
 * Copyright (C) 2006 The Android Open Source Project
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

/**
 * Test arithmetic operations.
 */
public class FloatMath {

    static native void convTest();
    /*
     * We pass in the arguments and return the results so the compiler
     * doesn't do the math for us.
     */
    static native float[] floatOperTest(float x, float y);
    static native void floatOperCheck(float[] results);
    /*
     * We pass in the arguments and return the results so the compiler
     * doesn't do the math for us.
     */
    static native double[] doubleOperTest(double x, double y);
    static native void doubleOperCheck(double[] results);

    /*
     * Try to cause some unary operations.
     */
    static native float unopTest(float f);
    static native int[] convI(long l, float f, double d, float zero);
    static native void checkConvI(int[] results);
    static native long[] convL(int i, float f, double d, double zero);
    static native void checkConvL(long[] results);
    static native float[] convF(int i, long l, double d);
    static native void checkConvF(float[] results);
    static native double[] convD(int i, long l, float f);
    static native void checkConvD(double[] results);
    static native void checkConsts();
    /*
     * Determine if two floating point numbers are approximately equal.
     *
     * (Assumes that floating point is generally working, so we can't use
     * this for the first set of tests.)
     */
    static native boolean approxEqual(float a, float b, float maxDelta);
    static native boolean approxEqual(double a, double b, double maxDelta);
    /*
     * Test some java.lang.Math functions.
     *
     * The method arguments are positive values.
     */
    static native void jlmTests(float ff, double dd);
    public static void run() {
        convTest();

        float[] floatResults;
        double[] doubleResults;
        int[] intResults;
        long[] longResults;

        floatResults = floatOperTest(70000.0f, -3.0f);
        floatOperCheck(floatResults);
        doubleResults = doubleOperTest(70000.0, -3.0);
        doubleOperCheck(doubleResults);

        intResults = convI(0x8877665544332211L, 123.456f, -3.1415926535, 0.0f);
        checkConvI(intResults);
        longResults = convL(0x88776655, 123.456f, -3.1415926535, 0.0);
        checkConvL(longResults);
        floatResults = convF(0x88776655, 0x8877665544332211L, -3.1415926535);
        checkConvF(floatResults);
        doubleResults = convD(0x88776655, 0x8877665544332211L, 123.456f);
        checkConvD(doubleResults);

        unopTest(123.456f);

        checkConsts();

        jlmTests(3.14159f, 123456.78987654321);
    }
}
