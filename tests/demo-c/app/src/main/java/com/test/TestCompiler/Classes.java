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

import java.io.Serializable;
import java.util.Arrays;
import java.lang.reflect.Array;
/**
 * Exercise some class-related instructions.
 */
public class Classes {
    int mSome;

    public void subFunc(boolean wantSub) {
        Main.assertTrue(!wantSub);
    }
    native void checkCast(Object thisRef, Object moreRef, Object nullRef);
    static native void xTests(Object x);
    static native void yTests(Object y);
    static native void xarTests(Object xar);
    static native void yarTests(Object yar);
    static native void xarararTests(Object xararar);
    static native void yarararTests(Object yararar);
    static native void iarTests(Object iar);
    static native void iararTests(Object iarar);
    /*
     * Exercise filled-new-array and test instanceof on arrays.
     *
     * We call out instead of using "instanceof" directly to avoid
     * compiler optimizations.
     */
    static native void arrayInstance();
    public static void run() {
        Classes classes = new Classes();
        MoreClasses more = new MoreClasses();
        classes.checkCast(classes, more, null);

        more.subFunc(true);
        more.superFunc(false);
        arrayInstance();
    }
}

class MoreClasses extends Classes {
    int mMore;

    public MoreClasses() {}

    public void subFunc(boolean wantSub) {
        Main.assertTrue(wantSub);
    }

    public void superFunc(boolean wantSub) {
        super.subFunc(wantSub);
    }
}
