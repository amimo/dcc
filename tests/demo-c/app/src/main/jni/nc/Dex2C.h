#ifndef _DEX2C_H_
#define _DEX2C_H_

#include <jni.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <android/log.h>

//#define DEBUG

#define D2C_RESOLVE_CLASS(cached_class, class_name)                          \
  if (cached_class == NULL && d2c_resolve_class(env, &cached_class, class_name)) {                   \
    goto EX_HANDLE;                                                            \
  }

#define D2C_RESOLVE_METHOD(cached_class, cached_method, class_name, method_name, signature)                             \
    if (cached_method == NULL && d2c_resolve_method(env, &cached_class, &cached_method, false, class_name, method_name, signature)) {            \
        goto EX_HANDLE;                                                                                                     \
    }

#define D2C_RESOLVE_STATIC_METHOD(cached_class, cached_method, class_name, method_name, signature)                      \
    if (cached_method == NULL && d2c_resolve_method(env, &cached_class, &cached_method, true, class_name, method_name, signature)) {             \
        goto EX_HANDLE;                                                                                                     \
    }

#define D2C_RESOLVE_FIELD(cached_class, cached_field, class_name, field_name, signature)                               \
  if (cached_field == NULL && d2c_resolve_field(env, &cached_class, &cached_field, false, class_name, field_name, signature)) {                  \
    goto EX_HANDLE;                                                                                                         \
  }

#define D2C_RESOLVE_STATIC_FIELD(cached_class, cached_field, class_name, field_name, signature)                        \
  if (cached_field == NULL && d2c_resolve_field(env, &cached_class, &cached_field, true, class_name, field_name, signature)) {                   \
    goto EX_HANDLE;                                                                                                         \
  }

#define D2C_CHECK_PENDING_EX                                                   \
  if (env->ExceptionCheck()) {                                                 \
    goto EX_HANDLE;                                                            \
  }

#define D2C_GET_PENDING_EX                                                     \
  exception = env->ExceptionOccurred();                                        \
  env->ExceptionClear();                                                       \

#define D2C_GOTO_UNWINDBLOCK                                                   \
  env->Throw(exception);                                                       \
  env->DeleteLocalRef(exception);                                              \
  goto EX_UnwindBlock;

#define D2C_NOT_NULL(obj)                                                               \
  if (obj == NULL) {                                                                    \
    d2c_throw_exception(env, "java/lang/NullPointerException", "NullPointerException"); \
    goto EX_HANDLE;                                                                     \
  }

#define D2C_CHECK_CAST(obj, clz, class_name)                                \
  if (d2c_check_cast(env, obj, clz, class_name)) {                          \
    goto EX_HANDLE;                                                         \
  }

#ifdef DEBUG
#define LOGD(...)                                                           \
  __android_log_print(ANDROID_LOG_DEBUG, "Dex2C", __VA_ARGS__)
#else
#define LOGD(...) (0)
#endif

inline jdouble d2c_bitcast_to_double(uint64_t val) {
    union {
        double dest;
        uint64_t src;
    } conv;
    conv.src = val;
    return conv.dest;
}

inline jfloat d2c_bitcast_to_float(uint32_t val) {
    union {
        float dest;
        uint32_t src;
    } conv;
    conv.src = val;
    return conv.dest;
}

inline double d2c_long_to_double(int64_t l) {
    return static_cast<double>(l);
}

inline float d2c_long_to_float(int64_t l) {
    return static_cast<float>(l);
}

int64_t d2c_double_to_long(double val);

int32_t d2c_double_to_int(double val);

int64_t d2c_float_to_long(float val);

int32_t d2c_float_to_int(float val);

void d2c_filled_new_array(JNIEnv *env, jarray array, const char *type, jint count, ...);

void d2c_throw_exception(JNIEnv *env, const char *name, const char *msg);

inline bool d2c_is_instance_of(JNIEnv *env, jobject instance, jclass clz) {
    if (instance) {
        return env->IsInstanceOf(instance, clz);
    } else {
        return false;
    }
}

bool d2c_is_instance_of(JNIEnv *env, jobject instance, const char *class_name);

inline bool d2c_is_same_object(JNIEnv *env, jobject obj1, jobject obj2) {
    if (obj1 == obj2) {
        return true;
    }
    if (obj1 && obj2) {
        return env->IsSameObject(obj1, obj2);
    } else {
        return false;
    }
}

/* The following functions return true if exception occurred */
bool d2c_check_cast(JNIEnv *env, jobject instance, jclass clz, const char *class_name);

bool d2c_resolve_class(JNIEnv *env, jclass *cached_class, const char *class_name);

bool d2c_resolve_method(JNIEnv *env, jclass *cached_class, jmethodID *cached_method, bool is_static,
                        const char *class_name, const char *method_name, const char *signature);

bool d2c_resolve_field(JNIEnv *env, jclass *cached_class, jfieldID *cached_field, bool is_static,
                       const char *class_name, const char *field_name, const char *signature);

#endif
