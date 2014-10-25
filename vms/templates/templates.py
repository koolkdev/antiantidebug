from vms import vminstruction
import re

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

    def __init__(self, data_reader):
        self.groups = {}
        self.line_to_templates = {}
        group_name = data_reader.readline().strip()
        while group_name:
            self.groups[group_name] = data_reader.readline().strip().split(" ")
            group_name = data_reader.readline().strip()
        self.templates = []
        line = data_reader.readline().strip()
            
        while line:
            instructions_from = []
            instructions_to = []
            while line != "=>":
                instructions_from.append(vminstruction.VMInstruction(*line.split(" ")))
                line = data_reader.readline().strip()
            line = data_reader.readline().strip()
            while line:
                instructions_to.append(vminstruction.VMInstruction(*line.split(" ")))
                line = data_reader.readline().strip()
            self.templates.append((instructions_from, instructions_to))
            
            line = data_reader.readline().strip()
            
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
            

    @classmethod
    def get_template(cls, name):
        if cls.cache.has_key(name):
            return cls.cache[name]
        res = cls(open(r"vms\templates\files\%s" % name, "rb"))
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
                            new_args = [eval(x, {}, values)&0xffffffff for x in inst.args]
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
        
def translate_to_assembly(self):
    pass
