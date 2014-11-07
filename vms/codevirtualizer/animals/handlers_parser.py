from handlers_decompiler import *


class VMStructFieldOffset(UnaryExpression):
    def __str__(self):
        return "VMStructFieldOffset(%s)" % str(self.value)

class VMStructField(ValueOf):
    def __str__(self):
        if self.size == 1:
            s = "Byte"
        if self.size == 2:
            s = "Word"
        if self.size == 4:
            s = "Dword"
        return "VMStructField%s(%s)" % (s, str(self.value))

def vm_struct_field_offset(expression):
    if not isinstance(expression, Add):
        return None
    if type(expression.lvalue.get_value()) == VMStruct:
        return VMStructFieldOffset(expression.rvalue.get_value())
    if type(expression.rvalue.get_value()) == VMStruct:
        return VMStructFieldOffset(expression.lvalue.get_value())
    return None

def vm_struct_field(expression):
    if not isinstance(expression, ValueOf) or isinstance(expression, VMStructField):
        return None
    if isinstance(expression.value.get_value(), VMStructFieldOffset):
        return VMStructField(expression.value.get_value().value, expression.size)
    return None

expressions_simplifers = [
    vm_struct_field_offset,
    vm_struct_field
]

def simplify_expression(expression):
    changed = False
    for child in expression.get_children():
        for simplify in expressions_simplifers:
            nchild = simplify(child)
            if nchild:
                expression.replace_child(child, nchild)
                changed = True
    for child in expression.get_children():
        changed |= simplify_expression(child)
    return changed

def simplify_instructions(instructions):
    for instruction in instructions:
        while simplify_expression(instruction):
            pass
        if isinstance(instruction, ConditionBlock):
            simplify_instructions(instruction.instructions)


def parse_handler(handler):
    simplify_instructions(handler.get_instructions())



