from collections import deque
import instruction

class Expression(object):
    def __init__(self):
        pass

    def get_value(self):
        return self

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

    def get_format(self):
        return "{0}++"

class DecValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "--")

    def get_format(self):
        return "{0}--"

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

    def __str__(self):
        return "Else"

class Variable(Expression):
    def __init__(self, name):
        self.name = name
        self.instructions = []
        self.proxies = set()
        self.hidden_vars = []
        self.used_instructions = []
        self.visible_if_used = []

    def equals(self, other):
        return Expression.equals(self, other) and self.name== other.name

    def get_format(self):
        return "var_%s"  % self.name

class VariableProxy(UnaryExpression):
    def __init__(self, reg_var, value):
        UnaryExpression.__init__(self, value)
        self.reg_var = reg_var
        self.show_reg = False
        self.visible = False

    def get_value(self):
        if self.show_reg:
            return self.reg_var
        else:
            return self.value.get_value()

    #def get_children(self):
    #    return [self.get_value()]

    def equals(self, other):
        return self.get_value().equals(other.get_value())

    def __str__(self):
        return str(self.get_value())

class Esp(Expression):
    def get_format(self):
        return "ESP"

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

def merge_variables(var1, var2):
    var = Variable(var1.name)
    var.instructions = var1.instructions + var2.instructions
    var.proxies.update(var1.proxies)
    var.proxies.update(var2.proxies)
    var.hidden_vars = var1.hidden_vars + var2.hidden_vars
    var.used_instructions = var1.used_instructions + var2.used_instructions
    var.visible_if_used = var1.visible_if_used + var2.visible_if_used
    return var

class State(object):
    def __init__(self, copy_state = None):
        if copy_state:
            self.registers = dict(copy_state.registers)
            self.registers_variables = dict(copy_state.registers_variables)
            self.stack = list(copy_state.stack)
            self.stack_variables = list(copy_state.stack_variables)
            self.stack_instructions = list(copy_state.stack_instructions)
            self.flags = copy_state.flags
            self.has_flags = copy_state.has_flags
            self.handler = copy_state.handler
        else:
            self.registers = {"eax": Invalid(),
                             "ecx": Register("ecx"),
                             "edx": Register("edx"),
                             "ebx": Register("ebx"),
                             "ebp": Register("ebp"),
                             "esi": Register("esi"),
                             "edi": Register("edi"),
                             "esp": Esp()}
            self.registers_variables = {"eax": Variable("eax"),
                                                     "ecx": Variable("ecx"),
                                                     "edx": Variable("edx"),
                                                     "ebx": Variable("ebx"),
                                                     "ebp": Variable("ebp"),
                                                     "esi": Variable("esi"),
                                                     "edi": Variable("edi"),
                                                     "esp": Variable("esp")} # esp shouldn't be used from here
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
            if self.has_flags:
                assert len(self.stack) + 1 == len(other.stack)
                assert len(self.stack) == 0 or len(self.stack) == 1
                self.handler.make_visible(other.stack[-1])
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
        if instruction.REGS["REG_DWORD"].count(reg) > 0:
            return reg
        elif instruction.REGS["REG_WORD"].count(reg) > 0:
            return instruction.REGS["REG_DWORD"][instruction.REGS["REG_WORD"].index(reg)]
        elif instruction.REGS["REG_BYTE"].count(reg) > 0:
            index = instruction.REGS["REG_BYTE"].index(reg)
            if index >= 4: # 2nd byte, should not appear
                return None
            return instruction.REGS["REG_DWORD"][index]
        return None

    def get_register(self, reg):
        return VariableProxy(self.registers_variables[self._get_full_register(reg)], self.registers[self._get_full_register(reg)])

    def set_register(self, reg, value):
        self.registers[self._get_full_register(reg)] = value

    def get_register_variable(self, reg):
        return self.registers_variables[self._get_full_register(reg)]

    def new_register_variable(self, reg):
        var =  Variable(self._get_full_register(reg))
        self.registers_variables[self._get_full_register(reg)] = var
        return var

class Handler(object):
    def __init__(self, function):
        state = State()
        state.handler = self
        nstate, instructions = self._get_handler_block(function.start_block, state)
        state.invalidate_diff(nstate) # For push instructions taking effect
        self.instructions = instructions
        self.clean_instructions()

    def get_instructions(self):
         return self.instructions

    def make_visible(self, instruction):
        #if isinstance(instruction, SetValueOperation):
        #    def print_childs(inst, pad=''):
        #        print pad + str(inst) + ", " + repr(inst)
        #        for child in inst.get_children():
        #            print_childs(child, pad + '    ')
        #    print_childs(instruction)
        if isinstance(instruction, SetValueOperation):
            if isinstance(instruction.lvalue, Variable):
                for p in instruction.lvalue.proxies:
                    p.show_reg = True
        if isinstance(instruction, NonVisible):
            if instruction.visible:
                return # TODO fix loop
            instruction.visible = True
        if isinstance(instruction, SetValueOperation):
            if isinstance(instruction.lvalue, Variable):
                for var in instruction.lvalue.hidden_vars:
                    for i in var.instructions:
                        #self.make_visible(i)
                        assert isinstance(i.lvalue, Variable)
                        i.lvalue.visible_if_used.append(instruction)
                        for proxy in list(i.lvalue.proxies):
                            if proxy.visible and proxy.show_reg:
                                self.make_visible(proxy.reg_var)

        if isinstance(instruction, Variable):
            for i in instruction.instructions:
                self.make_visible(i)

        for inst in instruction.get_all_children():
            if isinstance(inst, VariableProxy):
                inst.visible = True
                inst.reg_var.proxies.update(set([inst]))
                if not isinstance(inst.value.get_value(), Variable):
                    if len(inst.reg_var.proxies) >= 2:
                        for i in list(inst.reg_var.proxies):
                            self.make_visible(i.reg_var) # In case it is linked to a different reg val
                    #elif len(inst.reg_var.proxies) > 2:
                    #    self.make_visible(inst.reg_var)
                for i in list(inst.reg_var.proxies):
                    if len(i.reg_var.visible_if_used) > 0:
                        self.make_visible(i.reg_var)

            if isinstance(inst, Variable):
                if isinstance(instruction, SetValueOperation) and instruction.lvalue == inst:
                    continue
                inst.used_instructions.append(instruction)
                self.make_visible(inst)

    def update_instruction(self, instruction):
        if isinstance(instruction, SetValueOperation) and isinstance(instruction.lvalue, Variable):
            # TODO: kinda hackish right now. Does it always work as expected?
            for proxy in instruction.lvalue.proxies:
                proxy.value = instruction.rvalue
            if len(instruction.lvalue.visible_if_used) or len(instruction.lvalue.proxies) >= 2 or len(instruction.lvalue.used_instructions):
                self.make_visible(instruction.lvalue)
            else:
                self.make_unvisible(instruction.lvalue)
        else:
            self.make_visible(instruction)


    def make_unvisible(self, instruction):
        if isinstance(instruction, SetValueOperation):
            if isinstance(instruction.lvalue, Variable):
                for p in instruction.lvalue.proxies:
                    p.show_reg = False
        if isinstance(instruction, NonVisible):
            if not instruction.visible:
                return
            instruction.visible = False
        if isinstance(instruction, SetValueOperation):
            if isinstance(instruction.lvalue, Variable):
                for var in instruction.lvalue.hidden_vars:
                    for i in var.instructions:
                        assert isinstance(i.lvalue, Variable)
                        i.lvalue.visible_if_used.remove(instruction)
                        if len(i.lvalue.visible_if_used) == 0:
                            for proxy in list(i.lvalue.proxies):
                                if proxy.visible and proxy.show_reg:
                                    self.make_unvisible(proxy.reg_var)

        if isinstance(instruction, Variable):
            for i in instruction.instructions:
                self.make_unvisible(i)

        for inst in instruction.get_all_children():
            if isinstance(inst, VariableProxy):
                if inst.visible:
                    inst.visible = False
                    inst.reg_var.proxies.remove(inst)
                for i in list(inst.reg_var.proxies):
                    if len(i.reg_var.visible_if_used) == 0 and len(i.reg_var.proxies) < 2 and len(i.reg_var.used_instructions) == 0:
                        self.make_unvisible(i.reg_var)

            if isinstance(inst, Variable):
                if isinstance(instruction, SetValueOperation) and instruction.lvalue == inst:
                    continue
                inst.used_instructions.remove(instruction)
                if len(inst.visible_if_used) == 0 and len(inst.proxies) < 2 and len(inst.used_instructions) == 0:
                    self.make_unvisible(inst)

    def _get_handler_block(self, block, state, end = None, one_block = False):
        instructions = []
        state = State(state)
        def get_operand_value(op):
            if op.is_reg():
                return state.get_register(op.value)
            elif op.is_immediate():
                return Immediate(op.value)
            elif op.is_memory():
                assert op.index == None and op.displacement == 0 and op.scale == 0  # TODO (in case of unobfuscation)
                offset = state.get_register(op.base)
                return ValueOf(offset, op.size)
            return None

        def set_register_value(reg, value):
            hidden_vars = []
            for k, v in state.registers.iteritems():
                if state._get_full_register(reg) != k and v.contains(state.get_register_variable(reg)):
                    hidden_vars.append(state.get_register_variable(k))
            state.set_register(reg, value)
            op = SetValue(state.new_register_variable(reg), value)
            op.lvalue.instructions.append(op)
            op.lvalue.hidden_vars = hidden_vars
            instructions.append(op)

        def set_value(lvalue, value):
            if isinstance(lvalue, ValueOf):
                for k, v in state.registers.iteritems():
                    if v.contains(lvalue):
                        state.registers[k] = state.get_register_variable(k)
                for i in xrange(len(state.stack)):
                    if state.stack[i].contains(lvalue):
                        state.stack[i] = state.stack_variables[i]
                instructions.append(value)
                self.make_visible(value)

        new_block = True
        while new_block:
            new_block = False
            for inst in block.instructions:
                if inst.opcode in ("mov", "movzx", "movsx", "add", "sub", "xor", "and", "or", "shl", "shr", "rcl", "rcr", "rol", "ror", "imul", "inc", "dec", "not", "neg"):
                    state.flags = Invalid()
                    lvalue = get_operand_value(inst.operand1)
                    if inst.opcode in ("inc", "dec", "not", "neg"):
                        value = lvalue
                    else:
                        value = get_operand_value(inst.operand2)
                    if inst.operand1.is_reg() and not inst.operand1.is_reg("esp"):
                        if inst.opcode == "add":
                            value = Add(lvalue, value)
                        elif inst.opcode == "sub":
                            value = Sub(lvalue, value)
                        elif inst.opcode == "xor":
                            value = Xor(lvalue, value)
                        elif inst.opcode == "and":
                            value = And(lvalue, value)
                        elif inst.opcode == "and":
                            value = Add(lvalue, value)
                        elif inst.opcode == "or":
                            value = Or(lvalue, value)
                        elif inst.opcode == "shl":
                            value = Shl(lvalue, value)
                        elif inst.opcode == "shr":
                            value = Shr(lvalue, value)
                        elif inst.opcode == "rcr":
                            value = Rcr(lvalue, value)
                        elif inst.opcode == "rcl":
                            value = Rcl(lvalue, value)
                        elif inst.opcode == "rol":
                            value = Rol(lvalue, value)
                        elif inst.opcode == "ror":
                            value = Ror(lvalue, value)
                        elif inst.opcode == "imul":
                            value = Mul(lvalue, value)
                        elif inst.opcode == "inc":
                            value = Inc(value)
                        elif inst.opcode == "dec":
                            value = Dec(value)
                        elif inst.opcode == "not":
                            value = Not(value)
                        elif inst.opcode == "neg":
                            value = Neg(value)
                        elif inst.opcode == "mov":
                            pass
                        elif inst.opcode =="movzx":
                            if inst.operand2.is_reg():
                                value = UnsignedConversion(value, inst.operand2.size)
                        elif inst.opcode == "movsx":
                            assert inst.operand2.is_reg()
                            value = SignedConversion(value, inst.operand2.size)
                        else:
                            assert False
                        if not inst.opcode.startswith("mov"):
                            # TODO: line appear twice right now
                            state.flags = FlagsOf(value)
                        set_register_value(inst.operand1.value, value)
                    else:
                        if inst.opcode == "add":
                            value = AddValue(lvalue, value)
                        elif inst.opcode == "sub":
                            value = SubValue(lvalue, value)
                        elif inst.opcode == "xor":
                            value = XorValue(lvalue, value)
                        elif inst.opcode == "and":
                            value = AndValue(lvalue, value)
                        elif inst.opcode == "and":
                            value = AddValue(lvalue, value)
                        elif inst.opcode == "or":
                            value = OrValue(lvalue, value)
                        elif inst.opcode == "shl":
                            value = ShlValue(lvalue, value)
                        elif inst.opcode == "shr":
                            value = ShrValue(lvalue, value)
                        elif inst.opcode == "rcr":
                            value = RcrValue(lvalue, value)
                        elif inst.opcode == "rcl":
                            value = RclValue(lvalue, value)
                        elif inst.opcode == "rol":
                            value = RolValue(lvalue, value)
                        elif inst.opcode == "ror":
                            value = RorValue(lvalue, value)
                        elif inst.opcode == "imul":
                            value = MulValue(lvalue, value)
                        elif inst.opcode == "inc":
                            value = IncValue(value)
                        elif inst.opcode == "dec":
                            value = DecValue(value)
                        elif inst.opcode == "not":
                            value = NotValue(value)
                        elif inst.opcode == "neg":
                            value = NegValue(value)
                        elif inst.opcode == "mov":
                            value = SetValue(lvalue, value)
                        else:
                            assert False
                        if not inst.opcode.startswith("mov"):
                            # TODO: line appear twice right now
                            state.flags = FlagsOf(value)
                        set_value(lvalue, value)
                elif inst.opcode == "jmp":
                    instructions.append(Jump(get_operand_value(inst.operand1)))
                    self.make_visible(instructions[-1])
                    break
                elif inst.opcode in ("cmp", "test"):
                    value = get_operand_value(inst.operand2)
                    lvalue = get_operand_value(inst.operand1)
                    if inst.opcode == "cmp":
                        state.flags = FlagsOf(Cmp(lvalue, value))
                    elif inst.opcode == "test":
                        state.flags = FlagsOf(Test(lvalue, value))
                elif inst.opcode in ("jz", "jnz"):
                    # Determine if it is an If/Else or If
                    # If both have common block, than it is a. If one of the next blocks is the common block (or after an empty one), than it is a If.
                    # Else it is a If/Else
                    # Most of the time the condition link skip on the condition
                    try:
                        next_block = instruction.get_common_block(block.next, block.next_cond)
                    except:
                        return state, instructions # TODO: loop
                    assert next_block != block.next
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

                    self.make_visible(cond)
                    if one_block:
                        instructions.append(If(cond, []))
                        break

                    if next_block == block.next_cond:
                        # Only if
                        new_state, new_instructions = self._get_handler_block(block.next, state, next_block)
                        instructions.append(If(cond, new_instructions))
                        state.invalidate_diff(new_state)
                    else:
                        # If else
                        if_block = block.next
                        else_block = block.next_cond
                        if len(block.next_cond.froms) > 1:
                            # hack for Ors
                            if_block = block.next_cond
                            condition_blocks = []
                            b = block.next
                            while b != next_block:
                                if b.next_cond == block.next_cond:
                                    condition_blocks.append(b)
                                else:
                                    assert b.next == next_block and b.next_cond is None
                                    else_block = b
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
                        state2, instructions2 = self._get_handler_block(else_block, state, next_block)
                        instructions.append(If(cond, instructions1))
                        # TODO check for visibile instructions
                        if len(instructions2) > 0:
                            instructions.append(Else(instructions2))
                        if next_block == None:
                            break
                        state2.invalidate_diff(state1)
                        # Update state
                        state = state2
                    if next_block == end:
                        break
                    block = next_block
                    new_block = True
                    break
                elif inst.opcode in ("push", "pushf"):
                    if inst.opcode == "pushf":
                        value = state.flags
                        state.has_flags = True
                        nop = Push(Flags())
                    else:
                        value = get_operand_value(inst.operand1)
                        if inst.operand1.size == 4:
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
                elif inst.opcode in ("pop", "popf"):
                    if len(state.stack) > 0:
                        value = state.stack.pop()
                        state.stack_variables.pop()
                        state.stack_instructions.pop()
                        pop = False
                    else:
                        if inst.operand1.size == 4:
                            value = Pop()
                        else:
                            value = PopWord()
                        pop = True

                    if inst.operand1.is_reg() and not inst.operand1.is_reg("esp"):
                        assert inst.operand1.size == 4
                        if pop:
                            instructions.append(SetValue(Register(inst.operand1.value), value))
                            self.make_visible(instructions[-1])
                            set_register_value(inst.operand1.value, Invalid())
                        else:
                            set_register_value(inst.operand1.value, value)
                    else:
                        if inst.opcode == "popf":
                            state.has_flags = True
                            lvalue = Flags()
                        else:
                            lvalue = get_operand_value(inst.operand1)
                            if not pop:
                                assert inst.operand1.size == 4
                        value = SetValue(lvalue, value)
                        set_value(lvalue, value)
                elif inst.opcode == "retn":
                    instructions.append(Return(inst.operand1.value))
                elif inst.opcode == "call":
                    return state, instructions
                elif inst.opcode == "std":
                    instructions.append(Std())
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
        return [x for x in instructions if not isinstance(x, NonVisible) or x.visible]

    def print_instructions(self, instructions = None, pre=''):
        if instructions == None:
            instructions = self.instructions
        for inst in instructions:
            #if not isinstance(inst, NonVisible) or inst.visible:
            print pre + str(inst)
            if isinstance(inst, ConditionBlock):
                self.print_instructions(inst.instructions, pre + ' ' * 4)


