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

/**
 * Exercise arrays.
 */
public class Array {

    /*
     * Verify array contents.
     */
    static native void checkBytes(byte[] bytes);
    static native void checkShorts(short[] shorts);
    static native void checkChars(char[] chars);
    static native void checkInts(int[] ints);
    static native void checkBooleans(boolean[] booleans);
    static native void checkFloats(float[] floats);
    static native void checkLongs(long[] longs);
    static native void checkStrings(String[] strings);

    /*
     * Try bad range values, 32 bit get/put.
     */
    static native void checkRange32(int[] ints, int[] empty, int negVal1, int negVal2);
    /*
     * Try bad range values, 64 bit get/put.
     */
    static native void checkRange64(long[] longs, int negVal1, int negVal2);

    /*
     * Test negative allocations of object and primitive arrays.
     */
    static native void checkNegAlloc(int count);
    public native static void run();
}
