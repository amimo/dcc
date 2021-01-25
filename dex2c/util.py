# encoding=utf8
#
# Copyright (c) 2012 Geoffroy Gueguen <geoffroy.gueguen@gmail.com>
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

logger = logging.getLogger('dex2c.util')

TYPE_DESCRIPTOR = {
    'V': 'Void',
    'Z': 'Boolean',
    'B': 'Byte',
    'S': 'Short',
    'C': 'Char',
    'I': 'Int',
    'J': 'Long',
    'F': 'Float',
    'D': 'Double',
}

DECL_JNI_TYPE = {
    'Z': 'jboolean',  # jboolean
    'B': 'jbyte',
    'S': 'jshort',
    'C': 'jchar',
    'I': 'jint',
    'J': 'jlong',
    'F': 'jfloat',
    'D': 'jdouble',
    'V': 'void',
}

PRIMITIVE_TYPE_ORDER = {
    'Z': 1,
    'B': 2,
    'S': 3,  # signed
    'C': 3,  # unsigned
    'I': 5,
    'J': 6,
    'F': 8,
    'D': 9,
}

ACCESS_FLAGS_CLASSES = {
    0x1: 'public',
    0x2: 'private',
    0x4: 'protected',
    0x8: 'static',
    0x10: 'final',
    0x200: 'interface',
    0x400: 'abstract',
    0x1000: 'synthetic',
    0x2000: 'annotation',
    0x4000: 'enum',
}

ACCESS_FLAGS_FIELDS = {
    0x1: 'public',
    0x2: 'private',
    0x4: 'protected',
    0x8: 'static',
    0x10: 'final',
    0x40: 'volatile',
    0x80: 'transient',
    0x1000: 'synthetic',
    0x4000: 'enum',
}

ACCESS_FLAGS_METHODS = {
    0x1: 'public',
    0x2: 'private',
    0x4: 'protected',
    0x8: 'static',
    0x10: 'final',
    0x20: 'synchronized',
    0x40: 'bridge',
    0x80: 'varargs',
    0x100: 'native',
    0x400: 'abstract',
    0x800: 'strictfp',
    0x1000: 'synthetic',
    0x10000: 'constructor',
    0x20000: 'declared_synchronized',
}

ACCESS_ORDER = [0x1, 0x4, 0x2, 0x400, 0x8, 0x10, 0x80, 0x40, 0x20, 0x100, 0x800,
                0x200, 0x1000, 0x2000, 0x4000, 0x10000, 0x20000]

TYPE_LEN = {'J': 2, 'D': 2, }


def get_access_class(access):
    sorted_access = [i for i in ACCESS_ORDER if i & access]
    return [ACCESS_FLAGS_CLASSES.get(flag, 'unkn_%d' % flag)
            for flag in sorted_access]


def get_access_method(access):
    sorted_access = [i for i in ACCESS_ORDER if i & access]
    return [ACCESS_FLAGS_METHODS.get(flag, 'unkn_%d' % flag)
            for flag in sorted_access]


def get_access_field(access):
    sorted_access = [i for i in ACCESS_ORDER if i & access]
    return [ACCESS_FLAGS_FIELDS.get(flag, 'unkn_%d' % flag)
            for flag in sorted_access]


def build_path(graph, node1, node2, path=None):
    """
    Build the path from node1 to node2.
    The path is composed of all the nodes between node1 and node2,
    node1 excluded. Although if there is a loop starting from node1, it will be
    included in the path.
    """
    if path is None:
        path = []
    if node1 is node2:
        return path
    path.append(node2)
    for pred in graph.all_preds(node2):
        if pred in path:
            continue
        build_path(graph, node1, pred, path)
    return path


def common_dom(idom, cur, pred):
    if not (cur and pred):
        return cur or pred
    while cur is not pred:
        while cur.num < pred.num:
            pred = idom[pred]
        while cur.num > pred.num:
            cur = idom[cur]
    return cur


def merge_inner(clsdict):
    """
    Merge the inner class(es) of a class:
    e.g class A { ... } class A$foo{ ... } class A$bar{ ... }
    ==> class A { class foo{...} class bar{...} ... }
    """
    samelist = False
    done = {}
    while not samelist:
        samelist = True
        classlist = list(clsdict.keys())
        for classname in classlist:
            parts_name = classname.rsplit('$', 1)
            if len(parts_name) > 1:
                mainclass, innerclass = parts_name
                innerclass = innerclass[:-1]  # remove ';' of the name
                mainclass += ';'
                if mainclass in clsdict:
                    clsdict[mainclass].add_subclass(innerclass,
                                                    clsdict[classname])
                    clsdict[classname].name = innerclass
                    done[classname] = clsdict[classname]
                    del clsdict[classname]
                    samelist = False
                elif mainclass in done:
                    cls = done[mainclass]
                    cls.add_subclass(innerclass, clsdict[classname])
                    clsdict[classname].name = innerclass
                    done[classname] = done[mainclass]
                    del clsdict[classname]
                    samelist = False


def get_type_size(param):
    """
    Return the number of register needed by the type @param
    """
    return TYPE_LEN.get(param, 1)


def get_type(atype, size=None):
    """
    Retrieve the java type of a descriptor (e.g : I)
    """
    res = TYPE_DESCRIPTOR.get(atype)
    if res is None:
        if atype[0] == 'L':
            res = atype[1:-1]
        elif atype[0] == '[':
            res = atype
        else:
            res = atype
            logger.debug('Unknown descriptor: "%s".', atype)
    return res


def get_fully_qualified_class_name(signature):
    res = TYPE_DESCRIPTOR.get(signature)
    if res is None:
        if signature[0] == 'L':
            res = signature[1:-1]
        else:
            res = signature
            logger.debug('Unknown descriptor: "%s".', signature)
    return res


def get_type_descriptor(atype):
    res = TYPE_DESCRIPTOR.get(atype)
    if res is None:
        res = 'Object'
    return res


def is_primitive_type(atype):
    return atype and atype in PRIMITIVE_TYPE_ORDER


def get_params_type(descriptor):
    """
    Return the parameters type of a descriptor (e.g (IC)V)
    """
    params = descriptor.split(')')[0][1:].split()
    if params:
        return [param for param in params]
    return []


def get_method_triple(method, return_type=True):
    method_triple = method.get_triple()
    cls_name = method.class_name
    _, name, proto = method_triple
    if return_type:
        return cls_name, name, proto
    else:
        index = proto.find(')')
        proto = proto[:index + 1]
        return cls_name, name, proto


def create_png(cls_name, meth_name, graph, dir_name='graphs2'):
    m_name = ''.join(x for x in meth_name if x.isalnum())
    m_name = m_name.replace('<', '_').replace('>', '_')
    name = ''.join((cls_name.split('/')[-1][:-1], '#', m_name))
    graph.draw(name, dir_name)


def get_native_type(jtype):
    res = DECL_JNI_TYPE.get(jtype)
    if res is None:
        if jtype == 'Ljava/lang/String;':
            res = 'jstring'
        elif jtype[0] == 'L':
            res = 'jobject'
        elif jtype[0] == '[':
            res = 'jarray'
        else:
            res = 'jobject'
            logger.debug('Unknown descriptor: "%s".', jtype)
    return res


def is_int(atype):
    return atype and atype in 'ZBCSIJ'


def is_long(atype):
    return atype == 'J'


def is_float(atype):
    return atype and atype in 'FD'


def is_ref(atype):
    return atype and (atype[0] == 'L' or atype[0] == '[')


def is_array(atype):
    return atype and atype[0] == '['


def is_java_lang_object(atype):
    return atype and atype == 'Ljava/lang/Object;'


def is_java_lang_object_array(atype):
    return is_array(atype) and atype.endswith('Ljava/lang/Object;')


# Use for variable declaration
def get_cdecl_type(atype):
    if atype in 'ZBCSI':
        return 'jint'
    elif atype == 'J':
        return 'jlong'
    elif atype == 'F':
        return 'jfloat'
    elif atype == 'D':
        return 'jdouble'
    else:
        return 'jobject'


# art/runtime/utils.cc
def MangleForJni(name):
    result = ''
    for ch in name:
        if ('A' <= ch <= 'Z') or ('a' <= ch <= 'z') or ('0' <= ch <= '9'):
            result += ch
        elif ch == '.' or ch == '/':
            result += "_"
        elif ch == '_':
            result += "_1"
        elif ch == ';':
            result += "_2"
        elif ch == '[':
            result += "_3"
        else:
            result += '_0%04x' % (ord(ch))
    return result


def JniShortName(cls_name, method_name):
    assert cls_name[0] == 'L'
    assert cls_name[-1] == ';'
    cls_name = cls_name[1:-1]
    short_name = 'Java_'
    short_name += MangleForJni(cls_name)
    short_name += '_'
    short_name += MangleForJni(method_name)
    return short_name


def JniLongName(cls_name, method_name, signature):
    long_name = ''
    long_name += JniShortName(cls_name, method_name)
    long_name += "__"
    signature = signature[1:]
    index = signature.find(')')
    long_name += MangleForJni(signature[:index])
    return long_name


def compare_primitive_type(type1, type2):
    if type1 is None and type2 is None:
        return 0
    if type1 is None:
        # type1 < type2
        return -1
    elif type2 is None:
        # type1 > type2
        return 1

    assert is_primitive_type(type1)
    assert is_primitive_type(type2)

    o1 = PRIMITIVE_TYPE_ORDER.get(type1)
    o2 = PRIMITIVE_TYPE_ORDER.get(type2)
    return o1 - o2


def get_smaller_type(type1, type2):
    return type1 if compare_primitive_type(type1, type2) < 0 else type2


def get_bigger_type(type1, type2):
    return type1 if compare_primitive_type(type1, type2) > 0 else type2


def merge_array_type(type1, type2):
    assert is_array(type1) or is_array(type2)
    if is_java_lang_object(type2):
        return type2
    elif is_java_lang_object(type1):
        return type1
    if is_array(type1):
        if is_array(type2):
            new_type = merge_type(type1[1:], type2[1:])
            if new_type:
                return '[' + new_type
            else:
                return None
        else:
            return 'Ljava/lang/Object;'
    else:
        return merge_array_type(type2, type1)


# return bigger type
def merge_reference_type(type1, type2):
    assert is_ref(type1) and is_ref(type2)
    if type1 == type2:
        return type1
    elif is_java_lang_object(type1) and is_ref(type2):
        return type1
    elif is_java_lang_object(type2) and is_ref(type1):
        return type2
    else:
        return 'Ljava/lang/Object;'


def merge_type(type1, type2):
    if type1 is None and type2 is None:
        return None
    if type1 is None:
        return type2
    if type2 is None:
        return type1

    if (is_int(type1) and is_int(type2)) or \
            (is_float(type1) and is_float(type2)):
        return get_bigger_type(type1, type2)
    elif is_array(type1) or is_array(type2):
        new_type = merge_array_type(type1, type2)
        if new_type is None:
            return 'Ljava/lang/Object;'
        else:
            return new_type
    elif is_ref(type1) or is_ref(type2):
        return merge_reference_type(type1, type2)
    else:
        return None


def is_synthetic_method(method):
    return method.get_access_flags() & 0x1000


def is_native_method(method):
    return method.get_access_flags() & 0x100


def hex_escape_string(s):
    result = ''
    s = s.encode('utf8')
    for c in s:
        result += '\\x%02x' % c
    return result
    # ERROR: hex escape sequence out of range
    # result = ''
    # s = s.encode('utf8')
    # for c in s:
    #     if 0x20 <= c < 0x7f:
    #         if c in (0x22, 0x27, 0x5c):  # " ' \
    #             result += '\\'
    #         result += chr(c)
    #         continue
    #     if c < 0x20:
    #         if c == 0x9:
    #             result += '\\t'
    #         elif c == 0xa:
    #             result += '\\n'
    #         elif c == 0xd:
    #             result += '\\r'
    #         else:
    #             result += '\\x%02x' % c
    #         continue
    #     result += '\\x%02x' % c
    # return result


def get_cdecl_name(clsname):
    assert is_ref(clsname)
    return clsname[1:-1].replace('/', '_').repace('[', '_')


# ERROR: universal character name refers to a control character
def string(s):
    """
    Convert a string to a escaped ASCII representation including quotation marks
    :param s: a string
    :return: ASCII escaped string
    """
    ret = []
    for c in s:
        if ' ' <= c < '\x7f':
            if c == "'" or c == '"' or c == '\\':
                ret.append('\\')
            ret.append(c)
            continue
        elif c <= '\x7f':
            if c in ('\r', '\n', '\t'):
                # unicode-escape produces bytes
                ret.append(c.encode('unicode-escape').decode("ascii"))
                continue
        i = ord(c)
        ret.append('\\u')
        ret.append('%x' % (i >> 12))
        ret.append('%x' % ((i >> 8) & 0x0f))
        ret.append('%x' % ((i >> 4) & 0x0f))
        ret.append('%x' % (i & 0x0f))
    return ''.join(ret)
