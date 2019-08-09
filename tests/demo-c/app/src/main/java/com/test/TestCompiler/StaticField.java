package com.test.TestCompiler;
/*
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

public class StaticField {
    public static boolean mBoolean1, mBoolean2;
    public static byte mByte1, mByte2;
    public static char mChar1, mChar2;
    public static short mShort1, mShort2;
    public static int mInt1, mInt2;
    public static float mFloat1, mFloat2;
    public static long mLong1, mLong2;
    public static double mDouble1, mDouble2;
    public static volatile long mVolatileLong1, mVolatileLong2;
    public static String mString;

    public static void run() {
        assignFields();
        checkFields();
    }

    public native static void assignFields();
    public native static void checkFields();
}
