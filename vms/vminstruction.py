import struct

CONDITIONAL_JUMPS = "JA JNB JB JE JG JGE JL JLE JBE JNO JPO JNS JO JPE JS JNE JCXZ LOOP LOOPE".split(" ")

class BytesReader(object):
    def __init__(self, executable, address):
        self.executable = executable
        self.address = address

    def read(self, length):
        res = self.executable.read(self.address, length)
        self.address += length
        return res

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
             4: "L"}

    def read(self, bytes_reader):
        return struct.unpack("<%s" % self.SIZES[self.size], bytes_reader.read(self.size))[0]
        
    @staticmethod
    def do_operation(operation, left, right, size):
        return VMReadInfo.OPERATIONS[operation](long(long(left) % (1<<(8*size))), long(long(right) % (1<<(8*size)))) % (1 << (8*size))
            
class VMKey(object):
    def __init__(self, key):
        pass

INSTRUCTIONS = {x.split(" ", 1)[0]: x.split(" ", 1)[1] for x in open(r"vms\templates\ag_instructions.txt", "rb").read().splitlines()}

class VMInstruction(object):
    def __init__(self, name, *args):
        self.name = name
        self.args = list(args)
        self.info = {}
        self.address = 0

    def set_info(self, name, value):
        self.info[name] = value

    def to_asm(self, regs):
        if not INSTRUCTIONS.has_key(self.name):
            raise Exception("Couldn't translate %s to assembly" % self)
        inst = ""
        next_special = None
        for c in INSTRUCTIONS[self.name]:
            if next_special:
                arg = self.args[int(c)]
                if next_special == "#":
                    inst += regs[arg]
                elif next_special == "@":
                    inst += {"eax": "ax", "ebx": "bx", "ecx": "cx", "edx": "dx", "esi": "si", "edi": "di", "ebp": "bp", "esp": "sp"}[regs[arg]]
                elif next_special == "~":
                    inst += {"eax": "al", "ebx": "bl", "ecx": "cl", "edx": "dl"}[regs[arg]]
                elif next_special == "!":
                    inst += {"eax": "ah", "ebx": "bh", "ecx": "ch", "edx": "dh"}[regs[arg]]
                elif next_special == "$":
                    inst += "%X" % arg
                elif next_special == "&":
                    inst += "label_%X" % arg
                next_special = None
            elif c in "#@~!$&":
                next_special = c
            else:
                inst += c
        return inst

    def __repr__(self):
        return "<VMInstruction '%s %s'>" % (self.name, " ".join(map(str, self.args)))
    
    def __str__(self):
        return "0x%08X: %s %s" % (self.address, self.name, " ".join(["%X" % x for x in self.args]))
    

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
        self.index = self.history.pop(0)
        
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
