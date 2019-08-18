#include <string.h>
#include <pthread.h>
#include <map>

#include "Dex2C.h"
#include "ScopedLocalRef.h"
#include "ScopedPthreadMutexLock.h"
#include "well_known_classes.h"

struct MemberTriple {
    MemberTriple(const char *cls_name, const char *name, const char *sig):class_name_(cls_name), member_name_(name), signautre_(sig) {}
    const char *class_name_;
    const char *member_name_;
    const char *signautre_;

    bool operator < (const MemberTriple &member) const {
        if (class_name_ != member.class_name_) return class_name_ < member.class_name_;
        if (member_name_ != member.member_name_) return member_name_ < member.member_name_;
        if (signautre_ != member.signautre_) return signautre_ < member.signautre_;
        else return false;
    }
};

static std::map<MemberTriple, jfieldID> resvoled_fields;
static std::map<MemberTriple, jmethodID> resvoled_methods;
static std::map<MemberTriple, jclass> resvoled_classes;
static pthread_mutex_t resovle_method_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t resovle_field_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t resovle_class_mutex = PTHREAD_MUTEX_INITIALIZER;

static const int max_global_reference = 1500;

static void cache_well_known_classes(JNIEnv *env) {
    d2c::WellKnownClasses::Init(env);

    resvoled_classes[MemberTriple("Int", NULL, NULL)] = d2c::WellKnownClasses::primitive_int;
    resvoled_classes[MemberTriple("Long", NULL, NULL)] = d2c::WellKnownClasses::primitive_long;
    resvoled_classes[MemberTriple("Short", NULL, NULL)] = d2c::WellKnownClasses::primitive_short;
    resvoled_classes[MemberTriple("Char", NULL, NULL)] = d2c::WellKnownClasses::primitive_char;
    resvoled_classes[MemberTriple("Byte", NULL, NULL)] = d2c::WellKnownClasses::primitive_byte;
    resvoled_classes[MemberTriple("Boolean", NULL, NULL)] = d2c::WellKnownClasses::primitive_boolean;
    resvoled_classes[MemberTriple("Float", NULL, NULL)] = d2c::WellKnownClasses::primitive_float;
    resvoled_classes[MemberTriple("Double", NULL, NULL)] = d2c::WellKnownClasses::primitive_double;
}

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

    MemberTriple triple(class_name, NULL, NULL);

    if (max_global_reference > 0) {
        ScopedPthreadMutexLock lock(&resovle_class_mutex);

        auto iter = resvoled_classes.find(triple);
        if (iter != resvoled_classes.end()) {
            *cached_class = (jclass) iter->second;
            return false;
        }
    }

    jclass clz = env->FindClass(class_name);
    if (clz) {
        LOGD("resvoled class %s %zd", class_name, resvoled_classes.size());
        if (max_global_reference > 0 && resvoled_classes.size() < max_global_reference) {
            ScopedPthreadMutexLock lock(&resovle_class_mutex);
            *cached_class = (jclass) env->NewGlobalRef(clz);
            resvoled_classes[triple] = *cached_class;
            env->DeleteLocalRef(clz);
        } else {
            *cached_class = clz;
        }
        return false;
    } else {
        return true;
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

    MemberTriple triple(class_name, method_name, signature);
    {
        ScopedPthreadMutexLock lock(&resovle_method_mutex);

        auto iter = resvoled_methods.find(triple);
        if (iter != resvoled_methods.end()) {
            *cached_method = iter->second;
            return false;
        }
    }

    if (is_static) {
        *cached_method = env->GetStaticMethodID(*cached_class, method_name, signature);
    } else {
        *cached_method = env->GetMethodID(*cached_class, method_name, signature);
    }

    if (*cached_method) {
        ScopedPthreadMutexLock lock(&resovle_method_mutex);
        resvoled_methods[triple] = *cached_method;
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

    MemberTriple triple(class_name, field_name, signature);
    {
        ScopedPthreadMutexLock lock(&resovle_field_mutex);

        auto iter = resvoled_fields.find(triple);
        if (iter != resvoled_fields.end()) {
            *cached_field = iter->second;
            return false;
        }
    }

    if (is_static) {
        *cached_field = env->GetStaticFieldID(*cached_class, field_name, signature);
    } else {
        *cached_field = env->GetFieldID(*cached_class, field_name, signature);
    }

    if (*cached_field) {
        ScopedPthreadMutexLock lock(&resovle_field_mutex);
        resvoled_fields[triple] = *cached_field;
    }

    return *cached_field == NULL;
}

JNIEXPORT jint JNI_OnLoad(JavaVM *vm, void *reserved) {
    JNIEnv *env;

    if (vm->GetEnv((void **) &env, JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }
    cache_well_known_classes(env);
    return JNI_VERSION_1_6;
}
