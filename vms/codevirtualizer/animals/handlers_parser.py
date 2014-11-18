from handlers_decompiler import *
import fish_handlers
import re

GROUPS = {
    "SIMPLE_MATH": ["+", "-", "^"],
    "UPDATE_MATH": ["+", "-", "^", "&", "|"],
    "READ_PARAMETER": ["ReadParameterByte", "ReadParameterWord", "ReadParameterDword"],
    "STRUCT_FIELD": ["VMStructFieldByte", "VMStructFieldWord", "VMStructFieldDword"],
}

EXPRESSIONS_MACROS = [
    (
        "(ebp + &X)",
        "VMStructOffset(&X)"
    ),
    (
        "(&X + ebp)",
        "VMStructOffset(&X)"
    ),
    (
        "*(BYTE*)VMStructOffset(&X)",
        "VMStructFieldByte(&X)"
    ),
    (
        "*(WORD*)VMStructOffset(&X)",
        "VMStructFieldWord(&X)"
    ),
    (
        "*(DWORD*)VMStructOffset(&X)",
        "VMStructFieldDword(&X)"
    ),
    (
        "*(BYTE*)(VMStructFieldDword(@EIP) + &X)",
        "ReadParameterByte(&X, DecodingInfo(None, None, None, None, None, None, None, None, None))"
    ),
    (
        "*(WORD*)(VMStructFieldDword(@EIP) + &X)",
        "ReadParameterWord(&X, DecodingInfo(None, None, None, None, None, None, None, None, None))"
    ),
    (
        "*(DWORD*)(VMStructFieldDword(@EIP) + &X)",
        "ReadParameterDword(&X, DecodingInfo(None, None, None, None, None, None, None, None, None))"
    ),

    (
        "(!READ_PARAMETER_1(^IMM_1, DecodingInfo(None, None, None, None, None, None, None, None, None)) !SIMPLE_MATH_1 VMStructFieldDword(@KEY1))",
        "!READ_PARAMETER_1(^IMM_1, DecodingInfo(Operation(!SIMPLE_MATH_1), None, None, None, None, None, None, None, None))"
    ),
    (
        "(!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, None, None, None, None, None, None, None, None)) !SIMPLE_MATH_1 VMStructFieldDword(@KEY2))",
        "!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, Operation(!SIMPLE_MATH_1), None, None, None, None, None, None, None))"
    ),
    (
        "(!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, None, None, None, None, None, None, None)) !SIMPLE_MATH_1 VMStructFieldDword(@KEY6))",
        "!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, None, Operation(!SIMPLE_MATH_1), None, None, None, None, None))"
    ),
    (
        "(!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, None, None, None, None, None, None, None, None)) !SIMPLE_MATH_1 VMStructFieldDword(@KEY4))",
        "!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, None, Operation(!SIMPLE_MATH_1), None, None, None, None, None, None))"
    ),
    (
        "(!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, None, None, None, None, None, None, None, None)) !SIMPLE_MATH_1 ^IMM_2)",
        "!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, None, None, None, SimpleOperation(Operation(!SIMPLE_MATH_1), ^IMM_2), None, None, None, None))"
    ),
    (
        "(!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, &X6, &X7, None, None)) !SIMPLE_MATH_1 VMStructFieldDword(@KEY3))",
        "!READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, &X6, &X7, Operation(!SIMPLE_MATH_1), None))"
    ),
    (
        "((&X1 & 0xF0) >> 0x4)",
        "HIGH_NIBBLE(&X1)"
    ),
    (
        "(&X1 & 0xF)",
        "LOW_NIBBLE(&X1)"
    )
]

MACROS = [
    (
        [
        "^VAR_1 = !READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, None, None, None, None))",
        "VMStructFieldDword(@KEY1) !UPDATE_MATH_1= ^VAR_1"
        ],
        "^VAR_1 = !READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, Operation(!UPDATE_MATH_1), None, None, None))"
    ),
    (
        ["VMStructFieldDword(@KEY*) !UPDATE_MATH_1= ^IMM_2"],
        "UpdateKey(VMStructFieldDword(@KEY*), SimpleOperation(Operation(!UPDATE_MATH_1), ^IMM_2))"
    ),
    (
        [
        "^VAR_1 = !READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, &X6, None, None, None))",
        "UpdateKey(VMStructFieldDword(@KEY2), &Y1)",
        ],
        "^VAR_1 = !READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, &X6, &Y1, None, None))"
    ),
    (
        [
        "^VAR_1 = !READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, &X6, &X7, &X8, None))",
        "UpdateKey(VMStructFieldDword(@KEY3), &Y1)",
        ],
        "^VAR_1 = !READ_PARAMETER_1(^IMM_1, DecodingInfo(&X1, &X2, &X3, &X4, &X5, &X6, &X7, &X8, &Y1))"
    ),
    (
        ["!STRUCT_FIELD_1($ENCODED_VALUE_) = (&X1 !SIMPLE_MATH_1 ^IMM_1)"],
        "!STRUCT_FIELD_1($ENCODED_VALUE_) = EncodedValue(&X1, SimpleOperation(Operation(!SIMPLE_MATH_1), ^IMM_1), None)"
    ),
    (
        ["VMStructFieldDword($ENCODED_VALUE_) = ((&X1 !SIMPLE_MATH_1 VMStructFieldDword($JUNK)) !SIMPLE_MATH_2 ^IMM_1)"],
        "VMStructFieldDword($ENCODED_VALUE_) = EncodedValue(&X1, SimpleOperation(Operation(!SIMPLE_MATH_1), VMStructFieldDword($JUNK)), SimpleOperation(Operation(!SIMPLE_MATH_2), ^IMM_1))"
    ),
    (
        ["VMStructFieldDword($ENCODED_VALUE_) = ((&X1 !SIMPLE_MATH_1 ^IMM_1) !SIMPLE_MATH_2 VMStructFieldDword($JUNK))"],
        "VMStructFieldDword($ENCODED_VALUE_) = EncodedValue(&X1, SimpleOperation(Operation(!SIMPLE_MATH_1), ^IMM_1), SimpleOperation(Operation(!SIMPLE_MATH_2), VMStructFieldDword($JUNK)))"
    ),
    (
        ["VMStructFieldDword($ENCODED_VALUE_) = (&X1 !SIMPLE_MATH_1 VMStructFieldDword($JUNK))"],
        "VMStructFieldDword($ENCODED_VALUE_) = EncodedValue(&X1, SimpleOperation(Operation(!SIMPLE_MATH_1), VMStructFieldDword($JUNK)), None)"
    ),
    (
        ["VMStructFieldDword(@JUNK) !UPDATE_MATH_1= &X1"],
        None
    ),
    (
        [
        "VMStructFieldDword(@EIP) += &Y",
        "Jump(*(DWORD*)(VMStructFieldDword(@HANDLERS) + ((&X & 0xFFFF) << 0x2)))"
        ],
        "UpdateEipAndJump(&X, &Y)"
    ),
    (
        [
        "^VAR_1 = *(DWORD*)(VMStructFieldDword(@HANDLERS) + ((&X & 0xFFFF) << 0x2))",
        "VMStructFieldDword(@EIP) += &Y",
        "Jump(^VAR_1)"
        ],
        "UpdateEipAndJump(&X, &Y)"
    ),
    (
        [
        "^VAR_1 = *(DWORD*)(VMStructFieldDword(@HANDLERS) + (&X << 0x2))",
        "VMStructFieldDword(@EIP) += &Y",
        "Jump(^VAR_1)"
        ],
        "UpdateEipAndJump(&X, &Y)"
    ),
]

"""
    (
        [
        "^VAR_1 = ((ReadParameterWord(#NEXT_HANDLER) !SIMPLE_MATH_1 VMStructFieldDword(@KEY1)) !SIMPLE_MATH_2 ^IMM_1)",
        "VMStructFieldDword(@KEY1) !UPDATE_MATH_3= ^VAR_1",
        "UpdateEipAndJump(^VAR_1, ^IMM_2)"
        ],
        "UpdateEipAndJump(DecodeNextHandler(ReadParameterWord(#NEXT_HANDLER), ^SIMPLE_MATH_1, SimpleOperation(^SIMPLE_MATH_2, ^IMM_1), ^UPDATE_MATH_3), ^IMM_2)"
    ),
    (
        [
        "^VAR_1 = (ReadParameterWord(#NEXT_HANDLER) !SIMPLE_MATH_1 VMStructFieldDword(@KEY1))",
        "VMStructFieldDword(@KEY1) !UPDATE_MATH_3= ^VAR_1",
        "UpdateEipAndJump(^VAR_1, ^IMM_2)"
        ],
        "UpdateEipAndJump(DecodeNextHandler(ReadParameterWord(#NEXT_HANDLER), ^SIMPLE_MATH_1, None, ^UPDATE_MATH_3), ^IMM_2)"
    ),
    (
        [
        "UpdateEipAndJump(((ReadParameterWord(#NEXT_HANDLER) !SIMPLE_MATH_1 VMStructFieldDword(@KEY1)) !SIMPLE_MATH_2 ^IMM_1), ^IMM_2)"
        ],
        "UpdateEipAndJump(DecodeNextHandler(ReadParameterWord(#NEXT_HANDLER), ^SIMPLE_MATH_1, SimpleOperation(^SIMPLE_MATH_2, ^IMM_1), ^UPDATE_MATH_3), ^IMM_2)"
    ),
    (
        [
        "UpdateEipAndJump((ReadParameterWord(#NEXT_HANDLER) !SIMPLE_MATH_1 VMStructFieldDword(@KEY1)), ^IMM_2)",
        ],
        "UpdateEipAndJump(DecodeNextHandler(ReadParameterWord(#NEXT_HANDLER), ^SIMPLE_MATH_1, None, ^UPDATE_MATH_3), ^IMM_2)"
    ),

]"""

class NoneExpression(Expression):
    def get_format(self):
        return "None"

class Str(Expression):
    def __init__(self, value):
        self.value = value

    def get_format(self):
        return str(self.value)

class Macro(Expression):
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters

    def get_children(self):
        return self.parameters

    def replace_child(self, child, new_child):
        for i in xrange(len(self.parameters)):
            if self.parameters[i] == child:
                self.parameters[i] = new_child

    def equals(self, other):
        return Expression.equals(self, other) and self.name == other.name and \
            len(self.parameters) == len(other.parameters) and all([self.parameters[i].equals(other.parameters[i]) for i in xrange(len(self.parameters))])

    def get_format(self):
        return "%s(%s)" % (self.name, ", ".join([("{%d}" % i) for i in xrange(len(self.parameters))]))

class Params(object):
    def __init__(self, fields, parameters):
        self.fields = dict(fields)
        self.real_field_name = dict()
        self.parameters = dict(parameters)
        self.vars = {}
        self.specific_vars = {}
        self.group_vars = {}

    def copy(self):
        nparams = Params(self.fields, self.parameters)
        nparams.real_field_name = dict(self.real_field_name)
        nparams.vars = dict(self.vars)
        nparams.specific_vars = dict(self.specific_vars)
        nparams.group_vars = dict(self.group_vars)
        return nparams

    def update(self, other):
        self.fields.update(other.fields)
        self.real_field_name.update(other.real_field_name)
        self.parameters.update(other.parameters)
        self.vars.update(other.vars)
        self.specific_vars.update(other.specific_vars)
        self.group_vars.update(other.group_vars)

    def update_global(self, other):
        self.fields.update(other.fields)
        self.parameters.update(other.parameters)

    def _set_dict_value(self, dict, key, value, comp = lambda x,y: x == y):
        if dict.has_key(key):
            return comp(dict[key], value)
        else:
            # We don't want to always update it because of variables
            # If we have a Variable and VariableProxy, if we met the Varaible first, so we want it to stay variable hen we will create the result
            # For example setting a value of a variable. We will probably want to set the value of the varibale in the result (and not of the VariableProxy)
            dict[key] = value
        return True

    def get_field_name(self, value):
        for n, v in self.fields.iteritems():
            if v == value:
                return n
        return None

    def set_field_value(self, name, value):
        oname = self.get_field_name(value)
        if oname is not None:
            return oname == name
        else:
            return self._set_dict_value(self.fields, name, value)

    def set_param_value(self, name, value):
        return self._set_dict_value(self.parameters, name, value)

    def set_var_value(self, name, value):
        return self._set_dict_value(self.vars, name, value, comp = lambda x,y: x.equals(y))

    def set_specific_var_value(self, name, value):
        # The get value is important for some comprasions with vars (TODO: same for self.vars?)
        return self._set_dict_value(self.specific_vars, name, value, comp = lambda x,y: x.get_value().equals(y.get_value()))

    def set_group_var_value(self, name, value):
        return self._set_dict_value(self.group_vars, name, value, comp = lambda x,y: x.equals(y))

def is_var_name(string):
    if string[0] not in "!@#$^&":
        return False
    return re.subn("[^_A-Z0-9*]","",string[1:])[1] == 0

def is_constant(string):
    if not string.startswith("0x"):
        return False
    return string[2:].isdigit()

def match_expression(expression, match, params):
    #print expression, match
    parent = expression
    expression = expression.get_value()
    if is_var_name(match):
        var_type, name = match[0], match[1:]
        if var_type == "@" or var_type == "#" or var_type == "$":
            if not isinstance(expression, Immediate):
                return False
            int_value = expression.value
            if var_type == "#":
                return params.set_param_value(name, int_value)
            elif var_type == "@":
                if name[-1] == "*":
                    oname = params.get_field_name(int_value)
                    if oname is not None and oname.startswith(name[:-1]):
                        params.real_field_name[name] = oname
                        return True
                    return False
                return params.fields.has_key(name) and params.fields[name] == int_value
            else:
                if name[-1] == "_":
                    if params.set_field_value(name + str(int_value), int_value):
                        params.real_field_name[name] = name + str(int_value)
                        return True
                    return False
                else:
                    return params.set_field_value(name, int_value)
        elif var_type == "&":
            return params.set_var_value(name, parent)
        elif var_type == "^":
            if name.startswith("VAR_"):
                if isinstance(expression, Variable):
                    return params.set_specific_var_value(name, parent)
                return False
            elif name.startswith("IMM_"):
                if isinstance(expression, Immediate):
                    return params.set_specific_var_value(name, expression)
                return False
            else:
                return False
    elif is_constant(match):
        if not isinstance(expression, Immediate):
            return False
        return int(match,16) == expression.value
    else:
        fmt = expression.get_format()
        #print fmt
        # Try to match the expression with the format
        match_index = 0
        fmt_index = 0
        nparams = params.copy()
        while fmt_index < len(fmt) and match_index < len(match):
            if fmt[fmt_index] == "{":
                n = ''
                fmt_index += 1
                while fmt[fmt_index].isdigit():
                    n += fmt[fmt_index]
                    fmt_index += 1
                assert fmt[fmt_index] == "}"
                fmt_index += 1
                child = expression.get_children()[int(n)]
                #print "Child: " + str(child)
                if fmt_index == len(fmt):
                    if match_expression(child, match[match_index:], nparams):
                        params.update(nparams)
                        return True
                    return False
                else:
                    depth =0
                    start = match_index
                    while depth != 0 or fmt[fmt_index] != match[match_index]:
                        if match[match_index] == "(":
                            depth += 1
                        elif match[match_index] == ")":
                            depth -= 1
                            if depth < 0:
                                return False
                        match_index += 1
                        if match_index == len(match):
                            return False
                    if not match_expression(child, match[start:match_index], nparams):
                        return False
            elif match[match_index] == "!" and fmt[fmt_index] != match[match_index]:
                match_index += 1
                operation_name = ""
                while ("A" <= match[match_index] <= "Z") or ("0" <= match[match_index] <= "9") or match[match_index] == "_":
                    operation_name += match[match_index]
                    match_index += 1
                found = False
                for group in GROUPS.iterkeys():
                    if operation_name.startswith(group + "_"):
                        for value in GROUPS[group]:
                            if fmt[fmt_index:fmt_index+len(value)] == value:
                                if not nparams.set_group_var_value(operation_name, value):
                                    return False
                                found = True
                                fmt_index += len(value)
                            # Should i have break or? or give a chance to multi groups with similiar starts?
                            # probably the later, because even if we have some groups with common start, and we found a result, it is probably the correct one even if from the wrong group
                if not found:
                    return False
            else:
                if fmt[fmt_index] != match[match_index]:
                    return False
                fmt_index += 1
                match_index += 1
        if fmt_index == len(fmt) and match_index == len(match):
            params.update(nparams)
            return True
        return False

def create_macro_result(result_line, params, left = False):
    if result_line.find(" = ") != -1:
        lvalue, rvalue = result_line.split(" = ")
        return SetValue(create_macro_result(lvalue, params, True), create_macro_result(rvalue, params))
    else:
        if is_var_name(result_line):
            var_type, name = result_line[0], result_line[1:]
            if var_type == "@" or var_type == "#" or var_type == "$":
                if var_type == "@" or var_type == "$":
                    if name[-1] in ("_*"):
                        name = params.real_field_name[name]
                    int_val = params.fields[name]
                else:
                    int_val = params.parameters[name]
                return Immediate(int_val)
            elif var_type == "&":
                # TODO: return variable proxy if needed
                if params.vars.has_key(name):
                    return params.vars[name]
                else:
                    return NoneExpression()
            elif var_type == "!":
                return Str(params.group_vars[name])
            elif var_type == "^":
                if params.specific_vars.has_key(name):
                    # TODO: is it always good?
                    #if not left and name.startswith("VAR_"):
                    #    return VariableProxy(params.vars[name], None) # The None should be fixed on handler.update_instruction
                    return params.specific_vars[name]
                else:
                    assert False
                    #return NoneExpression()
        elif is_constant(result_line):
            return Immediate(int(result_line, 16))
        elif result_line == "None":
            return NoneExpression()
        else:
            macro_name = result_line[:result_line.index("(")]
            index = result_line.index("(") + 1
            parameters = []
            while result_line[index] != ")":
                # Find end
                depth = 0
                param = ''
                while depth > 0 or (result_line[index:index+2] != ", " and result_line[index] !=")"):
                    param += result_line[index]
                    if result_line[index] == "(":
                        depth += 1
                    elif result_line[index] == ")":
                        depth -= 1
                        assert depth >= 0
                    index += 1
                parameters.append(create_macro_result(param, params))
                if result_line[index:index+2] == ", ":
                    index += 2
            if is_var_name(macro_name):
                if macro_name[0] == "!":
                    macro_name = params.group_vars[macro_name[1:]]
                else:
                    assert False
            return Macro(macro_name, parameters)

def replace_macros_in_expression(handler, expression, params):
    changed = False

    for child in expression.get_children():
        for macro_line, macro_result in EXPRESSIONS_MACROS:
            nparams = params.copy()
            if match_expression(child, macro_line, nparams):
                new_child = create_macro_result(macro_result, nparams)
                params.update_global(nparams)
                #handler.make_unvisible(child.get_value())
                #handler.make_visible(new_child)
                expression.replace_child(child, new_child)
                changed = True
        changed |= replace_macros_in_expression(handler, child, params)
    return changed

def replace_macros_in_instructions(handler, instructions, params):
    changed = False
    for instruction in instructions:
        while replace_macros_in_expression(handler, instruction, params):
            changed = True
        if isinstance(instruction, ConditionBlock):
            changed |= replace_macros_in_instructions(handler, instruction.instructions, params)
    return changed

def match_instructions(instructions, index, lines, lines_index, params, pad = ''):
    nparams = params.copy()
    while index < len(instructions) and lines_index < len(lines):
        if not lines[lines_index].startswith(pad):
            return False, index, lines_index
        # Now, If we still in the wrong indentation, we will return error because the line will starts with padding
        line = lines[lines_index][len(pad):]
        optional_line = False
        #if line.startswith("["): # TODO: maybe add support for optional lines. if we add, need to fix instructions replacement code
        #    optional_line = True
        #    line = line[1:-1]
        if not match_expression(instructions[index], line, nparams):
            if optional_line:
                lines_index += 1
                continue
            return False, index, lines_index
        index += 1
        lines_index += 1
        if isinstance(instructions[index-1], ConditionBlock):
            match, nindex, lines_index = match_instructions(instructions[index-1].instructions, 0, lines, lines_index, nparams, pad + ' '*4)
            # Should match all the lines in the condition
            if not match or nindex != len(instructions[index-1].instructions):
                return False, index, lines_index
    params.update(nparams)
    return True, index, lines_index

def replace_instructions(handler, instructions_container, index, count, new_instructions):
    for line in instructions_container.instructions[index:index+count]:
        handler.make_unvisible(line)
    instructions_container.instructions[index:index+count] = new_instructions
    for inst in new_instructions:
        handler.update_instruction(inst)
    handler.clean_instructions()
    return instructions_container.instructions

def replace_instructions_macros(handler, instructions_container, index, params):
    changed = False
    instructions = instructions_container.instructions
    # TODO: if and else conditions
    for lines, result in MACROS:
        if len(lines) + index > len(instructions):
            continue
        nparams = params.copy()
        match, end_index, lines_end_index = match_instructions(instructions, index, lines, 0, nparams)
        if lines_end_index != len(lines):
            continue
        if match:
            if result is not None:
                nlines = [create_macro_result(result, nparams)]
            else:
                nlines = []
            instructions = replace_instructions(handler, instructions_container, index, len(lines), nlines)
            params.update_global(nparams)
            changed = True
    return changed

def replace_instructions_macros_in_instructions(handler, instructions_container, params):
    changed = False
    nchanged = True
    while nchanged:
        nchanged = False
        for i in xrange(len(instructions_container.instructions)):
            if replace_instructions_macros(handler, instructions_container, i, params):
                nchanged = True
                changed = True
                break # We changed the lines count
    return changed

def remove_unneeded_variable(handler, instructions_container, params):
    changed = False
    instructions = instructions_container.instructions
    i = 0
    while i < len(instructions) - 1:
        if isinstance(instructions[i], SetValue) and isinstance(instructions[i].lvalue, Variable) and len(instructions[i].lvalue.used_instructions)  == 1 and \
            len(instructions[i].lvalue.visible_if_used) == 0 and len(instructions[i].lvalue.proxies) == 1 and instructions[i].lvalue.used_instructions[0] == instructions[i + 1]:
            changed = True
            handler.make_unvisible(instructions[i+1])
            handler.make_unvisible(instructions[i])
            def find_and_replace(obj):
                for child in obj.get_children():
                    if isinstance(instructions[i+1], SetValueOperation) and instructions[i+1].lvalue == child:
                        continue
                    if isinstance(child, VariableProxy):
                        if child.reg_var == instructions[i].lvalue:
                            child.value = instructions[i].rvalue
                            child.show_reg = False
                    find_and_replace(child)
            find_and_replace(instructions[i+1])
            handler.make_visible(instructions[i+1])
            instructions[i:i+1] = []
        i += 1
    return changed

def run_on_all_instructions(handler, instructions_container, func, params):
    changed = False
    changed |= func(handler, instructions_container, params)
    for inst in instructions_container.instructions:
        if isinstance(inst, ConditionBlock):
            changed |= run_on_all_instructions(handler, inst, func, params)
    return changed

def parse_handler(handler, fields, parameters):
    changed = False
    params = Params(fields, parameters)
    changed |= replace_macros_in_instructions(handler, handler.get_instructions(), params)
    changed |= run_on_all_instructions(handler, handler, replace_instructions_macros_in_instructions, params)
    changed |= run_on_all_instructions(handler, handler, remove_unneeded_variable, params)
    if changed:
        fields.update(params.fields)
        parameters.update(params.parameters)
    return changed

def parse_fish_handler(handler, fields, parameters):
    instructions = handler.get_instructions()
    for name, lines in fish_handlers.HANDLERS.iteritems():
        params = Params(fields, parameters)
        match, index, lines_index = match_instructions(instructions, 0, lines, 0, params)
        if match and index == len(instructions) and lines_index == len(lines):
            fields.update(params.fields)
            parameters.update(params.parameters)
            # TODO return more stutfs (parameters read cases etc..)
            return name
    return None




