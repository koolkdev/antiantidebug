from collections import deque

class Invalid(object):
    def __repr__(self):
        return "Invalid"
    
class VMStruct(object):
    def __repr__(self):
        return "VMStruct"
        
class Immediate(object):
    def __init__(self, value):
        self.value = value
   
    def __repr__(self):
        return "0x%08X" % self.value

class ValueOf(object):
    def __init__(self, addr, size):
        self.addr = addr
        self.size = size
        
    def __repr__(self):
        if self.size == 1:
            s = "BYTE"
        if self.size == 2:
            s = "WORD"
        if self.size == 4:
            s = "DWORD"
        return "*(%s*)%s" % (s, repr(self.addr))
        
class SetValue(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        
    def __repr__(self):
        return "%s = %s" % (repr(self.a), repr(self.b))

class Add(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s+%s)" % (repr(self.a), repr(self.b))

class Sub(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s-%s)" % (repr(self.a), repr(self.b))

class Xor(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s^%s)" % (repr(self.a), repr(self.b))

class And(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s&%s)" % (repr(self.a), repr(self.b))

class Or(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s|%s)" % (repr(self.a), repr(self.b))

class Shl(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s<<%s)" % (repr(self.a), repr(self.b))

class Shr(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def __repr__(self):
        return "(%s>>%s)" % (repr(self.a), repr(self.b))

class Jump(object):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "JUMP(%s)" % (repr(self.value))
        
def get_handler(reader):
    instructions = []
    registers = {"eax": Invalid(),
                 "ecx": Invalid(),
                 "edx": Invalid(),
                 "ebx": Invalid(),
                 "ebp": VMStruct(),
                 "esi": Invalid(),
                 "edi": Invalid()}
    stack = deque()
    flags = Invalid()
    def get_operand_value(op):
        if op.is_reg():
            return registers[op.value]
        elif op.is_immediate():
            return Immediate(op.value)
        elif op.is_memory():
            assert op.index == None and op.displacement == 0 and op.scale == 0  # TODO (in case of unobfuscation)
            return ValueOf(registers[op.base], op.size)
        return None
    while True:
        opcode = reader.get()
        if opcode.opcode in ("mov", "movzx", "add", "sub", "xor", "and", "or","shl","shr"):
            value = get_operand_value(opcode.operand2)
            lvalue = get_operand_value(opcode.operand1)
            if opcode.opcode == "add":
                value = Add(lvalue, value)
            elif opcode.opcode == "sub":
                value = Sub(lvalue, value)
            elif opcode.opcode == "xor":
                value = Xor(lvalue, value)
            elif opcode.opcode == "and":
                value = And(lvalue, value)
            elif opcode.opcode == "and":
                value = Add(lvalue, value)
            elif opcode.opcode == "or":
                value = Or(lvalue, value)
            elif opcode.opcode == "shl":
                value = Shl(lvalue, value)
            elif opcode.opcode == "shr":
                value = Shr(lvalue, value)
                
            if opcode.operand1.is_reg():
                registers[opcode.operand1.value] = value
            elif opcode.operand1.is_memory():
                # TODO: check for changed values and move them to temporary variables instead
                assert opcode.operand1.index == None and opcode.operand1.displacement == 0 and opcode.operand1.scale == 0  # TODO (in case of unobfuscation)
                instructions.append(SetValue(lvalue, value))
        elif opcode.opcode == "jmp":
            instructions.append(Jump(get_operand_value(opcode.operand1)))
            break # TODO
        elif opcode.opcode == "cmp":
            pass  # TODO change flag
    return instructions
            
        
    