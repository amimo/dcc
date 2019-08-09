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

/**
 * Test exception throwing.
 */
public class Throw {
    public void throwNullPointerException() {
        throw new NullPointerException("npe!");
    }

    public void throwArithmeticException() {
        throw new ArithmeticException();
    }

    public native void one();
    public native void twoA();
    public native void twoN();
    public native void rethrow();
    public static void run() {
        Throw th = new Throw();

        th.one();
        th.twoA();
        th.twoN();
        th.rethrow();
    }
}
