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

#ifndef ART_RUNTIME_WELL_KNOWN_CLASSES_H_
#define ART_RUNTIME_WELL_KNOWN_CLASSES_H_

#include <jni.h>
#include <android/log.h>

namespace d2c {

// Various classes used in JNI. We cache them so we don't have to keep looking
// them up. Similar to libcore's JniConstants (except there's no overlap, so
// we keep them separate).

jmethodID CacheMethod(JNIEnv* env, jclass c, bool is_static, const char* name, const char* signature);
jclass CacheClass(JNIEnv* env, const char* jni_class_name);
jfieldID CacheField(JNIEnv* env, jclass c, bool is_static, const char* name, const char* signature);

struct WellKnownClasses {
 public:
  static void Init(JNIEnv* env);  // Run before native methods are registered.

  static jclass java_lang_Double;
  static jclass java_lang_Float;
  static jclass java_lang_Long;
  static jclass java_lang_Integer;
  static jclass java_lang_Short;
  static jclass java_lang_Character;
  static jclass java_lang_Byte;
  static jclass java_lang_Boolean;

  static jclass primitive_double;
  static jclass primitive_float;
  static jclass primitive_long;
  static jclass primitive_int;
  static jclass primitive_short;
  static jclass primitive_char;
  static jclass primitive_byte;
  static jclass primitive_boolean;
};

}  // namespace art

#endif  // ART_RUNTIME_WELL_KNOWN_CLASSES_H_
