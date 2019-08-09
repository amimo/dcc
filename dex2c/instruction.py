# encoding=utf8
#
# Copyright (C) 2012, Geoffroy Gueguen <geoffroy.gueguen@gmail.com>
# All rights reserved.
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
from typing import List, Set
from dex2c import util

logger = logging.getLogger('dex2c.instruction')


class Value(object):
    def __init__(self):
        self.var_type = None
        self.type_sealed = False

        self.definition = None
        self.uses = set()
        self.is_const = False

    def set_type(self, vtype: str):
        if vtype is None or self.type_sealed:
            return False

        self.type_sealed = True
        if self.var_type is None:
            self.var_type = vtype
            return True

        if self.var_type == vtype:
            return False
        else:
            self.var_type = vtype
            return True

    def refine_type(self, vtype: str):

        if vtype is None or self.type_sealed or self.var_type == vtype:
            return False

        if self.var_type is None:
            self.var_type = vtype
            return True

        if util.is_java_lang_object(vtype) and util.is_ref(self.var_type):
            return False

        if util.is_java_lang_object(self.var_type) and util.is_ref(vtype):
            return False

        if (util.is_int(self.var_type) and util.is_int(vtype)) or \
                (util.is_float(self.var_type) and util.is_float(vtype)):
            new_type = util.get_smaller_type(self.var_type, vtype)
            if new_type != self.var_type:
                self.var_type = new_type
                return True
            else:
                return False
        elif util.is_int(self.var_type) and (util.is_float(vtype) or util.is_ref(vtype)):
            # 常量转换成浮点,提升为浮点类型,或者引用类型 0->NULL, 0->int_to_float()
            if self.is_const:
                # 常量转换成浮点,需要调用相应的帮助函数
                self.var_type = vtype
                return True
            else:
                if util.is_float(vtype):
                    # 可以无损转化成浮点类型
                    return False
                else:
                    raise Exception("unable to refine type %s %s" % (self.var_type, vtype))
        else:
            new_type = util.merge_type(self.var_type, vtype)
            if new_type is None:
                raise Exception("unable to refine type %s %s" % (self.var_type, vtype))
            if self.var_type != new_type:
                self.var_type = new_type
                return True
            else:
                return False

    def get_type(self):
        return self.var_type

    def use_empty(self):
        return len(self.uses) == 0

    def get_uses(self):
        return self.uses

    def get_users(self):
        users = set()
        for use in self.uses:
            users.add(use.get_user())
        return list(users)

    def add_user(self, instr):
        for use in self.uses:
            if use.get_user() == instr:
                return
        else:
            use = Use(self, instr)
            self.uses.add(use)

    def visit_decl(self, visitor):
        return visitor.visit_decl(self)

    def remove_user(self, user):
        new_uses = set()
        for use in self.uses:
            if user != use.get_user():
                new_uses.add(use)
        self.uses = new_uses

    def replace_all_uses_with(self, new_value):
        for use in self.uses:
            user = use.get_user()
            user.replase_use_of_with(use.get_value(), new_value)
        self.uses.clear()


class Use(object):
    def __init__(self, value: Value, user):
        self.value = value
        self.user = user

    def get_user(self):
        return self.user

    def get_value(self):
        return self.value


class Constant(Value):
    def __init__(self, value, vtype=None):
        super(Constant, self).__init__()
        self.constant = value
        self.is_const = True
        if vtype:
            self.refine_type(vtype)

    def get_constant(self):
        if self.var_type and self.var_type[0] == 'L':
            return util.hex_escape_string(self.constant)
        else:
            return self.constant

    def visit(self, visitor):
        return visitor.visit_constant(self)

    def visit_decl(self, visitor):
        return visitor.visit_decl(self)

    def __str__(self):
        atype = self.var_type
        if atype == 'F':
            return 'd2c_bitcast_to_float(%r)' % self.constant
        elif atype == 'D':
            return 'd2c_bitcast_to_double(%r)' % self.constant
        elif util.is_int(atype) or util.is_long(atype):
            return '%r' % self.constant
        else:
            return '%s' % (self.get_constant())


class Variable(Value):
    def __init__(self, register, version):
        super(Variable, self).__init__()
        self.register = register
        self.version = version

    def set_type(self, vtype: str):
        return super(Variable, self).set_type(vtype)

    def refine_type(self, vtype: str):
        return super(Variable, self).refine_type(vtype)

    def get_register(self):
        return self.register

    def visit(self, visitor):
        return visitor.visit_variable(self)

    def visit_decl(self, visitor):
        return visitor.visit_decl(self)

    def __str__(self):
        return 'v%s_%s' % (self.register if self.register >= 0 else 'Result', self.version)


class Phi(Variable):
    def __init__(self, register, version):
        super(Phi, self).__init__(register, version)
        self.operands = {}
        self.block = None
        self.phi_users = set()

    def get_operands(self):
        return self.operands

    def set_block(self, block):
        self.block = block

    def get_block(self):
        return self.block

    def add_operand(self, pred, value):
        self.operands[pred] = value
        value.add_user(self)

    def get_incoming_blocks(self, value):
        result = []
        for k, v in self.operands.items():
            if v == value:
                result.append(k)
        return result

    def remove_operand(self, pred):
        self.operands.pop(pred)

    def replase_use_of_with(self, old: Value, new: Value):
        for pred, value in self.operands.items():
            if value == old:
                value.remove_user(self)
                new.add_user(self)
                self.operands[pred] = new

    def resolve_type(self):
        same_op_type = None

        for op in self.operands.values():
            if isinstance(op, Constant):
                continue
            op_type = op.get_type()
            if same_op_type and op_type != same_op_type:
                op_type = util.merge_type(same_op_type, op_type)
            same_op_type = op_type

        if same_op_type:
            new_type = same_op_type
        else:
            new_type = self.var_type

        Changed = False
        if new_type:
            if self.var_type != new_type:
                Changed |= self.refine_type(new_type)
            for op in self.operands.values():
                if isinstance(op, Constant):
                    continue
                if op.get_type() != new_type:
                    Changed |= op.refine_type(new_type)
        return Changed

    def remove_trivial_phi(self):
        # return
        same = None
        for op in self.operands.values():
            if op == same or op == self:
                continue

            if not same is None:
                return False
            same = op

        for op in self.operands.values():
            op.remove_user(self)

        self.replace_all_uses_with(same)
        self.block.remove_phi(self)
        assert len(self.uses) == 0
        return True

    def print(self):
        s = 'v%s_%s = Phi(' % (self.register, self.version)
        vars = []
        for n, v in self.operands.items():
            vars.append(str(v))
        s += ','.join(vars)
        s += ')'
        return s


class Instruction(object):
    def __init__(self):
        self.value: Value = None
        self.operands: List[Value] = []
        self.parent = None  # bb
        self.offset = -1  # current instruction's offset, used by branch instruction
        self.next_offset = -1  # next instruction's offset, used to get next basicblock
        self.dvm_instr = None

        # 活跃信息,如果一个引用类型变量在live_in但不在live_out,需要释放引用
        self.live_in: Set[Value] = set()
        self.live_out: Set[Value] = set()

    def set_value(self, value):
        self.value = value

    def set_value_type(self, vtype):
        return self.value.set_type(vtype)

    def get_value_type(self):
        return self.value.get_type()

    def set_operand_type(self, index, vtype):
        self.operands[index].refine_type(vtype)

    def get_operand_type(self, index):
        self.operands[index].get_type()

    def get_operans_number(self):
        return len(self.operands)

    def resolve_type(self):
        return False

    def is_const(self):
        return False

    def get_value(self):
        return self.value

    def get_users(self):
        return list(self.value.get_users())

    def add_user(self, instr):
        self.value.add_user(instr)

    def remove_user(self, user):
        self.value.remove_user(user)

    def replase_use_of_with(self, old_var: Value, new_var: Value):
        for idx, operand in enumerate(self.operands):
            if old_var == operand:
                self.operands[idx] = new_var
                new_var.add_user(self)
                old_var.remove_user(self)

    def visit(self, visitor):
        pass

    def get_class(self):
        return None

    def get_field(self):
        return None

    def get_call_method(self):
        return None

    def dump(self):
        if self.dvm_instr is not None:
            return '%x:%s %s' % (
                self.offset, self.dvm_instr.get_name(), util.hex_escape_string(self.dvm_instr.get_output()))
        else:
            return ''


class LoadConstant(Instruction):
    def __init__(self, value, cst):
        super(LoadConstant, self).__init__()
        self.value = value
        self.value.refine_type(cst.get_type())
        self.value.is_const = True
        self.operands.append(cst)

    @property
    def constant(self):
        return self.operands[0]

    def get_cst(self):
        return self.operands[0]

    def get_class(self):
        cst_type = self.get_cst().get_type()
        if cst_type == 'Ljava/lang/Class;':
            return self.get_cst().get_constant()
        else:
            return None

    def resolve_type(self):
        return False

    def visit(self, visitor):
        return visitor.visit_load_constant(self)

    def __str__(self):
        return '%s = %s' % (str(self.value), str(self.operands[0]))


class Param(object):
    def __init__(self, value):
        self.declared = True
        self.value = value
        self.this = False

    def get_value(self):
        return self.value

    def visit(self, visitor):
        return visitor.visit_param(self.value)

    def __str__(self):
        return 'PARAM_%s' % self.name


class ThisParam(Param):
    def __init__(self, value):
        super(ThisParam, self).__init__(value)
        self.this = True

    def visit(self, visitor):
        return visitor.visit_this()

    def __str__(self):
        return 'THIS'


class MoveParam(Instruction):
    def __init__(self, param):
        super(MoveParam, self).__init__()
        self.param = param

    def visit(self, visitor):
        return visitor.visit_move_param(self)

    def get_value(self):
        return self.param.get_value()

    def get_param(self):
        return self.param

    def __str__(self):
        return 'MoveParam(%s)' % self.param.get_value()


class MoveExpression(Instruction):
    def __init__(self, lhs, rhs):
        super(MoveExpression, self).__init__()
        self.value = lhs
        self.operands.append(rhs)
        rhs.add_user(self)

    def visit(self, visitor):
        return visitor.visit_move(self.value, self.operands[0])

    def resolve_type(self):
        op_type = self.operands[0].get_type()
        value_type = self.value.get_type()

        new_type = util.merge_type(op_type, value_type)
        if new_type is None:
            return False

        Changed = False
        if self.operands[0].type_sealed:
            Changed |= self.set_value_type(new_type)
        else:
            Changed |= self.value.refine_type(new_type)
            Changed |= self.operands[0].refine_type(new_type)

        return Changed

    def __str__(self):
        return '%s = %s' % (self.value, self.operands[0])


class MoveResultExpression(MoveExpression):
    def __init__(self, lhs, rhs):
        super(MoveResultExpression, self).__init__(lhs, rhs)

    def visit(self, visitor):
        return visitor.visit_move_result(self, self.value, self.operands[0])

    def __str__(self):
        return '%s = %s' % (self.value, self.operands[0])


class ArrayStoreInstruction(Instruction):
    def __init__(self, rhs, array, index, _type):
        super(ArrayStoreInstruction, self).__init__()
        rhs.add_user(self)
        array.add_user(self)
        index.add_user(self)
        self.operands.append(rhs)
        self.operands.append(array)
        self.operands.append(index)
        self.elem_type = _type

    @property
    def array(self):
        return self.operands[1]

    @property
    def index(self):
        return self.operands[2]

    def resolve_type(self):
        elem_type = self.get_elem_type()
        Changed = self.index.set_type('I')
        if elem_type:
            Changed |= self.operands[0].refine_type(elem_type)
            Changed |= self.array.refine_type('[' + elem_type)
        return Changed

    def get_elem_type(self):
        if self.elem_type:
            return self.elem_type
        else:
            if util.is_array(self.array.get_type()):
                type1 = self.array.get_type()[1:]
            else:
                type1 = None
            type2 = self.operands[0].get_type()
            return util.merge_type(type1, type2)

    def visit(self, visitor):
        return visitor.visit_astore(self, self.array,
                                    self.index,
                                    self.operands[0])

    def __str__(self):
        return '%s[%s] = %s' % (self.array, self.index, self.operands[0])


class StaticInstruction(Instruction):
    def __init__(self, rhs, klass, ftype, name):
        super(StaticInstruction, self).__init__()
        self.cls = util.get_type(klass)
        self.ftype = ftype
        self.name = name
        self.clsdesc = klass
        rhs.add_user(self)
        self.operands.append(rhs)

    def get_class(self):
        return self.clsdesc

    def get_field(self):
        return '%s.%s' % (self.clsdesc, self.name)

    def resolve_type(self):
        return self.operands[0].refine_type(self.ftype)

    def visit(self, visitor):
        return visitor.visit_put_static(self, self.clsdesc, self.name, self.ftype, self.operands[0])

    def __str__(self):
        return '%s.%s = %s' % (self.cls, self.name, self.operands[0])


class InstanceInstruction(Instruction):
    def __init__(self, rhs, lhs, klass, atype, name):
        super(InstanceInstruction, self).__init__()
        self.atype = atype
        self.cls = util.get_type(klass)
        self.name = name
        self.clsdesc = klass

        lhs.add_user(self)
        rhs.add_user(self)
        self.operands.append(lhs)
        self.operands.append(rhs)

    def get_class(self):
        return self.clsdesc

    def get_field(self):
        return '%s.%s' % (self.clsdesc, self.name)

    def resolve_type(self):
        Changed = False
        Changed |= self.operands[0].refine_type(self.clsdesc)
        Changed |= self.operands[1].refine_type(self.atype)
        return Changed

    def visit(self, visitor):
        return visitor.visit_put_instance(self, self.operands[0], self.operands[1], self.atype, self.clsdesc, self.name)

    def __str__(self):
        return '%s.%s = %s' % (self.operands[0], self.name, self.operands[1])


class NewInstance(Instruction):
    def __init__(self, lhs, ins_type):
        super(NewInstance, self).__init__()
        self.value = lhs
        self.value.refine_type(ins_type)
        self.type = ins_type

    def get_type(self):
        return self.type

    def get_class(self):
        return self.type

    def resolve_type(self):
        return self.set_value_type(self.type)

    def visit(self, visitor):
        return visitor.visit_new(self, self.value, self.type)

    def __str__(self):
        return '%s = NEW(%s)' % (self.value, self.type)


class InvokeInstruction(Instruction):
    def __init__(self, invoke_type, clsname, name, thiz, result, rtype, ptype, args, triple):
        super(InvokeInstruction, self).__init__()
        self.invoke_type = invoke_type
        self.is_static = True if invoke_type == 'static' else False
        self.clsdesc = clsname
        self.value = result
        self.name = name

        if not self.is_static:
            self.operands.append(thiz)
            thiz.add_user(self)

        if result:
            result.refine_type(rtype)

        self.rtype = rtype
        self.ptype = ptype
        self.args = []
        for arg in args:
            arg.add_user(self)
            self.operands.append(arg)

        self.triple = triple
        assert (triple[1] == name)

    @property
    def thiz(self):
        if self.is_static:
            return None
        else:
            return self.operands[0]

    def get_class(self):
        return self.clsdesc

    def get_call_method(self):
        return '%s->%s(%s)' % (self.clsdesc, self.name, ''.join(self.ptype))

    def resolve_type(self):
        Changed = False
        if self.is_static:
            assert self.thiz is None
            args = self.operands
        else:
            args = self.operands[1:]

        if self.thiz and self.thiz.get_type() != self.clsdesc:
            Changed |= self.thiz.refine_type(self.clsdesc)

        for idx, arg in enumerate(args):
            Changed |= arg.refine_type(self.ptype[idx])

        if self.value:
            Changed |= self.set_value_type(self.rtype)
        return Changed

    def visit(self, visitor):
        if self.is_static:
            assert self.thiz is None
            args = self.operands
        else:
            args = self.operands[1:]
        return visitor.visit_invoke(self, self.invoke_type, self.name, self.thiz, self.ptype,
                                    self.rtype, args, self.clsdesc)

    def __str__(self):
        args = []
        if not self.is_static:
            args.append(self.thiz)
        args.extend(self.args)
        return '%s.%s(%s)' % (self.clsdesc, self.name,
                              ', '.join('%s' % i for i in args))


class InvokeRangeInstruction(InvokeInstruction):
    def __init__(self, clsname, name, rtype, ptype, args, triple):
        base = args.pop(0)
        super(InvokeRangeInstruction, self).__init__(clsname, name, base, rtype,
                                                     ptype, args, triple)


class InvokeDirectInstruction(InvokeInstruction):
    def __init__(self, clsname, name, base, rtype, ptype, args, triple):
        super(InvokeDirectInstruction, self).__init__(
            clsname, name, base, rtype, ptype, args, triple)


class InvokeStaticInstruction(InvokeInstruction):
    def __init__(self, clsname, name, base, rtype, ptype, args, triple):
        super(InvokeStaticInstruction, self).__init__(
            clsname, name, base, rtype, ptype, args, triple)


class InvokeSuperInstruction(InvokeInstruction):
    def __init__(self, clsname, name, base, rtype, ptype, args, triple):
        super(InvokeSuperInstruction, self).__init__(clsname, name, base, rtype,
                                                     ptype, args, triple)


class ReturnInstruction(Instruction):
    def __init__(self, arg, rtype=None):
        super(ReturnInstruction, self).__init__()
        self.rtype = rtype
        if arg:
            arg.add_user(self)
            self.operands.append(arg)

    @property
    def retval(self):
        if self.rtype:
            return self.operands[0]
        else:
            return None

    def visit(self, visitor):
        if self.rtype is None:
            return visitor.visit_return_void()
        else:
            return visitor.visit_return(self.retval)

    def resolve_type(self):
        if self.rtype:
            return self.retval.refine_type(self.rtype)
        else:
            return False

    def __str__(self):
        if self.retval is not None:
            return 'RETURN(%s)' % self.retval
        else:
            return 'RETURN'


class NopExpression(Instruction):
    def __init__(self):
        super(NopExpression, self).__init__()
        pass

    def visit(self, visitor):
        return visitor.visit_nop()


class GotoInst(Instruction):
    def __init__(self, target):
        super(GotoInst, self).__init__()
        self.target = target

    def visit(self, visitor):
        return visitor.visit_goto((self.offset // 2 + self.target) * 2)

    def __str__(self):
        return "GOTO(%x)" % (self.target)


class SwitchExpression(Instruction):
    def __init__(self, src, cases):
        super(SwitchExpression, self).__init__()
        # src.set_type('I')
        src.add_user(self)
        self.cases = cases
        self.operands.append(src)

    def visit(self, visitor):
        return visitor.visit_switch_node(self, self.operands[0], self.cases)

    def resolve_type(self):
        return self.operands[0].refine_type('I')

    def __str__(self):
        return 'SWITCH(%s)' % (self.operands[0])


class CheckCastExpression(Instruction):
    def __init__(self, arg, _type, descriptor=None):
        super(CheckCastExpression, self).__init__()
        self.type = descriptor
        self.clsdesc = descriptor
        arg.add_user(self)
        self.operands.append(arg)

    def get_type(self):
        return self.type

    def get_class(self):
        return self.clsdesc

    def resolve_type(self):
        return self.operands[0].refine_type(self.type)

    def visit(self, visitor):
        return visitor.visit_check_cast(self, self.operands[0], self.clsdesc)

    def __str__(self):
        return 'CAST(%s) %s' % (self.type, self.operands[0])


class InstanceOfExpression(Instruction):
    def __init__(self, result, obj, clsdesc):
        super(InstanceOfExpression, self).__init__()
        self.clsdesc = clsdesc
        self.value = result
        obj.add_user(self)
        self.operands.append(obj)

    def get_class(self):
        return self.clsdesc

    def resolve_type(self):
        Changed = self.operands[0].refine_type(self.clsdesc)
        Changed |= self.set_value_type('Z')
        return Changed

    def visit(self, visitor):
        return visitor.visit_instanceof(self, self.value, self.operands[0], self.clsdesc)

    def __str__(self):
        return '(%s instanceof %s)' % (self.value, self.clsdesc)


class ArrayExpression(Instruction):
    def __init__(self):
        super(ArrayExpression, self).__init__()


class ArrayLoadExpression(ArrayExpression):
    def __init__(self, result, arg, index, _type):
        super(ArrayLoadExpression, self).__init__()
        self.value = result
        arg.add_user(self)
        index.add_user(self)
        self.operands.append(arg)
        self.operands.append(index)
        self.elem_type = _type

    @property
    def array(self):
        return self.operands[0]

    @property
    def idx(self):
        return self.operands[1]

    def resolve_type(self):
        Changed = False
        elem_type = self.get_elem_type()
        if elem_type:
            Changed |= self.value.refine_type(elem_type)
            Changed |= self.array.refine_type('[' + elem_type)
        Changed |= self.idx.refine_type("I")
        return Changed

    def visit(self, visitor):
        return visitor.visit_aload(self, self.value, self.array, self.idx)

    def get_elem_type(self):
        if self.elem_type:
            return self.elem_type
        else:
            if util.is_array(self.array.get_type()):
                type1 = self.array.get_type()[1:]
            else:
                type1 = None
            type2 = self.get_value_type()
            return util.merge_type(type1, type2)

    def __str__(self):
        return '%s = ARRAYLOAD(%s, %s)' % (self.value, self.array, self.idx)


class ArrayLengthExpression(ArrayExpression):
    def __init__(self, result, array):
        super(ArrayLengthExpression, self).__init__()
        self.value = result
        array.add_user(self)
        self.operands.append(array)

    @property
    def array(self):
        return self.operands[0]

    def resolve_type(self):
        return self.set_value_type('I')

    def visit(self, visitor):
        return visitor.visit_alength(self, self.value, self.array)

    def __str__(self):
        return 'ARRAYLEN(%s)' % self.array


class NewArrayExpression(ArrayExpression):
    def __init__(self, result, asize, atype):
        super(NewArrayExpression, self).__init__()
        self.value = result
        asize.add_user(self)
        self.type = atype
        self.elem_type = atype[1:]
        self.operands.append(asize)

    def get_size(self):
        return self.operands[0]

    def get_elem_type(self):
        return self.elem_type

    def get_class(self):
        return self.elem_type

    def resolve_type(self):
        Changed = False
        Changed |= self.set_value_type(self.type)
        Changed |= self.operands[0].set_type('I')
        return Changed

    def visit(self, visitor):
        return visitor.visit_new_array(self, self.value, self.type, self.get_size())

    def __str__(self):
        return '%s = NEWARRAY_%s[%s]' % (self.value, self.type, self.get_size())


class FilledArrayExpression(ArrayExpression):
    def __init__(self, result, asize, atype, args):
        super(FilledArrayExpression, self).__init__()
        self.value = result
        result.refine_type(atype)
        self.size = asize
        self.type = atype
        self.elem_type = atype[1:]
        for arg in args:
            arg.add_user(self)
            self.operands.append(arg)

    def get_class(self):
        return self.elem_type

    def resolve_type(self):
        Changed = False
        Changed |= self.set_value_type(self.type)
        for arg in self.operands:
            Changed |= arg.refine_type(self.elem_type)
        return Changed

    def visit(self, visitor):
        return visitor.visit_filled_new_array(self, self.value, self.type, self.size, self.operands)


class FillArrayExpression(ArrayExpression):
    def __init__(self, reg, value):
        super(FillArrayExpression, self).__init__()
        self.filldata = value
        self.operands.append(reg)
        self.reg.add_user(self)

    @property
    def reg(self):
        return self.operands[0]

    def resolve_type(self):
        return False

    def visit(self, visitor):
        return visitor.visit_fill_array(self, self.reg, self.filldata)


class MoveExceptionExpression(Instruction):
    def __init__(self, value, _type):
        super(MoveExceptionExpression, self).__init__()
        self.value = value
        self.value.refine_type(_type)
        self.type = _type

    def resolve_type(self):
        return self.value.refine_type(self.type)

    def visit(self, visitor):
        return visitor.visit_move_exception(self, self.value)

    def __str__(self):
        return 'MOVE_EXCEPT %s(%s)' % (self.value, self.value.get_type())


class MonitorEnterExpression(Instruction):
    def __init__(self, ref):
        super(MonitorEnterExpression, self).__init__()
        ref.add_user(self)
        self.operands.append(ref)

    def resolve_type(self):
        return self.operands[0].refine_type('Ljava/lang/Object;')

    def visit(self, visitor):
        return visitor.visit_monitor_enter(self, self.operands[0])

    def __str__(self):
        return 'MonitorEnter (%s)' % self.operands[0]


class MonitorExitExpression(Instruction):
    def __init__(self, ref):
        super(MonitorExitExpression, self).__init__()
        ref.add_user(self)
        self.operands.append(ref)

    def resolve_type(self):
        return self.operands[0].refine_type('Ljava/lang/Object;')

    def visit(self, visitor):
        return visitor.visit_monitor_exit(self, self.operands[0])

    def __str__(self):
        return 'MonitorExit (%s)' % self.operands[0]


class ThrowExpression(Instruction):
    def __init__(self, ref):
        super(ThrowExpression, self).__init__()
        ref.add_user(self)
        self.operands.append(ref)

    def resolve_type(self):
        return self.operands[0].set_type('Ljava/lang/Throwable;')

    def visit(self, visitor):
        return visitor.visit_throw(self, self.operands[0])

    def __str__(self):
        return 'Throw %s' % self.operands[0]


class BinaryExpression(Instruction):
    def __init__(self, op, result, arg1, arg2, vtype):
        super(BinaryExpression, self).__init__()
        self.value = result
        self.op = op

        self.operands.append(arg1)
        self.operands.append(arg2)

        self.op_type = vtype

        arg1.add_user(self)
        arg2.add_user(self)

    def resolve_type(self):
        Changed = False
        Changed |= self.value.refine_type(self.op_type)
        for op in self.operands:
            Changed |= op.refine_type(self.op_type)
        return Changed

    def visit(self, visitor):
        return visitor.visit_binary_expression(self, self.value, self.op, self.operands[0], self.operands[1])

    def __str__(self):
        return '%s = %s %s %s' % (self.value, self.operands[0], self.op, self.operands[1])


class BinaryCompExpression(BinaryExpression):
    def __init__(self, op, result, arg1, arg2, _type):
        super(BinaryCompExpression, self).__init__(op, result, arg1, arg2, _type)
        result.refine_type('I')

    def resolve_type(self):
        Changed = False
        Changed |= self.value.refine_type('I')
        for op in self.operands:
            Changed |= op.refine_type(self.op_type)
        return Changed


class BinaryExpression2Addr(BinaryExpression):
    def __init__(self, result, op, dest, arg, _type):
        super(BinaryExpression2Addr, self).__init__(result, op, dest, arg, _type)


class BinaryExpressionLit(BinaryExpression):
    def __init__(self, op, result, arg1, arg2):
        super(BinaryExpressionLit, self).__init__(op, result, arg1, arg2, 'I')


class UnaryExpression(Instruction):
    def __init__(self, result, op, arg, _type):
        super(UnaryExpression, self).__init__()
        result.refine_type(_type)
        self.value = result
        self.op = op
        self.type = _type
        self.operands.append(arg)
        arg.add_user(self)

    def resolve_type(self):
        return self.set_value_type(self.type)

    def visit(self, visitor):
        return visitor.visit_unary_expression(self, self.value, self.op, self.operands[0])

    def __str__(self):
        return '(%s, %s)' % (self.op, self.operands[0])


class CastExpression(Instruction):
    def __init__(self, result, op, dest_type, arg, src_type):
        super(CastExpression, self).__init__()
        self.type = dest_type
        self.src_type = src_type
        self.op = op
        self.value = result
        self.value.refine_type(dest_type)
        self.operands.append(arg)
        arg.add_user(self)

    def get_type(self):
        return self.type

    def resolve_type(self):
        Changed = self.value.refine_type(self.type)
        Changed |= self.operands[0].refine_type(self.src_type)
        return Changed

    def visit(self, visitor):
        return visitor.visit_cast(self.value, self.op, self.operands[0])

    def __str__(self):
        return '%s = %s(%s)' % (self.value, self.op, self.operands[0])


CONDS = {'==': '!=', '!=': '==', '<': '>=', '<=': '>', '>=': '<', '>': '<=', }


class ConditionalExpression(Instruction):
    def __init__(self, op, arg1, arg2, target):
        super(ConditionalExpression, self).__init__()
        self.op = op
        self.target = target
        arg1.add_user(self)
        arg2.add_user(self)
        self.operands.append(arg1)
        self.operands.append(arg2)

    def get_target(self):
        return self.target

    def resolve_type(self):
        Changed = False
        type1 = self.operands[0].get_type()
        type2 = self.operands[1].get_type()

        # 引用类型可以比较
        if (util.is_ref(type1) or util.is_array(type1)) and (util.is_ref(type2) or util.is_array(type2)):
            return False

        new_type = util.merge_type(type1, type2)
        Changed |= self.operands[0].refine_type(new_type)
        Changed |= self.operands[1].refine_type(new_type)
        return Changed

    def visit(self, visitor):
        return visitor.visit_cond_expression(self, self.op, self.operands[0],
                                             self.operands[1], (self.offset // 2 + self.target) * 2,
                                             self.next_offset)

    def __str__(self):
        return 'IF %s %s %s' % (self.operands[0], self.op, self.operands[1])


class ConditionalZExpression(Instruction):
    def __init__(self, op, arg, target):
        super(ConditionalZExpression, self).__init__()
        self.op = op
        self.target = target
        arg.add_user(self)
        self.operands.append(arg)

    # 无法使用该指令无法推断出操作类型
    def resolve_type(self):
        return False

    def visit(self, visitor):
        return visitor.visit_condz_expression(self, self.op, self.operands[0], (self.offset // 2 + self.target) * 2,
                                              self.next_offset)

    def __str__(self):
        return 'IF %s %s 0' % (self.operands[0], self.op)


class InstanceExpression(Instruction):
    def __init__(self, result, arg, klass, ftype, name):
        super(InstanceExpression, self).__init__()
        self.value = result
        self.cls = util.get_type(klass)
        self.ftype = ftype
        self.name = name
        self.clsdesc = klass

        arg.add_user(self)
        self.operands.append(arg)

    def get_class(self):
        return self.clsdesc

    def get_field(self):
        return '%s.%s' % (self.clsdesc, self.name)

    def resolve_type(self):
        Changed = self.set_value_type(self.ftype)
        Changed |= self.operands[0].refine_type(self.clsdesc)
        return Changed

    def get_type(self):
        return self.ftype

    def visit(self, visitor):
        return visitor.visit_get_instance(
            self,
            self.value,
            self.operands[0],
            self.ftype,
            self.clsdesc,
            self.name)

    def __str__(self):
        return '%s = %s.%s' % (self.value, self.operands[0], self.name)


class StaticExpression(Instruction):
    def __init__(self, result, cls_name, field_type, field_name):
        super(StaticExpression, self).__init__()
        self.value = result
        self.cls = util.get_type(cls_name)
        self.ftype = field_type
        self.name = field_name
        self.clsdesc = cls_name

    def get_class(self):
        return self.clsdesc

    def get_field(self):
        return '%s.%s' % (self.clsdesc, self.name)

    def resolve_type(self):
        return self.set_value_type(self.ftype)

    def visit(self, visitor):
        return visitor.visit_get_static(self, self.value, self.ftype, self.clsdesc, self.name)

    def __str__(self):
        return '%s = %s.%s' % (self.value, self.cls, self.name)
