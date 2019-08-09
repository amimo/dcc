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

public class InstField {
    public boolean mBoolean1, mBoolean2;
    public byte mByte1, mByte2;
    public char mChar1, mChar2;
    public short mShort1, mShort2;
    public int mInt1, mInt2;
    public float mFloat1, mFloat2;
    public long mLong1, mLong2;
    public double mDouble1, mDouble2;
    public volatile long mVolatileLong1, mVolatileLong2;
    public String mString1, mString2;

    public void run() {
        assignFields();
        checkFields();
        InstField.nullCheck(null);
    }

    /*
     * Check access to instance fields through a null pointer.
     */
    static public native void nullCheck(InstField nully);

    public native void assignFields();
    public native void checkFields();
}
