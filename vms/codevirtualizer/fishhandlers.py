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
        
class SetValueOperation(BinaryExpression):        
    def __init__(self, lvalue, rvalue, op_str):
        BinaryExpression.__init__(self, lvalue, rvalue)
        self.op_str = op_str
        self.visible = False
        
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

class Equal(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "==")

class NotEqual(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "!=")

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

    def equals(self, other):
        return Expression.equals(self, other) and self.name== other.name

    def __repr__(self):
        return "var_%s"  % self.name

class VariableProxy(UnaryExpression):
    def __init__(self, reg_var, value):
        UnaryExpression.__init__(self, value)
        self.reg_var = reg_var
        self.show_reg = False

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

class Return(Expression):
    def __init__(self, value):
        self.value = value

    def equals(self, other):
        return Expression.equals(self, other) and self.value == other.value

    def __repr__(self):
        return "Return(%x)" % self.value
        
class State(object):
    def __init__(self, copy_state = None):
        if copy_state:
            self.registers = dict(copy_state.registers)
            self.registers_variables = dict(copy_state.registers_variables)
            self.stack = list(copy_state.stack)
            self.stack_variables = list(copy_state.stack_variables)
            self.flags = copy_state.flags
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
            self.flags = Invalid()

    def invalidate_diff(self, other):
        for k, v in self.registers.iteritems():
            # TODO is it the right condition?
            #if not v.equals(other.registers[k]) or self.registers_variables[k].instructions != other.registers_variables[k].instructions:
            if self.registers_variables[k] != other.registers_variables[k]:
                self.registers_variables[k].instructions += other.registers_variables[k].instructions
                self.registers_variables[k].proxies.update(other.registers_variables[k].proxies)
                self.registers_variables[k].hidden_vars += other.registers_variables[k].hidden_vars
                self.registers[k] = self.registers_variables[k]
            # TODO vars
            assert len(self.stack) <= len(other.stack)
            for i in xrange(len(self.stack)):
                if self.stack_variables[i] != other.stack_variables[i]:
                    self.stack_variables[i].instructions += other.stack_variables[i].instructions
                    self.stack_variables[i].proxies.update(other.stack_variables[i].proxies)
                    self.stack_variables[i].hidden_vars += other.stack_variables[i].hidden_vars
                if len(self.stack) != len(other.stack):
                    # TODO
                    pass
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
            if instruction.visible:
                return # TODO fix loop
            instruction.visible = True
            if isinstance(instruction.lvalue, Variable):
                for var in instruction.lvalue.hidden_vars:
                    for i in var.instructions:
                        self.make_visible(i)
        for inst in instruction.get_childrens():
            if isinstance(inst, VariableProxy) and not isinstance(inst.value.get_value(), Variable):
                inst.reg_var.proxies.update(set([inst]))
                if len(inst.reg_var.proxies) == 2:
                    for i in list(inst.reg_var.proxies):
                        self.make_visible(i.reg_var) # In case it is linked to a different reg val
                elif len(inst.reg_var.proxies) > 2:
                    self.make_visible(inst.reg_var)
            if isinstance(inst, Variable):
                for i in inst.instructions:
                    self.make_visible(i)


def get_handler(function):
    state, instructions = get_handler_block(function.start_block, State())
    return instructions
            
def get_handler_block(block, state, end = None):
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
            if v.contains(state.get_register_variable(reg)):
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
            if inst.opcode in ("mov", "movzx", "add", "sub", "xor", "and", "or", "shl", "shr"):
                flags = None
                value = get_operand_value(inst.operand2)
                lvalue = get_operand_value(inst.operand1)
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
                    elif inst.opcode.startswith("mov"):
                        pass
                    else:
                        assert False
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
                    elif inst.opcode.startswith("mov"):
                        value = SetValue(lvalue, value)
                    else:
                        assert False
                    set_value(lvalue, value)
            elif inst.opcode == "jmp":
                instructions.append(Jump(get_operand_value(inst.operand1)))
                state.make_visible(instructions[-1])
                break
            elif inst.opcode in ("cmp", "test"):
                value = get_operand_value(inst.operand2)
                lvalue = get_operand_value(inst.operand1)
                if inst.opcode == "cmp":
                    state.flags = Cmp(lvalue, value)
                elif inst.opcode == "test":
                    state.flags = Test(lvalue, value)
            elif inst.opcode in ("jz", "jnz"):
                # Determine if it is an If/Else or If
                # If both have common block, than it is a. If one of the next blocks is the common block (or after an empty one), than it is a If.
                # Else it is a If/Else
                # Most of the time the condition link skip on the condition
                next_block = instruction.get_common_block(block.next, block.next_cond) 
                assert next_block != block.next
                cond = None
                if isinstance(state.flags, Cmp):
                    if inst.opcode == "jz":
                        cond = NotEqual(state.flags.lvalue, state.flags.rvalue)
                    elif inst.opcode == "jnz":
                        cond = Equal(state.flags.lvalue, state.flags.rvalue)
                    else:
                        assert False                    
                else:
                    assert False # TODO others?
                state.make_visible(cond)
                if next_block == block.next_cond:
                    # Only if
                    new_state, new_instructions = get_handler_block(block.next, state, next_block)
                    instructions.append(If(cond, new_instructions))
                    state.invalidate_diff(new_state)
                else:
                    # If else
                    state1, instructions1 = get_handler_block(block.next, state, next_block)
                    state2, instructions2 = get_handler_block(block.next_cond, state, next_block)
                    instructions.append(If(cond, instructions1))
                    instructions.append(Else(instructions2))
                    if next_block == None or next_block == end:
                        break
                    state2.invalidate_diff(state1)
                    # Update state
                    state = state2
                if next_block == None or next_block == end:
                    break
                block = next_block                
                new_block = True
                break
            elif inst.opcode in ("push", "pushf"):
                if inst.opcode == "pushf":
                    value = state.flags
                else:
                    value = get_operand_value(inst.operand1)
                    assert inst.operand1.size == 4
                state.stack.append(value)
                state.stack_variables.append(Variable(str(len(state.stack))))
                op = SetValue(state.stack_variables[-1], value)
                op.lvalue.instructions.append(op)
                instructions.append(op)
            elif inst.opcode in ("pop", "popf"):
                if len(state.stack) > 0:
                    value = state.stack.pop()
                    state.stack_variables.pop()
                    pop = False
                else:
                    value = Pop()
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
                        lvalue = Flags()
                    else:
                        lvalue = get_operand_value(inst.operand1)
                        assert inst.operand1.size == 4
                    value = SetValue(lvalue, value)
                    set_value(lvalue, value)
            elif inst.opcode == "retn":
                instructions.append(Return(inst.operand1.value))
            elif inst.opcode == "call":
                return state, instructions 
            else:
                print inst
                assert False
    return state, instructions
    
def print_instructions(instructions, pre=''):
    for inst in instructions:
        if not isinstance(inst, SetValueOperation) or inst.visible:
            print pre + repr(inst)
        if isinstance(inst, ConditionBlock):
            print_instructions(inst.instructions, pre + ' ' * 4)
        
    