LOCAL_PATH:= $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE    := nc
LOCAL_LDLIBS    := -llog

SOURCES := $(wildcard $(LOCAL_PATH)/nc/*.cpp)
LOCAL_C_INCLUDES := $(LOCAL_PATH)/nc

LOCAL_SRC_FILES := $(SOURCES:$(LOCAL_PATH)/%=%)

include $(BUILD_SHARED_LIBRARY)
