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
from collections import OrderedDict

from dex2c.instruction import MoveResultExpression
from dex2c.opcode_ins import INSTRUCTION_SET

logger = logging.getLogger('dex2c.basic_blocks')


class IrBasicBlock(object):
    def __init__(self, dvm_basicblock):
        self.dvm_basicblock = dvm_basicblock
        self.instr_list = []

        # MoveParam指令会给参数生成一个局部引用(local reference), 使用局部引用引用参数
        # 不能将它放入instr_list, 因为第一个基本块可以是循环
        self.move_param_insns = []
        self.var_to_declare = list()
        self.class_to_declare = list()
        self.field_to_declare = list()
        self.method_to_declare = list()
        self.num = -1  # 基本块编号

        # 处理异常相关
        self.in_catch = False
        self.catch_type = None

        # 构建SSA IR使用数据结构
        # Ref: <<Simple and Efficient Construction of Static Single Assignment Form>> by Matthias Braun
        self.filled = False
        self.sealed = False
        self.current_definitions = {}
        self.incomplete_phis = set()
        self.phis = set()

        self.catch_successors = set()

        if dvm_basicblock:
            self.start = self.dvm_basicblock.get_start()
        else:
            self.start = -1

    def get_instr_list(self):
        return self.instr_list

    def get_name(self):
        return self.label

    def add_ins_before(self, new_ins, before_ins):
        pos = self.instr_list.index(before_ins)
        self.instr_list = self.instr_list[:pos] + [new_ins] + self.instr_list[pos:]

    def remove_ins(self, ins):
        self.instr_list.remove(ins)

    def add_ins(self, new_ins):
        self.instr_list.append(new_ins)

    def add_variable_declaration(self, variable):
        self.var_to_declare.append(variable)

    def set_catch_type(self, _type):
        self.catch_type = _type

    def update_current_definition(self, register, var):
        self.current_definitions[register] = var

    def read_current_definition(self, register):
        return self.current_definitions[register] if register in self.current_definitions else None

    def visit(self, visitor):
        # pass
        visitor.visit_statement_node(self)

    def add_incomplete_phi(self, phi):
        self.incomplete_phis.add(phi)

    def get_incomplete_phis(self):
        return self.incomplete_phis

    def clear_incomplete_phis(self):
        self.incomplete_phis.clear()

    def add_phi(self, phi):
        self.phis.add(phi)

    def remove_phi(self, phi):
        if phi in self.phis:
            self.phis.remove(phi)

    def clear_phis(self):
        self.phis.clear()

    def add_catch_successor(self, node):
        if node not in self.catch_successors:
            self.catch_successors.add(node)

    @property
    def label(self):
        if self.dvm_basicblock:
            return 'BB_%x' % self.dvm_basicblock.start
        else:
            return 'BB_%d' % self.num

    def __str__(self):
        s = [self.label]
        for phi in self.phis:
            s.append(phi.print())

        for ins in self.instr_list:
            s.append(str(ins))
        return '\n'.join(s)


class LandingPad(IrBasicBlock):
    def __init__(self, source):
        super(LandingPad, self).__init__(None)
        self.node = source
        self.handles = OrderedDict()

    def add_catch_handle(self, atype, node):
        if atype in self.handles and atype != 'Ljava/lang/Throwable;':
            raise Exception("duplicate catch handle for %s" % atype)

        if atype not in self.handles:
            self.handles[atype] = node

    @property
    def label(self):
        return 'EX_LandingPad_%d' % self.node.num

    def __str__(self):
        return '%d' % self.node.num


def fill_node_from_block(irbuilder, node):
    block = node.dvm_basicblock
    idx = block.get_start()
    current_node = node
    for ins in block.get_instructions():
        opcode = ins.get_op_value()
        if opcode == -1:  # FIXME? or opcode in (0x0300, 0x0200, 0x0100):
            idx += ins.get_length()
            continue
        try:
            _ins = INSTRUCTION_SET[opcode]
        except IndexError:
            raise Exception('Unknown instruction : %s.', ins.get_name().lower())
        # fill-array-data
        if opcode == 0x26:
            fillarray = block.get_special_ins(idx)
            lastins = _ins(ins, irbuilder, fillarray)
            current_node.add_ins(lastins)
        # invoke-kind[/range]
        elif 0x6e <= opcode <= 0x72 or 0x74 <= opcode <= 0x78:
            lastins = _ins(ins, irbuilder)
            current_node.add_ins(lastins)
        elif 0x24 <= opcode <= 0x25:
            lastins = _ins(ins, irbuilder)
            current_node.add_ins(lastins)
        # move-result*
        elif 0xa <= opcode <= 0xc:
            lastins = _ins(ins, irbuilder)
            current_node.add_ins(lastins)
        # move-exception
        elif opcode == 0xd:
            lastins = _ins(ins, irbuilder, current_node.catch_type)
            current_node.add_ins(lastins)
        # {packed,sparse}-switch
        elif 0x2b <= opcode <= 0x2c:
            values = block.get_special_ins(idx)
            lastins = _ins(ins, irbuilder, values)
            current_node.add_ins(lastins)
        else:
            lastins = _ins(ins, irbuilder)
            current_node.add_ins(lastins)
            # aget-object v1_y, v1_x, v0
            # 如果v1_x在该指令后不再使用,我们会将v1_x释放,但是v1_x,v1_y分配到同一个寄存器(v1),导致v1_y被释放.
            # 解决办法是,我们将其转化为两条指令
            # aget-object vTmp, v1, v0
            # move-result-object v1, vTmp
            # 类似iget-object
            if opcode == 0x46 or opcode == 0x54:
                vtmp = irbuilder.write_result_variable()
                val = lastins.get_value()
                lastins.set_value(vtmp)
                move_ins = MoveResultExpression(val, vtmp)
                move_ins.parent = current_node  # 变量活跃分析会使用
                current_node.add_ins(move_ins)
        lastins.offset = idx
        lastins.parent = current_node
        if lastins.get_value():
            lastins.get_value().definition = lastins

        idx += ins.get_length()
        lastins.next_offset = idx
        lastins.dvm_instr = ins

    current_node.filled = True
    return current_node
