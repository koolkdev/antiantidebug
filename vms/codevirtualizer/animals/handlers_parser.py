from handlers_decompiler import *
import re
import os

OPS = {
    "+": Add,
    "-": Sub,
    "^": Xor,
    "&": And,
    "|": Or,
    ">>": Shr,
    "<<": Shl,
    "==": Equal,
    "!=": NotEqual,
    "&&": AndCond,
    "||": Test
}


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
    def __init__(self, fields):
        self.fields = dict(fields)
        self.real_field_name = dict()
        self.parameters = {}
        self.vars = {}
        self.handler_vars = {}
        self.unique = {}

    def copy(self):
        nparams = Params(self.fields)
        nparams.parameters = dict(self.parameters)
        nparams.real_field_name = dict(self.real_field_name)
        nparams.vars = dict(self.vars)
        nparams.handler_vars = dict(self.handler_vars)
        nparams.unique = dict(self.unique)
        return nparams

    def update(self, other):
        self.fields.update(other.fields)
        self.real_field_name.update(other.real_field_name)
        self.parameters.update(other.parameters)
        self.vars.update(other.vars)
        self.handler_vars.update(other.handler_vars)
        self.unique.update(other.unique)

    def update_global(self, other):
        self.fields.update(other.fields)
        self.parameters.update(other.parameters)
        self.handler_vars.update(other.handler_vars)

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

    def set_handler_var_value(self, name, value):
        return self._set_dict_value(self.handler_vars, name, value, comp = lambda x,y: x == y)

    def set_unique_value(self, name, value):
        if value in self.unique.values():
            return name in self.unique and self.unique[name] == value
        else:
            return self._set_dict_value(self.unique, name, value)


def is_var_name(string):
    if string[0] not in "$?":
        return False
    return re.match("^[$?][A-Z]{0,1}\[[_A-Z0-9:*]+\]$", string) is not None


def parse_var_name(string):
    if string[0] == "?":
        assert string[1] == "O"
    if string[1] == "[":
        var_type = "A"
    else:
        var_type = string[1]
    name = string[string.find("[")+1:-1]
    cond = None
    if name.find(":") != -1:
        cond, name = name.split(":")
    return var_type, cond, name

def is_constant(string):
    if not string.startswith("0x"):
        return False
    return re.subn("[^A-F0-9]", "", string[2:])[1] == 0

# $X[...] - variable
# Readings: (X)
#  - any
# N - number
# V - variable
# G - group
# O - offset
# ?O - offset that is already set
# P - handler parameter
# H - handler vars

class HandlerParser(object):
    cache = {}

    @classmethod
    def get_default_parser(cls):
        return cls(None, None)

    @classmethod
    def get_parser(cls, name, mode):
        if cls.cache.has_key((name, mode)):
            return cls.cache[(name, mode)]
        res = cls(open(r"%s\%s" % (os.path.dirname(os.path.abspath(__file__)), name), "r"), mode)
        cls.cache[(name, mode)] = res
        return res

    def __init__(self, data_reader, mode):
        self.groups = {}
        self.macros = {}
        self.templates = []
        self.expression_templates = []
        self.dont_optimize = False
        self.run_once = False
        self.default_funcs = [self.replace_expression_templates, self.replace_templates]

        if data_reader is not None:
            self.mode = mode

            # Parse the file first
            self._parse_file(data_reader)

    def _parse_file(self, data_reader):
        while True:
            line = data_reader.readline()
            if not line:
                break
            line = line.rstrip()
            if not line:
                continue
            if line[0] == "#":
                continue  # Comment

            tokens = line.split(" ")

            command = tokens[0]
            ignore = False
            if command.endswith("[32]"):
                if self.mode != 32:
                    ignore = True
                command = command[:-4]
            elif command.endswith("[64]"):
                if self.mode != 64:
                    ignore = True
                command = command[:-4]

            if command == "OPTION":
                if len(tokens) != 2:
                    raise Exception("Invalid OPTION")
                if not ignore:
                    option = tokens[1]
                    if option == "DONT_OPTIMIZE":
                        self.dont_optimize = True
                    elif option == "RUN_ONCE":
                        self.run_once = True
                    else:
                        raise Exception("Unrecognized option %s" % option)
            elif command == "DEFINE_GROUP":
                if len(tokens) < 3:
                    raise Exception("Invalid DEFINE_GROUP")
                group_name = tokens[1]
                group = []
                if group_name in self.groups:
                    group = self.groups[group_name]
                group.extend(tokens[2:])
                if not ignore:
                    self.groups[group_name] = group
            elif command == "DEFINE_MACRO":
                if len(tokens) != 3:
                    raise Exception("Invalid DEFINE_MACRO")
                macro_name = tokens[1]
                if not ignore and macro_name in self.macros:
                    raise Exception("Macro name already used")
                if not ignore:
                    self.macros[macro_name] = tokens[2]
            elif command == "DEFINE_TEMPLATE":
                if len(tokens) != 1:
                    raise Exception("Invalid DEFINE_TEMPLATE")
                lines = self._get_template_lines(data_reader, "=>")
                result = self._get_template_lines(data_reader)
                assert len(result) == 1
                result = result[0]
                if not ignore:
                    self.templates.append((lines, result))
            elif command == "DEFINE_EXPRESSION_TEMPLATE":
                if len(tokens) != 1:
                    raise Exception("Invalid DEFINE_EXPRESSION_TEMPLATE")
                line = self._get_template_lines(data_reader, "=>")
                assert len(line) == 1
                line = line[0]
                result = self._get_template_lines(data_reader)
                assert len(result) == 1
                result = result[0]
                if not ignore:
                    self.expression_templates.append((line, result))
            else:
                raise Exception("Invalid command %s" % command)

    def _get_template_lines(self, data_reader, end=''):
        lines = []
        while True:
            line = data_reader.readline()
            if not line:
                if not end:
                    return lines
                else:
                    raise Exception("Template EOF")
            line = line.rstrip()
            if line == end:
                return lines
            nline = ''
            p = 0
            while line.find("@", p) != -1:
                ps = line.find("@", p)
                nline += line[p:ps]
                pe = line.find("@", ps+1)
                if pe == -1:
                    raise Exception("Invalid template line %s" % line)
                nline += self.macros[line[ps+1:pe]]
                p = pe+1
            nline += line[p:]
            lines.append(nline)

    def match_expression(self, expression, match, params):
        #print expression, match
        if is_var_name(match) and match[1] != "G":
            var_type, cond, name = parse_var_name(match)
            if var_type in "OP":
                if not isinstance(expression, Immediate):
                    return False
                int_value = expression.value
                if var_type == "P":
                    return params.set_param_value(name, int_value)
                elif match[0] == "?":
                    if cond is not None:
                        if cond[-1] == "*":
                            oname = params.get_field_name(int_value)
                            if oname is not None and oname.startswith(cond[:-1]):
                                params.real_field_name[name] = oname
                                return True
                            return False
                        else:
                            if params.fields.has_key(cond) and params.fields[cond] == int_value:
                                params.real_field_name[name] = cond
                                return True
                            return False
                    return params.fields.has_key(name) and params.fields[name] == int_value
                else:
                    if cond is not None and cond[-1] == "*":
                        if params.set_field_value(cond + str(int_value), int_value):
                            params.real_field_name[name] = cond + str(int_value)
                            return True
                        return False
                    else:
                        return params.set_field_value(name, int_value)
            elif var_type in "AVN":
                if var_type == "V":
                    if not isinstance(expression, Variable):
                        return False
                if var_type == "N":
                    if not isinstance(expression, Immediate):
                        return False
                return params.set_var_value(name, expression)
            elif var_type == "H":
                if not isinstance(expression, Immediate):
                    return False
                return params.set_handler_var_value(name, expression.value)
            elif var_type == "U":
                if not isinstance(expression, Immediate):
                    return False
                return params.set_unique_value(name, expression.value)
            else:
                assert False
        elif is_constant(match):
            if not isinstance(expression, Immediate):
                return False
            return int(match, 16) == expression.value
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
                        if self.match_expression(child, match[match_index:], nparams):
                            params.update(nparams)
                            return True
                        return False
                    else:
                        depth = 0
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
                        # TODO: Match the layout of the expression first and than check the childs (Should be faster?)
                        if not self.match_expression(child, match[start:match_index], nparams):
                            return False
                elif match[match_index] == "$":
                    if match[match_index:match_index+3] != "$G[":
                        return False
                    group_name, var_name = match[match_index + 3:match.find("]", match_index)].split(":")
                    match_index = match.find("]", match_index) + 1
                    found = False
                    if group_name not in self.groups:
                        assert False
                    max_found = ""
                    for value in self.groups[group_name]:
                        if fmt[fmt_index:fmt_index+len(value)] == value and len(value) >= len(max_found):
                            found = True
                            max_found = value
                    if not found:
                        return False
                    if not nparams.set_var_value(var_name, Str(max_found)):
                        return False
                    fmt_index += len(max_found)
                else:
                    if fmt[fmt_index] != match[match_index]:
                        return False
                    fmt_index += 1
                    match_index += 1
            if fmt_index == len(fmt) and match_index == len(match):
                params.update(nparams)
                return True
            return False

    def create_macro_result(self, result_line, params):
        if result_line.find(" = ") != -1:
            lvalue, rvalue = result_line.split(" = ")
            return SetValue(self.create_macro_result(lvalue, params), self.create_macro_result(rvalue, params))
        else:
            if is_var_name(result_line):
                var_type, cond, name =  parse_var_name(result_line)
                assert cond is None
                if var_type in "OP":
                    if var_type == "O":
                        if name not in params.fields:
                            name = params.real_field_name[name]
                        int_val = params.fields[name]
                    else:
                        int_val = params.parameters[name]
                    return Immediate(int_val)
                elif var_type in "AVNG":
                    if name in params.vars:
                        return params.vars[name]
                    else:
                        assert False
                else:
                    assert False
            elif is_constant(result_line):
                return Immediate(int(result_line, 16))
            elif result_line == "None":
                return NoneExpression()
            else:
                macro_name = result_line[:result_line.index("(")]
                index = result_line.index("(") + 1
                parameters = []
                op = None
                while result_line[index] != ")":
                    # Find end
                    depth = 0
                    param = ''
                    while depth > 0 or (result_line[index:index+2] != ", " and result_line[index] != " " and result_line[index] !=")"):
                        param += result_line[index]
                        if result_line[index] == "(":
                            depth += 1
                        elif result_line[index] == ")":
                            depth -= 1
                            assert depth >= 0
                        index += 1
                    parameters.append(self.create_macro_result(param, params))
                    if result_line[index:index+2] == ", ":
                        index += 2
                    elif result_line[index] != ")":
                        assert result_line[index] == " "
                        op_name = result_line[index+1:result_line.find(" ", index + 1)]
                        index += 2 + len(op_name)
                        assert len(parameters) == 1
                        assert macro_name == ""
                        if is_var_name(op_name):
                            var_type, cond, name = parse_var_name(op_name)
                            assert cond is None
                            assert type(params.vars[name]) is Str
                            op_name = params.vars[name].value
                        op = OPS[op_name]
                if op is not None:
                    assert len(parameters) == 2
                    return op(parameters[0], parameters[1])
                if is_var_name(macro_name):
                    var_type, cond, name = parse_var_name(macro_name)
                    assert cond is None
                    assert type(params.vars[name]) is Str
                    macro_name = params.vars[name].value
                return Macro(macro_name, parameters)

    def replace_macros_in_expression(self, handler, macros, expression, params):
        changed = False
        for child in expression.get_children():
            changed |= self.replace_macros_in_expression(handler, macros, child, params)
            for macro_line, macro_result in macros:
                nparams = params.copy()
                if self.match_expression(child, macro_line, nparams):
                    new_child = self.create_macro_result(macro_result, nparams)
                    params.update_global(nparams)
                    #handler.make_unvisible(child.get_value())
                    #handler.make_visible(new_child)
                    expression.replace_child(child, new_child)
                    changed = True
        return changed

    def replace_expression_templates(self, handler, instructions_container, index, params):
        changed = False
        # TODO: make_unvisible/make_visible?
        while self.replace_macros_in_expression(handler, self.expression_templates, instructions_container.instructions[index], params):
            changed = True
        return changed

    def match_instructions(self, instructions, index, lines, lines_index, params, pad=None):
        if pad is None:
            pad = ''
        nparams = params.copy()
        while index < len(instructions) and lines_index < len(lines):
            if not lines[lines_index].startswith(pad):
                return False, index, lines_index
            # Now, If we still in the wrong indentation, we will return error because the line will starts with padding
            line = lines[lines_index][len(pad):]
            if line.startswith(" "):
                # Wrong indentation
                return False, index, lines_index
            optional_line = False
            #if line.startswith("["): # TODO: maybe add support for optional lines. if we add, need to fix instructions replacement code
            #    optional_line = True
            #    line = line[1:-1]
            if not self.match_expression(instructions[index], line, nparams):
                #print str(instructions[index]), line
                if optional_line:
                    lines_index += 1
                    continue
                return False, index, lines_index
            index += 1
            lines_index += 1
            if isinstance(instructions[index-1], ConditionBlock):
                match, nindex, lines_index = self.match_instructions(instructions[index-1].instructions, 0, lines, lines_index, nparams, pad + ' '*4)
                # Should match all the lines in the condition
                if not match or nindex != len(instructions[index-1].instructions):
                    return False, index, lines_index
        params.update(nparams)
        return True, index, lines_index

    def replace_instructions(self, handler, instructions_container, index, count, new_instructions):
        for inst in instructions_container.instructions[index:index+count]:
            handler.make_unvisible(inst, True)
        for inst in instructions_container.instructions[index:index+count]:
            if isinstance(inst, SetValueOperation) and isinstance(inst.lvalue, Variable):
                inst.lvalue.instructions.remove(inst)
        instructions_container.instructions[index:index+count] = new_instructions
        for inst in new_instructions:
            if isinstance(inst, SetValueOperation) and isinstance(inst.lvalue, Variable):
                inst.lvalue.instructions.append(inst)
            handler.make_visible(inst)
        if not self.dont_optimize:
            handler.optimize_instructions()
        handler.clean_instructions()
        return instructions_container.instructions

    def replace_instructions_templates(self, handler, templates, instructions_container, index, params):
        changed = False
        instructions = instructions_container.instructions
        # TODO: if and else conditions
        for lines, result in templates:
            real_len = len([l for l in lines if not l.startswith(" ")])
            if real_len + index > len(instructions):
                continue
            nparams = params.copy()
            match, end_index, lines_end_index = self.match_instructions(instructions, index, lines, 0, nparams)
            if lines_end_index != len(lines):
                continue
            if match:
                if result == "None":
                    nlines = []
                else:
                    nlines = [self.create_macro_result(result, nparams)]
                instructions = self.replace_instructions(handler, instructions_container, index, real_len, nlines)
                params.update_global(nparams)
                changed = True
        return changed

    def replace_templates(self, handler, instructions_container, index, params):
        return self.replace_instructions_templates(handler, self.templates, instructions_container, index, params)

    def clean_instructions_container(self, handler, instructions_container, params, funcs, reverse=None):
        if reverse is None:
            reverse = not self.run_once
        if reverse:
            i = len(instructions_container.instructions) - 1
        else:
            i = 0
        while 0 <= i < len(instructions_container.instructions):
            if i == 0:
                pass
            if isinstance(instructions_container.instructions[i], ConditionBlock):
                # Clean inner block first
                self.clean_instructions_container(handler, instructions_container.instructions[i], params, funcs, reverse)
            if i >= len(instructions_container.instructions):
                i = len(instructions_container.instructions) - 1

            changed = True
            while changed:
                changed = False
                for func in funcs:
                    changed |= func(handler, instructions_container, i, params)
                    # TODO: Do it proper
                    if i >= len(instructions_container.instructions):
                        i = len(instructions_container.instructions) - 1
                if self.run_once:
                    break

            if reverse:
                i -= 1
            else:
                i += 1

    def clean_handler(self, handler, fields, funcs=None, reverse=None):
        if funcs is None:
            funcs = self.default_funcs
        params = Params(fields)
        self.clean_instructions_container(handler, handler, params, funcs, reverse)
        fields.update(params.fields)
