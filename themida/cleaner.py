import instruction
import oreans_deobfuscator


# Just a proxy for the class
class Cleaner(object):
    # pe should have the function get_instruction_at
    def __init__(self, executable):
        self.executable = executable
        def read(address, size):
            return executable.read(address, size)
        self.cleaner = oreans_deobfuscator.Cleaner(read, self.executable.mode)


    def set_reg_unused(self, reg):
        self.cleaner.set_reg_unused(reg)

    def set_option(self, option, value):
        self.cleaner.set_option(option, value)
        
    def get_clean_instruction(self, address):
        next_address, data = self.cleaner.get_clean_instruction(address)
        if next_address is None:
            return None
        inst = instruction.Instruction(data, address, self.executable.mode)
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
        res = self.cleaner.get_clean_instruction(self.address)
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
    def __init__(self, executable):
        self.executable = executable
        self.instructions = {}
        self.loop = {}

    def get_next_real_instruction(self, address):
        if self.instructions.has_key(address):
            return self.instructions[address]
        if self.loop.has_key(address):
            raise Exception("loop")
        self.loop[address] = 1
        inst = self.executable.get_instruction(address)
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
