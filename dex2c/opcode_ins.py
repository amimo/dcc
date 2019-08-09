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
from builtins import range

from dex2c import util
from dex2c.instruction import (
    ArrayLengthExpression, ArrayLoadExpression, ArrayStoreInstruction,
    BinaryCompExpression, BinaryExpression,
    BinaryExpression2Addr, BinaryExpressionLit, CastExpression,
    CheckCastExpression, ConditionalExpression, ConditionalZExpression,
    LoadConstant, FillArrayExpression, FilledArrayExpression, InstanceExpression,
    InstanceInstruction, InvokeInstruction, MonitorEnterExpression,
    MonitorExitExpression, MoveExceptionExpression, MoveExpression,
    MoveResultExpression, NewArrayExpression, NewInstance, NopExpression,
    ThrowExpression, ReturnInstruction, StaticExpression,
    StaticInstruction, SwitchExpression, UnaryExpression, GotoInst, Constant,
    InstanceOfExpression)

logger = logging.getLogger('dex2c.opcode_ins')
# logger.setLevel(logging.DEBUG)


class Op(object):
    CMP = 'cmp'
    CMPL = 'cmpl'
    CMPG = 'cmpg'
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    MOD = '%'
    MODF = 'fmodf'
    MODD = 'fmod'
    AND = '&'
    OR = '|'
    XOR = '^'
    EQUAL = '=='
    NEQUAL = '!='
    GREATER = '>'
    LOWER = '<'
    GEQUAL = '>='
    LEQUAL = '<='
    NEG = '-'
    NOT = '~'
    INTSHL = 'shl-int'  # '(%s << ( %s & 0x1f ))'
    INTSHR = 'shr-int'  # '(%s >> ( %s & 0x1f ))'
    INTUSHR = 'ushr-int'  # '(%s >>> ( %s & 0x1f ))'
    LONGSHL = 'shl-long'  # '(%s << ( %s & 0x3f ))'
    LONGSHR = 'shr-long'  # '(%s << ( %s & 0x3f ))'
    LONGUSHR = 'ushl-long'  # '(%s >> ( %s & 0x3f ))'


def get_variables(irbuilder, *registers):
    res = []
    for register in registers:
        res.append(irbuilder.read_variable(register))
    return res


def assign_cmpl(reg_a, reg_b, reg_c, cmp_type, irbuilder):
    reg_b = irbuilder.read_variable(reg_b)
    reg_c = irbuilder.read_variable(reg_c)
    reg_a = irbuilder.write_variable(reg_a)

    return BinaryCompExpression(Op.CMPL, reg_a, reg_b, reg_c, cmp_type)


def assign_cmpg(reg_a, reg_b, reg_c, cmp_type, irbuilder):
    reg_b = irbuilder.read_variable(reg_b)
    reg_c = irbuilder.read_variable(reg_c)
    reg_a = irbuilder.write_variable(reg_a)

    return BinaryCompExpression(Op.CMPG, reg_a, reg_b, reg_c, cmp_type)


def assign_cmp(reg_a, reg_b, reg_c, cmp_type, irbuilder):
    reg_b = irbuilder.read_variable(reg_b)
    reg_c = irbuilder.read_variable(reg_c)
    reg_a = irbuilder.write_variable(reg_a)

    return BinaryCompExpression(Op.CMP, reg_a, reg_b, reg_c, cmp_type)


def load_array_exp(val_a, val_b, val_c, ar_type, irbuilder):
    reg_b, reg_c = get_variables(irbuilder, val_b, val_c)
    reg_a = irbuilder.write_variable(val_a)
    return ArrayLoadExpression(reg_a, reg_b, reg_c, ar_type)


def store_array_inst(val_a, val_b, val_c, ar_type, irbuilder):
    reg_a, reg_b, reg_c = get_variables(irbuilder, val_a, val_b, val_c)
    return ArrayStoreInstruction(reg_a, reg_b, reg_c, ar_type)


def assign_cast_exp(reg_a, reg_b, val_op, op_type, irbuilder):
    val_b = irbuilder.read_variable(reg_b)
    val_a = irbuilder.write_variable(reg_a)
    return CastExpression(val_a, val_op, op_type, val_b)


def assign_binary_exp(ins, val_op, op_type, irbuilder):
    val_c = irbuilder.read_variable(ins.CC)
    val_b = irbuilder.read_variable(ins.BB)
    val_a = irbuilder.write_variable(ins.AA)
    val_a.refine_type(op_type)
    return BinaryExpression(val_op, val_a, val_b, val_c, op_type)


def assign_binary_2addr_exp(ins, val_op, op_type, irbuilder):
    val_a = irbuilder.read_variable(ins.A)
    val_b = irbuilder.read_variable(ins.B)
    result = irbuilder.write_variable(ins.A)
    result.refine_type(op_type)
    return BinaryExpression2Addr(val_op, result, val_a, val_b, op_type)


def assign_lit(op_type, val_cst, val_a, val_b, irbuilder):
    var_b = irbuilder.read_variable(val_b)
    var_a = irbuilder.write_variable(val_a)
    var_a.refine_type('I')
    cst = Constant(val_cst, 'I')
    return BinaryExpressionLit(op_type, var_a, var_b, cst)


# nop
def nop(ins, irbuilder):
    return NopExpression()


# move vA, vB ( 4b, 4b )
def move(ins, irbuilder):
    logger.debug('Move %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.B)
    reg_a = irbuilder.write_variable(ins.A)
    return MoveExpression(reg_a, reg_b)


# move/from16 vAA, vBBBB ( 8b, 16b )
def movefrom16(ins, irbuilder):
    logger.debug('MoveFrom16 %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.BBBB)
    reg_a = irbuilder.write_variable(ins.AA)
    return MoveExpression(reg_a, reg_b)


# move/16 vAAAA, vBBBB ( 16b, 16b )
def move16(ins, irbuilder):
    logger.debug('Move16 %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.BBBB)
    reg_a = irbuilder.write_variable(ins.AAAA)
    return MoveExpression(reg_a, reg_b)


# move-wide vA, vB ( 4b, 4b )
def movewide(ins, irbuilder):
    logger.debug('MoveWide %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.B)
    reg_a = irbuilder.write_variable(ins.A)
    return MoveExpression(reg_a, reg_b)


# move-wide/from16 vAA, vBBBB ( 8b, 16b )
def movewidefrom16(ins, irbuilder):
    logger.debug('MoveWideFrom16 : %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.BBBB)
    reg_a = irbuilder.write_variable(ins.AA)
    return MoveExpression(reg_a, reg_b)


# move-wide/16 vAAAA, vBBBB ( 16b, 16b )
def movewide16(ins, irbuilder):
    logger.debug('MoveWide16 %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.BBBB)
    reg_a = irbuilder.write_variable(ins.AAAA)
    return MoveExpression(reg_a, reg_b)


# move-object vA, vB ( 4b, 4b )
def moveobject(ins, irbuilder):
    logger.debug('MoveObject %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.B)
    reg_a = irbuilder.write_variable(ins.A)
    return MoveExpression(reg_a, reg_b)


# move-object/from16 vAA, vBBBB ( 8b, 16b )
def moveobjectfrom16(ins, irbuilder):
    logger.debug('MoveObjectFrom16 : %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.BBBB)
    reg_a = irbuilder.write_variable(ins.AA)
    return MoveExpression(reg_a, reg_b)


# move-object/16 vAAAA, vBBBB ( 16b, 16b )
def moveobject16(ins, irbuilder):
    logger.debug('MoveObject16 : %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.BBBB)
    reg_a = irbuilder.write_variable(ins.AAAA)
    return MoveExpression(reg_a, reg_b)


def moveresultcommon(ins, irbuilder):
    val = irbuilder.write_variable(ins.AA)
    ret = irbuilder.read_result_variable()
    return MoveResultExpression(val, ret)


# move-result vAA ( 8b )
def moveresult(ins, irbuilder):
    logger.debug('MoveResult : %s', ins.get_output())
    ret = irbuilder.read_result_variable()
    return moveresultcommon(ins, irbuilder)


# move-result-wide vAA ( 8b )
def moveresultwide(ins, irbuilder):
    logger.debug('MoveResultWide : %s', ins.get_output())
    # return MoveResultExpression(get_variables(irbuilder, ins.AA), ret)
    ret = irbuilder.read_result_variable()
    return moveresultcommon(ins, irbuilder)


# move-result-object vAA ( 8b )
def moveresultobject(ins, irbuilder):
    logger.debug('MoveResultObject : %s', ins.get_output())
    val = irbuilder.write_variable(ins.AA)
    ret = irbuilder.read_result_variable()
    return MoveResultExpression(val, ret)


# move-exception vAA ( 8b )
def moveexception(ins, irbuilder, _type):
    logger.debug('MoveException : %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    return MoveExceptionExpression(val_a, _type)


# return-void
def returnvoid(ins, irbuilder):
    logger.debug('ReturnVoid')
    return ReturnInstruction(None)


# return vAA ( 8b )
def return_reg(ins, irbuilder):
    logger.debug('Return : %s', ins.get_output())
    val = irbuilder.read_variable(ins.AA)
    return ReturnInstruction(val, irbuilder.get_return_type())


# return-wide vAA ( 8b )
def returnwide(ins, irbuilder):
    logger.debug('ReturnWide : %s', ins.get_output())
    val = irbuilder.read_variable(ins.AA)
    val.refine_type(irbuilder.get_return_type())
    return ReturnInstruction(val, irbuilder.get_return_type())


# return-object vAA ( 8b )
def returnobject(ins, irbuilder):
    logger.debug('ReturnObject : %s', ins.get_output())
    val = irbuilder.read_variable(ins.AA)
    return ReturnInstruction(val, irbuilder.get_return_type())


# const/4 vA, #+B ( 4b, 4b )
def const4(ins, irbuilder):
    logger.debug('Const4 : %s', ins.get_output())
    value = irbuilder.write_variable(ins.A)
    return LoadConstant(value, Constant(ins.B))


# const/16 vAA, #+BBBB ( 8b, 16b )
def const16(ins, irbuilder):
    logger.debug('Const16 : %s', ins.get_output())
    value = irbuilder.write_variable(ins.AA)
    return LoadConstant(value, Constant(ins.BBBB))


# const vAA, #+BBBBBBBB ( 8b, 32b )
def const(ins, irbuilder):
    logger.debug('Const : %s', ins.get_output())
    # value = unpack("=f", pack("=i", ins.BBBBBBBB))[0]
    val_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(val_a, Constant(ins.BBBBBBBB))


# const/high16 vAA, #+BBBB0000 ( 8b, 16b )
def consthigh16(ins, irbuilder):
    logger.debug('ConstHigh16 : %s', ins.get_output())
    # value = unpack('=f', pack('=i', ins.BBBB << 16))[0]
    val_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(val_a, Constant(ins.BBBB << 16))


# const-wide/16 vAA, #+BBBB ( 8b, 16b )
def constwide16(ins, irbuilder):
    logger.debug('ConstWide16 : %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(val_a, Constant(ins.BBBB))


# const-wide/32 vAA, #+BBBBBBBB ( 8b, 32b )
def constwide32(ins, irbuilder):
    logger.debug('ConstWide32 : %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(val_a, Constant(ins.BBBBBBBB))


# const-wide vAA, #+BBBBBBBBBBBBBBBB ( 8b, 64b )
def constwide(ins, irbuilder):
    logger.debug('ConstWide : %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(val_a, Constant(ins.BBBBBBBBBBBBBBBB))


# const-wide/high16 vAA, #+BBBB000000000000 ( 8b, 16b )
def constwidehigh16(ins, irbuilder):
    logger.debug('ConstWideHigh16 : %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(val_a, Constant(ins.BBBB << 48))


# const-string vAA ( 8b )
def conststring(ins, irbuilder):
    logger.debug('ConstString : %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    val_a.refine_type('Ljava/lang/String;')
    return LoadConstant(val_a, Constant(ins.get_raw_string(), 'Ljava/lang/String;'))


# const-string/jumbo vAA ( 8b )
def conststringjumbo(ins, irbuilder):
    logger.debug('ConstStringJumbo %s', ins.get_output())
    val_a = irbuilder.write_variable(ins.AA)
    val_a.refine_type('Ljava/lang/String;')
    return LoadConstant(val_a, Constant(ins.get_raw_string(), 'Ljava/lang/String;'))


# const-class vAA, type@BBBB ( 8b )
def constclass(ins, irbuilder):
    logger.debug('ConstClass : %s', ins.get_output())
    reg_a = irbuilder.write_variable(ins.AA)
    return LoadConstant(reg_a, Constant(util.get_type(ins.get_string()), 'Ljava/lang/Class;'))


# monitor-enter vAA ( 8b )
def monitorenter(ins, irbuilder):
    logger.debug('MonitorEnter : %s', ins.get_output())
    ref = irbuilder.read_variable(ins.AA)
    return MonitorEnterExpression(ref)


# monitor-exit vAA ( 8b )
def monitorexit(ins, irbuilder):
    logger.debug('MonitorExit : %s', ins.get_output())
    ref = irbuilder.read_variable(ins.AA)
    return MonitorExitExpression(ref)


# check-cast vAA ( 8b )
def checkcast(ins, irbuilder):
    logger.debug('CheckCast: %s', ins.get_output())
    cast_type = ins.get_translated_kind()
    cast_var = irbuilder.read_variable(ins.AA)
    return CheckCastExpression(cast_var, cast_type, descriptor=ins.get_translated_kind())


# instance-of vA, vB ( 4b, 4b )
def instanceof(ins, irbuilder):
    logger.debug('InstanceOf : %s', ins.get_output())
    obj = irbuilder.read_variable(ins.B)
    result = irbuilder.write_variable(ins.A)
    atype = ins.get_translated_kind()
    return InstanceOfExpression(result, obj, atype)


# array-length vA, vB ( 4b, 4b )
def arraylength(ins, irbuilder):
    logger.debug('ArrayLength: %s', ins.get_output())
    reg_b = irbuilder.read_variable(ins.B)
    reg_a = irbuilder.write_variable(ins.A)
    return ArrayLengthExpression(reg_a, reg_b)


# new-instance vAA ( 8b )
def newinstance(ins, irbuilder):
    logger.debug('NewInstance : %s', ins.get_output())
    reg_a = irbuilder.write_variable(ins.AA)
    ins_type = ins.cm.get_type(ins.BBBB)
    return NewInstance(reg_a, ins_type)


# new-array vA, vB ( 8b, size )
def newarray(ins, irbuilder):
    logger.debug('NewArray : %s', ins.get_output())
    array_size = irbuilder.read_variable(ins.B)
    new_array = irbuilder.write_variable(ins.A)
    return NewArrayExpression(new_array, array_size, ins.cm.get_type(ins.CCCC))


# filled-new-array {vD, vE, vF, vG, vA} ( 4b each )
def fillednewarray(ins, irbuilder):
    logger.debug('FilledNewArray : %s', ins.get_output())
    regs = [ins.C, ins.D, ins.E, ins.F, ins.G][:ins.A]
    args = get_variables(irbuilder, *regs)
    array_type = ins.cm.get_type(ins.BBBB)
    result = irbuilder.write_result_variable()
    return FilledArrayExpression(result, ins.A, array_type, args)


# filled-new-array/range {vCCCC..vNNNN} ( 16b )
def fillednewarrayrange(ins, irbuilder):
    logger.debug('FilledNewArrayRange : %s', ins.get_output())
    args = []
    # base = ins.CCCC
    for reg in range(ins.CCCC, ins.NNNN + 1):
        arg = irbuilder.read_variable(reg)
        args.append(arg)
    array_type = ins.cm.get_type(ins.BBBB)
    result = irbuilder.write_result_variable()
    assert len(args) == ins.AA
    return FilledArrayExpression(result, ins.AA, array_type, args)


# fill-array-data vAA, +BBBBBBBB ( 8b, 32b )
def fillarraydata(ins, irbuilder, value):
    logger.debug('FillArrayData : %s', ins.get_output())
    var = irbuilder.read_variable(ins.AA)
    return FillArrayExpression(var, value)


# fill-array-data-payload vAA, +BBBBBBBB ( 8b, 32b )
def fillarraydatapayload(ins, irbuilder):
    logger.debug('FillArrayDataPayload : %s', ins.get_output())
    return FillArrayExpression(None)


# throw vAA ( 8b )
def throw(ins, irbuilder):
    logger.debug('Throw : %s', ins.get_output())
    ref = irbuilder.read_variable(ins.AA)
    return ThrowExpression(ref)


# goto +AA ( 8b )
def goto(ins, irbuilder):
    return GotoInst(ins.AA)


# goto/16 +AAAA ( 16b )
def goto16(ins, irbuilder):
    return GotoInst(ins.AAAA)


# goto/32 +AAAAAAAA ( 32b )
def goto32(ins, irbuilder):
    return GotoInst(ins.AAAAAAAA)


# packed-switch vAA, +BBBBBBBB ( reg to test, 32b )
def packedswitch(ins, irbuilder, values):
    logger.debug('PackedSwitch : %s', ins.get_output())
    reg_a = irbuilder.read_variable(ins.AA)
    targets = map(lambda x: x * 2, values.get_targets())
    cases = zip(values.get_keys(), targets)
    return SwitchExpression(reg_a, cases)


# sparse-switch vAA, +BBBBBBBB ( reg to test, 32b )
def sparseswitch(ins, irbuilder, values):
    logger.debug('SparseSwitch : %s', ins.get_output())
    reg_a = irbuilder.read_variable(ins.AA)
    targets = map(lambda x: x * 2, values.get_targets())
    cases = zip(values.get_keys(), targets)
    return SwitchExpression(reg_a, cases)


# cmpl-float vAA, vBB, vCC ( 8b, 8b, 8b )
def cmplfloat(ins, irbuilder):
    logger.debug('CmpglFloat : %s', ins.get_output())
    return assign_cmpl(ins.AA, ins.BB, ins.CC, 'F', irbuilder)


# cmpg-float vAA, vBB, vCC ( 8b, 8b, 8b )
def cmpgfloat(ins, irbuilder):
    logger.debug('CmpgFloat : %s', ins.get_output())
    return assign_cmpg(ins.AA, ins.BB, ins.CC, 'F', irbuilder)


# cmpl-double vAA, vBB, vCC ( 8b, 8b, 8b )
def cmpldouble(ins, irbuilder):
    logger.debug('CmplDouble : %s', ins.get_output())
    return assign_cmpl(ins.AA, ins.BB, ins.CC, 'D', irbuilder)


# cmpg-double vAA, vBB, vCC ( 8b, 8b, 8b )
def cmpgdouble(ins, irbuilder):
    logger.debug('CmpgDouble : %s', ins.get_output())
    return assign_cmpg(ins.AA, ins.BB, ins.CC, 'D', irbuilder)


# cmp-long vAA, vBB, vCC ( 8b, 8b, 8b )
def cmplong(ins, irbuilder):
    logger.debug('CmpLong : %s', ins.get_output())
    return assign_cmp(ins.AA, ins.BB, ins.CC, 'J', irbuilder)


# if-eq vA, vB, +CCCC ( 4b, 4b, 16b )
def ifeq(ins, irbuilder):
    logger.debug('IfEq : %s', ins.get_output())
    a, b = get_variables(irbuilder, ins.A, ins.B)
    return ConditionalExpression(Op.EQUAL, a, b, ins.CCCC)


# if-ne vA, vB, +CCCC ( 4b, 4b, 16b )
def ifne(ins, irbuilder):
    logger.debug('IfNe : %s', ins.get_output())
    a, b = get_variables(irbuilder, ins.A, ins.B)
    return ConditionalExpression(Op.NEQUAL, a, b, ins.CCCC)


# if-lt vA, vB, +CCCC ( 4b, 4b, 16b )
def iflt(ins, irbuilder):
    logger.debug('IfLt : %s', ins.get_output())
    a, b = get_variables(irbuilder, ins.A, ins.B)
    return ConditionalExpression(Op.LOWER, a, b, ins.CCCC)


# if-ge vA, vB, +CCCC ( 4b, 4b, 16b )
def ifge(ins, irbuilder):
    logger.debug('IfGe : %s', ins.get_output())
    vA = irbuilder.read_variable(ins.A)
    vB = irbuilder.read_variable(ins.B)
    return ConditionalExpression(Op.GEQUAL, vA, vB, ins.CCCC)


# if-gt vA, vB, +CCCC ( 4b, 4b, 16b )
def ifgt(ins, irbuilder):
    logger.debug('IfGt : %s', ins.get_output())
    a, b = get_variables(irbuilder, ins.A, ins.B)
    return ConditionalExpression(Op.GREATER, a, b, ins.CCCC)


# if-le vA, vB, +CCCC ( 4b, 4b, 16b )
def ifle(ins, irbuilder):
    logger.debug('IfLe : %s', ins.get_output())
    a = irbuilder.read_variable(ins.A)
    b = irbuilder.read_variable(ins.B)
    return ConditionalExpression(Op.LEQUAL, a, b, ins.CCCC)


# if-eqz vAA, +BBBB ( 8b, 16b )
def ifeqz(ins, irbuilder):
    logger.debug('IfEqz : %s', ins.get_output())
    val_a = irbuilder.read_variable(ins.AA)
    return ConditionalZExpression(Op.EQUAL, val_a, ins.BBBB)


# if-nez vAA, +BBBB ( 8b, 16b )
def ifnez(ins, irbuilder):
    logger.debug('IfNez : %s', ins.get_output())
    val_a = irbuilder.read_variable(ins.AA)
    return ConditionalZExpression(Op.NEQUAL, val_a, ins.BBBB)


# if-ltz vAA, +BBBB ( 8b, 16b )
def ifltz(ins, irbuilder):
    logger.debug('IfLtz : %s', ins.get_output())
    val_a = irbuilder.read_variable(ins.AA)
    return ConditionalZExpression(Op.LOWER, val_a, ins.BBBB)


# if-gez vAA, +BBBB ( 8b, 16b )
def ifgez(ins, irbuilder):
    logger.debug('IfGez : %s', ins.get_output())
    val_a = irbuilder.read_variable(ins.AA)
    val_a.refine_type('I')
    return ConditionalZExpression(Op.GEQUAL, val_a, ins.BBBB)


# if-gtz vAA, +BBBB ( 8b, 16b )
def ifgtz(ins, irbuilder):
    logger.debug('IfGtz : %s', ins.get_output())
    val_a = irbuilder.read_variable(ins.AA)
    return ConditionalZExpression(Op.GREATER, val_a, ins.BBBB)


# if-lez vAA, +BBBB (8b, 16b )
def iflez(ins, irbuilder):
    logger.debug('IfLez : %s', ins.get_output())
    val_a = irbuilder.read_variable(ins.AA)
    return ConditionalZExpression(Op.LEQUAL, val_a, ins.BBBB)


# TODO: check type for all aget
# aget vAA, vBB, vCC ( 8b, 8b, 8b )
def aget(ins, irbuilder):
    logger.debug('AGet : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, None, irbuilder)


# aget-wide vAA, vBB, vCC ( 8b, 8b, 8b )
def agetwide(ins, irbuilder):
    logger.debug('AGetWide : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, None, irbuilder)


# aget-object vAA, vBB, vCC ( 8b, 8b, 8b )
def agetobject(ins, irbuilder):
    logger.debug('AGetObject : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, None, irbuilder)


# aget-boolean vAA, vBB, vCC ( 8b, 8b, 8b )
def agetboolean(ins, irbuilder):
    logger.debug('AGetBoolean : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'Z', irbuilder)


# aget-byte vAA, vBB, vCC ( 8b, 8b, 8b )
def agetbyte(ins, irbuilder):
    logger.debug('AGetByte : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'B', irbuilder)


# aget-char vAA, vBB, vCC ( 8b, 8b, 8b )
def agetchar(ins, irbuilder):
    logger.debug('AGetChar : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'C', irbuilder)


# aget-short vAA, vBB, vCC ( 8b, 8b, 8b )
def agetshort(ins, irbuilder):
    logger.debug('AGetShort : %s', ins.get_output())
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'S', irbuilder)


# aput vAA, vBB, vCC
def aput(ins, irbuilder):
    logger.debug('APut : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, None, irbuilder)


# aput-wide vAA, vBB, vCC ( 8b, 8b, 8b )
def aputwide(ins, irbuilder):
    logger.debug('APutWide : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, None, irbuilder)


# aput-object vAA, vBB, vCC ( 8b, 8b, 8b )
def aputobject(ins, irbuilder):
    logger.debug('APutObject : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, None, irbuilder)


# aput-boolean vAA, vBB, vCC ( 8b, 8b, 8b )
def aputboolean(ins, irbuilder):
    logger.debug('APutBoolean : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'Z', irbuilder)


# aput-byte vAA, vBB, vCC ( 8b, 8b, 8b )
def aputbyte(ins, irbuilder):
    logger.debug('APutByte : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'B', irbuilder)


# aput-char vAA, vBB, vCC ( 8b, 8b, 8b )
def aputchar(ins, irbuilder):
    logger.debug('APutChar : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'C', irbuilder)


# aput-short vAA, vBB, vCC ( 8b, 8b, 8b )
def aputshort(ins, irbuilder):
    logger.debug('APutShort : %s', ins.get_output())
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'S', irbuilder)


def igetcommon(ins, irbuilder):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return InstanceExpression(a, b, klass, ftype, name)


# iget vA, vB ( 4b, 4b )
def iget(ins, irbuilder):
    logger.debug('IGet : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # exp = InstanceExpression(b, klass, ftype, name)
    # return AssignExpression(a, exp)
    return igetcommon(ins, irbuilder)


# iget-wide vA, vB ( 4b, 4b )
def igetwide(ins, irbuilder):
    logger.debug('IGetWide : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a = irbuilder.write_variable(ins.A)
    # b = irbuilder.read_variable(ins.B)
    # return InstanceExpression(a, b, klass, ftype, name)
    return igetcommon(ins, irbuilder)


# iget-object vA, vB ( 4b, 4b )
def igetobject(ins, irbuilder):
    logger.debug('IGetObject : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # exp = InstanceExpression(b, klass, ftype, name)
    # return AssignExpression(a, exp)
    return igetcommon(ins, irbuilder)


# iget-boolean vA, vB ( 4b, 4b )
def igetboolean(ins, irbuilder):
    logger.debug('IGetBoolean : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a = irbuilder.write_variable(ins.A)
    # b = irbuilder.read_variable(ins.B)
    # return InstanceExpression(a, b, klass, ftype, name)
    return igetcommon(ins, irbuilder)


# iget-byte vA, vB ( 4b, 4b )
def igetbyte(ins, irbuilder):
    logger.debug('IGetByte : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a = irbuilder.write_variable(ins.A)
    # b = irbuilder.read_variable(ins.B)
    # return InstanceExpression(a, b, klass, ftype, name)
    return igetcommon(ins, irbuilder)


# iget-char vA, vB ( 4b, 4b )
def igetchar(ins, irbuilder):
    logger.debug('IGetChar : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # exp = InstanceExpression(b, klass, ftype, name)
    # return AssignExpression(a, exp)
    return igetcommon(ins, irbuilder)


# iget-short vA, vB ( 4b, 4b )
def igetshort(ins, irbuilder):
    logger.debug('IGetShort : %s', ins.get_output())
    # klass, ftype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # exp = InstanceExpression(b, klass, ftype, name)
    # return AssignExpression(a, exp)
    return igetcommon(ins, irbuilder)


def iputcommon(ins, irbuilder):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(irbuilder, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput vA, vB ( 4b, 4b )
def iput(ins, irbuilder):
    logger.debug('IPut %s', ins.get_output())
    return iputcommon(ins, irbuilder)
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)


# iput-wide vA, vB ( 4b, 4b )
def iputwide(ins, irbuilder):
    logger.debug('IPutWide %s', ins.get_output())
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)
    return iputcommon(ins, irbuilder)


# iput-object vA, vB ( 4b, 4b )
def iputobject(ins, irbuilder):
    logger.debug('IPutObject %s', ins.get_output())
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)
    return iputcommon(ins, irbuilder)


# iput-boolean vA, vB ( 4b, 4b )
def iputboolean(ins, irbuilder):
    logger.debug('IPutBoolean %s', ins.get_output())
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)
    return iputcommon(ins, irbuilder)


# iput-byte vA, vB ( 4b, 4b )
def iputbyte(ins, irbuilder):
    logger.debug('IPutByte %s', ins.get_output())
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)
    return iputcommon(ins, irbuilder)


# iput-char vA, vB ( 4b, 4b )
def iputchar(ins, irbuilder):
    logger.debug('IPutChar %s', ins.get_output())
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)
    return iputcommon(ins, irbuilder)


# iput-short vA, vB ( 4b, 4b )
def iputshort(ins, irbuilder):
    logger.debug('IPutShort %s', ins.get_output())
    # klass, atype, name = ins.cm.get_field(ins.CCCC)
    # a, b = get_variables(irbuilder, ins.A, ins.B)
    # return InstanceInstruction(a, b, klass, atype, name)
    return iputcommon(ins, irbuilder)


def sgetcommon(ins, irbuilder):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    a = irbuilder.write_variable(ins.AA)
    a.refine_type(atype)
    return StaticExpression(a, klass, atype, name)


# sget vAA ( 8b )
def sget(ins, irbuilder):
    logger.debug('SGet : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


# sget-wide vAA ( 8b )
def sgetwide(ins, irbuilder):
    logger.debug('SGetWide : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


# sget-object vAA ( 8b )
def sgetobject(ins, irbuilder):
    logger.debug('SGetObject : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


# sget-boolean vAA ( 8b )
def sgetboolean(ins, irbuilder):
    logger.debug('SGetBoolean : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


# sget-byte vAA ( 8b )
def sgetbyte(ins, irbuilder):
    logger.debug('SGetByte : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


# sget-char vAA ( 8b )
def sgetchar(ins, irbuilder):
    logger.debug('SGetChar : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


# sget-short vAA ( 8b )
def sgetshort(ins, irbuilder):
    logger.debug('SGetShort : %s', ins.get_output())
    return sgetcommon(ins, irbuilder)


def sputcommon(ins, irbuilder):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = irbuilder.read_variable(ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput vAA ( 8b )
def sput(ins, irbuilder):
    logger.debug('SPut : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


# sput-wide vAA ( 8b )
def sputwide(ins, irbuilder):
    logger.debug('SPutWide : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


# sput-object vAA ( 8b )
def sputobject(ins, irbuilder):
    logger.debug('SPutObject : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


# sput-boolean vAA ( 8b )
def sputboolean(ins, irbuilder):
    logger.debug('SPutBoolean : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


# sput-wide vAA ( 8b )
def sputbyte(ins, irbuilder):
    logger.debug('SPutByte : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


# sput-char vAA ( 8b )
def sputchar(ins, irbuilder):
    logger.debug('SPutChar : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


# sput-short vAA ( 8b )
def sputshort(ins, irbuilder):
    logger.debug('SPutShort : %s', ins.get_output())
    return sputcommon(ins, irbuilder)


def get_args(irbuilder, param_type, largs):
    num_param = 0
    args = []
    if len(param_type) > len(largs):
        logger.warning('len(param_type) > len(largs) !')
        return args
    for type_ in param_type:
        param = largs[num_param]
        val = irbuilder.read_variable(param)
        # val.set_type(type_)
        args.append(val)
        num_param += util.get_type_size(type_)

    return args


def invokecommon(ins, irbuilder, invoke_type):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = method.get_class_name()
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    if invoke_type == 'static':
        largs = [ins.C, ins.D, ins.E, ins.F, ins.G]
        thiz = None
    else:
        thiz = irbuilder.read_variable(ins.C)
        largs = [ins.D, ins.E, ins.F, ins.G]
    args = get_args(irbuilder, param_type, largs)
    returned = None if ret_type == 'V' else irbuilder.write_result_variable()
    return InvokeInstruction(invoke_type, cls_name, name, thiz, returned, ret_type, param_type, args,
                             method.get_triple())


# invoke-virtual {vD, vE, vF, vG, vA} ( 4b each )
def invokevirtual(ins, irbuilder):
    logger.debug('InvokeVirtual : %s', ins.get_output())
    return invokecommon(ins, irbuilder, 'virtual')


# invoke-super {vD, vE, vF, vG, vA} ( 4b each )
def invokesuper(ins, irbuilder):
    logger.debug('InvokeSuper : %s', ins.get_output())
    return invokecommon(ins, irbuilder, 'super')


# invoke-direct {vD, vE, vF, vG, vA} ( 4b each )
def invokedirect(ins, irbuilder):
    logger.debug('InvokeDirect : %s', ins.get_output())
    return invokecommon(ins, irbuilder, 'direct')


# invoke-static {vD, vE, vF, vG, vA} ( 4b each )
def invokestatic(ins, irbuilder):
    logger.debug('InvokeStatic : %s', ins.get_output())
    return invokecommon(ins, irbuilder, 'static')


# invoke-interface {vD, vE, vF, vG, vA} ( 4b each )
def invokeinterface(ins, irbuilder):
    logger.debug('InvokeInterface : %s', ins.get_output())
    # method = ins.cm.get_method_ref(ins.BBBB)
    # cls_name = util.get_type(method.get_class_name())
    # name = method.get_name()
    # param_type, ret_type = method.get_proto()
    # param_type = util.get_params_type(param_type)
    # largs = [ins.D, ins.E, ins.F, ins.G]
    # args = get_args(irbuilder, param_type, largs)
    # c = get_variables(irbuilder, ins.C)
    # returned = None if ret_type == 'V' else ret.new()
    # exp = InvokeInstruction(cls_name, name, c, ret_type, param_type, args,
    #                         method.get_triple())
    # return AssignExpression(returned, exp)
    return invokecommon(ins, irbuilder, 'interface')


def invokecommonrange(ins, irbuilder, invoke_type):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = method.get_class_name()
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = list(range(ins.CCCC, ins.NNNN + 1))
    if invoke_type == 'static':
        thiz = None
    else:
        this_reg = largs.pop(0)
        thiz = irbuilder.read_variable(this_reg)
    args = get_args(irbuilder, param_type, largs)
    returned = None if ret_type == 'V' else irbuilder.write_result_variable()
    return InvokeInstruction(invoke_type, cls_name, name, thiz, returned, ret_type, param_type, args,
                             method.get_triple())


# invoke-virtual/range {vCCCC..vNNNN} ( 16b each )
def invokevirtualrange(ins, irbuilder):
    logger.debug('InvokeVirtualRange : %s', ins.get_output())
    return invokecommonrange(ins, irbuilder, 'virtual')
    # method = ins.cm.get_method_ref(ins.BBBB)
    # cls_name = util.get_type(method.get_class_name())
    # name = method.get_name()
    # param_type, ret_type = method.get_proto()
    # param_type = util.get_params_type(param_type)
    # largs = list(range(ins.CCCC, ins.NNNN + 1))
    # this_arg = get_variables(irbuilder, largs[0])
    # args = get_args(irbuilder, param_type, largs[1:])
    # returned = None if ret_type == 'V' else ret.new()
    # exp = InvokeRangeInstruction(cls_name, name, ret_type, param_type,
    #                              [this_arg] + args, method.get_triple())
    # return AssignExpression(returned, exp)


# invoke-super/range {vCCCC..vNNNN} ( 16b each )
def invokesuperrange(ins, irbuilder):
    logger.debug('InvokeSuperRange : %s', ins.get_output())
    # method = ins.cm.get_method_ref(ins.BBBB)
    # cls_name = util.get_type(method.get_class_name())
    # name = method.get_name()
    # param_type, ret_type = method.get_proto()
    # param_type = util.get_params_type(param_type)
    # largs = list(range(ins.CCCC, ins.NNNN + 1))
    # args = get_args(irbuilder, param_type, largs[1:])
    # base = get_variables(irbuilder, ins.CCCC)
    # if ret_type != 'V':
    #     returned = ret.new()
    # else:
    #     returned = base
    #     ret.set_to(base)
    # superclass = BaseClass('super')
    # exp = InvokeRangeInstruction(cls_name, name, ret_type, param_type,
    #                              [superclass] + args, method.get_triple())
    # return AssignExpression(returned, exp)
    return invokecommonrange(ins, irbuilder, 'super')


# invoke-direct/range {vCCCC..vNNNN} ( 16b each )
def invokedirectrange(ins, irbuilder):
    logger.debug('InvokeDirectRange : %s', ins.get_output())
    return invokecommonrange(ins, irbuilder, 'direct')


# invoke-static/range {vCCCC..vNNNN} ( 16b each )
def invokestaticrange(ins, irbuilder):
    logger.debug('InvokeStaticRange : %s', ins.get_output())
    return invokecommonrange(ins, irbuilder, 'static')


# invoke-interface/range {vCCCC..vNNNN} ( 16b each )
def invokeinterfacerange(ins, irbuilder):
    logger.debug('InvokeInterfaceRange : %s', ins.get_output())
    # method = ins.cm.get_method_ref(ins.BBBB)
    # cls_name = util.get_type(method.get_class_name())
    # name = method.get_name()
    # param_type, ret_type = method.get_proto()
    # param_type = util.get_params_type(param_type)
    # largs = list(range(ins.CCCC, ins.NNNN + 1))
    # base_arg = get_variables(irbuilder, largs[0])
    # args = get_args(irbuilder, param_type, largs[1:])
    # returned = None if ret_type == 'V' else ret.new()
    # exp = InvokeRangeInstruction(cls_name, name, ret_type, param_type,
    #                              [base_arg] + args, method.get_triple())
    # return AssignExpression(returned, exp)
    return invokecommonrange(ins, irbuilder, 'interface')


# neg-int vA, vB ( 4b, 4b )
def negint(ins, irbuilder):
    logger.debug('NegInt : %s', ins.get_output())
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return UnaryExpression(a, Op.NEG, b, 'I')


# not-int vA, vB ( 4b, 4b )
def notint(ins, irbuilder):
    logger.debug('NotInt : %s', ins.get_output())
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return UnaryExpression(a, Op.NOT, b, 'I')


# neg-long vA, vB ( 4b, 4b )
def neglong(ins, irbuilder):
    logger.debug('NegLong : %s', ins.get_output())
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return UnaryExpression(a, Op.NEG, b, 'J')


# not-long vA, vB ( 4b, 4b )
def notlong(ins, irbuilder):
    logger.debug('NotLong : %s', ins.get_output())
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return UnaryExpression(a, Op.NOT, b, 'J')


# neg-float vA, vB ( 4b, 4b )
def negfloat(ins, irbuilder):
    logger.debug('NegFloat : %s', ins.get_output())
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return UnaryExpression(a, Op.NEG, b, 'F')


# neg-double vA, vB ( 4b, 4b )
def negdouble(ins, irbuilder):
    logger.debug('NegDouble : %s', ins.get_output())
    b = irbuilder.read_variable(ins.B)
    a = irbuilder.write_variable(ins.A)
    return UnaryExpression(a, Op.NEG, b, 'D')


# int-to-long vA, vB ( 4b, 4b )
def inttolong(ins, irbuilder):
    logger.debug('IntToLong : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('I')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('J')
    return CastExpression(val_a, '(jlong)', 'J', val_b, 'I')


# int-to-float vA, vB ( 4b, 4b )
def inttofloat(ins, irbuilder):
    logger.debug('IntToFloat : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('I')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('F')
    return CastExpression(val_a, '(jfloat)', 'F', val_b, 'I')


# int-to-double vA, vB ( 4b, 4b )
def inttodouble(ins, irbuilder):
    logger.debug('IntToDouble : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('I')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('D')
    return CastExpression(val_a, '(jdouble)', 'D', val_b, 'I')


# long-to-int vA, vB ( 4b, 4b )
def longtoint(ins, irbuilder):
    logger.debug('LongToInt : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('J')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('I')
    return CastExpression(val_a, '(jint)', 'I', val_b, 'J')


# long-to-float vA, vB ( 4b, 4b )
def longtofloat(ins, irbuilder):
    logger.debug('LongToFloat : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('J')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('F')
    return CastExpression(val_a, '(jfloat)', 'F', val_b, 'J')


# long-to-double vA, vB ( 4b, 4b )
def longtodouble(ins, irbuilder):
    logger.debug('LongToDouble : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('J')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('D')
    return CastExpression(val_a, '(jdouble)', 'D', val_b, 'J')


# float-to-int vA, vB ( 4b, 4b )
def floattoint(ins, irbuilder):
    logger.debug('FloatToInt : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('F')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('I')
    return CastExpression(val_a, '(jint)', 'I', val_b, 'F')


# float-to-long vA, vB ( 4b, 4b )
def floattolong(ins, irbuilder):
    logger.debug('FloatToLong : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('F')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('J')
    return CastExpression(val_a, '(jlong)', 'J', val_b, 'F')


# float-to-double vA, vB ( 4b, 4b )
def floattodouble(ins, irbuilder):
    logger.debug('FloatToDouble : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('F')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('D')
    return CastExpression(val_a, '(jdouble)', 'D', val_b, 'F')


# double-to-int vA, vB ( 4b, 4b )
def doubletoint(ins, irbuilder):
    logger.debug('DoubleToInt : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('D')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('I')
    return CastExpression(val_a, '(jint)', 'I', val_b, 'D')


# double-to-long vA, vB ( 4b, 4b )
def doubletolong(ins, irbuilder):
    logger.debug('DoubleToLong : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('D')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('J')
    return CastExpression(val_a, '(jlong)', 'J', val_b, 'D')


# double-to-float vA, vB ( 4b, 4b )
def doubletofloat(ins, irbuilder):
    logger.debug('DoubleToFloat : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('D')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('F')
    return CastExpression(val_a, '(jfloat)', 'F', val_b, 'D')


# int-to-byte vA, vB ( 4b, 4b )
def inttobyte(ins, irbuilder):
    logger.debug('IntToByte : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('I')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('B')
    return CastExpression(val_a, '(jbyte)', 'B', val_b, 'I')


# int-to-char vA, vB ( 4b, 4b )
def inttochar(ins, irbuilder):
    logger.debug('IntToChar : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('I')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('C')
    return CastExpression(val_a, '(jchar)', 'C', val_b, 'I')


# int-to-short vA, vB ( 4b, 4b )
def inttoshort(ins, irbuilder):
    logger.debug('IntToShort : %s', ins.get_output())
    val_b = irbuilder.read_variable(ins.B)
    val_b.refine_type('I')
    val_a = irbuilder.write_variable(ins.A)
    val_a.refine_type('S')
    return CastExpression(val_a, '(jshort)', 'S', val_b, 'I')


# add-int vAA, vBB, vCC ( 8b, 8b, 8b )
def addint(ins, irbuilder):
    logger.debug('AddInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.ADD, 'I', irbuilder)


# sub-int vAA, vBB, vCC ( 8b, 8b, 8b )
def subint(ins, irbuilder):
    logger.debug('SubInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.SUB, 'I', irbuilder)


# mul-int vAA, vBB, vCC ( 8b, 8b, 8b )
def mulint(ins, irbuilder):
    logger.debug('MulInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MUL, 'I', irbuilder)


# div-int vAA, vBB, vCC ( 8b, 8b, 8b )
def divint(ins, irbuilder):
    logger.debug('DivInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.DIV, 'I', irbuilder)


# rem-int vAA, vBB, vCC ( 8b, 8b, 8b )
def remint(ins, irbuilder):
    logger.debug('RemInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MOD, 'I', irbuilder)


# and-int vAA, vBB, vCC ( 8b, 8b, 8b )
def andint(ins, irbuilder):
    logger.debug('AndInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.AND, 'I', irbuilder)


# or-int vAA, vBB, vCC ( 8b, 8b, 8b )
def orint(ins, irbuilder):
    logger.debug('OrInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.OR, 'I', irbuilder)


# xor-int vAA, vBB, vCC ( 8b, 8b, 8b )
def xorint(ins, irbuilder):
    logger.debug('XorInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.XOR, 'I', irbuilder)


# shl-int vAA, vBB, vCC ( 8b, 8b, 8b )
def shlint(ins, irbuilder):
    logger.debug('ShlInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.INTSHL, 'I', irbuilder)


# shr-int vAA, vBB, vCC ( 8b, 8b, 8b )
def shrint(ins, irbuilder):
    logger.debug('ShrInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.INTSHR, 'I', irbuilder)


# ushr-int vAA, vBB, vCC ( 8b, 8b, 8b )
def ushrint(ins, irbuilder):
    logger.debug('UShrInt : %s', ins.get_output())
    return assign_binary_exp(ins, Op.INTUSHR, 'I', irbuilder)


# add-long vAA, vBB, vCC ( 8b, 8b, 8b )
def addlong(ins, irbuilder):
    logger.debug('AddLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.ADD, 'J', irbuilder)


# sub-long vAA, vBB, vCC ( 8b, 8b, 8b )
def sublong(ins, irbuilder):
    logger.debug('SubLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.SUB, 'J', irbuilder)


# mul-long vAA, vBB, vCC ( 8b, 8b, 8b )
def mullong(ins, irbuilder):
    logger.debug('MulLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MUL, 'J', irbuilder)


# div-long vAA, vBB, vCC ( 8b, 8b, 8b )
def divlong(ins, irbuilder):
    logger.debug('DivLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.DIV, 'J', irbuilder)


# rem-long vAA, vBB, vCC ( 8b, 8b, 8b )
def remlong(ins, irbuilder):
    logger.debug('RemLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MOD, 'J', irbuilder)


# and-long vAA, vBB, vCC ( 8b, 8b, 8b )
def andlong(ins, irbuilder):
    logger.debug('AndLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.AND, 'J', irbuilder)


# or-long vAA, vBB, vCC ( 8b, 8b, 8b )
def orlong(ins, irbuilder):
    logger.debug('OrLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.OR, 'J', irbuilder)


# xor-long vAA, vBB, vCC ( 8b, 8b, 8b )
def xorlong(ins, irbuilder):
    logger.debug('XorLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.XOR, 'J', irbuilder)


# shl-long vAA, vBB, vCC ( 8b, 8b, 8b )
def shllong(ins, irbuilder):
    logger.debug('ShlLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.LONGSHL, 'J', irbuilder)


# shr-long vAA, vBB, vCC ( 8b, 8b, 8b )
def shrlong(ins, irbuilder):
    logger.debug('ShrLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.LONGSHR, 'J', irbuilder)


# ushr-long vAA, vBB, vCC ( 8b, 8b, 8b )
def ushrlong(ins, irbuilder):
    logger.debug('UShrLong : %s', ins.get_output())
    return assign_binary_exp(ins, Op.LONGUSHR, 'J', irbuilder)


# add-float vAA, vBB, vCC ( 8b, 8b, 8b )
def addfloat(ins, irbuilder):
    logger.debug('AddFloat : %s', ins.get_output())
    return assign_binary_exp(ins, Op.ADD, 'F', irbuilder)


# sub-float vAA, vBB, vCC ( 8b, 8b, 8b )
def subfloat(ins, irbuilder):
    logger.debug('SubFloat : %s', ins.get_output())
    return assign_binary_exp(ins, Op.SUB, 'F', irbuilder)


# mul-float vAA, vBB, vCC ( 8b, 8b, 8b )
def mulfloat(ins, irbuilder):
    logger.debug('MulFloat : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MUL, 'F', irbuilder)


# div-float vAA, vBB, vCC ( 8b, 8b, 8b )
def divfloat(ins, irbuilder):
    logger.debug('DivFloat : %s', ins.get_output())
    return assign_binary_exp(ins, Op.DIV, 'F', irbuilder)


# rem-float vAA, vBB, vCC ( 8b, 8b, 8b )
def remfloat(ins, irbuilder):
    logger.debug('RemFloat : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MODF, 'F', irbuilder)


# add-double vAA, vBB, vCC ( 8b, 8b, 8b )
def adddouble(ins, irbuilder):
    logger.debug('AddDouble : %s', ins.get_output())
    return assign_binary_exp(ins, Op.ADD, 'D', irbuilder)


# sub-double vAA, vBB, vCC ( 8b, 8b, 8b )
def subdouble(ins, irbuilder):
    logger.debug('SubDouble : %s', ins.get_output())
    return assign_binary_exp(ins, Op.SUB, 'D', irbuilder)


# mul-double vAA, vBB, vCC ( 8b, 8b, 8b )
def muldouble(ins, irbuilder):
    logger.debug('MulDouble : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MUL, 'D', irbuilder)


# div-double vAA, vBB, vCC ( 8b, 8b, 8b )
def divdouble(ins, irbuilder):
    logger.debug('DivDouble : %s', ins.get_output())
    return assign_binary_exp(ins, Op.DIV, 'D', irbuilder)


# rem-double vAA, vBB, vCC ( 8b, 8b, 8b )
def remdouble(ins, irbuilder):
    logger.debug('RemDouble : %s', ins.get_output())
    return assign_binary_exp(ins, Op.MODD, 'D', irbuilder)


# add-int/2addr vA, vB ( 4b, 4b )
def addint2addr(ins, irbuilder):
    logger.debug('AddInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.ADD, 'I', irbuilder)


# sub-int/2addr vA, vB ( 4b, 4b )
def subint2addr(ins, irbuilder):
    logger.debug('SubInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.SUB, 'I', irbuilder)


# mul-int/2addr vA, vB ( 4b, 4b )
def mulint2addr(ins, irbuilder):
    logger.debug('MulInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MUL, 'I', irbuilder)


# div-int/2addr vA, vB ( 4b, 4b )
def divint2addr(ins, irbuilder):
    logger.debug('DivInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.DIV, 'I', irbuilder)


# rem-int/2addr vA, vB ( 4b, 4b )
def remint2addr(ins, irbuilder):
    logger.debug('RemInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MOD, 'I', irbuilder)


# and-int/2addr vA, vB ( 4b, 4b )
def andint2addr(ins, irbuilder):
    logger.debug('AndInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.AND, 'I', irbuilder)


# or-int/2addr vA, vB ( 4b, 4b )
def orint2addr(ins, irbuilder):
    logger.debug('OrInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.OR, 'I', irbuilder)


# xor-int/2addr vA, vB ( 4b, 4b )
def xorint2addr(ins, irbuilder):
    logger.debug('XorInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.XOR, 'I', irbuilder)


# shl-int/2addr vA, vB ( 4b, 4b )
def shlint2addr(ins, irbuilder):
    logger.debug('ShlInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.INTSHL, 'I', irbuilder)


# shr-int/2addr vA, vB ( 4b, 4b )
def shrint2addr(ins, irbuilder):
    logger.debug('ShrInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.INTSHR, 'I', irbuilder)


# ushr-int/2addr vA, vB ( 4b, 4b )
def ushrint2addr(ins, irbuilder):
    logger.debug('UShrInt2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.INTUSHR, 'I', irbuilder)


# add-long/2addr vA, vB ( 4b, 4b )
def addlong2addr(ins, irbuilder):
    logger.debug('AddLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.ADD, 'J', irbuilder)


# sub-long/2addr vA, vB ( 4b, 4b )
def sublong2addr(ins, irbuilder):
    logger.debug('SubLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.SUB, 'J', irbuilder)


# mul-long/2addr vA, vB ( 4b, 4b )
def mullong2addr(ins, irbuilder):
    logger.debug('MulLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MUL, 'J', irbuilder)


# div-long/2addr vA, vB ( 4b, 4b )
def divlong2addr(ins, irbuilder):
    logger.debug('DivLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.DIV, 'J', irbuilder)


# rem-long/2addr vA, vB ( 4b, 4b )
def remlong2addr(ins, irbuilder):
    logger.debug('RemLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MOD, 'J', irbuilder)


# and-long/2addr vA, vB ( 4b, 4b )
def andlong2addr(ins, irbuilder):
    logger.debug('AndLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.AND, 'J', irbuilder)


# or-long/2addr vA, vB ( 4b, 4b )
def orlong2addr(ins, irbuilder):
    logger.debug('OrLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.OR, 'J', irbuilder)


# xor-long/2addr vA, vB ( 4b, 4b )
def xorlong2addr(ins, irbuilder):
    logger.debug('XorLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.XOR, 'J', irbuilder)


# shl-long/2addr vA, vB ( 4b, 4b )
def shllong2addr(ins, irbuilder):
    logger.debug('ShlLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.LONGSHL, 'J', irbuilder)


# shr-long/2addr vA, vB ( 4b, 4b )
def shrlong2addr(ins, irbuilder):
    logger.debug('ShrLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.LONGSHR, 'J', irbuilder)


# ushr-long/2addr vA, vB ( 4b, 4b )
def ushrlong2addr(ins, irbuilder):
    logger.debug('UShrLong2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.LONGUSHR, 'J', irbuilder)


# add-float/2addr vA, vB ( 4b, 4b )
def addfloat2addr(ins, irbuilder):
    logger.debug('AddFloat2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.ADD, 'F', irbuilder)


# sub-float/2addr vA, vB ( 4b, 4b )
def subfloat2addr(ins, irbuilder):
    logger.debug('SubFloat2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.SUB, 'F', irbuilder)


# mul-float/2addr vA, vB ( 4b, 4b )
def mulfloat2addr(ins, irbuilder):
    logger.debug('MulFloat2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MUL, 'F', irbuilder)


# div-float/2addr vA, vB ( 4b, 4b )
def divfloat2addr(ins, irbuilder):
    logger.debug('DivFloat2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.DIV, 'F', irbuilder)


# rem-float/2addr vA, vB ( 4b, 4b )
def remfloat2addr(ins, irbuilder):
    logger.debug('RemFloat2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MODF, 'F', irbuilder)


# add-double/2addr vA, vB ( 4b, 4b )
def adddouble2addr(ins, irbuilder):
    logger.debug('AddDouble2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.ADD, 'D', irbuilder)


# sub-double/2addr vA, vB ( 4b, 4b )
def subdouble2addr(ins, irbuilder):
    logger.debug('subDouble2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.SUB, 'D', irbuilder)


# mul-double/2addr vA, vB ( 4b, 4b )
def muldouble2addr(ins, irbuilder):
    logger.debug('MulDouble2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MUL, 'D', irbuilder)


# div-double/2addr vA, vB ( 4b, 4b )
def divdouble2addr(ins, irbuilder):
    logger.debug('DivDouble2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.DIV, 'D', irbuilder)


# rem-double/2addr vA, vB ( 4b, 4b )
def remdouble2addr(ins, irbuilder):
    logger.debug('RemDouble2Addr : %s', ins.get_output())
    return assign_binary_2addr_exp(ins, Op.MODD, 'D', irbuilder)


# add-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def addintlit16(ins, irbuilder):
    logger.debug('AddIntLit16 : %s', ins.get_output())
    return assign_lit(Op.ADD, ins.CCCC, ins.A, ins.B, irbuilder)


# rsub-int vA, vB, #+CCCC ( 4b, 4b, 16b )
# a = #+cccc - vB
def rsubint(ins, irbuilder):
    logger.debug('RSubInt : %s', ins.get_output())
    var_b = irbuilder.read_variable(ins.B)
    var_a = irbuilder.write_variable(ins.A)
    var_a.refine_type('I')
    cst = Constant(ins.CCCC, 'I')
    return BinaryExpressionLit(Op.SUB, var_a, cst, var_b)


# mul-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def mulintlit16(ins, irbuilder):
    logger.debug('MulIntLit16 : %s', ins.get_output())
    return assign_lit(Op.MUL, ins.CCCC, ins.A, ins.B, irbuilder)


# div-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def divintlit16(ins, irbuilder):
    logger.debug('DivIntLit16 : %s', ins.get_output())
    return assign_lit(Op.DIV, ins.CCCC, ins.A, ins.B, irbuilder)


# rem-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def remintlit16(ins, irbuilder):
    logger.debug('RemIntLit16 : %s', ins.get_output())
    return assign_lit(Op.MOD, ins.CCCC, ins.A, ins.B, irbuilder)


# and-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def andintlit16(ins, irbuilder):
    logger.debug('AndIntLit16 : %s', ins.get_output())
    return assign_lit(Op.AND, ins.CCCC, ins.A, ins.B, irbuilder)


# or-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def orintlit16(ins, irbuilder):
    logger.debug('OrIntLit16 : %s', ins.get_output())
    return assign_lit(Op.OR, ins.CCCC, ins.A, ins.B, irbuilder)


# xor-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def xorintlit16(ins, irbuilder):
    logger.debug('XorIntLit16 : %s', ins.get_output())
    return assign_lit(Op.XOR, ins.CCCC, ins.A, ins.B, irbuilder)


# add-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def addintlit8(ins, irbuilder):
    logger.debug('AddIntLit8 : %s', ins.get_output())
    literal, op = [(ins.CC, Op.ADD), (-ins.CC, Op.SUB)][ins.CC < 0]
    var_b = irbuilder.read_variable(ins.BB)
    var_a = irbuilder.write_variable(ins.AA)
    cst = Constant(literal, 'B')
    return BinaryExpressionLit(op, var_a, var_b, cst)


# rsub-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def rsubintlit8(ins, irbuilder):
    logger.debug('RSubIntLit8 : %s', ins.get_output())
    var_b = irbuilder.read_variable(ins.BB)
    var_a = irbuilder.write_variable(ins.AA)
    var_a.refine_type('I')
    cst = Constant(ins.CC, 'I')
    return BinaryExpressionLit(Op.SUB, var_a, cst, var_b)


# mul-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def mulintlit8(ins, irbuilder):
    logger.debug('MulIntLit8 : %s', ins.get_output())
    return assign_lit(Op.MUL, ins.CC, ins.AA, ins.BB, irbuilder)


# div-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def divintlit8(ins, irbuilder):
    logger.debug('DivIntLit8 : %s', ins.get_output())
    return assign_lit(Op.DIV, ins.CC, ins.AA, ins.BB, irbuilder)


# rem-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def remintlit8(ins, irbuilder):
    logger.debug('RemIntLit8 : %s', ins.get_output())
    return assign_lit(Op.MOD, ins.CC, ins.AA, ins.BB, irbuilder)


# and-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def andintlit8(ins, irbuilder):
    logger.debug('AndIntLit8 : %s', ins.get_output())
    return assign_lit(Op.AND, ins.CC, ins.AA, ins.BB, irbuilder)


# or-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def orintlit8(ins, irbuilder):
    logger.debug('OrIntLit8 : %s', ins.get_output())
    return assign_lit(Op.OR, ins.CC, ins.AA, ins.BB, irbuilder)


# xor-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def xorintlit8(ins, irbuilder):
    logger.debug('XorIntLit8 : %s', ins.get_output())
    return assign_lit(Op.XOR, ins.CC, ins.AA, ins.BB, irbuilder)


# shl-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def shlintlit8(ins, irbuilder):
    logger.debug('ShlIntLit8 : %s', ins.get_output())
    return assign_lit(Op.INTSHL, ins.CC, ins.AA, ins.BB, irbuilder)


# shr-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def shrintlit8(ins, irbuilder):
    logger.debug('ShrIntLit8 : %s', ins.get_output())
    return assign_lit(Op.INTSHR, ins.CC, ins.AA, ins.BB, irbuilder)


# ushr-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def ushrintlit8(ins, irbuilder):
    logger.debug('UShrIntLit8 : %s', ins.get_output())
    return assign_lit(Op.INTUSHR, ins.CC, ins.AA, ins.BB, irbuilder)


INSTRUCTION_SET = [
    # 0x00
    nop,  # nop
    move,  # move
    movefrom16,  # move/from16
    move16,  # move/16
    movewide,  # move-wide
    movewidefrom16,  # move-wide/from16
    movewide16,  # move-wide/16
    moveobject,  # move-object
    moveobjectfrom16,  # move-object/from16
    moveobject16,  # move-object/16
    moveresult,  # move-result
    moveresultwide,  # move-result-wide
    moveresultobject,  # move-result-object
    moveexception,  # move-exception
    returnvoid,  # return-void
    return_reg,  # return
    # 0x10
    returnwide,  # return-wide
    returnobject,  # return-object
    const4,  # const/4
    const16,  # const/16
    const,  # const
    consthigh16,  # const/high16
    constwide16,  # const-wide/16
    constwide32,  # const-wide/32
    constwide,  # const-wide
    constwidehigh16,  # const-wide/high16
    conststring,  # const-string
    conststringjumbo,  # const-string/jumbo
    constclass,  # const-class
    monitorenter,  # monitor-enter
    monitorexit,  # monitor-exit
    checkcast,  # check-cast
    # 0x20
    instanceof,  # instance-of
    arraylength,  # array-length
    newinstance,  # new-instance
    newarray,  # new-array
    fillednewarray,  # filled-new-array
    fillednewarrayrange,  # filled-new-array/range
    fillarraydata,  # fill-array-data
    throw,  # throw
    goto,  # goto
    goto16,  # goto/16
    goto32,  # goto/32
    packedswitch,  # packed-switch
    sparseswitch,  # sparse-switch
    cmplfloat,  # cmpl-float
    cmpgfloat,  # cmpg-float
    cmpldouble,  # cmpl-double
    # 0x30
    cmpgdouble,  # cmpg-double
    cmplong,  # cmp-long
    ifeq,  # if-eq
    ifne,  # if-ne
    iflt,  # if-lt
    ifge,  # if-ge
    ifgt,  # if-gt
    ifle,  # if-le
    ifeqz,  # if-eqz
    ifnez,  # if-nez
    ifltz,  # if-ltz
    ifgez,  # if-gez
    ifgtz,  # if-gtz
    iflez,  # if-l
    nop,  # unused
    nop,  # unused
    # 0x40
    nop,  # unused
    nop,  # unused
    nop,  # unused
    nop,  # unused
    aget,  # aget
    agetwide,  # aget-wide
    agetobject,  # aget-object
    agetboolean,  # aget-boolean
    agetbyte,  # aget-byte
    agetchar,  # aget-char
    agetshort,  # aget-short
    aput,  # aput
    aputwide,  # aput-wide
    aputobject,  # aput-object
    aputboolean,  # aput-boolean
    aputbyte,  # aput-byte
    # 0x50
    aputchar,  # aput-char
    aputshort,  # aput-short
    iget,  # iget
    igetwide,  # iget-wide
    igetobject,  # iget-object
    igetboolean,  # iget-boolean
    igetbyte,  # iget-byte
    igetchar,  # iget-char
    igetshort,  # iget-short
    iput,  # iput
    iputwide,  # iput-wide
    iputobject,  # iput-object
    iputboolean,  # iput-boolean
    iputbyte,  # iput-byte
    iputchar,  # iput-char
    iputshort,  # iput-short
    # 0x60
    sget,  # sget
    sgetwide,  # sget-wide
    sgetobject,  # sget-object
    sgetboolean,  # sget-boolean
    sgetbyte,  # sget-byte
    sgetchar,  # sget-char
    sgetshort,  # sget-short
    sput,  # sput
    sputwide,  # sput-wide
    sputobject,  # sput-object
    sputboolean,  # sput-boolean
    sputbyte,  # sput-byte
    sputchar,  # sput-char
    sputshort,  # sput-short
    invokevirtual,  # invoke-virtual
    invokesuper,  # invoke-super
    # 0x70
    invokedirect,  # invoke-direct
    invokestatic,  # invoke-static
    invokeinterface,  # invoke-interface
    nop,  # unused
    invokevirtualrange,  # invoke-virtual/range
    invokesuperrange,  # invoke-super/range
    invokedirectrange,  # invoke-direct/range
    invokestaticrange,  # invoke-static/range
    invokeinterfacerange,  # invoke-interface/range
    nop,  # unused
    nop,  # unused
    negint,  # neg-int
    notint,  # not-int
    neglong,  # neg-long
    notlong,  # not-long
    negfloat,  # neg-float
    # 0x80
    negdouble,  # neg-double
    inttolong,  # int-to-long
    inttofloat,  # int-to-float
    inttodouble,  # int-to-double
    longtoint,  # long-to-int
    longtofloat,  # long-to-float
    longtodouble,  # long-to-double
    floattoint,  # float-to-int
    floattolong,  # float-to-long
    floattodouble,  # float-to-double
    doubletoint,  # double-to-int
    doubletolong,  # double-to-long
    doubletofloat,  # double-to-float
    inttobyte,  # int-to-byte
    inttochar,  # int-to-char
    inttoshort,  # int-to-short
    # 0x90
    addint,  # add-int
    subint,  # sub-int
    mulint,  # mul-int
    divint,  # div-int
    remint,  # rem-int
    andint,  # and-int
    orint,  # or-int
    xorint,  # xor-int
    shlint,  # shl-int
    shrint,  # shr-int
    ushrint,  # ushr-int
    addlong,  # add-long
    sublong,  # sub-long
    mullong,  # mul-long
    divlong,  # div-long
    remlong,  # rem-long
    # 0xa0
    andlong,  # and-long
    orlong,  # or-long
    xorlong,  # xor-long
    shllong,  # shl-long
    shrlong,  # shr-long
    ushrlong,  # ushr-long
    addfloat,  # add-float
    subfloat,  # sub-float
    mulfloat,  # mul-float
    divfloat,  # div-float
    remfloat,  # rem-float
    adddouble,  # add-double
    subdouble,  # sub-double
    muldouble,  # mul-double
    divdouble,  # div-double
    remdouble,  # rem-double
    # 0xb0
    addint2addr,  # add-int/2addr
    subint2addr,  # sub-int/2addr
    mulint2addr,  # mul-int/2addr
    divint2addr,  # div-int/2addr
    remint2addr,  # rem-int/2addr
    andint2addr,  # and-int/2addr
    orint2addr,  # or-int/2addr
    xorint2addr,  # xor-int/2addr
    shlint2addr,  # shl-int/2addr
    shrint2addr,  # shr-int/2addr
    ushrint2addr,  # ushr-int/2addr
    addlong2addr,  # add-long/2addr
    sublong2addr,  # sub-long/2addr
    mullong2addr,  # mul-long/2addr
    divlong2addr,  # div-long/2addr
    remlong2addr,  # rem-long/2addr
    # 0xc0
    andlong2addr,  # and-long/2addr
    orlong2addr,  # or-long/2addr
    xorlong2addr,  # xor-long/2addr
    shllong2addr,  # shl-long/2addr
    shrlong2addr,  # shr-long/2addr
    ushrlong2addr,  # ushr-long/2addr
    addfloat2addr,  # add-float/2addr
    subfloat2addr,  # sub-float/2addr
    mulfloat2addr,  # mul-float/2addr
    divfloat2addr,  # div-float/2addr
    remfloat2addr,  # rem-float/2addr
    adddouble2addr,  # add-double/2addr
    subdouble2addr,  # sub-double/2addr
    muldouble2addr,  # mul-double/2addr
    divdouble2addr,  # div-double/2addr
    remdouble2addr,  # rem-double/2addr
    # 0xd0
    addintlit16,  # add-int/lit16
    rsubint,  # rsub-int
    mulintlit16,  # mul-int/lit16
    divintlit16,  # div-int/lit16
    remintlit16,  # rem-int/lit16
    andintlit16,  # and-int/lit16
    orintlit16,  # or-int/lit16
    xorintlit16,  # xor-int/lit16
    addintlit8,  # add-int/lit8
    rsubintlit8,  # rsub-int/lit8
    mulintlit8,  # mul-int/lit8
    divintlit8,  # div-int/lit8
    remintlit8,  # rem-int/lit8
    andintlit8,  # and-int/lit8
    orintlit8,  # or-int/lit8
    xorintlit8,  # xor-int/lit8
    # 0xe0
    shlintlit8,  # shl-int/lit8
    shrintlit8,  # shr-int/lit8
    ushrintlit8,  # ushr-int/lit8
]
