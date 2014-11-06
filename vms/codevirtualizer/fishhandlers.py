from collections import deque
import instruction

class Expression(object):
    def __init__(self):
        pass

    def get_value(self):
        return self
        
    def get_childrens(self):
        return [self]

    def equals(self, expression):
        return type(self) == type(expression)
    
    def contains(self, expression):
        return self.equals(expression)
        
    def __repr__(self):
        return ""
            
class UnaryExpression(Expression):
    def __init__(self, value):
        self.value = value
        
    def get_childrens(self):
        return Expression.get_childrens(self) + self.value.get_childrens()
        
    def equals(self, expression):
        return Expression.equals(self, expression) and self.value.equals(expression.value)
        
    def contains(self, expression):
        return Expression.contains(self, expression) or self.value.contains(expression)

class UnaryOperationExpression(UnaryExpression):
    def __init__(self, value, op_str):
        UnaryExpression.__init__(self, value)
        self.op_str = op_str

    def __repr__(self):
        return "(%s%s)" % (self.op_str, repr(self.value))
            
class BinaryExpression(Expression):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue
        
    def get_childrens(self):
        return Expression.get_childrens(self) + self.lvalue.get_childrens() + self.rvalue.get_childrens()
        
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
        return Expression.equals(self, expression) and ((self.lvalue.equals(expression.lvalue) and self.rvalue.equals(expression.rvalue)) or (self.swappable and self.rvalue.equals(expression.lvalue) and self.lvalue.equals(expression.rvalue)))
        
    def __repr__(self):
        return "(%s %s %s)" % (repr(self.lvalue), self.op_str, repr(self.rvalue))

class Invalid(Expression):
    def __repr__(self):
        return "Invalid"
        
class Immediate(Expression):   
    def __init__(self, value):
        self.value = value
        
    def equals(self, expression):
        return Expression.equals(self, expression) and self.value == expression.value
        
    def __repr__(self):
        return "0x%X" % self.value

class ValueOf(UnaryExpression):
    def __init__(self, value, size):
        UnaryExpression.__init__(self, value)
        self.size = size
        
    def equals(self, expression):
        return UnaryExpression.equals(self, expression) and self.size == expression.size
        
    def __repr__(self):
        if self.size == 1:
            s = "BYTE"
        if self.size == 2:
            s = "WORD"
        if self.size == 4:
            s = "DWORD"
        return "*(%s*)%s" % (s, repr(self.value))
        
class NonVisible(object):
    def __init__(self):
        self.visible = False

class SetValueOperation(BinaryExpression, NonVisible):
    def __init__(self, lvalue, rvalue, op_str):
        BinaryExpression.__init__(self, lvalue, rvalue)
        NonVisible.__init__(self)
        self.op_str = op_str
        
    def __repr__(self):
        return "%s %s= %s" % (repr(self.lvalue), self.op_str, repr(self.rvalue))
        
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

    def __repr__(self):
        return "%s = %s%s" % (repr(self.lvalue), self.op_str, repr(self.rvalue))

class NotValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "~")

class NegValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "-")

class IncValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "++")

    def __repr__(self):
        return "%s++" % repr(self.lvalue)

class DecValue(SetValueUnaryOperation):
    def __init__(self, value):
        SetValueUnaryOperation.__init__(self, value, "--")

    def __repr__(self):
        return "%s--" % repr(self.lvalue)
    
class VMStruct(Expression):
    def __repr__(self):
        return "VMStruct"
        
class VMStructFieldOffset(UnaryExpression):   
    def __repr__(self):
        return "VMStructFieldOffset(%s)" % repr(self.value)
        
class VMStructField(ValueOf):   
    def __repr__(self):
        if self.size == 1:
            s = "Byte"
        if self.size == 2:
            s = "Word"
        if self.size == 4:
            s = "Dword"
        return "VMStructField%s(%s)" % (s, repr(self.value))

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
        
    def __repr__(self):
        return "%s(%s, %s)" % (self.op_str, repr(self.lvalue), repr(self.rvalue))

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
    def __repr__(self):
        return "JUMP(%s)" % (repr(self.value))
        
class ConditionBlock(UnaryExpression):
    def __init__(self, value, instructions):
        self.value = value
        self.instructions = instructions

class If(ConditionBlock):
    def __repr__(self):
        return "If(%s)" % (repr(self.value))

class Else(ConditionBlock):
    def __init__(self, instructions):
        ConditionBlock.__init__(self, None, instructions)
        
    def __repr__(self):
        return "Else"
        
class Variable(Expression):
    def __init__(self, name):
        self.name = name
        self.instructions = []
        self.proxies = set()
        self.hidden_vars = []
        self.visible_if_used = False

    def equals(self, other):
        return Expression.equals(self, other) and self.name== other.name

    def __repr__(self):
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

    def equals(self, other):
        return self.get_value().equals(other.get_value())

    def __repr__(self):
        return repr(self.get_value())

class Esp(Expression):
    def __repr__(self):
        return "ESP"

class Flags(Expression):
    def __repr__(self):
        return "flags"

class FlagsOf(UnaryExpression):
    def __repr__(self):
        return "Flags(%s)" % repr(self.value)

class Register(Expression):
    def __init__(self, value):
        self.value = value

    def equals(self, other):
        return Expression.equals(self, other) and self.value == other.value

    def __repr__(self):
        return "%s" % self.value

class Pop(Expression):
    def __repr__(self):
        return "Pop()"

class PopWord(Expression):
    def __repr__(self):
        return "PopWord()"

class Push(UnaryExpression, NonVisible):
    def __init__(self, value):
        UnaryExpression.__init__(self, value)
        NonVisible.__init__(self)

    def __repr__(self):
        return "Push(%s)" % repr(self.value)

class PushWord(UnaryExpression, NonVisible):
    def __init__(self, value):
        UnaryExpression.__init__(self, value)
        NonVisible.__init__(self)

    def __repr__(self):
        return "PushWord(%s)" % repr(self.value)

class Return(Expression):
    def __init__(self, value):
        self.value = value

    def equals(self, other):
        return Expression.equals(self, other) and self.value == other.value

    def __repr__(self):
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

    def __repr__(self):
        return "(%s)%s" % (self._get_size_name(), repr(self.value))

class UnsignedConversion(Conversion):
    pass

class SignedConversion(Conversion):
    def __repr__(self):
        return "(S%s)%s" % (self._get_size_name(), repr(self.value))

class Std(Expression):
    def __repr__(self):
        return "Std()"
        
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
        else:
            self.registers = {"eax": Invalid(),
                             "ecx": Invalid(),
                             "edx": Invalid(),
                             "ebx": Invalid(),
                             "ebp": VMStruct(),
                             "esi": Invalid(),
                             "edi": Invalid(),
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

    def invalidate_diff(self, other):
        for k, v in self.registers.iteritems():
            # TODO is it the right condition?
            #if not v.equals(other.registers[k]) or self.registers_variables[k].instructions != other.registers_variables[k].instructions:
            if self.registers_variables[k] != other.registers_variables[k]:
                self.registers_variables[k].instructions += other.registers_variables[k].instructions
                self.registers_variables[k].proxies.update(other.registers_variables[k].proxies)
                self.registers_variables[k].hidden_vars += other.registers_variables[k].hidden_vars
                self.registers[k] = self.registers_variables[k]
        assert len(self.stack) <= len(other.stack)
        for i in xrange(len(self.stack)):
            if self.stack_variables[i] != other.stack_variables[i]:
                self.stack_variables[i].instructions += other.stack_variables[i].instructions
                self.stack_variables[i].proxies.update(other.stack_variables[i].proxies)
                self.stack_variables[i].hidden_vars += other.stack_variables[i].hidden_vars
                self.stack_instructions[i] += other.stack_instructions[i]
                self.stack[i] = self.stack_variables[i]
        self.has_flags = self.has_flags or other.has_flags
        if len(self.stack) != len(other.stack):
            # Hack for flags
            if self.has_flags:
                assert len(self.stack) + 1 == len(other.stack)
                assert len(self.stack) == 0 or len(self.stack) == 1
                self.make_visible(other.stack[-1])
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
                    self.stack_variables[0].instructions += other.stack_variables[1].instructions
                    self.stack_variables[0].proxies.update(other.stack_variables[1].proxies)
                    self.stack_variables[0].hidden_vars += other.stack_variables[1].hidden_vars
                    self.stack_instructions[0] += other.stack_instructions[1]
                    self.stack[0] = self.stack_variables[0]
            else:
                for insts in other.stack_instructions[len(self.stack):]:
                    for i in insts:
                        self.make_visible(i)
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

    def make_visible(self, instruction):
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
                        i.lvalue.visible_if_used = True
                        for proxy in list(i.lvalue.proxies):
                            if proxy.visible:
                                self.make_visible(proxy.reg_var)

        for inst in instruction.get_childrens():
            if isinstance(inst, VariableProxy):
                inst.visible = True
                inst.reg_var.proxies.update(set([inst]))
                if not isinstance(inst.value.get_value(), Variable):
                    if len(inst.reg_var.proxies) == 2:
                        for i in list(inst.reg_var.proxies):
                            self.make_visible(i.reg_var) # In case it is linked to a different reg val
                    elif len(inst.reg_var.proxies) > 2:
                        self.make_visible(inst.reg_var)
                for i in list(inst.reg_var.proxies):
                    if i.reg_var.visible_if_used:
                        self.make_visible(i.reg_var)

            if isinstance(inst, Variable):
                for i in inst.instructions:
                    self.make_visible(i)


def get_handler(function):
    state = State()
    nstate, instructions = get_handler_block(function.start_block, state)
    state.invalidate_diff(nstate) # For push instructions taking effect
    return instructions
            
def get_handler_block(block, state, end = None, one_block = False):
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
            if isinstance(offset.get_value(), VMStructFieldOffset):
                return VMStructField(offset.get_value().value, op.size)
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
            state.make_visible(value)

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
                        if type(lvalue.get_value()) == VMStruct:
                            value = VMStructFieldOffset(value.get_value())
                        elif type(value.get_value()) == VMStruct:
                            value = VMStructFieldOffset(lvalue.get_value())
                        else:
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
                state.make_visible(instructions[-1])
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

                state.make_visible(cond)
                if one_block:
                    instructions.append(If(cond, []))
                    break

                if next_block == block.next_cond:
                    # Only if
                    new_state, new_instructions = get_handler_block(block.next, state, next_block)
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
                            new_state, new_instructions = get_handler_block(b, state, one_block = True)
                            state.invalidate_diff(new_state)
                            assert len(new_instructions) == 1
                            assert isinstance(new_instructions[0], If)
                            cond = OrCond(cond, new_instructions[-1].value.invert())

                    state1, instructions1 = get_handler_block(if_block, state, next_block)
                    state2, instructions2 = get_handler_block(else_block, state, next_block)
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
                        state.make_visible(instructions[-1])
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
    
def print_instructions(instructions, pre=''):
    for inst in instructions:
        if not isinstance(inst, NonVisible) or inst.visible:
            print pre + repr(inst)
        if isinstance(inst, ConditionBlock):
            print_instructions(inst.instructions, pre + ' ' * 4)
        
    