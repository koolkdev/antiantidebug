import instruction
import ctypes

REG_EAX = 0x30
REG_ECX = 0x31
REG_EDX = 0x32
REG_EBX = 0x33
REG_ESP = 0x34
REG_EBP = 0x35
REG_ESI = 0x36
REG_EDI = 0x37

READERFUNC = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_void_p)
cleaner_dll = ctypes.CDLL(r"themida\themidacleaner.dll")
cleaner_dll.create_cleaner.argtypes = [READERFUNC]
cleaner_dll.create_cleaner.restype = ctypes.c_void_p
cleaner_dll.clean_instruction.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
cleaner_dll.clean_instruction.restype = ctypes.c_int
cleaner_dll.destroy_cleaner.argtypes = [ctypes.c_void_p]
cleaner_dll.destroy_cleaner.restype = None
cleaner_dll.set_reg_unused.argtypes = [ctypes.c_void_p, ctypes.c_int]
cleaner_dll.set_reg_unused.restype = None
cleaner_dll.set_option.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
cleaner_dll.set_option.restype = None

class Cleaner(object):
    # pe should have the function get_instruction_at
    def __init__(self, executable):
        self.cache = {}
        self.executable = executable
        def __read(address, buffer_pointer):
            #print hex(address)
            try:
                data = executable.read(address, 20)
            except:
                return 0
            ctypes.memmove(buffer_pointer, ctypes.c_buffer(data), 20)
            return 1
        # We need to keep ref to this...
        self.read_func = READERFUNC(__read)
        self.cleaner_obj = cleaner_dll.create_cleaner(self.read_func)


    def set_reg_unused(self, reg):
        if reg == "eax":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_EAX)
        elif reg == "ecx":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_ECX)
        elif reg == "edx":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_EDX)
        elif reg == "ebx":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_EBX)
        elif reg == "esp":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_ESP)
        elif reg == "ebp":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_EBP)
        elif reg == "esi":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_ESI)
        elif reg == "edi":
            cleaner_dll.set_reg_unused(self.cleaner_obj, REG_EDI)
        else:
            raise ValueError("Invalid register %s" % reg)

    def set_option(self, option, value):
        cleaner_dll.set_option(self.cleaner_obj, option, value)        
        
    def get_clean_instruction(self, address):
        b = ctypes.c_buffer(20)
        try:
            next_address = cleaner_dll.clean_instruction(self.cleaner_obj, address, b)
        except:
            return self.executable.get_instruction(address)
        if next_address == 0:
            return None
        inst = instruction.Instruction(address, b.raw)
        inst.next = next_address
        return inst

    def get_reader(self, address):
        return CleanReader(self, address)

    def __del__(self):
        cleaner_dll.destroy_cleaner(self.cleaner_obj)
        
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
        if inst.opcode == "jmp" and inst.operand1.is_immediate():
            return self.get_next_real_instruction(inst.operand1.value)
        elif inst.opcode in ("ja", "jnb", "jc", "jbe", "jz", "jg", "jge", "jl", "jle", "jnz", "jno", "jpo", "jns", "jo", "jp", "js"):
            next1 = self.get_next_real_instruction(inst.next)
            next2 = self.get_next_real_instruction(inst.operand1.value)
            if next1.address != next2.address:
                return inst
            return next1
        elif inst.opcode == "pusha":
            next = self.get_next_real_instruction(inst.next)
            if next.opcode != "popa":
                return inst
            return self.get_next_real_instruction(next.next)
        elif inst.opcode == "pushf":
            next = self.get_next_real_instruction(inst.next)
            if next.opcode != "popf":
                return inst
            return self.get_next_real_instruction(next.next)
        elif inst.opcode == "push" and inst.operand1.is_reg():
            next = self.get_next_real_instruction(inst.next)
            if next.opcode == "pop" and next.operand1.is_reg(inst.operand1.value):
                return self.get_next_real_instruction(next.next)
            if inst.operand1.is_reg("eax") and next.opcode == "push" and next.operand1.is_reg("edx"):
                next2 = self.get_next_real_instruction(next.next)
                next3 = self.get_next_real_instruction(next2.next)
                next4 = self.get_next_real_instruction(next3.next)
                if next2.opcode == "rdtsc" and next3.opcode == "pop" and next3.operand1.is_reg("edx") and next4.opcode == "pop" and next4.operand1.is_reg("eax"):
                    return self.get_next_real_instruction(next4.next)
            return inst
        return inst


"""   

MATH_OPERANDS = ("inc", "dec", "add", "sub", "shr", "shl", "not", "or", "and", "xor", "neg")
def math_operation(num, inst, value, flags):
    

    
COND_JUMPS = {

    def get_clean_instruction(self, address, ignore_jumps = True):
        if self.cache.has_key(address):
            return self.cache[address]
        inst = self.pe.get_instruction_at(address)
        address += inst.length
        if ignore_jumps and inst.opcode == "jmp" and inst.operand1.is_immediate() and innst.operand1.size == 4:
            return get_clean_instruction(inst.operand1.value)

        changed = True
        while changed:
            changed = False
            if inst.opcode in MATH_OPERANDS or inst.opcode in ("push", "pop", "mov", "xchg"):
                for cleaner in CLEANERS:
                    res = cleaner(self, inst)
                    if res:
                        inst.next = res
                        changed = True
                        break

        cache[address] = inst
        return cache[address]
       
def is_inc(cleaner, inst):
    return inst.opcode =="inc" or (cleanIncDec(cleaner, inst) and inst.opcode == "inc")

def is_dec(cleaner, inst, do_change = True):
    if inst.opcode == "dec":
        return True
    if do_change:
        return cleanIncDec(cleaner, inst) and inst.opcode == "dec"
    else:
        tempinst = inst.copy()
        return cleanIncDec(cleaner, tempinst) and inst.opcode == "dec"

def cleanIncDec(cleaner, inst):
    if (inst.opcode == "add" and inst.operand2.is_immediate(1)) or (inst.opcode == "sub" and inst.operand2.immediate(-1)):
        inst.opcode = "inc"
        inst.operand2 = instruction.NoneOperand()
        return inst.next
    elif (inst.opcode == "add" and inst.operand2.is_immediate(-1)) or (inst.opcode == "sub" and inst.operand2.immediate(1)):
        inst.opcode = "dec"
        inst.operand2 = instruction.NoneOperand()
        return inst.next
    return 0
    
def mergeMemorySplit(cleaner, inst):
    if inst.opcode != "push" or not inst.operand1.is_reg():
        return 0
    used_reg = inst.operand1.value
    if inst.operand1.size != 4 or used_reg== "esp":
        return 0

    next = cleaner.get_clean_instruction(inst.next)
    if next.opcode != "mov" or not next.operand1.is_reg(used_reg):
        return 0

    mem = instruction.MemoryOperand()
    if next.operand2.is_reg() and next.operand2.value != used_reg and next.operand2.value != "esp":
        mem.index = next.operand2.value
        next = cleaner.get_clean_instruction(next.next)
        if next.opcode == "shl":
            if not next.operand1.is_reg(used_reg) or not next.operand2.is_immediate() or next.operand2.size != 1:
                return 0
            if 1 <= next.operand2.value <= 3:
                mem.scale = 1 << next.operand2.value
            else:
                return 0
            next = cleaner.get_clean_instruction(next.next)
        else:
            mem.scale = 1
        if next.opcode !="add" or not next.operand1.is_reg(used_reg):
            return 0
    if not next.operand2.is_immediate(): # We know that it is dword because of preivous checks
        return 0
    mem.displacement = next.operand2.value
    mem.dispsize = 4

    next = cleaner.get_clean_instruction(next.next)
    if next.opcode != "add" or not next.operand1.is_reg(used_reg) or not next.operand2.is_reg() or next.operand2.value == used_reg or next.operand2.value == "esp":
        return 0

    mem.base = next.operand2.value
    main = cleaner.get_clean_instruction(next.next)
    if not main.opcode in ("add", "xor", "mov"):
        return 0

    if main.operand2.is_memory() and (main.operand2.base == used_reg or main.operand2.index == used_reg):
        memory_operand = "operand2"
        other_operand = "operand1"
    elif main.operand1.is_memory() and (main.operand1.base == used_reg or main.operand2.index == used_reg):
        memory_operand = "operand1"
        other_operand = "opernad2"
    else:
        return 0

    # I think that we can give up on this check
    if not main.__getattribute__(other_operand).is_reg() and not main.__getattribute__(other_operand).is_immediate():
        return 0
        
    next = cleaner.get_clean_instruction(main.next)
    if next.opcode != "pop" or not next.operand1.is_reg(next.operand1.value):
        return 0

    inst.opcode = main.opcode
    mem.size = main.__getattribute__(other_operand).size
    inst.__setattr__(other_operand, main.__getattribute__(other_operand).copy())
    inst.__setattr__(memory_operand, mem)
                
    return next.next

# ADD/SUB REG/[ESP+..]
# =>
# ADD/SUB REG/[ESP+..], X
# ADD/SUB REG/[ESP+..], REG/[ESP+..]
# SUB/ADD REG/[ESP+..], X
def clearJunkAddSub(cleaner, inst):
    if not inst.opcode in ("add", "sub"):
        return 0
    if not (inst.operand1.is_reg() or (inst.operand1.is_memory() and inst.operand1.is_mem_esp())):
        return 0
    if not inst.operand2.is_immediate():
        return 0
    
    main = cleaner.get_clean_instruction(inst.next)
    if not (main.opcode in ("add", "sub") and main.operand1 == inst.operand1 and (inst.operand2.is_reg() or (inst.operand2.is_memory() and inst.operand2.base.is_mem_esp()))):
        return 0

    next = cleaner.get_clean_instruction(main.next)
    if not (next.opcode in ("add", "sub") and next.opcode != inst.opcode and next.operand1 == inst.operand1 and next.operand2 == inst.operand2):
        return 0

    inst.opcode = main.opcode
    inst.operand1 = main.operand1.copy()
    inst.operand2 = main.operand2.copy()
            
    return next.next

# NEG ...
# =>
# NOT/DEC ...
# INC/NOT ...
    
def clearNotIncDecNot(cleaner, inst):
    if not ((inst.opcode == "not" or is_dec(cleaner, inst, False)) and ((inst.operand1.is_reg() and not inst.operand1.is_reg_esp()) or (inst.operand1.is_mem() and not inst.operand1.is_mem_esp()))):
        return 0

    next = cleaner.get_clean_instruction(inst.next)
    if not (((is_inc(next) and inst.opcode == "not") or (is_dec(inst) and next.opcode == "not")) and inst.operand1 == next.operand1):
        return 0

    inst.opcode = "neg"
    return next.next

# NEG ..
# =>
# PUSH 0/-2/-4
# SUB [ESP], ...
# POP .... / MOV ...., [ESP]. ADD ESP, 2/4
def clear0Minus(cleaner, inst):
    if inst.opcode != "push" or not inst.operand1.is_immediate():
        return 0
    size = inst.operand1.size
    real_size = size
    is_esp = False
    if inst.operand1.is_immediate(0):
        pass
    elif inst.operand1.is_immediate(-size):
        is_esp = True
    else:
        return 0

    main = cleaner.get_clean_instruction(inst.next)
    if not (main.opcode == "sub" and main.operand1.is_memory()  and main.operand1.base == "esp" and main.operand1.dispsize == 0 and main.operand1.index_reg == None and main.operand2.is_reg()):
        return 0

    if is_esp != (main.operand2.value == "esp"):
        return 0

    if main.operand1.size == 1:
        if is_esp:
            return 0
        real_size = 1
    elif main.operand1.size != size:
        return 0
    
    next = cleaner.get_clean_instruction(main.next)
    if main.operand2 != next.operand1:
        return 0

    if real_size == 1:
        if not (next.opcode == "mov" and main.operand1 == next.operand2):
            return 0
        next = cleaner.get_clean_instruction(next.next)
        if not (next.opcode == "add" and next.operand1.is_reg("esp") and next.operand2.is_immediate(size) and next.operand2.size == 1):
            return 0
    else:
        if next.opcode != "pop":
            return 0

    inst.opcode = "neg"
    inst.operand1 = main.operand2.copy()
    inst.operand2 = instruction.NoneOperand()

    return next.next
    
# INPUT:
# NEG [32/16]
# OUTPUT:
# PUSH R32/R16
# MOV R32/R16, 0
# SUB R32/R16, [32/16]
# MOV/XCHG [32/16], R32/R16
# POP R32/R16
def clear0MinusThruReg(cleaner, inst):
    if not (inst.opcode == "push" and inst.operand1.is_reg()):
        return 0

    next = cleaner.get_clean_instruction(inst.next)
    if not (next.opcode == "mov" and inst.operand1 == next.operand1 and inst.operand2.is_immediate(0)):
        return 0

    main = cleaner.get_clean_instruction(next.next)
    if not (main.opcode == "sub" and main.operand1 == inst.operand1 and main.operand2.size != 1 and ((main.operand1.is_reg() and not main.operand1.is_reg_esp()) or (main.operand1.is_mem() and not main.operand1.is_mem_esp()))):
        return 0
    
    next = cleaner.get_clean_instruction(main.next)
    if (next.opcode == "mov" or next.opcode == "xchg") and next.operand1 == main.operand2 and next.operand2 == main.operand1:
        pass
    elif next.opcode == "xchg" and next.operand1 == main.operand1 and next.operand2 == main.operand2:
        pass
    else:
        return 0
    
    next = cleaner.get_clean_instruction(main.next)
    if not (next.opcode == "pop" and next.operand1 == main.operand1):
        return 0

    inst.opcode = "neg"
    inst.operand1 = main.operand2.copy()
    inst.operand2 = instruction.NoneOperand()
    
    return next.next

def clearMovConstant(cleaner, inst):
    if not (inst.opcode == "mov" and not inst.operand1.is_reg("esp") and inst.operand2.is_immediate()):
        return 0
    size = inst.operand2.size
    last_address = inst.next

    next = cleaner.get_clean_instruction(inst.next)
    while (next.opcode in MATH_OPERANDS and next.operand1 == inst.operand1 and (next.operand2.is_none() or next.operand2.is_immediate())) or (
    
def fixPushPop(cleaner, inst):
def fixPushMovMovPop(cleaner, inst):
def fixPushMovMovCalcPop(cleaner, inst):
def fixPushPopAddSub(cleaner, inst):
def fixPush(cleaner, inst):
def fixPop(cleaner, inst):
def fixXorXorXor(cleaner, inst):
def fixPushMovPop(cleaner, inst):
def fixXchgByteThruReg(cleaner, inst):
def fixOperationThruReg(cleaner, inst):
def fixOperationThruReg2(cleaner, inst):
def fixOperationThruStack(cleaner, inst):
def fixOperationThruStackByte(cleaner, inst):
def fixOperationThruRegByte(cleaner, inst):
def fixOperationConstantThruReg(cleaner, inst):
def fixOperationConstantOnEsp(cleaner, inst):
						   
def fixPushMovMovPopUnusedRegs(cleaner, inst):
def fixPushMovMovCalcPopUnusedRegs(cleaner, inst):
def fixOperationConstantThruRegUnusedRegs(cleaner, inst):
"""
