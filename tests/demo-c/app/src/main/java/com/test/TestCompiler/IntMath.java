package com.test.TestCompiler;/*
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
public class IntMath {

    static native void shiftTest1();
    static native void shiftTest2();
    static native void unsignedShiftTest();
    static native void shiftTest3(int thirtyTwo);
    static native void convTest();
    static native void charSubTest();
    /*
     * We pass in the arguments and return the results so the compiler
     * doesn't do the math for us.  (x=70000, y=-3)
     */
    static native int[] intOperTest(int x, int y);
    static native void intOperCheck(int[] results);
    /*
     * More operations, this time with 16-bit constants.  (x=77777)
     */
    static native int[] lit16Test(int x);
    static native void lit16Check(int[] results);

    /*
     * More operations, this time with 8-bit constants.  (x=-55555)
     */
    static native int[] lit8Test(int x);
    static native void lit8Check(int[] results);
    /*
     * Make sure special-cased literal division matches
     * normal division.
     */
    static native void divLiteralTestBody(int start, int count);
    static native void divLiteralTest();
    /*
     * Shift some data.  (value=0xff00aa01, dist=8)
     */
    static native int[] intShiftTest(int value, int dist);
    static native void intShiftCheck(int[] results);
    /*
     * We pass in the arguments and return the results so the compiler
     * doesn't do the math for us.  (x=70000000000, y=-3)
     */
    static native long[] longOperTest(long x, long y);
    static native void longOperCheck(long[] results);
    /*
     * Shift some data.  (value=0xd5aa96deff00aa01, dist=8)
     */
    static native long[] longShiftTest(long value, int dist);
    static native long longShiftCheck(long[] results);

    /*
     * Try to cause some unary operations.
     */
    static native int unopTest(int x);
    static native void unopCheck(int result);

    static class Shorty {
        public short mShort;
        public char mChar;
        public byte mByte;
    };

    /*
     * Truncate an int.
     */
    static native Shorty truncateTest(int x);
    static native void truncateCheck(Shorty shorts);
    /*
     * Verify that we get a divide-by-zero exception.
     */
    static native void divideByZero(int z);

    /*
     * Check an edge condition: dividing the most-negative integer by -1
     * returns the most-negative integer, and doesn't cause an exception.
     *
     * Pass in -1, -1L.
     */
    static native void bigDivideOverflow(int idiv, long ldiv);
    /*
     * Check "const" instructions.  We use negative values to ensure that
     * sign-extension is happening.
     */
    static native void checkConsts(byte small, short medium, int large, long huge);
    /*
     * Test some java.lang.Math functions.
     *
     * The method arguments are positive values.
     */
    static native void jlmTests(int ii, long ll);
    public static void run() {
        shiftTest1();
        shiftTest2();
        unsignedShiftTest();
        shiftTest3(32);
        convTest();
        charSubTest();

        int[] intResults;
        long[] longResults;

        intResults = intOperTest(70000, -3);
        intOperCheck(intResults);
        longResults = longOperTest(70000000000L, -3L);
        longOperCheck(longResults);

        intResults = lit16Test(77777);
        lit16Check(intResults);
        intResults = lit8Test(-55555);
        lit8Check(intResults);
        divLiteralTest();

        intResults = intShiftTest(0xff00aa01, 8);
        intShiftCheck(intResults);
        longResults = longShiftTest(0xd5aa96deff00aa01L, 16);
        long longRet = longShiftCheck(longResults);
        Main.assertTrue(longRet == 0x96deff00aa010000L);

        Shorty shorts = truncateTest(-16717277);    // 0xff00ea23
        truncateCheck(shorts);

        divideByZero(0);
        bigDivideOverflow(-1, -1L);

        checkConsts((byte) 1, (short) -256, -88888, 0x9922334455667788L);

        unopCheck(unopTest(38));

        jlmTests(12345, 0x1122334455667788L);
    }
}
