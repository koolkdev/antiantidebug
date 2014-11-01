from collections import deque
import instruction

class Expression(object):
    def __init__(self):
        pass
        
    def equals(self, expression):
        return type(self) == type(expression)
    
    def contains(self, expression):
        return self.equals(expression)
        
    def __repr__(self):
        return ""
            
class UnaryExpression(Expression):
    def __init__(self, value):
        self.value = value
        
    def equals(self, expression):
        return Expression.equals(self, expression) and self.value.equals(expression.value)
        
    def contains(self, expression):
        return Expression.contains(self, expression) or self.value.contains(expression)
            
class BinaryExpression(Expression):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue
        
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
        
class Variable(UnaryExpression):
    def __init__(self, name, value):
        UnaryExpression.__init__(self, value)
        self.name = name
        
    def __repr__(self):
        return "%s" % self.name
        
class PushFlags(Expression):
    def __repr__(self):
        return "PushFlags"
        
class State(object):
    def __init__(self, copy_state = None):
        if copy_state:
            self.registers = dict(copy_state.registers)
            self.vars = dict(copy_state.vars)
            self.vars_index = copy_state.vars_index
            self.stack = deque(copy_state.stack)
            self.flags = copy_state.flags
        else:
            self.registers = {"eax": Invalid(),
                             "ecx": Invalid(),
                             "edx": Invalid(),
                             "ebx": Invalid(),
                             "ebp": VMStruct(),
                             "esi": Invalid(),
                             "edi": Invalid()}
            self.vars = {}
            self.vars_index = 1
            self.stack = deque()
            self.flags = Invalid()
    def invalidate_diff(self, other):
        for k, v in self.registers.iteritems():
            if not v.equals(other.registers[k]):
                self.registers[k] = Invalid()
            # TODO vars
            # TODO stack
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
        return self.registers[self._get_full_register(reg)]
        
    def set_register(self, reg, value):
        self.registers[self._get_full_register(reg)] = value
                
            
def get_handler(function):
    return get_handler_block(function.start_block, State())[1]
    #return instructions
            
        
        
def get_handler_block(block, state):
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
            if isinstance(offset, VMStructFieldOffset):
                return VMStructField(offset.value, op.size)
            return ValueOf(offset, op.size)
        return None
      
    new_block = True
    while new_block:
        new_block = False
        for inst in block.instructions:
            if inst.opcode in ("mov", "movzx", "add", "sub", "xor", "and", "or", "shl", "shr"):
                flags = None
                value = get_operand_value(inst.operand2)
                lvalue = get_operand_value(inst.operand1)
                if inst.operand1.is_reg():
                    if inst.opcode == "add":
                        if type(lvalue) == VMStruct:
                            value = VMStructFieldOffset(value)
                        elif type(value) == VMStruct:
                            value = VMStructFieldOffset(lvalue)
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
                    state.set_register(inst.operand1.value, value)
                elif inst.operand1.is_memory():
                    # TODO: check for changed values and move them to temporary variables instead
                    assert inst.operand1.index == None and inst.operand1.displacement == 0 and inst.operand1.scale == 0  # TODO (in case of unobfuscation)
                    if isinstance(lvalue, ValueOf):                    
                        for k, v in state.registers.iteritems():
                            if v.contains(lvalue):
                                var = Variable("v%d" % state.vars_index, v)
                                state.registers[k] = var
                                state.vars_index += 1
                                instructions.append(SetValue(var, v))
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
                    instructions.append(value)
                else:
                    assert False
            elif inst.opcode == "jmp":
                instructions.append(Jump(get_operand_value(inst.operand1)))
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
                if next_block == block.next_cond:
                    # Only if
                    new_state, new_instructions = get_handler_block(block.next, state)
                    instructions.append(If(cond, new_instructions))
                    state.invalidate_diff(new_state)
                else:
                    # If else
                    state1, instructions1 = get_handler_block(block.next, state)
                    state2, instructions2 = get_handler_block(block.next_cond, state)
                    instructions.append(If(cond, instructions1))
                    instructions.append(Else(instructions2))
                    if next_block == None:
                        break
                    state2.invalidate_diff(state1)
                    # Update state
                    state = state2
                block = next_block                
                new_block = True
                break
    return state, instructions
    
def print_instructions(instructions, pre=''):
    for inst in instructions:
        print pre + repr(inst)
        if isinstance(inst, ConditionBlock):
            print_instructions(inst.instructions, pre + ' ' * 4)
        
    