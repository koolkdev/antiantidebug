import instruction
import oreans_deobfuscator


# Just a proxy for the class
class Cleaner(object):
    # pe should have the function get_instruction_at
    def __init__(self, file):
        self.file = file
        self.mode = file.mode
        def read(address, size):
            return file.read(address, size)
        self.cleaner = oreans_deobfuscator.Cleaner(read, self.file.mode)


    def set_reg_unused(self, reg):
        self.cleaner.set_reg_unused(reg)

    def set_option(self, option, value):
        self.cleaner.set_option(option, value)
        
    def get_instruction(self, address):
        next_address, data = self.cleaner.get_clean_instruction(address)
        if next_address is None:
            return None
        inst = instruction.Instruction(data, address, self.file.mode)
        inst.next = next_address
        return inst

    def get_reader(self, address):
        return CleanReader(self, address)

        
class CleanerException(Exception):
    pass


class CleanReader(object):
    def __init__(self, cleaner, address):
        self.address = address
        self.cleaner = cleaner

    def get(self):
        res = self.cleaner.get_instruction(self.address)
        self.address = res.next
        return res

    def get_cond(self, cond):
        old_address = self.address
        res = self.get()
        if not cond(res):
            self.address = old_address
            #for i in xrange(30):
            #    print "%08x: %s" % (self.address, self.get())
            raise CleanerException("Wrong condition: %s" % str(res))
        return res


class JunkSkipper(object):
    def __init__(self, file):
        self.file = file
        self.instructions = {}
        self.loop = {}

    def get_next_real_instruction(self, address):
        if self.instructions.has_key(address):
            return self.instructions[address]
        if self.loop.has_key(address):
            raise Exception("loop")
        self.loop[address] = 1
        inst = self.file.get_instruction(address)
        inst = self._clean_instruction(inst)
        self.instructions[address] = inst
        return inst

    def _clean_instruction(self, inst):
        if inst.opcode == "jmp" and inst.operands[0].is_immediate():
            return self.get_next_real_instruction(inst.operands[0].value)
        elif inst.opcode in ("ja", "jae", "jb", "jbe", "jz", "jg", "jge", "jl", "jle", "jnz", "jno", "jnp", "jns", "jo", "jp" ,"js"):
            next1 = self.get_next_real_instruction(inst.next)
            next2 = self.get_next_real_instruction(inst.operands[0].value)
            if next1.address != next2.address:
                return inst
            return next1
        elif inst.opcode == "pushad":
            next = self.get_next_real_instruction(inst.next)
            if next.opcode != "popad":
                return inst
            return self.get_next_real_instruction(next.next)
        elif inst.opcode.startswith("pushf"):
            next = self.get_next_real_instruction(inst.next)
            if not next.opcode.startswith("popf"):
                return inst
            return self.get_next_real_instruction(next.next)
        elif inst.opcode == "push" and inst.operands[0].is_reg():
            next = self.get_next_real_instruction(inst.next)
            if next.opcode == "pop" and next.operands[0].is_reg(inst.operands[0].reg):
                return self.get_next_real_instruction(next.next)
            if inst.operands[0].is_reg("eax") and next.opcode == "push" and next.operands[0].is_reg("edx"):
                next2 = self.get_next_real_instruction(next.next)
                next3 = self.get_next_real_instruction(next2.next)
                next4 = self.get_next_real_instruction(next3.next)
                if next2.opcode == "rdtsc" and next3.opcode == "pop" and next3.operands[0].is_reg("edx") and next4.opcode == "pop" and next4.operands[0].is_reg("eax"):
                    return self.get_next_real_instruction(next4.next)
            return inst
        return inst


def _get_opcode(line):
    return line.split(" ")[0]


def _get_operand(line, i):
    return line[line.find(" ")+1:].split(", ")[i]


def clean_animals_vm_code(code, arch):
    lines = code.splitlines()
    while _get_opcode(lines[0]) == "push" and _get_operand(lines[0], 0) in arch.get_registers():
        stack = [_get_operand(lines[0], 0)]
        i = 1
        while stack:
            opcode = _get_opcode(lines[i])
            if opcode in ("test", "mov", "add", "sub", "and", "xor", "or", "shr", "shl"):
                op1 = _get_operand(lines[i], 0)
                op2 = _get_operand(lines[i], 1)
                if arch.reg_native(op1) is None:
                    return code
                if opcode != "test" and arch.reg_native(op1) not in stack:
                    return code
                if arch.reg_native(op2) is None and not op2.startswith("0x"):
                    return code
            elif opcode == "push":
                op1 = _get_operand(lines[i], 0)
                if op1 not in arch.get_registers():
                    return code
                stack.append(op1)
            elif opcode == "pop":
                op1 = _get_operand(lines[i], 0)
                if op1 != stack.pop() and op1 not in stack:
                    return code
            elif opcode == "pushf":
                stack.append("flags")
            elif opcode == "popf":
                if stack.pop() != "flags":
                    return code
            else:
                return code
            i += 1
        code = "\n".join(lines[i:]) + "\n"
        lines = code.splitlines()
    return code

