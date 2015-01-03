import utils
import sys
from themida import cleaner
from vms import vminstruction
from vms import templates
import instruction
import mappedfile
try:
    import progressbar
    PROGRESSBAR = True
except ImportError:
    PROGRESSBAR = False

import handlers_common
import handlers_32
import handlers_64


import Queue

import os
import tempfile
import subprocess

class VMHandler(object):
    def __init__(self, reader):
        pass

# TODO, do not just remove MATHF POP, becuase it is real math!

def get_cleaner_reader(file, address, options=None, unused_regs=None):
    clean = cleaner.Cleaner(file)
    if options:
        for option, value in options:
            clean.set_option(option, value)
    if unused_regs:
        for reg in unused_regs:
            clean.set_reg_unused(reg)
    return clean.get_reader(address)

class VMInit(VMHandler):
    cache = {}
    def __init__(self, file, address):
        print "Reading VMInit...",
        mode = file.get_arch()
        address_mask = (1 << file.mode) - 1
        if file.mode == 32:
            reader = get_cleaner_reader(file, address, [("ignore_jumps", False)])
            registers = 8
            ptr = utils.uint32
        else:
            reader = file.get_reader(address)
            registers = 15
            ptr = utils.uint64

        self.regs = []
        if file.mode == 32:
            reader.get_cond(lambda x: x.opcode == "pushfd")
            self.regs.append("flags")
        self.regs += [reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg()).operands[0].reg for i in xrange(registers)]
        if file.mode == 64:
            reader.get_cond(lambda x: x.opcode == "pushfq")
            self.regs.append("flags")

        reader.get_cond(lambda x: x.opcode == "cld")
        if file.mode == 32:
            reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("eax"))

        self.encode = ptr(reader.get_cond(lambda x: x.opcode == "call" and x.operands[0].value == x.address + 5).operands[0].value)
        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(mode.reg_native("di")))

        if file.mode == 32:
            self.encode -= reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate()).operands[1].value
            reader.get_cond(lambda x: x.opcode == "and" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate(0xFFFFF000))
            self.encode &= 0xFFFFF000
            reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate(0x14))
            self.encode += 0x14
            reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("edi"))
            self.vm_struct = long(self.encode + reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate()).operands[1].value)
        else:
            encode2 = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("rax") and x.operands[1].is_immediate()).operands[1].value
            reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ecx") and x.operands[1].is_reg("eax"))
            self.encode2 = (encode2 & 0xFFFFFFFF)
            reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg("rcx") and x.operands[1].is_reg("rdi"))
            self.encode2 -= self.encode2
            reader.get_cond(lambda x: x.opcode == "neg" and x.operands[0].is_reg("rcx"))
            self.encode2 = -self.encode2
            self.encode2 &= address_mask
            reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg("rdi") and x.operands[1].is_reg("rax"))
            self.encode -= encode2
            reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("rax") and x.operands[1].is_reg("rdi"))
            self.vm_struct = long(self.encode + reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("rbx") and x.operands[1].is_immediate()).operands[1].value)
            reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("rdi") and x.operands[1].is_reg("rbx"))

        self.encode_in_vm_struct = reader.get_cond(lambda x: x.opcode == "cmp" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_memory() and (x.operands[1].base == mode.reg_native("di") or x.operands[1].index == mode.reg_native("di")) and x.operands[1].scale == 0).operands[1].offset
        jnz = reader.get_cond(lambda x: x.opcode == "jnz").operands[0].value
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())
        reader.get_cond(lambda x: x.address == jnz and x.opcode == "mov" and x.operands[1].is_reg(mode.reg_native("ax")) and x.operands[0].is_memory() and (x.operands[0].base == mode.reg_native("di") or x.operands[0].index == mode.reg_native("di")) and x.operands[0].offset == self.encode_in_vm_struct and x.operands[0].scale == 0)
        if file.mode == 64:
            self.encode2_in_vm_struct = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_reg(mode.reg_native("cx")) and x.operands[0].is_memory() and (x.operands[0].base == mode.reg_native("di") or x.operands[0].index == mode.reg_native("di")) and x.operands[0].scale == 0).operands[0].offset

        self.handlers_count = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ecx") and x.operands[1].is_immediate()).operands[1].value
        if file.mode == 64:
            test_address = reader.get_cond(lambda x: x.opcode == "test" and x.operands[0].is_reg("ecx") and x.operands[1].is_reg("ecx")).address
            after_loop = reader.get_cond(lambda x: x.opcode == "jz" and x.operands[0].is_immediate()).operands[0].value
        else:
            reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())

        add_address = reader.address
        self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg(mode.reg_native("ax")) and x.operands[0].is_memory() and x.operands[0].base == mode.reg_native("di") and x.operands[0].index == mode.reg_native("cx") and x.operands[0].scale == mode.pointer_size()).operands[0].offset + mode.pointer_size()
        reader.get_cond(lambda x: x.opcode == "dec" and x.operands[0].is_reg("ecx"))

        if file.mode == 64:
            reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate(test_address))
            assert after_loop == reader.address
        else:
            reader.get_cond(lambda x: x.opcode == "or" and x.operands[0].is_reg("ecx") and x.operands[1].is_reg("ecx"))
            reader.get_cond(lambda x: x.opcode == "jnz" and x.operands[0].is_immediate(add_address))

        #try:
        #    self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and x.operands[0].base == "edi" and x.operands[0].index == "ecx" and x.operands[0].scale == 4).operands[0].offset + 4
        #except cleaner.CleanerException, e:
        #    # Are they trying to confuse us?
        #    reader.address = reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate()).operands[0].value
        #    self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and x.operands[0].base == "edi" and x.operands[0].index == "ecx" and x.operands[0].scale == 4).operands[0].offset + 4

        if file.mode == 64:
            self.encode_address_high_dword = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("rdx") and x.operands[1].is_immediate()).operands[1].value
        else:
            self.encode_address_high_dword = 0

        # mov esi, [esp+0x24]/[rsp+80h]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("esi") and x.operands[1].is_memory() and x.operands[1].base == mode.reg_native("sp") and x.operands[1].offset == (registers + 1) * mode.pointer_size())
        # mov ebx, esi
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_reg("esi"))
        if file.mode == 64:
            # add rsi, edx
            reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("rsi") and x.operands[1].is_reg("rdx"))
        # add rsi, rax
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg(mode.reg_native("si")) and x.operands[1].is_reg(mode.reg_native("ax")))
        # mov ecx, 0x1
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ecx") and x.operands[1].is_immediate(1))
        # xor eax, eax
        lock_loop_address = reader.get_cond(lambda x: x.opcode == "xor" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("eax")).address
        # lock cmpxchg [rdi+lock_offset], rcx
        self.lock_in_vm_struct = reader.get_cond(lambda x: x.opcode == "cmpxchg" and x.operands[1].is_reg(mode.reg_native("cx")) and x.operands[0].is_memory() and (x.operands[0].base == mode.reg_native("di") or x.operands[0].index == mode.reg_native("di"))).operands[0].offset

        reader.get_cond(lambda x: x.opcode == "jnz" and x.operands[0].is_immediate(lock_loop_address))

        self.main_handler_address = reader.address
        print "SUCCESS"


class VMReadInfo(vminstruction.VMReadInfo):
    READ_SIZES = {"lodsb": 1,
                  "lodsw": 2,
                  "lodsd": 4,
                  "lodsq": 8}
    REGISTERS = {1: ("al", "bl"),
                 2: ("ax", "bx"),
                 4: ("eax", "ebx"),
                 8: ("rax", "rbx")}
    def __init__(self, reader):
        self.size = self.READ_SIZES[reader.get_cond(lambda x: x.opcode in self.READ_SIZES).opcode]
        value_reg, key_reg = self.REGISTERS[self.size]
        real_size = self.size
        current_address = reader.address
        self.before_operation = None
        self.first_operation = None
        self.second_operation = None
        self.after_operation = None
        self.encrypted = False
        self.extend_dword = False
        try:
            try:
                self.before_operation = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg(value_reg) and x.operands[1].is_reg(key_reg)).opcode
            except cleaner.CleanerException:
                # In old version they didn't have lodsw, so try with size 2
                if self.size == 4:
                    self.size = 2
                    real_size = 4
                    value_reg, key_reg = self.REGISTERS[self.size]
                    self.before_operation = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg(value_reg) and x.operands[1].is_reg(key_reg)).opcode
                elif self.size <= 2:
                    # Hack
                    # In some rare cases, because of the obfuscator the first and second operation can be switched
                    # It won't happen in size 4 and won't happen with xor
                    res = reader.get_cond(lambda x: x.opcode in ("add", "sub") and x.operands[0].is_reg() and x.operands[0].is_reg(value_reg) and x.operands[1].is_immediate())
                    self.first_operation = (res.opcode, res.operands[1].value)
                    self.before_operation = reader.get_cond(lambda x: x.opcode in ("add", "sub") and x.operands[0].is_reg(value_reg) and x.operands[1].is_reg(key_reg)).opcode
                    res = reader.get_cond(lambda x: x.opcode in ("add", "sub") and x.operands[0].is_reg() and x.operands[0].is_reg(value_reg) and x.operands[1].is_immediate())
                    self.second_operation = (res.opcode, res.operands[1].value)
            if self.first_operation is None:
                res = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg() and x.operands[0].is_reg(value_reg) and x.operands[1].is_immediate())
                self.first_operation = (res.opcode, res.operands[1].value)
            if self.second_operation is None:
                res = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg() and x.operands[0].is_reg(value_reg) and x.operands[1].is_immediate())
                self.second_operation = (res.opcode, res.operands[1].value)
            self.after_operation = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[1].is_reg(value_reg) and x.operands[0].is_reg(key_reg)).opcode
            self.encrypted = True
        except cleaner.CleanerException:
            self.size = real_size
            reader.address = current_address
        if not self.encrypted and self.size == 4:
            current_address = reader.address
            try:
                reader.get_cond(lambda x: x.opcode == "nop")
                reader.get_cond(lambda x: x.opcode == "cdqe")
                self.extend_dword = True
            except cleaner.CleanerException:
                reader.address = current_address

    def decode(self, bytes_reader, key):
        value = self.read(bytes_reader)
        if not self.encrypted:
            if self.extend_dword:
                if value >> 31:
                    value |= ((~0) & ((1 << 32) - 1)) << 32
            return value
        value = vminstruction.VMReadInfo.do_operation(self.before_operation, value, key.key, self.size)
        value = vminstruction.VMReadInfo.do_operation(self.first_operation[0], value, self.first_operation[1], self.size)
        value = vminstruction.VMReadInfo.do_operation(self.second_operation[0], value, self.second_operation[1], self.size)
        key.key = (key.key & ((~((1<<(self.size * 8))-1))&((1<<32)-1))) | vminstruction.VMReadInfo.do_operation(self.after_operation, key.key, value, self.size)
        return value

class VMMainHandler(VMHandler):
    cache = {}
    def __init__(self, file, address):
        print "Reading VMMainHandler...",
        reader = get_cleaner_reader(file, address, unused_regs = ["r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"])
        mode = file.get_arch()
        self.read = VMReadInfo(reader)
        if self.read.size != 1:
            raise cleaner.CleanerException("Invalid size for main handler reader")
        reader.get_cond(lambda x: str(x) == mode.translate("movzx {R:ax}, al"))
        reader.get_cond(lambda x: str(x) == mode.translate("jmp {S} [{R:di}+{R:ax}*{N}]"))
        print "SUCCESS"

class VMOpcodeHandler(VMHandler):
    def __init__(self, reader):
        self.address = reader.address
        try:
            self.read = VMReadInfo(reader)
        except cleaner.CleanerException, e:
            self.read = None

        self.insts = []
        
        while True:
            inst = reader.get()
            #print "0x%x: %s" % (inst.address, str(inst))
            if inst.opcode == "jmp" and inst.operands[0].is_immediate():
                # Since we ignore jumps, if we get a jump anyway,
                # it means that it was a jump to the end, to the main handler
                break
            self.insts.append(inst)
            if inst.opcode == "ret":
                break


    def assign_name(self, name):
        self.name = name
        #del self.insts

    def get_vm_instruction(self, bytes_reader, key):
        if self.read != None:
            return vminstruction.VMInstruction(self.name, self.read.decode(bytes_reader, key))
        return vminstruction.VMInstruction(self.name)
            
class VMHandlers(object):
    def __init__(self, file, vm_info):
        clean = cleaner.Cleaner(file)
        for reg in ["r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]:
            clean.set_reg_unused(reg)
        fix_handlers = file.read_pointer(vm_info.init_handler.vm_struct + vm_info.init_handler.encode_in_vm_struct) != vm_info.init_handler.encode
        mode = file.get_arch()

        self.handlers = {}
        handlers_to_process = Queue.Queue()

        print ("Reading %d Handlers..." % (vm_info.init_handler.handlers_in_vm_struct / mode.pointer_size())),
        # Let's find all the handlers now
        for i in xrange(vm_info.init_handler.handlers_in_vm_struct / mode.pointer_size(), vm_info.init_handler.handlers_in_vm_struct / mode.pointer_size() + vm_info.init_handler.handlers_count):
            handler_address = file.read_pointer(vm_info.init_handler.vm_struct + i * mode.pointer_size())
            if fix_handlers:
                handler_address = long(handler_address + vm_info.init_handler.encode + vm_info.init_handler.encode_address_high_dword)
            clean.set_option("end_address", vm_info.init_handler.main_handler_address)
            #print hex(handler_address)
            self.handlers[i] = VMOpcodeHandler(clean.get_reader(handler_address))
            clean.set_option("end_address", 0)
            handlers_to_process.put(self.handlers[i])
        print "SUCCESS"

        print "Detecting Handlers...",
        variables = {"FLAGS": 7 * mode.native_size(), "ENCODE": vm_info.init_handler.encode_in_vm_struct, "100_PTRS": 0x100 * mode.native_size()}
        if file.mode == 64:
            variables["ENCODE2"] = vm_info.init_handler.encode2_in_vm_struct
        processed = []
        while not handlers_to_process.empty():
            handler = handlers_to_process.get()
            # Try to match with HANDLERS
            matches = handlers_common.find_matches(mode, handlers_common.HANDLERS, handler, variables)
            if file.mode == 32:
                matches += handlers_common.find_matches(mode, handlers_32.HANDLERS, handler, variables)
            else:
                matches += handlers_common.find_matches(mode, handlers_64.HANDLERS, handler, variables)
            if matches:
                if len(matches) == 1:
                    handler.assign_name(matches[0][0])
                    variables = matches[0][1]
                else:
                    if processed.count(handler) > 10:
                        raise Exception("Couldn't determine handler")
                    processed.append(handler)
                    handlers_to_process.put(handler)
            else:
                # So it is math operation, let's find it
                if handler.read is not None:
                    for inst in handler.insts:
                        print hex(inst.address)
                        print inst
                    raise Exception("Undetected handler")
                # Detect math operation
                operation_name = handlers_common.find_math_handler(mode, handler, variables)

                if len(handler.insts) == 0:
                    operation_name = "NOP"
                try:
                    assert operation_name is not None
                except:
                    print hex(handler.address)
                    for inst in handler.insts:
                        print hex(inst.address)
                        print inst
                    raise
                handler.assign_name(operation_name)
        # Good, we have handlers now
        print "SUCCESS"

        self.realloc_offset = file.read_pointer(vm_info.init_handler.vm_struct + variables["REALLOC"])
                        

class VMInfo(object):
    cache = {}
    def __init__(self, file, vm_address):
        print "Parsing CISC%d VM at 0x%08x" % (file.mode, vm_address)
        self.init_handler = VMInit(file, vm_address)
        self.main_handler = VMMainHandler(file, self.init_handler.main_handler_address)
        self.handlers = VMHandlers(file, self)

    @classmethod
    def get_vm_info(cls, file, address):
        if cls.cache.has_key(address):
            return cls.cache[address]
        #try:
        res = cls(file, address)
        #except cleaner.CleanerException, e:
        #    res = None
            
        cls.cache[address] = res
        return res

    
class VMFunctionSection(object):
    def __init__(self, address):
        self.address = address
        self.start = False
        self.end = False
        self.instructions = [] 
    

class VMKey(vminstruction.VMKey):
    def __init__(self, key):
        self.key = utils.uint32(key)

    def reset(self):
        self.key = utils.uint32(0)

class VMFunctionJumper(object):
    def __init__(self, file, address):
        push_inst = file.get_instruction(address)
        jmp_inst = file.get_instruction(push_inst.next)
        assert push_inst.opcode == "push" and push_inst.operands[0].is_immediate()
        assert jmp_inst.opcode == "jmp" and jmp_inst.operands[0].is_immediate()
        self.vm_code_address = push_inst.operands[0].value
        self.vm_address = jmp_inst.operands[0].value

class VMFunction(object):
    def __init__(self, file, jumper):
        self.mode = file.mode
        self.file = file
        vm_address = jumper.vm_address
        vm_code_address = jumper.vm_code_address

        self.vm_info = VMInfo.get_vm_info(file, vm_address)
        assert self.vm_info is not None
        
        addresses_to_explore = Queue.Queue()
        starts = []
        instructions = {}
        instructions_size = {}
        
        # The code is layout like this:
        # jmp label
        # push adress2
        # jmp vm
        # ..
        # push adressN
        # jmp vm
        # vmcode
        # ..
        # ..
        # push address1
        # jmp vm
        # ...
        # labal1:
        # ....

        # Start address is the address of push address2/jmp and end address is the address of vmcode
        real_vm_code_address = long(vm_code_address + self.vm_info.init_handler.encode + self.vm_info.init_handler.encode_address_high_dword)
        self.code_address = real_vm_code_address

        print ("Reading VMFunction at 0x%08x..." % self.code_address),

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put((real_vm_code_address, vm_code_address))
        starts.append(real_vm_code_address)

        to_print = False
        while not addresses_to_explore.empty():
            next_labeled = True
            address, key = addresses_to_explore.get()
            key = VMKey(key)
            if instructions.has_key(address):
                instructions[address].set_info("labled", True)
                continue
            bytes_reader = vminstruction.BytesReader(file, address)
            while True:
                if instructions.has_key(bytes_reader.address):
                    if next_labeled:
                        instructions[bytes_reader.address].set_info("labled", True)
                    break

                # TODO: Do a method to do this
                address = bytes_reader.address
                func = self.vm_info.main_handler.read.decode(bytes_reader, key)
                assert self.vm_info.handlers.handlers.has_key(func)
                instructions_size[address] = 1
                if self.vm_info.handlers.handlers[func].read is not None:
                    instructions_size[address] += self.vm_info.handlers.handlers[func].read.size
                inst = self.vm_info.handlers.handlers[func].get_vm_instruction(bytes_reader, key)
                if inst.name == "HIGH_MAIN_HANDLER":
                    func = inst.args[0] + 0x100
                    assert self.vm_info.handlers.handlers.has_key(func)
                    instructions_size[address] = 1
                    if self.vm_info.handlers.handlers[func].read is not None:
                        instructions_size[address] += self.vm_info.handlers.handlers[func].read.size
                    inst = self.vm_info.handlers.handlers[func].get_vm_instruction(bytes_reader, key)

                inst.address = address
                inst.set_info("labled", next_labeled)
                next_labeled = False

                if inst.name in ("JMP", "JMPIF"):
                    inst.args[0] += bytes_reader.address
                    inst.args[0] &= (1 << self.mode) - 1
                    
                if inst.name == "JMP":
                    next_labeled = True
                    bytes_reader.address = inst.args[0]
                    key.reset()
                elif inst.name == "JMPIF":
                    addresses_to_explore.put((inst.args[0], 0))
                elif inst.name == "RESETKEY":
                    key.reset()
                    # It isn't really an opcode, so don't store it
                    continue
                elif inst.name == "PUSH_ENCODED":
                    try:
                        jumper = VMFunctionJumper(file, long(inst.args[0] + self.vm_info.init_handler.encode))
                    except:
                        tinst = file.get_instruction(long(inst.args[0] + self.vm_info.init_handler.encode))
                        jumper = VMFunctionJumper(file, tinst.next)
                    jmp_vm_code_address = long(jumper.vm_code_address + self.vm_info.init_handler.encode + self.vm_info.init_handler.encode_address_high_dword)
                    addresses_to_explore.put((jmp_vm_code_address, jumper.vm_code_address))
                    starts.append(jmp_vm_code_address)
                elif inst.name in ("ADD_DX_REALLOC", "STACK_ADD_REALLOC"): # TODO: Properly support reallocation
                    inst.name += "_VALUE"
                    inst.args = [self.vm_info.handlers.realloc_offset]

                instructions[inst.address] = inst
                #print inst
                if inst.name == "RETURN":
                    break
        print "SUCCESS"

        last_address = 0
        last_size = 0
        self.instructions = []
        for address in sorted(instructions.keys()):
            if instructions[address].info["labled"]:
                if starts.count(address):
                    label = vminstruction.VMInstruction("STARTLABEL", address)
                else:
                    label = vminstruction.VMInstruction("LABEL", address)
                label.address = address
                self.instructions.append(label)
            #if last_address and address - last_address != last_size:
            #    print "Gap: %d" % (address - last_address - last_size)
            last_address = address
            last_size = instructions_size[address]
            self.instructions.append(instructions[address])
        self.code = None

        self._clean()

        print "Converting VMCode to Assembly...",
        try:
            self.get_code()
        except:
            print ""
            self.printfunc()
            raise
        print "SUCCESS"

    def _clean(self):
        TEMPLATES = ["cisc_00_clean.txt", "cisc_01_flags.txt", "cisc_02_realloc.txt", "cisc_03_movdx.txt", "cisc_04_push_pop.txt", "cisc_05_jumps_prepare.txt"]
        if self.mode == 32:
            TEMPLATES.append("cisc_templates_32.txt")
        else:
            TEMPLATES.append("cisc_templates_64.txt")
        TEMPLATES += ["cisc_06_jumps.txt", "cisc_07_final.txt"]
        print "Processing VMFunction (%d instructions)..." % len(self.instructions)


        for template in TEMPLATES:
            print ("Applying %s," % template),
            templates.Templates.get_template(r"codevirtualizer\cisc\%s" % template, self.mode).clean(self.instructions)
            print "OK."

        print "After processing: %d instructions" % len(self.instructions)

        # Clean labels
        refs = []
        for inst in self.instructions:
            if (inst.name.startswith("J") or inst.name.startswith("LOOP")) and len(inst.args): # JMP
                refs.append(inst.args[0])

        i = 0
        while i < len(self.instructions):
            if self.instructions[i].name == "LABEL":
                if not refs.count(self.instructions[i].args[0]):
                    # Remove label
                    self.instructions[i:i+1] = []
                    continue
            i += 1

    def get_code(self):
        if self.code != None:
            return self.code
        if self.mode == 32:
            native_size_word = "DWORD"
        else:
            native_size_word = "QWORD"
        push_native = "PUSH_%s" % native_size_word
        sections = {}
        for inst in self.instructions:
            if inst.name == "STARTLABEL":
                section = VMFunctionSection(inst.args[0])
                section.start = True
                sections[section.address] = section
            elif inst.name == "LABEL":
                section = VMFunctionSection(inst.args[0])
                sections[section.address] = section
                section.instructions.append(inst)                
            else:
                section.instructions.append(inst)
        section.end = True

        code = ""
        code_base = code
        section_counter = 0
        next_section = 0
        registers = None

        for address in sorted(sections.keys()):
            if next_section:
                assert next_section == address
                next_section = 0
            section = sections[address]
            sectioncode = ""
            reader = vminstruction.VMInstructionsReader(section.instructions)

            if section.start:
                registers = {}

                if section_counter == 1:
                    index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
                    # Deal with anti-debugging
                    if index != -1:
                        code = code_base + code[code.find("\n", index+1)+1:]
                section_counter += 1

                regs = list(self.vm_info.init_handler.regs)

                # For older version
                #reader.get_cond(lambda x: x.name == "POPF") # flags
                #assert regs.pop() == "flags"

                pop_reg = "POP_%s_REG" % native_size_word
                # Check reg
                if self.mode == 32:
                    for i in xrange(4):
                        registers[reader.get_cond(lambda x: x.name == pop_reg).args[0]] = regs.pop()
                    reader.get_cond(lambda x: x.name == "SET_CHECK_CX_REG")  # TODO: Verify that it is ecx?
                    for i in xrange(4):
                        registers[reader.get_cond(lambda x: x.name == pop_reg).args[0]] = regs.pop()
                    reader.get_cond(lambda x: x.name == pop_reg and x.args[0] == 0x7) # POPF
                    assert regs.pop() == "flags"
                else:
                    reader.get_cond(lambda x: x.name == pop_reg and x.args[0] == 0x7) # POPF
                    assert regs.pop() == "flags"
                    for i in xrange(15):
                        registers[reader.get_cond(lambda x: x.name == pop_reg).args[0]] = regs.pop()
                
                reader.get_cond(lambda x: x.name == "VM_START_SP_ADJUST")
                if self.mode == 64:
                    reader.get_cond(lambda x: x.name == "SET_CHECK_CX_REG")  # TODO: Verify that it is ecx?

            elif section.end:
                continue

            inst = reader.get()
            stop = False

            while inst:
                if inst.name in ("PUSH_ADDRESS_IMM", "PUSH_ADDRESS_RELIMM"):
                    reader.push()
                    try:
                        jmp = reader.get_cond(lambda x: (x.name in vminstruction.CONDITIONAL_JUMPS or x.name == "JMP") and sections[x.args[0]].end)
                    except vminstruction.ReaderException:
                        reader.pop()
                    else:
                        # LOOPs are buggy
                        if jmp.name not in ("JMP", "LOOP", "LOOPE"):
                            reader.get_cond(lambda x: x.name == "POP_ADDRESS")
                        inst = vminstruction.VMInstruction(inst.name.replace("PUSH_ADDRESS", jmp.name), *inst.args)
                elif inst.name.startswith(push_native):
                    reader.push()
                    try:
                        reader.get_cond(lambda x: x.name == "JMP" and sections[x.args[0]].end)
                    except vminstruction.ReaderException:
                        reader.pop()
                    else:
                        inst = vminstruction.VMInstruction(inst.name.replace(push_native, "JMP"), *inst.args)
                        stop = True
                elif inst.name == "PUSH_ENCODED":
                    next = reader.get()
                    if next.name == "JMP":
                        assert sections[next.args[0]].end
                        asminst = self.file.get_instruction(long(inst.args[0] + self.vm_info.init_handler.encode))                    
                        asminst_after = self.file.get_instruction(asminst.next)
                        assert asminst_after.opcode == "push"
                        assert asminst_after.operands[0].is_immediate()
                        #sectioncode += "\n".join(["db 0x%x" % ord(x) for x in asminst.bytes]) + "\n"
                        sectioncode += str(asminst) + "\n"
                        next_section = long(asminst_after.operands[0].value + self.vm_info.init_handler.encode)
                        break
                    else:
                        if next.name.startswith(push_native) and next.name[len(push_native):] not in ("_IMM", "_RELIMM"):
                            push = push_native
                        elif next.name in ("PUSH_ADDRESS_IMM", "PUSH_ADDRESS_RELIMM"):
                            push = "PUSH_ADDRESS"
                        else:
                            assert False
                        reader.get_cond(lambda x: x.name == "JMP" and sections[x.args[0]].end)
                        inst = vminstruction.VMInstruction(next.name.replace(push, "CALL"), *next.args)
                        stop = True
                elif inst.name == "MOV_EAX_EAX":
                    # It is just a nop
                    inst = vminstruction.VMInstruction("NOP")
                elif inst.name == ("MOV_%s_REG_ENCODE" % native_size_word):
                    # TODO: Clear the anti-dumps code only if this register appears, and it should appear only in the first section
                    if self.mode == 32:
                        inst = vminstruction.VMInstruction("MOV_%s_REG_IMM" % native_size_word, inst.args[0], long(self.vm_info.init_handler.encode))
                    else:
                        # Not sure about 64bit, should be checked, TODO
                        inst = vminstruction.VMInstruction("MOV_%s_REG_IMM" % native_size_word, inst.args[0], long(self.vm_info.init_handler.encode2))
                elif inst.name == "JMP" and not sections[inst.args[0]].end:
                    inst = vminstruction.VMInstruction("JMP_LABEL", inst.args[0])
                elif inst.name in vminstruction.CONDITIONAL_JUMPS:
                    inst = vminstruction.VMInstruction(inst.name + "_LABEL", inst.args[0])
                elif inst.name == "SET_RETURN_POP_SIZE":
                    reader.get_cond(lambda x: x.name == "JMP" and sections[x.args[0]].end)
                    inst = vminstruction.VMInstruction("RET_IMM", inst.args[0])
                    stop = True
                elif inst.name == "JMP": # jmp to end
                    inst = vminstruction.VMInstruction("RET")
                    stop = True

                sectioncode += inst.to_asm(registers, self.mode) + "\n"
                if stop:
                    break

                inst = reader.get()
            code += sectioncode


        if section_counter == 1:
            index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
            # Deal with anti-debugging
            if index != -1:
                code = code_base + code[code.find("\n", index+1)+1:]

        if self.mode == 32:
            code = code.replace("push eax\npush ecx\npush edx\npush ebx\npush ebx\npush ebp\npush esi\npush edi", "pushad")
            code = code.replace("pop edi\npop esi\npop ebp\npop ebx\npop ebx\npop edx\npop ecx\npop eax", "popad")
            code = code.replace("mov esp, ebp\npop ebp", "leave")
        else:
            code = code.replace("mov rsp, rbp\npop rbp", "leave")
        #print code
        self.code = code[:-1]
        return self.code

    # TODO: Make this base class function
    def compile_code(self, address = None, relocs = False):
        code = self.get_code()
        if address == None:
            address = self.code_address
        compiled_code = instruction.Assembler(self.mode).assemble(code, address, relocs)
        if not compiled_code:
            raise Exception("Failed to compile code")
        if relocs:
            return address, compiled_code[0], compiled_code[1]
        return address, compiled_code        
        
    
        
    def printfunc(self):
        for inst in self.instructions:
            print inst
