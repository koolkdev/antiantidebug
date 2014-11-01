import pydasm
from collections import deque

REGS = {"REG_DWORD": ["eax",  "ecx",  "edx",  "ebx",  "esp",  "ebp",  "esi",  "edi"],
        "REG_WORD": ["ax",   "cx",   "dx",   "bx",   "sp",   "bp",   "si",   "di"],
        "REG_BYTE": ["al",   "cl",   "dl",   "bl",   "ah",   "ch",   "dh",   "bh"],
        "REG_SEGMENT": ["es",   "cs",   "ss",   "ds",   "fs",   "gs",   "??",   "??"],
	"REG_DEBUG": ["dr0",  "dr1",  "dr2",  "dr3",  "dr4",  "dr5",  "dr6",  "dr7"],
        "REG_CONTROL": ["cr0",  "cr1",  "cr2",  "cr3",  "cr4",  "cr5",  "cr6",  "cr7"],
        "REG_TEST": ["tr0",  "tr1",  "tr2",  "tr3",  "tr4",  "tr5",  "tr6",  "tr7"],
	"REG_XMM": ["xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7"],
	"REG_MMX": ["mm0",  "mm1",  "mm2",  "mm3",  "mm4",  "mm5",  "mm6",  "mm7"],
	"REG_FPU": ["st(0)","st(1)","st(2)","st(3)","st(4)","st(5)","st(6)","st(7)"],
	"REG_BRANCH": ["??",   "(bnt)","??",   "(bt)", "??",   "??",   "??",   "??"]}



class Operand(object):
    def __init__(self):
        self.string = ""
        self.size = 0
        
    def create_from_info(self, size, string):
        self.size = size
        self.string = string

    def __str__(self):
        return self.string

    def __eq__(self, other):
        raise NotImplemented()

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def is_reg(self, reg = None):
        if not isinstance(self, RegisterOperand):
            return False
        if reg:
            return self.value == reg
        return True

    def is_immediate(self, value = None):
        if not isinstance(self, ImmediateOperand):
            return False
        if value != None:
            return self.get_value() == (value % (1<<32))
        return True

    def is_memory(self):
        return isinstance(self, MemoryOperand)

    def is_none(self):
        return isinstance(self, NoneOperand)

class NoneOperand(Operand):
    def create_from_info(self, address, inst, operand, string):
        pass
    
    def __eq__(self, other):
        return other.is_none()

OT_TO_SIZE = {
    0x02000000: lambda mode: 1,
    0x03000000: lambda mode: 2 if mode else 1,
    0x04000000: lambda mode: 4,
    0x05000000: lambda mode: 8,
    0x06000000: lambda mode: 16,
    0x07000000: lambda mode: 2 if mode else 4,
    0x08000000: lambda mode: 2,
    0x09000000: lambda mode: 6,
    0x0a000000: lambda mode: 8,
    0x0b000000: lambda mode: 16,
    0x0c000000: lambda mode: 16,
    0x0d000000: lambda mode: 6,
    0x0e000000: lambda mode: 16,
    0x0f000000: lambda mode: 16,
    0x10000000: lambda mode: 4,
    0x11000000: lambda mode: 10
    }
def OPERAND_SIZE(operand, mode):
    if OT_TO_SIZE.has_key(operand.flags & 0xff000000):
        return OT_TO_SIZE[operand.flags & 0xff000000](mode)
    return 0
    
class MemoryOperand(Operand):
    def __init__(self):
        Operand.__init__(self)
        self.segment = None
        self.index = None
        self.base = None
        self.scale = 0
        self.displacement = 0
        self.dispsize = 0
        
    def __eq__(self, other):
        return other.is_memory() and self.segment == other.segment and self.index == other.index and self.base == other.base and self.scale == other.scale and self.displacement == other.displacement and self.dispsize == other.dispsize and self.size == other.size

    def create_from_info(self, address, inst, operand, string):
        assert operand.type == pydasm.OPERAND_TYPE_MEMORY

        if (inst.flags & 0x00ff0000) >> 16:
            self.segment = REGS["REG_SEGMENT"][((inst.flags & 0x00ff0000) >> 16) - 1]
        else:
            self.segment = None
            
        if (inst.flags & 0x0000f000) >> 12:
            regtype = "REG_WORD"
        else:
            regtype = "REG_DWORD"

        if operand.indexreg != pydasm.REGISTER_NOP:
            self.index = REGS[regtype][operand.indexreg]
        else:
            self.index = None
            
        if operand.basereg != pydasm.REGISTER_NOP:
            self.base = REGS[regtype][operand.basereg]
        else:
            self.base = None

        self.scale = operand.scale
        self.displacement = operand.displacement % (1<<(operand.dispbytes*8))
        self.dispsize = operand.dispbytes
        
        Operand.create_from_info(self, OPERAND_SIZE(operand, (inst.flags & 0x00000f00) >> 8), string)

    def __str__(self):
        res = ""
        if self.size == 4:
            res += "dword "
        elif self.size == 2:
            res += "word "
        elif self.size == 1:
            res += "byte "
        if self.segment:
            res += self.segment + ":"
        res += "["
        if self.base:
            res += self.base
        if self.index:
            if self.base:
                res += "+" + self.index
            else:
                res += self.index
            if self.scale != 1:
                res += "*%d" % self.scale
        if self.dispsize:
            if (self.index != None or self.base != None):
                if self.displacement & (1<<(self.dispsize*8-1)):
                    displacement = self.displacement
                    if self.dispsize == 1:
                        displacement = (~displacement) & 0xff
                    elif self.dispsize == 2:
                        displacement = (~displacement) & 0xffff
                    elif self.dispsize == 4:
                        displacement = (~displacement) & 0xffffffff
                    res += "-0x%x" % (displacement + 1)
                else:
                    res += "+0x%x" % self.displacement
            else:
                res += "0x%x" % self.displacement
            
        res += "]"
        return res

    def is_mem_esp(self):
        return self.base in ("sp", "esp")
                
                

FLAGS_TO_REG_TYPE = {0x00000200: "REG_SEGMENT",
                     0x00000400: "REG_FPU"}

AM_TO_REG_TYPE_DICT = {0x00210000: lambda flags: FLAGS_TO_REG_TYPE[flags & 0x00000f00] if FLAGS_TO_REG_TYPE.has_key(flags & 0x00000f00) else "REG_DWORD",
                  0x00040000: lambda flags: "REG_DWORD",
                  0x00050000: lambda flags: "REG_DWORD",	    
                  0x000C0000: lambda flags: "REG_DWORD",
                  0x00020000: lambda flags: "REG_CONTROL",
                  0x00030000: lambda flags: "REG_DEBUG",
                  0x000D0000: lambda flags: "REG_SEGMENT",
                  0x000E0000: lambda flags: "REG_TEST",
                  0x000A0000: lambda flags: "REG_MMX",
                  0x000B0000: lambda flags: "REG_MMX",
                  0x000F0000: lambda flags: "REG_XMM",
                  0x00100000: lambda flags: "REG_XMM"}

OT_TO_REG_TYPE = {0x02000000: lambda mode: "REG_BYTE",
                  0x07000000: lambda mode: "REG_WORD" if mode else "REG_DWORD",
                  0x08000000: lambda mode: "REG_WORD",
                  0x04000000: lambda mode: "REG_DWORD"}

def AM_TO_REG_TYPE(flags, mode):
    regtype = "REG_DWORD"
    if AM_TO_REG_TYPE_DICT.has_key(flags & 0x00ff0000):
        regtype = AM_TO_REG_TYPE_DICT[flags & 0x00ff0000](flags)
    if regtype == "REG_DWORD":
        if OT_TO_REG_TYPE.has_key(flags & 0xff000000):
            regtype = OT_TO_REG_TYPE[flags & 0xff000000](mode)
    return regtype
        
class RegisterOperand(Operand):
    def __init__(self):
        Operand.__init__(self)
        self.value = ""
        
    def __eq__(self, other):
        return other.is_register() and self.value == other.value
        
    def create_from_info(self, address, inst, operand, string):
        assert operand.type == pydasm.OPERAND_TYPE_REGISTER
        regtype = AM_TO_REG_TYPE(operand.flags, (inst.flags & 0x00000f00) >> 8)

        self.value = REGS[regtype][operand.reg]

        Operand.create_from_info(self, OPERAND_SIZE(operand, (inst.flags & 0x00000f00) >> 8), string)

    def __str__(self):
        return self.value

    def is_reg_esp(self):
        return self.value in ("esp", "sp")
    
class ImmediateOperand(Operand):
    def __init__(self):
        Operand.__init__(self)
        self.value = 0
        self.is_address = False
        
    def __eq__(self, other):
        return other.is_immediate() and self.value == other.value and self.is_address == other.is_address
        
    def create_from_info(self, address, inst, operand, string):
        assert operand.type == pydasm.OPERAND_TYPE_IMMEDIATE
        
        size = OPERAND_SIZE(operand, (inst.flags & 0x00000f00) >> 8)
        self.value = operand.immediate
        if operand.flags & 0x00ff0000 == 0x00070000:
            self.value += address + inst.length
            self.is_address = True
        else:
            self.value %= (1 << (size * 8))



        # TODO
        assert operand.flags & 0x00ff0000 != 0x00010000

        Operand.create_from_info(self, size, string)

    # Return dword value
    def get_value(self):
        value = self.value
        if not self.is_address:
            if self.value & (1<<(self.size*8-1)):
                if self.size == 1:
                    value = (~value) & 0xff
                elif self.size == 2:
                    value = (~value) & 0xffff
                elif self.size == 4:
                    value = (~value) & 0xffffffff
                value = - (value + 1)
        return value % (1<<32)
    
    def __str__(self):
        return "0x%x" % self.get_value()
    
OPERANDS = {
    pydasm.OPERAND_TYPE_IMMEDIATE: ImmediateOperand,
    pydasm.OPERAND_TYPE_MEMORY: MemoryOperand,
    pydasm.OPERAND_TYPE_REGISTER: RegisterOperand,
    pydasm.OPERAND_TYPE_NONE: NoneOperand}

class Instruction(object):        
    def __init__(self, address, data):
        inst = pydasm.get_instruction(data, pydasm.MODE_32)
        self.address = address
        if inst != None:
            if OPERANDS.has_key(inst.op1.type):
                self.operand1 = OPERANDS[inst.op1.type]()
                self.operand1.create_from_info(address, inst, inst.op1, pydasm.get_operand_string(inst, 0, pydasm.FORMAT_INTEL, address))
            else:
                self.operand1 = None
            if OPERANDS.has_key(inst.op2.type):
                self.operand2 = OPERANDS[inst.op2.type]()
                self.operand2.create_from_info(address, inst, inst.op2, pydasm.get_operand_string(inst, 1, pydasm.FORMAT_INTEL, address))
            else:
                self.operand2 = None
            if OPERANDS.has_key(inst.op3.type):
                self.operand3 = OPERANDS[inst.op3.type]()
                self.operand3.create_from_info(address, inst, inst.op3, pydasm.get_operand_string(inst, 2, pydasm.FORMAT_INTEL, address))
            else:
                self.operand3 = None

            self.opcode = pydasm.get_mnemonic_string(inst, pydasm.FORMAT_INTEL).split(" ")[0]
            self.length = inst.length
            self.string = pydasm.get_instruction_string(inst, pydasm.FORMAT_INTEL, address)
        else:
            self.opcode = "db 0x%x" % ord(data[0])
            self.operand1 = NoneOperand()
            self.operand2 = NoneOperand()
            self.operand3 = NoneOperand()
            self.length = 1
        self.next = self.address + self.length
        self.bytes = data[:self.length]
        
    def __str__(self):
        res = "%s" % self.opcode
        if not self.operand1.is_none():
            res += " " + str(self.operand1)
            if not self.operand2.is_none():
                if self.opcode in ("movzx", "movsx"):
                    res += ", " + str(self.operand2)
                else:
                    res += ", " + str(self.operand2).split(" ")[-1]
                if not self.operand3.is_none():
                    res += ", " + str(self.operand3)
        return res

    def __repr__(self):
        return "<instruction.Instruction '%s' >" % str(self)
    
class ReaderException(Exception):
    pass
    
class InstructionReader(object):
    def __init__(self, executable, address):
        self.address = address
        self.executable = executable

    def get(self):
        res = self.executable.get_instruction(self.address)
        self.address = res.next
        return res

    def get_cond(self, cond):
        old_address = self.address
        res = self.get()
        if not cond(res):
            self.address = old_address
            raise ReaderException("Wrong condition: %s" % str(res))
        return res
        
class FunctionBlock(object):
    def __init__(self, address):
        self.address = address
        self.instructions = []
        self.next = None
        self.next_cond = None
        self.froms = []
        
    def __str__(self):
        s = ""
        for inst in self.instructions:
            if s:
                s += "\n"
            s += str(inst)
        return s

def get_common_block(block1, block2):
    blocks_visited = []
    blocks_visited2 = []
    while block1 != None or block2 != None:
        if block1 != None:
            if blocks_visited2.count(block1) > 0:
                return block1
            if blocks_visited.count(block1) > 0:
                break
            blocks_visited.append(block1)
            if block1.next_cond != None:
                block1 = get_common_block(block1.next, block1.next_cond)
            else:
                block1 = block1.next
        if block2 != None:
            if blocks_visited.count(block2) > 0:
                return block2
            if blocks_visited2.count(block2) > 0:
                break
            blocks_visited2.append(block2)
            if block2.next_cond != None:
                block2 = get_common_block(block2.next, block2.next_cond)
            else:
                block2 = block2.next
    return None
        
        
            
        
        
CONDITIONAL_JUMPS = "jz jnz".split(" ") # TODO more
class Function(object):
    def __init__(self, executable, address):
        instructions_blocks = {}
        self.blocks = {}
        blocks_to_explores = deque()
        def get_block(address):
            if self.blocks.has_key(address):
                return self.blocks[address]
            block = FunctionBlock(address)
            self.blocks[address] = block
            blocks_to_explores.append(block)
            return block
        self.start_block = get_block(address)
        while len(blocks_to_explores):
            block = blocks_to_explores.popleft()
            address = block.address
            if instructions_blocks.has_key(address):
                # Dirive the block from the other block
                old_block = instructions_blocks[address]
                index = None
                for i in xrange(len(old_block.instructions)):
                    if old_block.instructions[i].address == address:
                        index = i
                        break
                assert index is not None
                block.instructions = old_block.instructions[index:]
                old_block.instructions = old_block.instructions[:index]
                for inst in block.instructions:
                    instructions_blocks[inst.address] = block
                block.next = old_block.next
                block.next_cond = old_block.next_cond
                block.froms.append(old_block)
                old_block.next = block
                old_block.next_cond = None
                continue
            while True:
                if instructions_blocks.has_key(address):
                    if instructions_blocks[address].address != address:
                        nblock = FunctionBlock(address)
                        self.blocks[address] = nblock
                        old_block = instructions_blocks[address]
                        index = None
                        for i in xrange(len(old_block.instructions)):
                            if old_block.instructions[i].address == address:
                                index = i
                                break
                        assert index is not None
                        nblock.instructions = old_block.instructions[index:]
                        old_block.instructions = old_block.instructions[:index]
                        for inst in nblock.instructions:
                            instructions_blocks[inst.address] = nblock
                        nblock.next = old_block.next
                        nblock.next_cond = old_block.next_cond
                        nblock.froms.append(old_block)
                        old_block.next = nblock
                        old_block.next_cond = None
                        block.next = nblock
                        nblock.froms.append(block)
                    else:
                        block.next = instructions_blocks[address]
                        instructions_blocks[address].froms.append(block)
                    break
                inst = executable.get_instruction(address)
                if inst.opcode == "jmp" and inst.operand1.is_immediate():
                    # Ignore jmps
                    address = inst.operand1.value
                    continue
                block.instructions.append(inst)
                instructions_blocks[inst.address] = block
                if inst.opcode == "jmp" or inst.opcode == "retn": # and not immediate
                    break
                if inst.opcode in CONDITIONAL_JUMPS:
                    block.next = get_block(inst.next)
                    block.next.froms.append(block)
                    block.next_cond = get_block(inst.operand1.value)
                    block.next_cond.froms.append(block)
                    break
                address = inst.next
        
        