#include <string.h>
#include "Dex2C.h"
#include "ScopedLocalRef.h"
#include "well_known_classes.h"

void d2c_throw_exception(JNIEnv *env, const char *class_name, const char *message) {
    LOGD("d2c_throw_exception %s %s", class_name, message);
    ScopedLocalRef<jclass> c(env, env->FindClass(class_name));
    if (c.get()) {
        env->ThrowNew(c.get(), message);
    }
}

void d2c_filled_new_array(JNIEnv *env, jarray array, const char *type, jint count, ...) {
    va_list args;
    va_start(args, count);
    char ty = type[0];
    bool ref = ty == '[' || ty == 'L';
    for (int i = 0; i < count; i++) {
        if (ref) {
            env->SetObjectArrayElement((jobjectArray) array, i, (jobject) va_arg(args, long));
        } else {
            int val = va_arg(args, jint);
            LOGD("idx = %d, val = %d", i, val);
            env->SetIntArrayRegion((jintArray) array, i, 1, &val);
        }
    }
    va_end(args);
}

int64_t d2c_double_to_long(double val) {
    int64_t result;
    if (val != val) { //NaN
        result = 0;
    } else if (val > static_cast<double>(INT64_MAX)) {
        result = INT64_MAX;
    } else if (val < static_cast<double>(INT64_MIN)) {
        result = INT64_MIN;
    } else {
        result = static_cast<int64_t>(val);
    }
    return result;
}

int64_t d2c_float_to_long(float val) {
    int64_t result;
    if (val != val) { //NaN
        result = 0;
    } else if (val > static_cast<float>(INT64_MAX)) {
        result = INT64_MAX;
    } else if (val < static_cast<float>(INT64_MIN)) {
        result = INT64_MIN;
    } else {
        result = static_cast<int64_t>(val);
    }
    return result;
}

int32_t d2c_double_to_int(double val) {
    int32_t result;
    if (val != val) {
        result = 0;
    } else if (val > static_cast<float>(INT32_MAX)) {
        result = INT32_MAX;
    } else if (val < static_cast<float>(INT32_MIN)) {
        result = INT32_MIN;
    } else {
        result = static_cast<int32_t>(val);
    }
    return result;
}

int32_t d2c_float_to_int(float val) {
    int32_t result;
    if (val != val) {
        result = 0;
    } else if (val > static_cast<float>(INT32_MAX)) {
        result = INT32_MAX;
    } else if (val < static_cast<float>(INT32_MIN)) {
        result = INT32_MIN;
    } else {
        result = static_cast<int32_t>(val);
    }
    return result;
}

bool d2c_is_instance_of(JNIEnv *env, jobject instance, const char *class_name) {
    if (instance == NULL) {
        return false;
    }

    ScopedLocalRef<jclass> c(env, env->FindClass(class_name));
    if (c.get()) {
        return env->IsInstanceOf(instance, c.get());
    } else {
        return false;
    }
}

bool d2c_check_cast(JNIEnv *env, jobject instance, jclass clz, const char *class_name) {
    if (env->IsInstanceOf(instance, clz)) {
        return false;
    } else {
        d2c_throw_exception(env, "java/lang/ClassCastException", class_name);
        return true;
    }
}

bool d2c_resolve_class(JNIEnv *env, jclass *cached_class, const char *class_name) {
    if (*cached_class) {
        return false;
    }

    if (strcmp(class_name, "Int") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_int;
        return false;
    } else if (strcmp(class_name, "Long") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_long;
        return false;
    } else if (strcmp(class_name, "Short") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_short;
        return false;
    } else if (strcmp(class_name, "Char") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_char;
        return false;
    } else if (strcmp(class_name, "Byte") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_byte;
        return false;
    } else if (strcmp(class_name, "Boolean") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_boolean;
        return false;
    } else if (strcmp(class_name, "Float") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_float;
        return false;
    } else if (strcmp(class_name, "Double") == 0) {
        *cached_class = d2c::WellKnownClasses::primitive_double;
        return false;
    } else {
        jclass clz = env->FindClass(class_name);
        if (clz) {
            *cached_class = clz;
            return false;
        } else {
            return true;
        }
    }
}

bool d2c_resolve_method(JNIEnv *env, jclass *cached_class, jmethodID *cached_method, bool is_static,
                        const char *class_name, const char *method_name, const char *signature) {
    if (*cached_method) {
        return false;
    }

    if (d2c_resolve_class(env, cached_class, class_name)) {
        return true;
    }

    if (is_static) {
        *cached_method = env->GetStaticMethodID(*cached_class, method_name, signature);
    } else {
        *cached_method = env->GetMethodID(*cached_class, method_name, signature);
    }
    return *cached_method == NULL;
}

bool d2c_resolve_field(JNIEnv *env, jclass *cached_class, jfieldID *cached_field, bool is_static,
                       const char *class_name, const char *field_name, const char *signature) {
    if (*cached_field) {
        return false;
    }

    if (d2c_resolve_class(env, cached_class, class_name)) {
        return true;
    }

    if (is_static) {
        *cached_field = env->GetStaticFieldID(*cached_class, field_name, signature);
    } else {
        *cached_field = env->GetFieldID(*cached_class, field_name, signature);
    }
    return *cached_field == NULL;
}


JNIEXPORT jint JNI_OnLoad(JavaVM *vm, void *reserved) {
    JNIEnv *env;

    if (vm->GetEnv((void **) &env, JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }

    d2c::WellKnownClasses::Init(env);
    return JNI_VERSION_1_6;
}
