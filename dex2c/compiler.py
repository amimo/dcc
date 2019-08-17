# -*- coding: utf-8 -*-

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
from __future__ import print_function
import sys
import os
import inspect
from builtins import next
from builtins import object
from builtins import range
from builtins import str

from dex2c.basic_blocks import fill_node_from_block

import logging
import struct
from collections import defaultdict
import androguard.core.androconf as androconf
import dex2c.util as util
from androguard.core.analysis import analysis
from androguard.core.bytecodes import apk, dvm
from dex2c.graph import construct
from dex2c.instruction import Param, ThisParam, MoveParam, Phi, Variable, LoadConstant
from dex2c.writer import Writer
from androguard.util import read

DEBUG = False
# DEBUG = True

logger = logging.getLogger('dex2c.compiler')

def auto_vm(filename):
    ret = androconf.is_android(filename)
    if ret == 'APK':
        return dvm.DalvikVMFormat(apk.APK(filename).get_dex())
    elif ret == 'DEX':
        return dvm.DalvikVMFormat(read(filename))
    elif ret == 'DEY':
        return dvm.DalvikOdexVMFormat(read(filename))
    return None


class RegisterAllocator(object):
    def __init__(self, vars):
        self.slots = {}
        self.next_name = 0
        for var in vars:
            self.allocate(var)

    def allocate(self, var):
        register = var.get_register()
        assert var.get_type()
        atype = util.get_cdecl_type(var.get_type())
        if (register, atype) not in self.slots:
            logger.debug("%s -> v%s:%s" % (var, self.next_name, atype))
            self.slots[(register, atype)] = self.next_name
            self.next_name += 1
        else:
            logger.debug("%s -> v%s:%s" % (var, self.slots[(register, atype)], atype))
        return self.slots[(register, atype)]


class IrMethod(object):
    def __init__(self, graph, method):
        self.method = method

        self.graph = graph
        self.entry = graph.entry
        self.offset_to_node = graph.offset_to_node
        self.node_to_landing_pad = graph.node_to_landing_pad
        self.landing_pads = graph.landing_pads
        self.irblocks = self.graph.compute_block_order()

        self.cls_name = method.get_class_name()
        self.name = method.get_name()
        self.ra = RegisterAllocator(self.entry.var_to_declare).allocate
        self.writer = None

        self.rtype = None
        self.params = []
        self.params_type = []

    def show_source(self):
        print(self.get_source())

    def get_source(self):
        if self.writer:
            return str(self.writer)
        return ''

    def __repr__(self):
        return 'class IrMethod(object): %s' % self.name


class IrBuilder(object):
    def __init__(self, methanalysis):
        method = methanalysis.get_method()
        self.method = method
        self.irmethod = None
        self.start_block = next(methanalysis.get_basic_blocks().get(), None)
        self.cls_name = method.get_class_name()
        self.name = method.get_name()
        self.lparams = []
        self.var_to_name = defaultdict()
        self.offset_to_node = {}
        self.graph = None

        self.access = util.get_access_method(method.get_access_flags())

        desc = method.get_descriptor()
        self.type = desc.split(')')[-1]
        self.params_type = util.get_params_type(desc)
        self.triple = method.get_triple()

        self.exceptions = methanalysis.exceptions.exceptions
        self.curret_block = None

        self.var_versions = defaultdict(int)

        code = self.method.get_code()
        if code:
            start = code.registers_size - code.ins_size
            if 'static' not in self.access:
                self.lparams.append(start)
                start += 1
            num_param = 0
            for ptype in self.params_type:
                param = start + num_param
                self.lparams.append(param)
                num_param += util.get_type_size(ptype)

        if DEBUG:
            from androguard.core import bytecode
            bytecode.method2png('graphs/%s#%s.png' % \
                                (self.cls_name.split('/')[-1][:-1], self.name),
                                methanalysis)

    def get_return_type(self):
        return self.type

    def process(self):
        logger.debug('METHOD : %s', self.name)

        # Native methods... no blocks.
        if self.start_block is None:
            return

        graph = construct(self.start_block)
        self.graph = graph
        if DEBUG:
            util.create_png(self.cls_name, self.name, graph, 'blocks')

        # if __debug__:
        #     util.create_png(self.cls_name, self.name, graph, 'blocks')

        self.build()
        if DEBUG:
            util.create_png(self.cls_name, self.name + 'ir', graph, 'blocks')

        irmethod = IrMethod(graph, self.method)
        irmethod.rtype = self.get_return_type()
        irmethod.params = self.lparams
        irmethod.params_type = self.params_type

        writer = Writer(irmethod)
        writer.write_method()
        irmethod.writer = writer
        return irmethod

    def build(self):
        self.define_params()

        self.graph.entry.sealed = True  # Entry has Predecessor?

        todo = [self.graph.entry]
        while todo:
            node = todo.pop(0)
            if node.filled:
                continue
            self.curret_block = node
            node = fill_node_from_block(self, node)
            self.try_seal_block(node)
            todo.extend(self.graph.all_sucs(node))

        self.remove_trivial_phi()
        if DEBUG:
            util.create_png(self.cls_name, self.name + '_before_hack', self.graph, 'blocks')
        self.hack_polymorphic_constant()
        if DEBUG:
            util.create_png(self.cls_name, self.name + '_after_hack', self.graph, 'blocks')
        self.infer_type()
        self.fix_const_type()
        self.verify_operand_type()
        self.verify_phi_operand_type()

        # self.dump_type()

        self.add_var_to_decl()

    def remove_trivial_phi(self):
        Changed = True
        while Changed:
            Changed = False
            for node in self.graph.rpo:
                phis = list(node.phis)
                for phi in phis:
                    Changed |= phi.remove_trivial_phi()

    def verify_operand_type(self):
        nodes = self.graph.compute_block_order()
        for node in nodes:
            for ins in node.get_instr_list():
                var = ins.get_value()
                if var and var.get_type() is None:
                    raise Exception('unkonw type %s' % var)

    def verify_phi_operand_type(self):
        for node in self.graph.rpo:
            phis = list(node.phis)
            for phi in phis:
                same_type = phi.get_type()
                for operand in phi.get_operands().values():
                    op_type = operand.get_type()
                    if util.is_int(same_type) and util.is_int(op_type):
                        continue
                    elif util.is_float(same_type) and util.is_float(op_type):
                        continue
                    elif util.is_ref(same_type) and util.is_ref(op_type):
                        continue
                    else:
                        raise Exception("inconsistency phi operand type %s %s %s" % (phi, same_type, op_type))

    def hack_polymorphic_constant(self):
        nodes = self.graph.compute_block_order()
        todo_list = []
        for node in nodes:
            for ins in node.get_instr_list():
                if isinstance(ins, LoadConstant) and ins.get_value_type() is None:
                    todo_list.append(ins)
        while todo_list:
            ins = todo_list.pop(0)
            bb = ins.parent
            for user in ins.get_users():
                new_val = self.write_variable(ins.get_value().get_register())
                new_ins = LoadConstant(new_val, ins.get_cst())
                bb.add_ins_before(new_ins, ins)
                # 每处引用不同的常量拷贝,解决常量多态问题.如0,可以当NULL,整型0,false使用.
                user.replase_use_of_with(ins.get_value(), new_val)
            ins.parent.remove_ins(ins)

    def infer_type(self):
        Changed = True
        nodes = self.graph.compute_block_order()
        max = 500
        while Changed:
            # self.dump_type()
            max -= 1
            if max == 0:
                raise Exception("type infer failed")

            Changed = False
            for node in nodes:
                for phi in node.phis:
                    Changed |= phi.resolve_type()
                for ins in node.get_instr_list():
                    Changed |= ins.resolve_type()

    # 无法推导出的常量类型,根据其大小,设置类型
    def fix_const_type(self):
        nodes = self.graph.rpo
        Changed = False
        for node in nodes:
            for ins in node.get_instr_list():
                if isinstance(ins, LoadConstant) and ins.get_value_type() is None:
                    if -2147483648 <= ins.get_cst().get_constant() <= 2147483647:
                        Changed = True
                        logger.debug("Set constant type to int: %s" % ins)
                        ins.set_value_type('I')
                    else:
                        Changed = True
                        logger.debug("Set constant type to long: %s" % ins)
                        ins.set_value_type('J')

        if Changed:
            self.infer_type()

    def dump_type(self):
        nodes = self.graph.compute_block_order()
        for node in nodes:
            for ins in node.get_instr_list():
                var = ins.get_value()
                if var is not None:
                    print('Type: %s %s' % (var, var.get_type()))

    def add_var_to_decl(self):
        entry = self.graph.entry
        nodes = self.graph.compute_block_order()
        for node in nodes:
            for ins in node.get_instr_list():
                var = ins.get_value()
                if var is not None:
                    entry.var_to_declare.append(var)

                clz = ins.get_class()
                if clz:
                    entry.class_to_declare.append(clz)

                field = ins.get_field()
                if field:
                    entry.field_to_declare.append(field)

                method = ins.get_call_method()
                if method:
                    entry.method_to_declare.append(method)

    def try_seal_block(self, block):
        sucs = self.graph.all_sucs(block)

        if len(sucs) == 0:
            return

        for suc in sucs:
            preds = self.graph.all_preds(suc)
            filled = list(filter(lambda pred: pred.filled, preds))
            if len(filled) == len(preds):
                self.seal_block(suc)

    def seal_block(self, block):
        preds = self.graph.all_preds(block)
        block.sealed = True
        for phi in block.get_incomplete_phis():
            for pred in preds:
                incoming = self.read_variable(phi.get_register(), pred)
                phi.add_operand(pred, incoming)
            block.add_phi(phi)
        block.clear_incomplete_phis()

    def set_current_block(self, block):
        self.curret_block = block

    def get_current_block(self):
        return self.curret_block

    def read_result_variable(self):
        var = self.read_variable(-1, self.curret_block)
        if isinstance(var, Phi):
            raise Exception("invoke result is a Phi node")
        return var

    def write_result_variable(self):
        return self.write_variable(-1)

    def write_variable(self, register):
        value = self.new_ssa_variable(register)
        self.curret_block.update_current_definition(register, value)
        return value

    def read_variable(self, register, block=None):
        if block is None:
            block = self.curret_block
        value = block.read_current_definition(register)
        if value is None:
            return self.read_variable_recursive(register, block)
        else:
            return value

    def read_variable_recursive(self, register, block):
        preds = self.graph.all_preds(block)
        if not block.sealed:
            value = self.new_ssa_variable(register, True)
            block.add_incomplete_phi(value)
            value.set_block(block)
        elif len(preds) == 1:
            value = self.read_variable(register, preds[0])
        else:
            value = self.new_ssa_variable(register, True)
            block.update_current_definition(register, value)
            block.add_phi(value)
            value.set_block(block)
            for pred in preds:
                incoming = self.read_variable(register, pred)
                value.add_operand(pred, incoming)
        block.update_current_definition(register, value)
        return value

    def define_params(self):
        entry = self.graph.entry
        code = self.method.get_code()
        if code:
            start = code.registers_size - code.ins_size
            if 'static' not in self.access:
                param = self.new_ssa_variable(start)
                param.set_type(self.cls_name)
                entry.move_param_insns.append(MoveParam(ThisParam(param)))
                entry.update_current_definition(start, param)
                entry.var_to_declare.append(param)
                start += 1
            num_param = 0
            for ptype in self.params_type:
                register = start + num_param
                param = self.new_ssa_variable(register)
                param.set_type(ptype)
                entry.move_param_insns.append(MoveParam(Param(param)))
                entry.update_current_definition(register, param)
                entry.var_to_declare.append(param)
                num_param += util.get_type_size(ptype)

    def new_ssa_variable(self, register, phi=False):

        ver = self.var_versions.get(register, 0)
        new_var = Phi(register, ver) if phi else Variable(register, ver)

        ver += 1
        self.var_versions[register] = ver
        return new_var

    def __repr__(self):
        # return 'Method %s' % self.name
        return 'class DvMethod(object): %s' % self.name


class DvClass(object):
    def __init__(self, dvclass, vma):
        name = dvclass.get_name()
        if name.find('/') > 0:
            pckg, name = name.rsplit('/', 1)
        else:
            pckg, name = '', name
        self.package = pckg[1:].replace('/', '.')
        self.name = name[:-1]

        self.vma = vma
        self.methods = dvclass.get_methods()
        self.fields = dvclass.get_fields()
        self.code = []
        self.inner = False

        access = dvclass.get_access_flags()
        # If interface we remove the class and abstract keywords
        if 0x200 & access:
            prototype = '%s %s'
            if access & 0x400:
                access -= 0x400
        else:
            prototype = '%s class %s'

        self.access = util.get_access_class(access)
        self.prototype = prototype % (' '.join(self.access), self.name)

        self.interfaces = dvclass.get_interfaces()
        self.superclass = dvclass.get_superclassname()
        self.thisclass = dvclass.get_name()

        logger.info('Class : %s', self.name)
        logger.info('Methods added :')
        for meth in self.methods:
            logger.info('%s (%s, %s)', meth.get_method_idx(), self.name,
                        meth.name)
        logger.info('')

    def get_methods(self):
        return self.methods

    def process_method(self, num):
        method = self.methods[num]
        if not isinstance(method, IrMethod):
            irbuilder = IrBuilder(self.vma.get_method(method))
            self.methods[num] = irbuilder.process()
        else:
            method.process()

    def process(self):
        for i in range(len(self.methods)):
            try:
                self.process_method(i)
            except Exception as e:
                logger.warning('Error decompiling method %s: %s', self.methods[i], e)

    def get_source(self):
        source = []
        for method in self.methods:
            if isinstance(method, IrMethod):
                source.append(method.get_source())
        return ''.join(source)

    def show_source(self):
        print(self.get_source())

    def __repr__(self):
        return 'Class(%s)' % self.name


class DvMachine(object):
    def __init__(self, name):
        vm = auto_vm(name)
        if vm is None:
            raise ValueError('Format not recognised: %s' % name)
        self.vma = analysis.Analysis(vm)
        self.classes = dict((dvclass.get_name(), dvclass)
                            for dvclass in vm.get_classes())

    def get_classes(self):
        return list(self.classes.keys())

    def get_class(self, class_name):
        for name, klass in self.classes.items():
            if class_name in name:
                if isinstance(klass, DvClass):
                    return klass
                dvclass = self.classes[name] = DvClass(klass, self.vma)
                return dvclass

    def process(self):
        for name, klass in self.classes.items():
            logger.info('Processing class: %s', name)
            if isinstance(klass, DvClass):
                klass.process()
            else:
                dvclass = self.classes[name] = DvClass(klass, self.vma)
                dvclass.process()

    def show_source(self):
        for klass in self.classes.values():
            klass.show_source()

    def process_and_show(self):
        for name, klass in sorted(self.classes.items()):
            logger.info('Processing class: %s', name)
            if not isinstance(klass, DvClass):
                klass = DvClass(klass, self.vma)
            klass.process()
            klass.show_source()


class Dex2C:
    def __init__(self, vm, vmx):
        self.vm = vm
        self.vmx = vmx
        
    def get_source_method(self, m):
        mx = self.vmx.get_method(m)
        z = IrBuilder(mx)
        irmethod = z.process()
        if irmethod:
            return irmethod.get_source()
        else:
            return None

    def get_source_class(self, _class):
        c = DvClass(_class, self.vmx)
        c.process()
        return c.get_source()
