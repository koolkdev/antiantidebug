import struct
import instruction
import os

CONDITIONAL_JUMPS = "JO JNO JB JAE JZ JNZ JBE JA JS JNS JP JNP JL JGE JLE JG JCXZ LOOP LOOPE".split(" ")

class BytesReader(object):
    def __init__(self, file, address):
        self.file = file
        self.address = address

    def read(self, length):
        res = self.file.read(self.address, length)
        self.address += length
        return res


# TODO: Move to cisc vm
class VMReadInfo(object):
    def __init__(self, reader):
        self.size = 0

    def decode(self, value, key):
        pass
    
    OPERATIONS = {"add": long.__add__,
                  "sub": long.__sub__,
                  "xor": long.__xor__}

    SIZES = {1: "B",
             2: "H",
             4: "L",
             8: "Q"}

    def read(self, bytes_reader):
        return struct.unpack("<%s" % self.SIZES[self.size], bytes_reader.read(self.size))[0]
        
    @staticmethod
    def do_operation(operation, left, right, size):
        return VMReadInfo.OPERATIONS[operation](long(long(left) % (1<<(8*size))), long(long(right) % (1<<(8*size)))) % (1 << (8*size))
            
class VMKey(object):
    def __init__(self, key):
        pass

INSTRUCTIONS_32 = {x.split(" ", 1)[0]: x.split(" ", 1)[1] for x in open(r"%s\templates\instructions_32.txt" % os.path.dirname(os.path.abspath(__file__)), "rb").read().splitlines()}
INSTRUCTIONS_64 = {x.split(" ", 1)[0]: x.split(" ", 1)[1] for x in open(r"%s\templates\instructions_64.txt" % os.path.dirname(os.path.abspath(__file__)), "rb").read().splitlines()}

class VMInstruction(object):
    def __init__(self, name, *args):
        self.name = name
        self.args = list(args)
        self.info = {}
        self.address = 0

    def set_info(self, name, value):
        self.info[name] = value

    def to_asm(self, regs, mode):
        if mode == 32:
            insts = INSTRUCTIONS_32
        else:
            insts = INSTRUCTIONS_64
        if not insts.has_key(self.name):
            raise Exception("Couldn't translate %s to assembly" % self)
        inst = ""
        next_special = None
        for c in insts[self.name]:
            if next_special:
                arg = self.args[int(c)]
                if next_special == "~":
                    inst += instruction.Arch(mode).reg_byte(regs[arg])
                elif next_special == "!":
                    inst += instruction.Arch(mode).reg_byte_high(regs[arg])
                elif next_special == "@":
                    inst += instruction.Arch(mode).reg_word(regs[arg])
                elif next_special == "#":
                    inst += instruction.Arch(mode).reg_dword(regs[arg])
                elif next_special == "%":
                    inst += instruction.Arch(mode).reg_qword(regs[arg])
                elif next_special == "$":
                    inst += "%x" % arg
                elif next_special == "&":
                    inst += "label_%x" % arg
                next_special = None
            elif c in "#@~!$&%":
                next_special = c
            else:
                inst += c
        return inst

    def __repr__(self):
        return "<VMInstruction '%s %s'>" % (self.name, " ".join(map(str, self.args)))
    
    def __str__(self):
        return "0x%08X: %s %s" % (self.address, self.name, " ".join(["0x%X" % x for x in self.args]))
    

class ReaderException(Exception):
    pass

class VMInstructionsReader(object):
    def __init__(self, instructions):
        self.index = 0
        self.instructions = instructions
        self.history = []

    def push(self):
        self.history.append(self.index)
        
    def pop(self):
        self.index = self.history.pop()
        
    def get(self):
        if self.index >= len(self.instructions):
            return None
        self.index += 1
        return self.instructions[self.index-1]
    
    def get_cond(self, cond):
        old_index = self.index
        res = self.get()
        if not res or not cond(res):
            self.index = old_index
            raise ReaderException("Wrong condition: %s" % str(res))
        return res
