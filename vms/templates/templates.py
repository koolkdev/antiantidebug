from vms import vminstruction
import re
import os

# itertools.product
def product(*args, **kwds):
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

nop = vminstruction.VMInstruction("NOP")

class Templates(object):
    cache = {}

    def __init__(self, data_reader, mode):
        self.groups = {}
        self.line_to_templates = {}
        self.macros = {}
        self.template_macros = {}
        self.templates = []
        self.mode = mode
        self.run_once = False

        # Parse the file first
        self._parse_file(data_reader)

        # Some optimization
        for template in self.templates:
            parts = []
            for part in template[0][0].name.split("|"):
                part = part.split("=")[-1]
                if part.startswith("^"):
                    parts.append(self.groups[part[1:]])
                else:
                    parts.append([part])
            for name in product(*parts):
                name = "".join(name)
                if not self.line_to_templates.has_key(name):
                    self.line_to_templates[name] = []
                self.line_to_templates[name].append(template)


    def _parse_file(self, data_reader):
        while True:
            line = data_reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            if line[0] == "#":
                continue # Comment

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
                    if option == "RUN_ONCE":
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
                for member in tokens[2:]:
                    parts = []
                    for part in member.split("|"):
                        if part.startswith("^"):
                            parts.append(self.groups[part[1:]])
                        else:
                            parts.append([part])
                    for name in product(*parts):
                        name = "".join(name)
                        group.append(name)
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
            elif command == "DEFINE_TEMPLATE_MACRO":
                if len(tokens) != 2:
                    raise Exception("Invalid DEFINE_TEMPLATE_MACRO")
                macro_name = tokens[1]
                if not ignore and macro_name in self.template_macros:
                    raise Exception("Template macro name already used")
                lines = self._get_template_lines(data_reader)
                if not ignore:
                    self.template_macros[macro_name] = lines
            elif command == "DEFINE_TEMPLATE":
                if len(tokens) != 1:
                    raise Exception("Invalid DEFINE_TEMPLATE")
                instructions_from = []
                instructions_to = []
                lines = self._get_template_lines(data_reader, "=>")
                for line in lines:
                    instructions_from.append(vminstruction.VMInstruction(*line.split(" ")))
                for line in self._get_template_lines(data_reader):
                    instructions_to.append(vminstruction.VMInstruction(*line.split(" ")))
                if not ignore:
                    self.templates.append((instructions_from, instructions_to))
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
            line = line.strip()
            if line == end:
                return lines
            if line.startswith("@") and line.count("@") == 1:
                lines.extend(self.template_macros[line[1:]])
                continue
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

    @classmethod
    def get_template(cls, name, mode):
        if cls.cache.has_key(name):
            return cls.cache[name]
        res = cls(open(r"%s\files\%s" % (os.path.dirname(os.path.abspath(__file__)), name), "r"), mode)
        cls.cache[name] = res
        return res


    def match_instruction(self, first, second, variables):
        if first.startswith("*"):
            first = first[1:]
        parts = []
        gvars = []
        parts = []
        i = 0
        for part in first.split("|"):
            i += 1
            if part.startswith("&"):
                var, part = part[1:].split("=")
                if variables.has_key(var):
                    parts.append([variables[var]])
                    continue
                gvars.append((i-1, var))
            if part.startswith("^"):
                parts.append(self.groups[part[1:]])
            else:
                parts.append([part])
            
        match = re.match("^" + "".join(["(" + "|".join([re.escape(y) for y in x]) + ")" for x in parts]) + "$", second)
        if not match:
            return False
        nvariables = variables.copy()
        if match:
            for index,var in gvars:
                if nvariables.has_key(var):
                    if nvariables[var] != match.groups()[index]:
                        return False
                else:
                    nvariables[var] = match.groups()[index]  
        variables.update(nvariables)
        return True

    def clean(self, insts):
        # TODO clean insts as i should clean (get_clean_instruction), so I won't need the outer loop
        value_mask = (1 << self.mode) - 1
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(insts):
                if not self.line_to_templates.has_key(insts[i].name):
                    i += 1
                    continue
                match = False
                for template in self.line_to_templates[insts[i].name]:
                    releated = []
                    values = {}
                    variables = {}
                    saved_args = {}
                    j = i
                    ti = 0
                    match = True
                    while j < len(insts) and ti < len(template[0]):
                        tinst = template[0][ti].name
                        inst = insts[j].name
                        if tinst.startswith("*"):
                            if ti + 1 != len(template[0]) and self.match_instruction(template[0][ti+1].name, inst, variables):
                                ti += 1
                            elif self.match_instruction(tinst, inst, variables):
                                j += 1
                                continue
                            else:
                                match = False
                                break
                        elif not self.match_instruction(tinst, inst, variables):
                            match = False
                            break
                        if len(template[0][ti].args) == 1 and template[0][ti].args[0].startswith("*"):
                            var_name = template[0][ti].args[0][1:]
                            if var_name in saved_args:
                                if len(saved_args[var_name]) != len(insts[j].args):
                                    match = False
                                    break
                                for ai in xrange(len(insts[j].args)):
                                    if insts[j].args[ai] != saved_args[var_name][ai]:
                                        match = False
                                        break
                            else:
                                saved_args[var_name] = insts[j].args
                        else:
                            if len(template[0][ti].args) > len(insts[j].args):
                                match = False
                                break
                            for ai in xrange(len(template[0][ti].args)):
                                # Check if a number
                                arg = template[0][ti].args[ai]
                                # TODO Check that hexdigits
                                if arg.isdigit() or ((arg.startswith("0x") or arg.startswith("0X"))):
                                    if insts[j].args[ai] != eval(arg):
                                        match = False
                                        break
                                else:
                                    if values.has_key(arg):
                                        if values[arg] != insts[j].args[ai]:
                                            match = False
                                            break
                                    else:
                                        values[arg] = insts[j].args[ai]
                        if not match:
                            break
                        releated.append(j)
                        ti += 1
                        j += 1

                    if ti != len(template[0]):
                        match = False
                    if match:
                        new_insts = []
                        for inst in template[1]:
                            new_name = inst.name
                            while new_name.find("*") != -1:
                                splitted = new_name.split("*", 2)
                                new_name = splitted[0] + variables[splitted[1]] + splitted[2]
                            new_args = []
                            for arg in inst.args:
                                if arg.startswith("*"):
                                    new_args.extend(["0x%x" % x for x in saved_args[arg[1:]]])
                                else:
                                    new_args.append(arg)
                            new_args = [eval(x, {}, values)&value_mask for x in new_args]
                            new_insts.append(vminstruction.VMInstruction(new_name, *new_args))
                        new_insts += [nop] * (len(releated) - len(new_insts))
                        diff = 0
                        for ri in xrange(len(releated)):
                            if new_insts[ri].name == "NOP":
                                insts.pop(releated[ri]-diff)
                                diff += 1
                            else:
                                insts[releated[ri]-diff] = new_insts[ri]
                        break
                if not match:
                    i += 1
                else:
                    changed = True
            if self.run_once:
                break
        
def translate_to_assembly(self):
    pass
