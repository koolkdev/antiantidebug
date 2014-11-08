from handlers_decompiler import *
import re

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
        "ReadParameterByte(&X)"
    ),
    (
        "*(WORD*)(VMStructFieldDword(@EIP) + &X)",
        "ReadParameterWord(&X)"
    ),
    (
        "*(DWORD*)(VMStructFieldDword(@EIP) + &X)",
        "ReadParameterDword(&X)"
    )
]

MACROS = [
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
        self.parameters = dict(parameters)
        self.vars = {}
        self.specific_vars = {}

    def copy(self):
        nparams = Params(self.fields, self.parameters)
        nparams.vars = dict(self.vars)
        nparams.specific_vars = dict(self.specific_vars)
        return nparams

    def update(self, other):
        self.fields.update(other.fields)
        self.parameters.update(other.parameters)
        self.vars.update(other.vars)
        self.specific_vars.update(other.specific_vars)

    def update_global(self, other):
        self.fields.update(other.fields)
        self.parameters.update(other.parameters)

    def _set_dict_value(self, dict, key, value, comp = lambda x,y: x == y):
        if dict.has_key(key):
            if not comp(dict[key], value):
                return False
        dict[key] = value
        return True

    def set_field_value(self, name, value):
        return self._set_dict_value(self.fields, name, value)

    def set_param_value(self, name, value):
        return self._set_dict_value(self.parameters, name, value)

    def set_var_value(self, name, value):
        return self._set_dict_value(self.vars, name, value, comp = lambda x,y: x.equals(y))

    def set_specific_var_value(self, name, value):
        return self._set_dict_value(self.specific_vars, name, value, comp = lambda x,y: x.equals(y))

def is_var_name(string):
    if string[0] not in "@#$^&":
        return False
    return re.subn("[^_A-Z0-9]","",string[1:])[1] == 0

def is_constant(string):
    if not string.startswith("0x"):
        return False
    return string[2:].isdigit()

def match_expression(expression, match, params):
    if is_var_name(match):
        var_type, name = match[0], match[1:]
        if var_type == "@" or var_type == "#" or var_type == "$":
            if not isinstance(expression, Immediate):
                return False
            int_value = expression.value
            if var_type == "#":
                return params.set_param_value(name, int_value)
            elif var_type == "@":
                return params.fields.has_key(name) and params.fields[name] == int_value
            else:
                return params.set_field_value(name, int_value)
        elif var_type == "&":
            return params.set_var_value(name, expression)
        elif var_type == "^":
            if name.startswith("VAR_"):
                if isinstance(expression, Variable):
                    return params.set_specific_var_value(name, expression)
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
                if fmt_index == len(fmt):
                    if match_expression(child.get_value(), match[match_index:], nparams):
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
                    if not match_expression(child.get_value(), match[start:match_index], nparams):
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

def create_macro_result(result_line, params):
    macro_name = result_line[:result_line.index("(")]
    macro_params = result_line[result_line.index("(")+1:-1].split(", ")
    parameters = []
    for param in macro_params:
        if is_var_name(param):
            var_type, name = param[0], param[1:]
            if var_type == "@" or var_type == "#" or var_type == "$":
                if var_type == "@" or var_type == "$":
                    int_val = params.fields[name]
                else:
                    int_val = params.parameters[name]
                parameters.append(Immediate(int_val))
            elif var_type == "&":
                parameters.append(params.vars[name])
            elif var_type == "^":
                parameters.append(params.specific_vars[name])
        elif is_constant(param):
            parameters.append(Immediate(int(param, 16)))
        else:
            assert False
    return Macro(macro_name, parameters)

def replace_macros_in_expression(expression, params):
    changed = False
    for child in expression.get_children():
        for macro_line, macro_result in EXPRESSIONS_MACROS:
            nparams = params.copy()
            if match_expression(child.get_value(), macro_line, nparams):
                new_child = create_macro_result(macro_result, nparams)
                params.update_global(nparams)
                expression.replace_child(child.get_value(), new_child)
                changed = True
        changed |= replace_macros_in_expression(child, params)
    return changed

def replace_macros_in_instructions(instructions, params):
    changed = False
    for instruction in instructions:
        while replace_macros_in_expression(instruction, params):
            changed = True
        if isinstance(instruction, ConditionBlock):
            changed |= replace_macros_in_instructions(instruction.instructions, params)
    return changed

def replace_instructions_macros(instructions, index, params):
    changed = False
    # TODO: if and else conditions
    for lines, result in MACROS:
        if len(lines) + index > len(instructions):
            continue
        nparams = params.copy()
        match = True
        for i in xrange(len(lines)):
            if not match_expression(instructions[index+i], lines[i], nparams):
                match = False
                break
        if match:
            instructions[index:index+len(lines)] = [create_macro_result(result, nparams)]
            params.update_global(nparams)
            changed = True
    return changed

def parse_handler(handler, fields, parameters):
    changed = False
    params = Params(fields, parameters)
    replace_macros_in_instructions(handler.get_instructions(), params)
    nchanged = True
    while nchanged:
        nchanged = False
        for i in xrange(len(handler.get_instructions())):
            if replace_instructions_macros(handler.get_instructions(), i, params):
                nchanged = True
                changed = True
                break # We changed the lines count
    if changed:
        fields.update(params.fields)
        parameters.update(params.parameters)
    return changed

def parse_fish_handler(handler, fields, parameters):
    return None




