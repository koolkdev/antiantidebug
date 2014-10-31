from collections import deque

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
    def __init__(self, lvalue, rvalue, op_str):
        BinaryExpression.__init__(self, lvalue, rvalue)
        self.op_str = op_str
        
    def equals(self, expression):
        return Expression.equals(self, expression) and ((lvalue.equals(expression.lvalue) and rvalue.equals(expression.rvalue)) or (rvalue.equals(expression.lvalue) and lvalue.equals(expression.rvalue)))
        
    def __repr__(self):
        return "(%s%s%s)" % (repr(self.lvalue), self.op_str, repr(self.rvalue))

class Invalid(Expression):
    def __repr__(self):
        return "Invalid"
    
class VMStruct(Expression):
    def __repr__(self):
        return "VMStruct"
        
class VMStructField(UnaryExpression):   
    def __repr__(self):
        return "VMStructField(%s)" % repr(self.value)
        
class Immediate(Expression):   
    def __init__(self, value):
        self.value = value
        
    def equals(self, expression):
        return Expression.equals(self, expression) and self.value == expression.value
        
    def __repr__(self):
        return "0x%08X" % self.value

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
        
class SetValue(BinaryExpression):        
    def __repr__(self):
        return "%s = %s" % (repr(self.lvalue), repr(self.rvalue))

class Add(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "+")

class Sub(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "-")

class Xor(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "^")

class And(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "&")

class Or(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "|")

class Shl(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, "<<")

class Shr(BinaryOperationExpression):
    def __init__(self, lvalue, rvalue):
        BinaryOperationExpression.__init__(self, lvalue, rvalue, ">>")

class Jump(UnaryExpression):
    def __repr__(self):
        return "JUMP(%s)" % (repr(self.value))
        
class Variable(UnaryExpression):
    def __init__(self, name, value):
        UnaryExpression.__init__(self, value)
        self.name = name
        
    def __repr__(self):
        return "%s" % self.name
        
def get_handler(reader):
    instructions = []
    registers = {"eax": Invalid(),
                 "ecx": Invalid(),
                 "edx": Invalid(),
                 "ebx": Invalid(),
                 "ebp": VMStruct(),
                 "esi": Invalid(),
                 "edi": Invalid()}
    vars = {}
    vars_index = 1
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
                if type(lvalue) == VMStruct:
                    value = VMStructField(value)
                elif type(value) == VMStruct:
                    value = VMStructField(lvalue)
                else:
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
                if isinstance(lvalue, ValueOf):                    
                    for k, v in registers.iteritems():
                        if v.contains(lvalue):
                            var = Variable("v%d" % vars_index, v)
                            registers[k] = var
                            vars_index += 1
                            instructions.append(SetValue(var, v))
                instructions.append(SetValue(lvalue, value))
        elif opcode.opcode == "jmp":
            instructions.append(Jump(get_operand_value(opcode.operand1)))
            break # TODO
        elif opcode.opcode == "cmp":
            pass  # TODO change flag
    return instructions
            
        
    