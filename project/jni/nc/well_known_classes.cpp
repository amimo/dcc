/*
 * Copyright (C) 2012 The Android Open Source Project
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

#include <jni.h>
#include <android/log.h>
#include <stdlib.h>

#include "well_known_classes.h"
#include "ScopedLocalRef.h"

#define LOG_FATAL(...) __android_log_print(ANDROID_LOG_FATAL, "WellKnownClasses", __VA_ARGS__)


namespace d2c {

jclass WellKnownClasses::java_lang_Double;
jclass WellKnownClasses::java_lang_Float;
jclass WellKnownClasses::java_lang_Long;
jclass WellKnownClasses::java_lang_Integer;
jclass WellKnownClasses::java_lang_Short;
jclass WellKnownClasses::java_lang_Character;
jclass WellKnownClasses::java_lang_Byte;
jclass WellKnownClasses::java_lang_Boolean;

jclass WellKnownClasses::primitive_double;
jclass WellKnownClasses::primitive_float;
jclass WellKnownClasses::primitive_long;
jclass WellKnownClasses::primitive_int;
jclass WellKnownClasses::primitive_short;
jclass WellKnownClasses::primitive_char;
jclass WellKnownClasses::primitive_byte;
jclass WellKnownClasses::primitive_boolean;

static jobject CachePrimitiveClass(JNIEnv *env, jclass c, const char *name, const char *signature) {
    jfieldID fid = env->GetStaticFieldID(c, name, signature);
    if (fid == NULL) {
        LOG_FATAL ( "Couldn't find field \"%s\" with signature \"%s\"", name, signature);
    }
    jobject val = env->GetStaticObjectField(c, fid);
    return env->NewGlobalRef(val);
}

jclass CacheClass(JNIEnv* env, const char* jni_class_name) {
  ScopedLocalRef<jclass> c(env, env->FindClass(jni_class_name));
  if (c.get() == NULL) {
    LOG_FATAL ("Couldn't find class: %s",  jni_class_name);
  }
  return reinterpret_cast<jclass>(env->NewGlobalRef(c.get()));
}

jfieldID CacheField(JNIEnv* env, jclass c, bool is_static, const char* name, const char* signature) {
  jfieldID fid = is_static ? env->GetStaticFieldID(c, name, signature) : env->GetFieldID(c, name, signature);
  if (fid == NULL) {
    LOG_FATAL ( "Couldn't find field \"%s\" with signature \"%s\"", name, signature);
  }
  return fid;
}

jmethodID CacheMethod(JNIEnv* env, jclass c, bool is_static, const char* name, const char* signature) {
  jmethodID mid = is_static ? env->GetStaticMethodID(c, name, signature) : env->GetMethodID(c, name, signature);
  if (mid == NULL) {
    LOG_FATAL ( "Couldn't find method \"%s\" with signature \"%s\"", name, signature);
  }
  return mid;
}


void WellKnownClasses::Init(JNIEnv* env) {
    java_lang_Double = CacheClass(env, "java/lang/Double");
    java_lang_Float = CacheClass(env, "java/lang/Float");
    java_lang_Long = CacheClass(env, "java/lang/Long");
    java_lang_Integer = CacheClass(env, "java/lang/Integer");
    java_lang_Short = CacheClass(env, "java/lang/Short");
    java_lang_Character = CacheClass(env, "java/lang/Character");
    java_lang_Byte = CacheClass(env, "java/lang/Byte");
    java_lang_Boolean = CacheClass(env, "java/lang/Boolean");

    primitive_double = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Double, "TYPE",
                                                               "Ljava/lang/Class;"));
    primitive_float = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Float, "TYPE",
                                                              "Ljava/lang/Class;"));
    primitive_long = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Long, "TYPE",
                                                             "Ljava/lang/Class;"));
    primitive_int = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Integer, "TYPE",
                                                            "Ljava/lang/Class;"));
    primitive_short = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Short, "TYPE",
                                                              "Ljava/lang/Class;"));
    primitive_char = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Character, "TYPE",
                                                             "Ljava/lang/Class;"));
    primitive_byte = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Byte, "TYPE",
                                                             "Ljava/lang/Class;"));
    primitive_boolean = static_cast<jclass>(CachePrimitiveClass(env, java_lang_Boolean, "TYPE",
                                                                "Ljava/lang/Class;"));

}

}
