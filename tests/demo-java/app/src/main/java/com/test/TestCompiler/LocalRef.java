package com.test.TestCompiler;

public class LocalRef {
    private static String foo(int a) {
        return String.valueOf(a);
    }

    private static void DeleteLocalRef() {
        System.out.println("LocalRef.DeleteLocalRef");
        int good = 0;
        String s = null;
        for (int i = 0;i < 1024;i ++) {
            // result is not used
            foo(i);

            // s in last iteration is no longer used (kill s)
            s = foo(i);

            // No local reference leak in exception handling
            try {
                int l = ((String)null).length();
            } catch (NullPointerException e) {
                good += 1;
            }
        }

        Main.assertTrue(good == 1024);
        Main.assertTrue(s.equals("1023"));
    }

    public static void run() {
        System.out.println("LocalRef.run");
        DeleteLocalRef();
    }
}
