from pyx86utils import *
from collections import deque
import re

class Arch(object):
    REGS = [
        ["al", "ah", "ax", "eax", "rax"],
        ["bl", "bh", "bx", "ebx", "rbx"],
        ["cl", "ch", "cx", "ecx", "rcx"],
        ["dl", "dh", "dx", "edx", "rdx"],
        ["bpl", None, "bp", "ebp", "rbp"],
        ["spl", None, "sp", "esp", "rsp"],
        ["sil", None, "si", "esi", "rsi"],
        ["dil", None, "di", "edi", "rdi"],
        ["r8b", None, "r8w", "r8d", "r8"],
        ["r9b", None, "r9w", "r9d", "r9"],
        ["r10b", None, "r10w", "r10d", "r10"],
        ["r11b", None, "r11w", "r11d", "r11"],
        ["r12b", None, "r12w", "r12d", "r12"],
        ["r13b", None, "r13w", "r13d", "r13"],
        ["r14b", None, "r14w", "r14d", "r14"],
        ["r15b", None, "r15w", "r15d", "r15"],
    ]

    SIZES = {1: "byte", 2: "word", 4: "dword", 8: "qword"}
    def __init__(self, mode):
        self.mode = mode

    def native_size(self):
        return self.mode >> 3

    def pointer_size(self):
        return self.native_size()

    def get_registers(self):
        if self.mode == 32:
            return [x[3] for x in self.REGS[:8]]
        else:
            return [x[4] for x in self.REGS]

    def _get_reg(self, reg, size_index):
        for r in self.REGS:
            if reg in r:
                return r[size_index]
        return None

    def reg_byte(self, reg):
        return self._get_reg(reg, 0)

    def reg_byte_high(self, reg):
        return self._get_reg(reg, 1)

    def reg_word(self, reg):
        return self._get_reg(reg, 2)

    def reg_dword(self, reg):
        return self._get_reg(reg, 3)

    def reg_qword(self, reg):
        return self._get_reg(reg, 4)

    def reg_native(self, reg):
        if self.mode == 32:
            return self.reg_dword(reg)
        else:
            return self.reg_qword(reg)

    def _translate_var(self, var):
        fields = var.split(":")
        if len(fields) == 0:
            return None
        type = fields[0]
        size = self.native_size()
        special = False
        times = 1

        if type in ("S", "SU", "SB", "SS", "N"):
            expected_fields = 1
        elif type in ("R", "RS"):
            expected_fields = 2
        else:
            raise None

        if not expected_fields <= len(fields) <= expected_fields + 1:
            raise None

        if len(fields) > expected_fields :
            if type == "N":
                times = int(fields[-1], 16)
            else:
                if fields[-1] == "1h":
                    size = 1
                    special = True
                else:
                    size = int(fields[-1])

        if size not in self.SIZES:
            return None

        if type == "S":
            return self.SIZES[size]
        elif type == "SU":
            return self.SIZES[size].upper()
        elif type == "SS":
            return self.SIZES[size][:1].upper() + self.SIZES[size][1:]
        elif type == "SB":
            return self.SIZES[size][0]
        elif type == "N":
            return hex(size*times)[2:]
        elif type in ("R", "RS"):
            if type == "RS":
                if size == 1:
                    size = 2
                if size == 4 and self.mode == 64:
                    size = 8
            reg = fields[1]
            if size == 1:
                if special:
                    return self.reg_byte_high(reg)
                else:
                    return self.reg_byte(reg)
            elif size == 2:
                return self.reg_word(reg)
            elif size == 4:
                return self.reg_dword(reg)
            elif size == 8:
                return self.reg_qword(reg)
        return None

    def translate(self, s):
        """
        :param s: the format string. Syntax:
                    {S} - native size word (dword/qword)
                    {SU} - native size word uppercase
                    {SS} - native size word first letter uppercase
                    {SB} - native size letter {d/q}
                    {S:size} - specific size word
                    {SB:size} - specific size letter {d/q}
                    {N} - native size number
                    {N:times} - native size number multiplied by times
                    {R:reg} - native size register
                    {R:reg:size} - specific size version of reg (if size = 1h => high byte)
                    {RS:reg:size} - specific size version of reg upped to stack size
        :return:
        """
        ns = s
        for var in re.findall("\{([\w:]+)\}", s):
            nvar = self._translate_var(var)
            if nvar is None:
                raise Exception("Invalid var: %s" % var)
            ns = ns.replace("{%s}" % var, nvar)
        return ns

class ReaderException(Exception):
    pass


class InstructionReader(object):
    def __init__(self, file, address):
        self.address = address
        self.file = file

    def get(self):
        res = self.file.get_instruction(self.address)
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
        self.blocks_cache = None
        
    def __str__(self):
        s = ""
        for inst in self.instructions:
            if s:
                s += "\n"
            s += str(inst)
        return s


def get_common_block(block1, block2, blocks=None, loop_p=[]):
    blocks_visited = []
    blocks_visited2 = []
    if blocks is None:
        blocks = block1.blocks_cache
    loop_p_1 = list(loop_p)
    loop_p_2 = list(loop_p)
    #loop = False
    while block1 is not None or block2 is not None:
        if block1 is not None:
            if blocks_visited2.count(block1) > 0:
                return block1
            if blocks_visited.count(block1) > 0:
                break
            blocks_visited.append(block1)
            add = block1.address
            if loop_p_1.count(add):
                block1 = None
                #loop = True
                continue
            loop_p_1.append(add)
            if blocks.has_key(add):
                block1 = blocks[add]
            else:
                if block1.next_cond is not None:
                    block1 = get_common_block(block1.next, block1.next_cond, blocks, loop_p_1)
                else:
                    block1 = block1.next
                blocks[add] = block1
        if block2 is not None:
            if blocks_visited.count(block2) > 0:
                return block2
            if blocks_visited2.count(block2) > 0:
                break
            blocks_visited2.append(block2)
            add = block2.address
            if loop_p_2.count(add):
                block2 = None
                #loop = True
                continue
            loop_p_2.append(add)
            if blocks.has_key(add):
                block2 = blocks[add]
            else:
                if block2.next_cond is not None:
                    block2 = get_common_block(block2.next, block2.next_cond, blocks, loop_p_2)
                else:
                    block2 = block2.next
                blocks[add] = block2
    #if loop:
    #    raise Exception("loop") # TODO: support loops
    return None


class Loop(BaseException):
    def __init__(self, id):
        self.id = id

def get_common_block2(block1, block2, blocks=None, loop_p=[]):
    blocks_visited = []
    blocks_visited2 = []
    if blocks is None:
        blocks = block1.blocks_cache
    loop_p_1 = list(loop_p)
    loop_p_2 = list(loop_p)
    while block1 is not None or block2 is not None:
        if block1 is not None:
            if blocks_visited2.count(block1) > 0:
                return block1
            if blocks_visited.count(block1) > 0:
                break
            blocks_visited.append(block1)
            add = block1.address
            if loop_p_1.count(add):
                raise Loop(0)
            loop_p_1.append(add)
            if blocks.has_key(add):
                block1 = blocks[add]
            else:
                if block1.next_cond is not None:
                    try:
                        block1 = get_common_block2(block1.next, block1.next_cond, blocks, loop_p_1)
                    except Loop, e:
                        if e.id == 0:
                            block1 = block1.next_cond
                        elif e.id == 1:
                            block1 = block1.next
                else:
                    block1 = block1.next
                blocks[add] = block1
        if block2 is not None:
            if blocks_visited.count(block2) > 0:
                return block2
            if blocks_visited2.count(block2) > 0:
                break
            blocks_visited2.append(block2)
            add = block2.address
            if loop_p_2.count(add):
                raise Loop(1)
            loop_p_2.append(add)
            if blocks.has_key(add):
                block2 = blocks[add]
            else:
                if block2.next_cond is not None:
                    try:
                        block2 = get_common_block2(block2.next, block2.next_cond, blocks, loop_p_2)
                    except Loop, e:
                        if e.id == 0:
                            block2 = block2.next_cond
                        elif e.id == 1:
                            block2 = block2.next
                else:
                    block2 = block2.next
                blocks[add] = block2
    return None

CONDITIONAL_JUMPS = ("ja", "jae", "jb", "jbe", "jz", "jg", "jge", "jl", "jle", "jnz", "jno", "jnp", "jns", "jo", "jp" ,"js")


class Function(object):
    def __init__(self, file, address, stop_condition=None, filter=None):
        self.blocks_cache = {}
        instructions_blocks = {}
        self.blocks = {}
        self.mode = file.mode
        blocks_to_explores = deque()

        def get_block(address):
            if self.blocks.has_key(address):
                return self.blocks[address]
            block = FunctionBlock(address)
            block.blocks_cache = self.blocks_cache
            self.blocks[address] = block
            blocks_to_explores.append(block)
            return block
        self.start_block = get_block(address)
        while len(blocks_to_explores):
            block = blocks_to_explores.popleft()
            address = block.address
            if address in instructions_blocks:
                # Derive the block from the other block
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
                if old_block.next is not None:
                    old_block.next.froms.remove(old_block)
                    old_block.next.froms.append(block)
                if old_block.next_cond is not None:
                    old_block.next_cond.froms.remove(old_block)
                    old_block.next_cond.froms.append(block)
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
                        nblock.blocks_cache = self.blocks_cache
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
                        if old_block.next is not None:
                            old_block.next.froms.remove(old_block)
                            old_block.next.froms.append(nblock)
                        if old_block.next_cond is not None:
                            old_block.next_cond.froms.remove(old_block)
                            old_block.next_cond.froms.append(nblock)
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
                real_address = address
                if filter is not None:
                    naddress = filter(address)
                    while naddress != address:
                        address = naddress
                        naddress = filter(address)
                inst = file.get_instruction(address)
                inst.address = real_address
                if stop_condition is not None and stop_condition(inst):
                    # It is here, because the stop condition may be a jump
                    block.instructions.append(inst)
                    break
                if inst.opcode == "jmp" and inst.operands[0].is_immediate():
                    # Ignore jmps
                    address = inst.operands[0].value
                    continue
                block.instructions.append(inst)
                instructions_blocks[inst.address] = block
                if inst.opcode == "jmp" or inst.opcode == "ret":  # and not immediate
                    break
                if inst.opcode in CONDITIONAL_JUMPS:
                    block.next = get_block(inst.next)
                    block.next.froms.append(block)
                    block.next_cond = get_block(inst.operands[0].value)
                    block.next_cond.froms.append(block)
                    break
                address = inst.next
        self._clean_blocks()

    def _clean_blocks(self):
        for block in self.blocks.values():
            if len(block.instructions) == 0 and block.next_cond is None:
                block.next.froms.remove(block)
                for f in block.froms:
                    if f.next == block:
                        f.next = block.next
                        block.next.froms.append(f)
                    if f.next_cond == block:
                        f.next_cond = block.next
                        # We assume that f.next != f.next_cond
                        # Because we doesn't even handle this case in the main function
                        block.next.froms.append(f)

    def get_end_block(self):
        block = self.start_block
        while block.next is not None:
            if block.next_cond is not None:
                block = get_common_block2(block.next, block.next_cond)
                if block is None:
                    return None
            else:
                block = block.next
        return block

