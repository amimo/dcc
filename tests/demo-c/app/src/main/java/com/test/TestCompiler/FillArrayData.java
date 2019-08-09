package com.test.TestCompiler;

public class FillArrayData {

    public native static byte[] newByteArray();
    public native static char[] newCharArray();
    public native static long[] newLongArray();

    public static void run() {
        byte[] bytes = newByteArray();
        Main.assertTrue(bytes[1] == 1);
        char[] chars = newCharArray();
        Main.assertTrue(chars[1] == 0x4321);
        long[] longs = newLongArray();
        Main.assertTrue(longs[1] == 7540113804746346429L);
    }
}
