from pyx86utils import *
from collections import deque


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
    while block1 is not None or block2 is not None:
        if block1 is not None:
            if blocks_visited2.count(block1) > 0:
                return block1
            if blocks_visited.count(block1) > 0:
                break
            blocks_visited.append(block1)
            add = block1.address
            if loop_p_1.count(add):
                raise Exception("loop")  # TODO: support loops
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
                raise Exception("loop") # TODO: support loops
            loop_p_2.append(add)
            if blocks.has_key(add):
                block2 = blocks[add]
            else:
                if block2.next_cond is not None:
                    block2 = get_common_block(block2.next, block2.next_cond, blocks, loop_p_2)
                else:
                    block2 = block2.next
                blocks[add] = block2
    return None
        
CONDITIONAL_JUMPS = "jz jnz".split(" ")  # TODO more


class Function(object):
    def __init__(self, executable, address):
        self.blocks_cache = {}
        instructions_blocks = {}
        self.blocks = {}
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
                if inst.opcode == "jmp" or inst.opcode == "retn":  # and not immediate
                    break
                if inst.opcode in CONDITIONAL_JUMPS:
                    block.next = get_block(inst.next)
                    block.next.froms.append(block)
                    block.next_cond = get_block(inst.operand1.value)
                    block.next_cond.froms.append(block)
                    break
                address = inst.next

