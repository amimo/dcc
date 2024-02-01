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
from builtins import object
from builtins import range
from builtins import zip
from struct import unpack

from dex2c import util
from dex2c.instruction import BinaryCompExpression, Constant
from dex2c.opcode_ins import Op
from dex2c.util import get_type_descriptor, get_native_type, JniLongName, is_primitive_type, \
    get_cdecl_type, get_type

logger = logging.getLogger('dex2c.writer')


class TmpnameAllocator(object):
    def __init__(self, vars, prefix=''):
        self.numbering = {}
        self.next_name = 0
        self.prefix = prefix
        for item in vars:
            assert item is not None
            if item is None:
                raise Exception("Unable to allocate tmpname for None.")
            if item in self.numbering:
                continue
            else:
                self.numbering[item] = self.next_name
                self.next_name += 1

    def get_name(self, item):
        assert item and item in self.numbering
        logger.debug("%s - > %s%s" % (item, self.prefix, self.numbering[item]))
        return '%s%s' % (self.prefix, self.numbering[item])


class Writer(object):
    def __init__(self, irmethod, dynamic_register):
        self.graph = irmethod.graph
        self.method = irmethod.method
        self.irmethod = irmethod
        self.visited_nodes = set()
        self.buffer = []
        self.dynamic_register = dynamic_register
        self.prototype = []

        entry = irmethod.entry
        self.ra = irmethod.ra
        self.ca = TmpnameAllocator(entry.class_to_declare, 'cls').get_name
        self.fa = TmpnameAllocator(entry.field_to_declare, 'fld').get_name
        self.ma = TmpnameAllocator(entry.method_to_declare, 'mth').get_name

    def __str__(self):
        return ''.join(self.buffer)
    
    def get_prototype(self):
        return ''.join(self.prototype)

    def write_trace(self, ins):
        s = ins.dump()
        if s:
            self.write('LOGD("%s");\n' % s)

    def write(self, s):
        self.buffer.append(s)

    def end_ins(self):
        self.write(';\n')

    def visit_ins(self, ins):
        ins.visit(self)

    def visit_move_param(self, ins):
        param = ins.get_param()
        value = param.get_value()
        self.write('v%s = (%s)' % (self.ra(value), get_cdecl_type(value.get_type())))
        param.visit(self)
        self.write(";\n")

    def write_method(self):
        access = util.get_access_method(self.method.get_access_flags())
        class_name = self.method.get_class_name()
        _, name, proto = self.method.get_triple()

        jni_name = JniLongName(class_name, name, proto)

        self.write("\n/* %s->%s%s */\n" % (class_name, name, proto))

        if not self.dynamic_register:
            self.write('extern "C" JNIEXPORT %s JNICALL\n' % get_native_type(self.irmethod.rtype))
        else:
            self.write(get_native_type(self.irmethod.rtype) + ' ')
            self.prototype.append(get_native_type(self.irmethod.rtype) + ' ')
        self.write(jni_name)
        if self.dynamic_register:
            self.prototype.append(jni_name)
        params = self.irmethod.params
        if 'static' not in access:
            params = params[1:]
        proto = ''
        if self.irmethod.params_type:
            proto = ', '.join(['%s p%s' % (get_native_type(p_type), param) for p_type,
                                                                               param in
                               zip(self.irmethod.params_type, params)])
        if proto:
            self.write('(JNIEnv *env, jobject thiz, %s)' % proto)
            if self.dynamic_register:
                self.prototype.append('(JNIEnv *env, jobject thiz, %s)' % proto)
        else:
            self.write('(JNIEnv *env, jobject thiz)')
            if self.dynamic_register:
                self.prototype.append('(JNIEnv *env, jobject thiz)')
        self.write('{\n')
        nodes = self.irmethod.irblocks
        for node in nodes:
            self.visit_node(node)

        for lp in self.irmethod.landing_pads:
            self.write('\n')
            self.visit_landing_pad(lp)

        return_type = self.irmethod.rtype
        if return_type[0] != 'V':
            if return_type[0] == 'L':
                self.write("EX_UnwindBlock: return NULL;\n")
            else:
                self.write("EX_UnwindBlock: return (%s)0;\n" % (get_native_type(return_type)))
        else:
            self.write("EX_UnwindBlock: return;\n")

        self.write('}\n')

    def visit_node(self, node):
        if node in self.visited_nodes:
            return
        self.visited_nodes.add(node)
        var_declared = set()
        for var in node.var_to_declare:
            var_type = var.get_type()
            r = self.ra(var)
            if r in var_declared:
                continue
            var_declared.add(r)
            self.write('%s v%s' % (get_cdecl_type(var_type), r))
            if util.is_ref(var_type):
                self.write(' = NULL')
            self.write(";\n")

        if node.var_to_declare and self.irmethod.landing_pads:
            self.write("jthrowable exception;\n")

        declared = set()
        to_declare = []
        for jclass in node.class_to_declare:
            if jclass in declared:
                continue
            declared.add(jclass)
            to_declare.append('%s = NULL' % (self.ca(jclass)))
        if to_declare:
            self.write('jclass %s;\n' % (','.join(to_declare)))

        declared.clear()
        to_declare.clear()
        for jfield in node.field_to_declare:
            if jfield in declared:
                continue
            declared.add(jfield)
            to_declare.append('%s = NULL' % (self.fa(jfield)))
        if to_declare:
            self.write('jfieldID %s;\n' % (','.join(to_declare)))

        declared.clear()
        to_declare.clear()
        for jmethod in node.method_to_declare:
            if jmethod in declared:
                continue
            declared.add(jmethod)
            to_declare.append('%s = NULL' % (self.ma(jmethod)))
        if to_declare:
            self.write('jmethodID %s;\n' % (', '.join(to_declare)))

        for ins in node.move_param_insns:
            ins.visit(self)
        node.visit(self)

    def visit_landing_pad(self, landing_pad):
        self.write("%s:\n" % (landing_pad.label))
        self.write("D2C_GET_PENDING_EX\n")
        for atype, handle in landing_pad.handles.items():
            self.write('if(d2c_is_instance_of(env, exception, "%s")) {\n' % (get_type(atype)))
            self.write('goto L%d;\n' % handle.num)
            self.write('}\n')
        self.write("D2C_GOTO_UNWINDBLOCK\n")

    def write_delete_dead_local_reference(self, val):
        if val.use_empty() and val.get_register() < 0:
            self.write_kill_local_reference(val, True)

    def write_kill_local_reference(self, val, tmp=False):
        if val is None:
            return

        if get_native_type(val.get_type()) in ('jarray', 'jobject', 'jstring'):
            if tmp or val.get_register() >= 0:
                reg = self.ra(val)
                self.write('if (v%s) {\n' % (reg))
                self.write('LOGD("env->DeleteLocalRef(%%p):v%s", v%s);\n' % (reg, reg))
                self.write('env->DeleteLocalRef(v%s);\n' % reg)
                self.write('}\n')

    def visit_switch_node(self, ins, switch, cases):
        self.write('switch (')
        switch.visit(self)
        self.write(') {\n')
        for case, offset in cases:
            node = self.irmethod.offset_to_node[offset + ins.offset]
            self.write('case %d: goto L%d;\n' % (case, node.num))
        self.write('}\n')

    def visit_statement_node(self, stmt):
        if stmt.num >= 0:
            self.write("L%d:\n" % stmt.num)
        for ins in stmt.get_instr_list():
            self.visit_ins(ins)

    def visit_return_node(self, ret):
        for ins in ret.get_ins():
            self.visit_ins(ins)

    def visit_load_constant(self, ins):
        val = ins.get_value()
        atype = val.get_type()
        self.write_trace(ins)
        self.write_kill_local_reference(val)
        cst = ins.get_cst().get_constant()
        cst_type = ins.get_cst().get_type()
        if atype == 'F':
            self.write('v%s = d2c_bitcast_to_float(%r);\n' % (self.ra(val), cst))
        elif atype == 'D':
            self.write('v%s = d2c_bitcast_to_double(%r);\n' % (self.ra(val), cst))
        elif cst_type == 'Ljava/lang/String;':
            self.write(
                'v%s = (%s) env->NewStringUTF("%s");\n' % (self.ra(val), get_native_type(atype), cst))
        elif cst_type == 'Ljava/lang/Class;':
            self.write('{\n')
            self.write_define_ex_handle(ins)
            self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
            self.write('D2C_RESOLVE_CLASS(clz,"%s");\n' % (cst))
            self.write('v%s = env->NewLocalRef(clz);\n' % (self.ra(val)))
            self.write_undefine_ex_handle(ins)
            self.write('}\n')
        else:
            self.write('v%s = %r;\n' % (self.ra(val), cst))

    def visit_constant(self, cst):
        self.write('%s' % cst)

    def visit_variable(self, var):
        self.write('v%s' % self.ra(var))

    def visit_param(self, param):
        decl_type = get_native_type(param.get_type())
        if decl_type in ('jstring', 'jobject', 'jarray'):
            self.write('env->NewLocalRef(p%s)' % (param.get_register()))
        else:
            self.write('p%s' % param.get_register())

    def visit_this(self):
        self.write('env->NewLocalRef(thiz)')

    def visit_move_result(self, ins, lhs, rhs):
        self.write_trace(ins)
        self.write_kill_local_reference(ins.get_value())
        self.write('v%s = (%s) %s;\n' % (self.ra(lhs), get_cdecl_type(lhs.get_type()), self.get_variable_or_const(rhs)))

    def visit_move(self, lhs, rhs):
        self.write_kill_local_reference(lhs)
        self.write('v%s = ' % (self.ra(lhs)))
        if is_primitive_type(rhs.get_type()):
            self.write('%s' % (self.get_variable_or_const(rhs)))
        else:
            self.write('(%s) env->NewLocalRef(v%s)' % (get_cdecl_type(lhs.get_type()), self.ra(rhs)))
        self.write(';\n')

    def visit_astore(self, ins, array, index, rhs):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(array)
        elem_type = ins.get_elem_type()
        if is_primitive_type(elem_type):
            self.write('{%s val = %s;' % (get_native_type(elem_type), self.get_variable_or_const(rhs)))
            self.write('env->Set%sArrayRegion((%sArray) v%s, (jint) %s, 1, &val);' %
                       (get_type_descriptor(elem_type), get_native_type(elem_type),
                        self.ra(array),
                        self.get_variable_or_const(index)))
            self.write('}\n')
        else:
            self.write('env->SetObjectArrayElement((jobjectArray) v%s, (jint) %s, v%s);' %
                       (self.ra(array),
                        self.get_variable_or_const(index),
                        self.ra(rhs)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_put_static(self, ins, clsdesc, name, ftype, rhs):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('jfieldID &fld = %s;\n' % (self.fa(ins.get_field())))
        self.write('D2C_RESOLVE_STATIC_FIELD(clz, fld, "%s", "%s", "%s");\n' % (get_type(clsdesc), name, ftype))
        self.write('env->SetStatic%sField(clz,fld,(%s) %s);\n' % (
            get_type_descriptor(ftype), get_native_type(ftype), self.get_variable_or_const(rhs)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def write_not_null(self, var):
        self.write('D2C_NOT_NULL(%s);\n' % (self.get_variable_or_const(var)))

    def visit_put_instance(self, ins, lhs, rhs, ftype, clsdesc, name):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(lhs)
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('jfieldID &fld = %s;\n' % (self.fa(ins.get_field())))
        self.write('D2C_RESOLVE_FIELD(clz, fld, "%s", "%s", "%s");\n' % (get_type(clsdesc), name, ftype))
        self.write('env->Set%sField(v%s,fld,(%s) %s);\n' % (
            get_type_descriptor(ftype), self.ra(lhs), get_native_type(ftype), self.get_variable_or_const(rhs)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_new(self, ins, result, atype):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        # should kill local reference after D2C_RESOLVE_CLASS, since D2C_RESOLVE_CLASS may throw exception,
        # so this ref may be double killed in exception handle.
        self.write_kill_local_reference(ins.get_value())
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('D2C_RESOLVE_CLASS(clz,"%s");\n' % (get_type(atype)))
        self.write('v%s = (%s) env->AllocObject(clz);\n' % (self.ra(result), get_native_type(result.get_type())))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def _invoke_common(self, ins, invoke_type, name, base, ptype, rtype, args, clsdesc):
        self.write('{\n')
        self.write_define_ex_handle(ins)
        if invoke_type != 'static':
            self.write("D2C_NOT_NULL(v%s);\n" % (self.ra(base)))
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('jmethodID &mid = %s;\n' % (self.ma(ins.get_call_method())))
        if invoke_type != 'static':
            self.write('D2C_RESOLVE_METHOD(clz, mid, "%s", "%s", "(%s)%s");\n' % (get_type(clsdesc), name, ''.join(ptype), rtype))
        else:
            self.write('D2C_RESOLVE_STATIC_METHOD(clz, mid, "%s", "%s", "(%s)%s");\n' % (get_type(clsdesc), name, ''.join(ptype), rtype))
        self.write('jvalue args[] = {')
        vars = []
        for arg, atype in zip(args, ptype):
            if atype[0] == 'L' or atype[0] == '[':
                vars.append('{.l = %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'Z':
                vars.append('{.z = (jboolean) %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'B':
                vars.append('{.b = (jbyte) %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'C':
                vars.append('{.c = (jchar) %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'S':
                vars.append('{.s = (jshort) %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'I':
                vars.append('{.i = %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'J':
                vars.append('{.j = (jlong) %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'F':
                vars.append('{.f = %s}' % (self.get_variable_or_const(arg)))
            elif atype[0] == 'D':
                vars.append('{.d = %s}' % (self.get_variable_or_const(arg)))
            else:
                raise Exception("Unknow signuare type %s" % (atype))
        self.write(','.join(vars))
        self.write('};\n')
        if rtype != 'V':
            self.write_kill_local_reference(ins.get_value())
            ins.get_value().visit(self)
            self.write(' = ')
            self.write("(%s) " % (get_native_type(ins.get_value().get_type())))

        if invoke_type == 'super':
            self.write(
                'env->CallNonvirtual%sMethodA(v%s, clz, mid, args);\n' % (get_type_descriptor(rtype), self.ra(base)))
        elif invoke_type == 'static':
            self.write('env->CallStatic%sMethodA(clz, mid, args);\n' % (get_type_descriptor(rtype)))
        else:
            self.write('env->Call%sMethodA(v%s, mid, args);\n' % (get_type_descriptor(rtype), self.ra(base)))

        self.write_undefine_ex_handle(ins)
        self.write('}\n')
        if rtype != 'V':
            self.write_delete_dead_local_reference(ins.get_value())

    def visit_invoke(self, ins, invoke_type, name, base, ptype, rtype, args, clsdesc):
        self.write_trace(ins)
        return self._invoke_common(ins, invoke_type, name, base, ptype, rtype, args, clsdesc)

    def visit_return_void(self):
        self.write('return')
        self.end_ins()

    def visit_return(self, arg):
        return_type = self.irmethod.rtype
        if return_type[0] != 'V':
            self.write("return (%s) %s;\n" % (get_native_type(return_type), self.get_variable_or_const(arg)))
        else:
            self.write('return;')

    def visit_nop(self):
        pass

    def visit_goto(self, target):
        self.write('goto L%d' % (self.irmethod.offset_to_node[target].num))
        self.end_ins()

    def visit_check_cast(self, ins, arg, atype):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('D2C_RESOLVE_CLASS(clz,"%s");\n' % (get_type(atype)))
        self.write('D2C_CHECK_CAST(%s, clz, "%s");\n' % (self.get_variable_or_const(arg), get_type(atype)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_instanceof(self, ins, result, arg, atype):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('D2C_RESOLVE_CLASS(clz,"%s");\n' % (get_type(atype)))
        self.write('v%s = d2c_is_instance_of(env, v%s, clz);\n' % (self.ra(result), self.ra(arg)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_aload(self, ins, result, array, index):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(array)
        elem_type = ins.get_elem_type()
        if is_primitive_type(elem_type):
            self.write('{%s val;' % (get_native_type(elem_type)))
            self.write('env->Get%sArrayRegion((%sArray) v%s, (jint) %s, 1, &val);' %
                       (get_type_descriptor(elem_type), get_native_type(elem_type), self.ra(array),
                        self.get_variable_or_const(index)))
            self.write('v%s = val;}' % (self.ra(result)))
        else:
            self.write_kill_local_reference(result)
            self.write('v%s = (%s) env->GetObjectArrayElement((jobjectArray) v%s, (jint) %s);' %
                       (self.ra(result), get_native_type(result.get_type()),
                        self.ra(array),
                        self.get_variable_or_const(index)))
        self.write('\n')
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_alength(self, ins, result, array):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(array)
        self.write('v%s = env->GetArrayLength((jarray) v%s);\n' % (self.ra(result), self.ra(array)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def write_check_array_size(self, size):
        self.write('if (%s < 0) {\n'
                   'd2c_throw_exception(env, "java/lang/NegativeArraySizeException", "negative array size");\n'
                   % self.get_variable_or_const(size))
        self.write('goto EX_HANDLE;\n')
        self.write('}\n')

    def visit_new_array(self, ins, result, atype, size):
        self.write_trace(ins)
        elem_type = ins.get_elem_type()
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_check_array_size(size)
        self.write_kill_local_reference(ins.get_value())
        if is_primitive_type(elem_type):
            result.visit(self)
            self.write(
                ' = (%s) env->New%sArray((jint) %s);\n' % (
                get_native_type(result.get_type()), get_type_descriptor(elem_type), self.get_variable_or_const(size)))
        else:
            self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
            self.write('D2C_RESOLVE_CLASS(clz,"%s");\n' % (get_type(elem_type)))
            result.visit(self)
            self.write(' = env->NewObjectArray((jint) %s, clz, NULL);\n' % (self.get_variable_or_const(size)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_filled_new_array(self, ins, result, atype, size, args):
        self.write_trace(ins)
        params = []
        for arg in args:
            p = '%s' % (self.get_variable_or_const(arg))
            params.append(p)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_kill_local_reference(ins.get_value())
        elem_type = atype[1:]
        assert elem_type != 'D' and elem_type != 'J'
        if is_primitive_type(elem_type):
            result.visit(self)
            self.write(' = env->New%sArray((jint) %r);\n' % (get_type_descriptor(elem_type), size))
        else:
            self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
            self.write('D2C_RESOLVE_CLASS(clz,"%s");\n' % (get_type(elem_type)))
            result.visit(self)
            self.write(' = env->NewObjectArray((jint) %r, clz, NULL);\n' % (size))
        self.write('d2c_filled_new_array(env, (jarray) v%s, "%s", %d, %s);\n'
                   % (self.ra(result), elem_type, len(params), ', '.join(params)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_fill_array(self, ins, array, value):
        self.write_trace(ins)
        self.write('{\n')
        self.write('static const unsigned char data[] = {')
        data = value.get_data()
        tab = []
        elem_id = 'B'
        elem_size = 1

        for i in range(0, value.size * value.element_width, elem_size):
            tab.append('%s' % unpack(elem_id, data[i:i + elem_size])[0])
        self.write(', '.join(tab))
        self.write('};\n')

        elem_type = array.get_type()[1:]
        array_size = value.size

        self.write(
            'env->Set%sArrayRegion((%sArray) v%s, 0, %d, (const %s *) data);\n' % (get_type_descriptor(elem_type), \
                                                                                   get_native_type(elem_type),
                                                                                   self.ra(array), \
                                                                                   array_size,
                                                                                   get_native_type(elem_type)))
        self.write('}\n')

    def visit_move_exception(self, ins, var):
        self.write_trace(ins)
        self.write_kill_local_reference(var)
        var.declared = True
        var.visit(self)
        self.write(' = exception;\n')

    def visit_monitor_enter(self, ins, ref):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(ref)
        self.write('env->MonitorEnter(%s);\n' % (self.get_variable_or_const(ref)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def visit_monitor_exit(self, ins, ref):
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write('if (env->MonitorExit(%s) != JNI_OK) {\n' % (self.get_variable_or_const(ref)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')
        self.write('}\n')

    def visit_throw(self, ins, ref):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(ref)
        self.write('env->Throw((jthrowable) v%s);\n' % self.ra(ref))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def write_div_expression(self, ins, result, op, arg1, arg2):
        self.write('{\n')
        if result.get_type() not in 'FD':
            self.write_define_ex_handle(ins)
            self.write('if (%s == 0) {\n'
                       'd2c_throw_exception(env, "java/lang/ArithmeticException", "divide by zero");\n'
                       % self.get_variable_or_const(arg2))
            self.write('goto EX_HANDLE;\n')
            self.write('}\n')
            self.write('#undef EX_HANDLE\n')
        self.write('v%s = ' % (self.ra(result)))
        arg1.visit(self)
        self.write(' %s ' % (op))
        arg2.visit(self)
        self.write(';\n')
        self.write('}\n')

    def visit_binary_expression(self, ins, result, op, arg1, arg2):
        self.write_trace(ins)
        if op == Op.DIV or op == Op.MOD:
            self.write_div_expression(ins, result, op, arg1, arg2)
            return

        self.write('v%s = ' % self.ra(result))
        # 浮点数有个NaN值,任何值与他比较都不成立,包括NaN.
        if op == Op.CMP:
            self.write('(')
            arg1.visit(self)
            self.write(' == ')
            arg2.visit(self)
            self.write(') ? 0 :')
            self.write(' (')
            arg1.visit(self)
            self.write(' > ')
            arg2.visit(self)
            self.write(') ? 1 : -1;\n')
        elif op == Op.CMPL:
            self.write('(')
            arg1.visit(self)
            self.write(' == ')
            arg2.visit(self)
            self.write(') ? 0 :')
            self.write(' (')
            arg1.visit(self)
            self.write(' > ')
            arg2.visit(self)
            self.write(') ? 1 : -1;\n')
        elif op == Op.CMPG:
            self.write('(')
            arg1.visit(self)
            self.write(' == ')
            arg2.visit(self)
            self.write(') ? 0 :')
            self.write(' (')
            arg1.visit(self)
            self.write(' < ')
            arg2.visit(self)
            self.write(') ? -1 : 1;\n')
        elif op == Op.INTSHR:
            self.write('(%s) >> (' % (self.get_variable_or_const(arg1)))
            arg2.visit(self)
            self.write(' & 0x1f);\n')
        elif op == Op.INTSHL:
            self.write('(%s) << (' % (self.get_variable_or_const(arg1)))
            arg2.visit(self)
            self.write(' & 0x1f);\n')
        elif op == Op.INTUSHR:
            self.write('((uint32_t) %s) >> (' % (self.get_variable_or_const(arg1)))
            arg2.visit(self)
            self.write(' & 0x1f);\n')
        elif op == Op.LONGSHR:
            self.write('(v%s) >> (' % (self.ra(arg1)))
            arg2.visit(self)
            self.write(' & 0x3f);\n')
        elif op == Op.LONGSHL:
            self.write('(%s) << (' % (self.get_variable_or_const(arg1)))
            arg2.visit(self)
            self.write(' & 0x3f);\n')
        elif op == Op.LONGUSHR:
            self.write('((uint64_t) v%s) >> (' % (self.ra(arg1)))
            arg2.visit(self)
            self.write(' & 0x3f);\n')
        elif op == Op.MODF:
            self.write('fmodf(v%s, v%s);\n' % (self.ra(arg1), self.ra(arg2)))
        elif op == Op.MODD:
            self.write('fmod(v%s, v%s);\n' % (self.ra(arg1), self.ra(arg2)))
        else:
            self.write('(')
            arg1.visit(self)
            self.write(' %s ' % op)
            arg2.visit(self)
            self.write(');\n')

    def visit_unary_expression(self, ins, result, op, arg):
        self.write_trace(ins)
        self.write('v%s = (%s %s);\n' % (self.ra(result), op, self.get_variable_or_const(arg)))

    def visit_cast(self, lhs, op, arg):
        type1 = arg.get_type()
        type2 = lhs.get_type()
        # double to long
        if type1 == 'D' and type2 == 'J':
            self.write('v%s = d2c_double_to_long(v%s);\n' % (self.ra(lhs), self.ra(arg)))
        # double to int
        elif type1 == 'D' and type2 == 'I':
            self.write('v%s = d2c_double_to_int(v%s);\n' % (self.ra(lhs), self.ra(arg)))
        # float to long
        elif type1 == 'F' and type2 == 'J':
            self.write('v%s = d2c_float_to_long(v%s);\n' % (self.ra(lhs), self.ra(arg)))
        elif type1 == 'F' and type2 == 'I':
            self.write('v%s = d2c_float_to_int(v%s);\n' % (self.ra(lhs), self.ra(arg)))
        else:
            self.write('v%s = %s(%s);\n' % (self.ra(lhs), op, self.get_variable_or_const(arg)))

    def visit_cond_expression(self, ins, op, arg1, arg2, true_target, false_target):
        self.write_trace(ins)
        true_target_node = self.irmethod.offset_to_node[true_target]
        false_target_node = self.irmethod.offset_to_node[false_target]
        self.write('if(')
        if is_primitive_type(arg1.get_type()):
            arg1.visit(self)
            self.write(' %s ' % op)
            arg2.visit(self)
        else:
            if op == '!=':
                self.write('!')
            self.write('d2c_is_same_object(env,')
            arg1.visit(self)
            self.write(',')
            arg2.visit(self)
            self.write(')')
        self.write(') ')
        self.write('{\n')
        self.write('goto L%d;\n' % true_target_node.num)
        self.write('}\n')
        self.write('else {\n')
        self.write('goto L%d;\n' % false_target_node.num)
        self.write('}\n')

    def visit_condz_expression(self, ins, op, arg, true_target, false_target):
        self.write_trace(ins)
        true_target_node = self.irmethod.offset_to_node[true_target]
        false_target_node = self.irmethod.offset_to_node[false_target]
        if isinstance(arg, BinaryCompExpression):
            arg.op = op
            return arg.visit(self)
        atype = arg.get_type()
        self.write('if(')
        arg.visit(self)
        if atype in 'ZBSCIJFD':
            self.write(' %s 0' % op)
        else:
            self.write(' %s NULL' % op)
        self.write(')')
        self.write('{\n')
        self.write('goto L%d;\n' % (true_target_node.num))
        self.write('}\n')
        self.write('else {\n')
        self.write('goto L%d;\n' % (false_target_node.num))
        self.write('}\n')

    def visit_get_instance(self, ins, result, arg, ftype, clsdesc, name):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_not_null(arg)
        self.write_kill_local_reference(result)
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('jfieldID &fld = %s;\n' % (self.fa(ins.get_field())))
        self.write('D2C_RESOLVE_FIELD(clz, fld, "%s", "%s", "%s");\n' % (get_type(clsdesc), name, ftype))
        result.visit(self)
        self.write(
            ' = (%s) env->Get%sField(v%s,fld);\n' % (
                get_native_type(result.get_type()), get_type_descriptor(ftype), self.ra(arg)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def write_define_ex_handle(self, ins):
        bb = ins.parent
        if bb in self.irmethod.node_to_landing_pad:
            landing_pad = self.irmethod.node_to_landing_pad[ins.parent].label
        else:
            landing_pad = 'EX_UnwindBlock'
        self.write("#define EX_HANDLE %s\n" % (landing_pad))

    def write_undefine_ex_handle(self, ins):
        self.write('D2C_CHECK_PENDING_EX;\n')
        self.write('#undef EX_HANDLE\n')

    def visit_get_static(self, ins, result, ftype, clsdesc, name):
        self.write_trace(ins)
        self.write('{\n')
        self.write_define_ex_handle(ins)
        self.write_kill_local_reference(result)
        self.write('jclass &clz = %s;\n' % (self.ca(ins.get_class())))
        self.write('jfieldID &fld = %s;\n' % (self.fa(ins.get_field())))
        self.write('D2C_RESOLVE_STATIC_FIELD(clz, fld, "%s", "%s", "%s");\n' % (get_type(clsdesc), name, ftype))
        result.visit(self)
        self.write(' = (%s) env->GetStatic%sField(clz,fld);\n' % (
            get_native_type(result.get_type()), get_type_descriptor(ftype)))
        self.write_undefine_ex_handle(ins)
        self.write('}\n')

    def get_variable_or_const(self, var):
        if isinstance(var, Constant):
            return '%s' % var
        else:
            return 'v%s' % self.ra(var)
