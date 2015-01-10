from collections import deque
import instruction

class Expression(object):
    def __init__(self):
        pass

    def get_all_children(self):
        return self.get_children() + sum([x.get_all_children() for x in self.get_children()], [])

    def get_children(self):
        return []

    def replace_child(self, child, new_child):
        pass

    def equals(self, expression):
        return type(self) == type(expression)

    def contains(self, expression):
        return self.equals(expression)

    def get_format(self):
        return ""

    def __str__(self):
        return self.get_format().format(*[str(x) for x in self.get_children()])

class UnaryExpression(Expression):
    def __init__(self, value):
        self.value = value

    def get_children(self):
        return [self.value]

    def replace_child(self, child, new_child):
        if self.value == child:
            self.value = new_child

    def equals(self, expression):
        return Expression.equals(self, expression) and self.value.equals(expression.value)

    def contains(self, expression):
        return Expression.contains(self, expression) or self.value.contains(expression)

class UnaryOperationExpression(UnaryExpression):
    def __init__(self, value, op_str):
        UnaryExpression.__init__(self, value)
        self.op_str = op_str

    def get_format(self):
        return "(%s{0})" % self.op_str

class BinaryExpression(Expression):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

    def get_children(self):
        return [self.lvalue, self.rvalue]

    def replace_child(self, child, new_child):
        if self.lvalue == child:
            self.lvalue = new_child
        if self.rvalue == child:
            self.rvalue = new_child

    def equals(self, expression):
        return Expression.equals(self, expression) and (self.lvalue.equals(expression.lvalue) and self.rvalue.equals(expression.rvalue))

    def contains(self, expression):
        return Expression.contains(self, expression) or self.lvalue.contains(expression) or self.rvalue.contains(expression)

class BinaryOperationExpression(BinaryExpression):
    def __init__(self, lvalue, rvalue, op_str, swappable = False):
        BinaryExpression.__init__(self, lvalue, rvalue)
        self.op_str = op_str
        self.swappable = swappable

    def equals(self, expression):
        return Expression.equals(self, expression) and \
            ((self.lvalue.equals(expression.lvalue) and self.rvalue.equals(expression.rvalue)) or \
             (self.swappable and self.rvalue.equals(expression.lvalue) and self.lvalue.equals(expression.rvalue)))

    def get_format(self):
        return "({0} %s {1})" % self.op_str

class Invalid(Expression):
    def __str__(self):
        return "Invalid"

class Immediate(Expression):
    def __init__(self, value):
        self.value = value

    def equals(self, expression):
        return Expression.equals(self, expression) and self.value == expression.value

    def get_format(self):
        return "0x%X" % self.value

class ValueOf(UnaryExpression):
    def __init__(self, value, size):
        UnaryExpression.__init__(self, value)
        self.size = size

    def equals(self, expression):
        return UnaryExpression.equals(self, expression) and self.size == expression.size

    def get_format(self):
        if self.size == 1:
            s = "BYTE"
        if self.size == 2:
            s = "WORD"
        if self.size == 4:
            s = "DWORD"
        if self.size == 8:
            s = "QWORD"
        return "*(%s*){0}" % s

class NonVisible(object):
    def __init__(self):
        self.visible = False

class SetValueOperation(BinaryExpression, NonVisible):
    def __init__(self, lvalue, rvalue, op_str):
        BinaryExpression.__init__(self, lvalue, rvalue)
        NonVisible.__init__(self)
        self.op_str = op_str

    def get_format(self):
        return "{0} %s= {1}" % self.op_str

class SetValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "")

class AddValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "+")

class SubValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "-")

class XorValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "^")

class AndValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "&")

class OrValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "|")

class ShlValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "<<")

class ShrValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, ">>")

class RclValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "rcl")

class RcrValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "rcr")

class RolValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "rol")

class RorValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "ror")

class MulValue(SetValueOperation):
    def __init__(self, lvalue, rvalue):
        SetValueOperation.__init__(self, lvalue, rvalue, "*")

class SetValueUnaryOperation(SetValueOperation):
    def __init__(self, value, op_str):
        SetValueOperation.__init__(self, value, value, op_str)

    def get_format(self):
        return "{0} = %s{1}" % self.op_str

class NotValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "~")

class NegValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "-")

class IncValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "++")

class DecValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "--")

class Add(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "+", True)

class Sub(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "-")

class Xor(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "^", True)

class And(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "&")

class Or(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "|", True)

class Shl(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "<<")

class Shr(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, ">>")

class Rcl(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "rcl")

class Rcr(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "rcr")

class Rol(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "rol")

class Ror(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "ror")

class Mul(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "*")

class Not(UnaryOperationExpression):
    def __init__(self, value):
        UnaryOperationExpression.__init__(self, value, "~")

class Neg(UnaryOperationExpression):
    def __init__(self, value):
        UnaryOperationExpression.__init__(self, value, "-")

class Inc(UnaryOperationExpression):
    def __init__(self, value):
        UnaryOperationExpression.__init__(self, value, "++")

class Dec(UnaryOperationExpression):
    def __init__(self, value):
        UnaryOperationExpression.__init__(self, value, "--")

class BinaryCompressionExpression(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue, op_str, swappable = False):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, op_str, swappable)

    def get_format(self):
        return "%s({0}, {1})" % self.op_str

class Cmp(BinaryCompressionExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "Compare")

class Test(BinaryCompressionExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "Test")

class ConditionExpression(object):
    def invert(self):
        return None

class Equal(BinaryOperationExpression, ConditionExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "==")

    def invert(self):
        return NotEqual(self.lvalue, self.rvalue)

class NotEqual(BinaryOperationExpression, ConditionExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "!=")

    def invert(self):
        return Equal(self.lvalue, self.rvalue)

class AndCond(BinaryOperationExpression, ConditionExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "&&")

    def invert(self):
        return NotCond(OrCond(self.lvalue, self.rvalue))

class OrCond(BinaryOperationExpression, ConditionExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "||")

    def invert(self):
        return NotCond(AndCond(self.lvalue, self.rvalue))

class NotCond(UnaryOperationExpression, ConditionExpression):
    def __init__(self, value):
        UnaryOperationExpression.__init__(self, value, "!")

    def invert(self):
        return self.value

class Jump(UnaryExpression):
    def get_format(self):
        return "Jump({0})"

class ConditionBlock(object):
    def __init__(self, instructions):
        self.instructions = instructions

class If(UnaryExpression, ConditionBlock):
    def __init__(self, value, instructions):
        UnaryExpression.__init__(self, value)
        ConditionBlock.__init__(self, instructions)

    def get_format(self):
        return "If({0})"

class Else(Expression, ConditionBlock):
    def __init__(self, instructions):
        ConditionBlock.__init__(self, instructions)

    def get_format(self):
        return "Else"

class Variable(Expression):
    def __init__(self, name):
        self.name = name
        self.instructions = []
        self.used_instructions = []

    def equals(self, other):
        return Expression.equals(self, other) and self.name == other.name

    def get_format(self):
        return "var_%s"  % self.name

class SP(Expression):
    def get_format(self):
        return "SP"

class Flags(Expression):
    def get_format(self):
        return "flags"

class FlagsOf(UnaryExpression):
    def get_format(self):
        return "Flags({0})"

class Register(Expression):
    def __init__(self, value):
        self.value = value

    def equals(self, other):
        return Expression.equals(self, other) and self.value == other.value

    def get_format(self):
        return "%s" % self.value

class Pop(Expression):
    def get_format(self):
        return "Pop()"

class PopWord(Expression):
    def get_format(self):
        return "PopWord()"

class Push(UnaryExpression, NonVisible):
    def __init__(self, value):
        UnaryExpression.__init__(self, value)
        NonVisible.__init__(self)

    def get_format(self):
        return "Push({0})"

class PushWord(UnaryExpression, NonVisible):
    def __init__(self, value):
        UnaryExpression.__init__(self, value)
        NonVisible.__init__(self)

    def get_format(self):
        return "PushWord({0})"

class Return(Expression):
    def __init__(self, value):
        self.value = value

    def equals(self, other):
        return Expression.equals(self, other) and self.value == other.value

    def get_format(self):
        return "Return(%x)" % self.value

class Conversion(UnaryExpression):
    def __init__(self, value, size):
        UnaryExpression.__init__(self, value)
        self.size = size

    def _get_size_name(self):
        if self.size == 1:
            return "BYTE"
        if self.size == 2:
            return "WORD"
        if self.size == 4:
            return "DWORD"
        if self.size == 8:
            return "QWORD"

    def get_format(self):
        return "(%s){0}" % self._get_size_name()

class UnsignedConversion(Conversion):
    pass

class SignedConversion(Conversion):
    def get_format(self):
        return "(S%s){0}" % self._get_size_name()

class Std(Expression):
    def get_format(self):
        return "Std()"

class MemCopy(Expression):
    def __init__(self, dst, src, size):
        self.dst = dst
        self.src = src
        self.size = size

    def get_children(self):
        return [self.dst, self.src, self.size]

    def replace_child(self, child, new_child):
        if self.dst == child:
            self.dst = new_child
        if self.src == child:
            self.src = new_child
        if self.size == child:
            self.size = new_child

    def get_format(self):
        return "MemCopy({0}, {1}, {2})"


MATH_OP = {
    "add": Add,
    "sub": Sub,
    "xor": Xor,
    "and": And,
    "or": Or,
    "shl": Shl,
    "shr": Shr,
    "rcr": Rcr,
    "rcl": Rcl,
    "ror": Ror,
    "rol": Rol,
    "imul": Mul,
}
MATH_OP_UNARY = {
    "inc": Inc,
    "dec": Dec,
    "not": Not,
    "neg": Neg,
}

MATH_OP_VALUE = {
    "add": AddValue,
    "sub": SubValue,
    "xor": XorValue,
    "and": AndValue,
    "or": OrValue,
    "shl": ShlValue,
    "shr": ShrValue,
    "rcr": RcrValue,
    "rcl": RclValue,
    "ror": RorValue,
    "rol": RolValue,
    "imul": MulValue,
}
MATH_OP_UNARY_VALUE = {
    "inc": IncValue,
    "dec": DecValue,
    "not": NotValue,
    "neg": NegValue,
}

def merge_variables(var1, var2):
    var = Variable(var1.name)
    var.instructions = list(set(var1.instructions + var2.instructions))
    var.used_instructions = list(set(var1.used_instructions + var2.used_instructions))
    return var

class State(object):
    def __init__(self, copy_state=None, mode=None, fish=False):
        if copy_state:
            self.mode = copy_state.mode
            self.fish = copy_state.fish
            self.registers = dict(copy_state.registers)
            self.registers_variables = dict(copy_state.registers_variables)
            self.stack = list(copy_state.stack)
            self.stack_variables = list(copy_state.stack_variables)
            self.stack_instructions = list(copy_state.stack_instructions)
            self.flags = copy_state.flags
            self.has_flags = copy_state.has_flags
            self.handler = copy_state.handler
        else:
            self.mode = instruction.Arch(mode)
            self.fish = fish
            self.registers = {}
            self.registers_variables = {}
            for reg in self.mode.get_registers():
                if reg == self.mode.reg_native("sp"):
                    self.registers[reg] = SP()
                else:
                    self.registers[reg] = Register(reg)
                self.registers_variables[reg] = Variable(reg) # esp shouldn't be used from here
            self.stack = list()
            self.stack_variables = list()
            self.stack_instructions = list()
            self.flags = Invalid()
            self.has_flags = False
            self.handler = None

    def invalidate_diff(self, other):
        for k, v in self.registers.iteritems():
            # TODO is it the right condition?
            #if not v.equals(other.registers[k]) or self.registers_variables[k].instructions != other.registers_variables[k].instructions:
            if self.registers_variables[k] != other.registers_variables[k]:
                self.registers_variables[k] = merge_variables(self.registers_variables[k], other.registers_variables[k])
                self.registers[k] = self.registers_variables[k]
        assert len(self.stack) <= len(other.stack)
        for i in xrange(len(self.stack)):
            if self.stack_variables[i] != other.stack_variables[i]:
                self.stack_variables[i] = merge_variables(self.stack_variables[i], other.stack_variables[i])
                self.stack_instructions[i] += other.stack_instructions[i]
                self.stack[i] = self.stack_variables[i]
        self.has_flags = self.has_flags or other.has_flags
        if len(self.stack) != len(other.stack):
            # Hack for flags
            if self.has_flags and self.fish:
                assert len(self.stack) + 1 == len(other.stack)
                assert len(self.stack) == 0 or len(self.stack) == 1
                # I think that I don't want this becuse I don't want to make the condition visible
                # The whole instruction will be made visible (so it will be double visible)
                # Only full instructions should be made visible
                # TODO: Fix this in other cases (Push()..)
                #self.handler.make_visible(other.stack[-1])
                assert isinstance(other.stack[-1], FlagsOf) or isinstance(other.stack[-1], Variable)
                #other.stack_variables[-1].name = 1
                for i in other.stack_variables[-1].instructions:
                    if isinstance(i, SetValue) and isinstance(i.lvalue, Variable) and i.lvalue.name == "2":
                        i.lvalue.name = "1"
                if len(self.stack) == 0:
                    self.stack.append(other.stack_variables[0])
                    self.stack_variables.append(other.stack_variables[0])
                    self.stack_instructions.append(other.stack_instructions[0])
                else:
                    self.stack_variables[0] = merge_variables(self.stack_variables[0], other.stack_variables[1])
                    self.stack_instructions[0] += other.stack_instructions[1]
                    self.stack[0] = self.stack_variables[0]
            else:
                for insts in other.stack_instructions[len(self.stack):]:
                    for i in insts:
                        self.handler.make_visible(i)
        if not self.flags.equals(other.flags):
            self.flags = Invalid()

    def _get_full_register(self, reg):
        return self.mode.translate("{R:%s}" % reg)

    def get_register(self, reg):
        return self.registers[self._get_full_register(reg)]

    def set_register(self, reg, value):
        self.registers[self._get_full_register(reg)] = value

    def get_register_variable(self, reg):
        return self.registers_variables[self._get_full_register(reg)]

    def new_register_variable(self, reg):
        var =  Variable(self._get_full_register(reg))
        self.registers_variables[self._get_full_register(reg)] = var
        return var

class Handler(object):
    def __init__(self, function, fish=False):
        state = State(mode=function.mode, fish=fish)
        state.handler = self
        nstate, instructions = self._get_handler_block(function.start_block, state)
        state.invalidate_diff(nstate) # For push instructions taking effect
        self.instructions = instructions
        self.clean_instructions()
        self.optimize_instructions()
        self.clean_instructions()

    def get_instructions(self):
        return self.instructions

    def make_visible(self, instruction):
        if isinstance(instruction, NonVisible):
            if instruction.visible:
                return
            instruction.visible = True

        for inst in instruction.get_all_children():
            if isinstance(inst, Variable):
                if isinstance(instruction, SetValueOperation) and instruction.lvalue == inst:
                    continue
                for i in inst.instructions:
                    i.lvalue.used_instructions.append(instruction)
                    self.make_visible(i)

    def make_unvisible(self, instruction, recursive=False):
        if isinstance(instruction, NonVisible):
            if not instruction.visible:
                return
            instruction.visible = False

        for inst in instruction.get_all_children():
            if isinstance(inst, Variable):
                if isinstance(instruction, SetValueOperation) and instruction.lvalue == inst:
                    continue
                for i in inst.instructions:
                    i.lvalue.used_instructions.remove(instruction)
                    if len(i.lvalue.used_instructions) == 0:
                        self.make_unvisible(i)
        # Notice that it isn't the same behaviour as in make_visible, but that is how we are going to use it
        if recursive:
            if isinstance(instruction, ConditionBlock):
                for inst in instruction.instructions:
                    self.make_unvisible(inst, True)

    def _optimize_instructions(self, instructions, to_replace):
        # TODO: Because we don't do it in one run, we may miss some memory changes because we won't compare against
        # the real memory reference. II don't really care about that right now, because the only case when it happens
        # it at the end of the handler. So there isn't any reason that it will fail there.
        # But it is better to optimize it in one run because performance anyway.

        # This is an hack to do that:
        def extended_contain(x, y):
            # Check if x contains y or and address reference by x is included in y
            if x.contains(y):
                return True
            if isinstance(y, ValueOf) and isinstance(y.value, Variable) and len(y.value.instructions) == 1:
                if x.contains(y.value.instructions[0].rvalue):
                    return True

            if isinstance(y, ValueOf):
                for c in [x] + x.get_all_children():
                    if isinstance(c, ValueOf) and isinstance(c.value, Variable) and len(c.value.instructions) == 1:
                        c = c.value.instructions[0].rvalue
                        if isinstance(y.value, Variable) and len(y.value.instructions) == 1:
                            if c.contains(y.value.instructions[0].rvalue):
                                return True
                        elif c.contains(y.value):
                            return True

            return False

        changed = False
        for instruction in instructions:
            if isinstance(instruction, NonVisible):
                if not instruction.visible:
                    continue

            if instruction in to_replace:
                for inst in to_replace[instruction]:
                    if inst.lvalue not in instruction.get_all_children():
                        # It is a merged variable, so the usage count isn't really 1
                        continue
                    self.make_unvisible(instruction)
                    for c in [instruction] + instruction.get_all_children():
                        c.replace_child(inst.lvalue, inst.rvalue)
                    self.make_visible(instruction)
                    changed = True
                    # For debugging
                    # c = 0
                    # for insts in to_replace.itervalues():
                    #     if inst in insts:
                    #         c += 1
                    # if c == 1:
                    #     # If we replace all the instances of it, it should disappear
                    #     assert not inst.visible
                to_replace.pop(instruction)

            if isinstance(instruction, SetValueOperation):
                inst = None
                if isinstance(instruction.lvalue, Variable):
                    var = instruction.lvalue
                    assert instruction in var.instructions
                    if len(var.instructions) == 1 and (len(var.used_instructions) == 1) or type(instruction.rvalue) in (Variable, Immediate, Register):
                        for inst in var.used_instructions:
                            if inst not in to_replace:
                                to_replace[inst] = []
                            to_replace[inst].append(instruction)

                items_to_remove = set()
                for k, v in to_replace.iteritems():
                    if k != inst:
                        for i in v:
                            if extended_contain(i.rvalue, instruction.lvalue):
                                items_to_remove.add(k)
                for i in items_to_remove:
                    to_replace.pop(i)

            if isinstance(instruction, ConditionBlock):
                changed |= self._optimize_instructions(instruction.instructions, to_replace)
        return changed

    def optimize_instructions(self):
        while self._optimize_instructions(self.instructions, {}):
            pass

    def _get_handler_block(self, block, state, end = None, one_block = False):
        instructions = []
        state = State(state)
        def get_operand_value(op):
            if op.is_reg():
                return state.get_register(op.reg)
            elif op.is_immediate():
                return Immediate(op.value)
            elif op.is_memory():
                assert op.index is None and op.offset == 0 and op.scale == 0  # TODO (in case of unobfuscation)
                offset = state.get_register(op.base)
                return ValueOf(offset, op.size)
            return None

        def set_register_value(reg, value):
            op = SetValue(state.new_register_variable(reg), value)
            op.lvalue.instructions.append(op)
            #if not isinstance(value, Immediate) and not isinstance(value, Register):
            value = op.lvalue
            state.set_register(reg, value)
            instructions.append(op)

        def set_value(lvalue, value):
            if isinstance(lvalue, ValueOf) or type(lvalue) is SP:
                instructions.append(value)
                self.make_visible(value)

        new_block = True
        while new_block:
            new_block = False
            for inst in block.instructions:
                if inst.opcode in ("mov", "movzx", "movsx", "add", "sub", "xor", "and", "or", "shl", "shr", "rcl", "rcr", "rol", "ror", "imul", "inc", "dec", "not", "neg"):
                    state.flags = Invalid()
                    lvalue = get_operand_value(inst.operands[0])
                    if inst.opcode in ("inc", "dec", "not", "neg"):
                        value = lvalue
                    else:
                        value = get_operand_value(inst.operands[1])
                    if inst.operands[0].is_reg() and state.mode.reg_native(inst.operands[0].reg) != state.mode.reg_native("sp"):
                        if inst.opcode.startswith("mov"):
                            if inst.opcode =="movzx":
                                if inst.operands[1].is_reg():
                                    value = UnsignedConversion(value, inst.operands[1].size)
                            elif inst.opcode == "movsx":
                                assert inst.operands[1].is_reg()
                                value = SignedConversion(value, inst.operands[1].size)
                            else:
                                assert inst.opcode == "mov"
                        else:
                            if inst.opcode in MATH_OP:
                                op = MATH_OP[inst.opcode]
                                # TODO: line appear twice right now
                                # I duplicate the operation, so when optimizing it, optimizing the first line,
                                # won't optimize the second
                                state.flags = FlagsOf(op(lvalue, value))
                                value = op(lvalue, value)
                            else:
                                op = MATH_OP_UNARY[inst.opcode]
                                state.flags = FlagsOf(op(value))
                                value = op(value)
                        set_register_value(inst.operands[0].reg, value)
                    else:
                        if inst.opcode == "mov":
                            value = SetValue(lvalue, value)
                        else:
                            if inst.opcode in MATH_OP:
                                op = MATH_OP_VALUE[inst.opcode]
                                state.flags = FlagsOf(op(lvalue, value))
                                value = op(lvalue, value)
                            else:
                                op = MATH_OP_UNARY_VALUE[inst.opcode]
                                state.flags = FlagsOf(op(value))
                                value = op(value)
                        set_value(lvalue, value)
                elif inst.opcode == "jmp":
                    instructions.append(Jump(get_operand_value(inst.operands[0])))
                    self.make_visible(instructions[-1])
                    break
                elif inst.opcode in ("cmp", "test"):
                    value = get_operand_value(inst.operands[1])
                    lvalue = get_operand_value(inst.operands[0])
                    if inst.opcode == "cmp":
                        state.flags = FlagsOf(Cmp(lvalue, value))
                    elif inst.opcode == "test":
                        state.flags = FlagsOf(Test(lvalue, value))
                elif inst.opcode in ("jz", "jnz"):
                    # Determine if it is an If/Else or If
                    # If both have common block, than it is a. If one of the next blocks is the common block (or after an empty one), than it is a If.
                    # Else it is a If/Else
                    # Most of the time the condition link skip on the condition

                    next_block = instruction.get_common_block(block.next, block.next_cond)

                    if next_block is None:
                        # Hack for memcpy
                        if str(state.flags) == state.mode.translate("Flags(Compare(var_{R:cx}, 0x0))"):
                            if len(block.next.instructions) == 2 and \
                                            str(block.next.instructions[0]) == state.mode.translate("movs{SB}") and \
                                            (str(block.next.instructions[1]) == state.mode.translate("dec ecx") or \
                                             str(block.next.instructions[1]) == state.mode.translate("sub ecx, 0x1") or \
                                             str(block.next.instructions[1]) == state.mode.translate("add ecx, 0xffffffff")):
                                # This is actually rep movsd
                                instructions.append(MemCopy(state.get_register("di"),
                                                            state.get_register("si"),
                                                            state.get_register("cx")))
                                self.make_visible(instructions[-1])
                                block = block.next_cond
                                new_block = True
                                break

                    cond = None
                    if isinstance(state.flags.value, Cmp):
                        if inst.opcode == "jz":
                            cond = NotEqual(state.flags.value.lvalue, state.flags.value.rvalue)
                        elif inst.opcode == "jnz":
                            cond = Equal(state.flags.value.lvalue, state.flags.value.rvalue)
                        else:
                            assert False
                    elif isinstance(state.flags.value, And):
                        # TODO: it is litle bit hacked right now
                        assert isinstance(instructions[-1], SetValue)
                        reg_var = instructions[-1].lvalue
                        var = state.get_register(reg_var.name)
                        if inst.opcode == "jz":
                            cond = var
                        elif inst.opcode == "jnz":
                            cond = NotCond(var)
                        else:
                            assert False
                    else:
                        assert False # TODO others? for most of them should be same as for and

                    if one_block:
                        instructions.append(If(cond, []))
                        self.make_visible(instructions[-1])
                        break

                    assert next_block != block.next

                    if next_block == block.next_cond:
                        # Only if
                        new_state, new_instructions = self._get_handler_block(block.next, state, next_block)
                        instructions.append(If(cond, new_instructions))
                        self.make_visible(instructions[-1])
                        state.invalidate_diff(new_state)
                    else:
                        # If else
                        if_block = block.next
                        else_block = block.next_cond
                        if len(block.next_cond.froms) > 1:
                            # hack for Ors
                            if_block = block.next_cond
                            else_block = None
                            condition_blocks = []
                            b = block.next
                            while b != next_block:
                                assert b.next_cond == block.next_cond
                                condition_blocks.append(b)
                                b = b.next
                            assert len(block.next_cond.froms) == len(condition_blocks) + 1
                            cond = cond.invert()
                            for b in condition_blocks:
                                new_state, new_instructions = self._get_handler_block(b, state, one_block = True)
                                state.invalidate_diff(new_state)
                                assert len(new_instructions) == 1
                                assert isinstance(new_instructions[0], If)
                                cond = OrCond(cond, new_instructions[-1].value.invert())

                        state1, instructions1 = self._get_handler_block(if_block, state, next_block)
                        if else_block is not None:
                            state2, instructions2 = self._get_handler_block(else_block, state, next_block)
                        instructions.append(If(cond, instructions1))
                        self.make_visible(instructions[-1])
                        # TODO check for visible instructions
                        if else_block is not None:
                            if next_block is None:
                                # No else if not needed
                                instructions.extend(instructions2)
                                break
                            if len(instructions2) > 0:
                                instructions.append(Else(instructions2))
                            state2.invalidate_diff(state1)
                            # Update state
                            state = state2
                        else:
                            state.invalidate_diff(state1)
                    if next_block == end:
                        break
                    block = next_block
                    new_block = True
                    break
                elif inst.opcode in ("push", state.mode.translate("pushf{SB}")):
                    if inst.opcode == state.mode.translate("pushf{SB}"):
                        value = state.flags
                        state.has_flags = True
                        nop = Push(Flags())
                    else:
                        value = get_operand_value(inst.operands[0])
                        if inst.operands[0].size == state.mode.native_size():
                            nop = Push(value)
                        else:
                            nop = PushWord(value)

                    state.stack.append(value)
                    state.stack_variables.append(Variable(str(len(state.stack))))
                    state.stack_instructions.append([nop])
                    op = SetValue(state.stack_variables[-1], value)
                    op.lvalue.instructions.append(op)
                    instructions.append(op)
                    instructions.append(nop)
                elif inst.opcode in ("pop", state.mode.translate("popf{SB}")):
                    if len(state.stack) > 0:
                        # TODO: Maybe remove state.stack?
                        state.stack.pop()
                        value = state.stack_variables.pop()
                        state.stack_instructions.pop()
                        pop = False
                    else:
                        if inst.opcode == state.mode.translate("popf{SB}"):
                            value = Pop()
                        elif inst.operands[0].size == state.mode.native_size():
                            value = Pop()
                        else:
                            value = PopWord()
                        pop = True

                    if inst.opcode == "pop" and inst.operands[0].is_reg() and state.mode.reg_native(inst.operands[0].reg) != state.mode.reg_native("sp"):
                        assert inst.operands[0].size == state.mode.native_size()
                        if pop and block.instructions[-1].opcode == "ret":
                            instructions.append(SetValue(Register(inst.operands[0].reg), value))
                            self.make_visible(instructions[-1])
                            set_register_value(inst.operands[0].reg, Invalid())
                        else:
                            set_register_value(inst.operands[0].reg, value)
                    else:
                        if inst.opcode == state.mode.translate("popf{SB}"):
                            state.has_flags = True
                            lvalue = Flags()
                        else:
                            lvalue = get_operand_value(inst.operands[0])
                            if not pop:
                                assert inst.operands[0].size == state.mode.native_size()
                        value = SetValue(lvalue, value)
                        set_value(lvalue, value)
                elif inst.opcode == "ret":
                    if inst.operands[0] is not None:
                        val = inst.operands[0].value
                    else:
                        val = 0
                    instructions.append(Return(val))
                elif inst.opcode == "call":
                    return state, instructions
                elif inst.opcode == "std":
                    instructions.append(Std())
                elif inst.opcode == state.mode.translate("movs{SB}") and inst.prefix == "rep":
                    instructions.append(MemCopy(state.get_register("di"),
                                                state.get_register("si"),
                                                state.get_register("cx")))
                    self.make_visible(instructions[-1])
                else:
                    print inst
                    assert False
        return state, instructions

    def clean_instructions(self):
        self.instructions = self._clean_instructions(self.instructions)

    def _clean_instructions(self, instructions):
        for inst in instructions:
            if isinstance(inst, ConditionBlock):
                inst.instructions = self._clean_instructions(inst.instructions)
        return [x for x in instructions if not ((isinstance(x, NonVisible) and not x.visible) or (isinstance(x, Else) and len(x.instructions) == 0))]

    def print_instructions(self, instructions = None, pre=''):
        if instructions == None:
            instructions = self.instructions
        for inst in instructions:
            #if not isinstance(inst, NonVisible) or inst.visible:
            print pre + str(inst)
            if isinstance(inst, ConditionBlock):
                self.print_instructions(inst.instructions, pre + ' ' * 4)


