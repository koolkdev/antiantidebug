import utils
from themida import cleaner
from vms import vminstruction
from vms import templates
from vms.codevirtualizer import cischandlers
import instruction

import Queue

import os
import tempfile
import subprocess

class VMHandler(object):
    def __init__(self, reader):
        pass

# TODO, do not just remove MATHF POP, becuase it is real math!

class VMInit(VMHandler):
    cache = {}
    def __init__(self, reader):
        reader.get_cond(lambda x: x.opcode == "pushfd")
        self.regs = ["flags"]
        self.regs += [reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg()).operands[0].reg for i in xrange(8)]
        reader.get_cond(lambda x: x.opcode == "cld")
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("eax"))
        self.encode = utils.uint32(reader.get_cond(lambda x: x.opcode == "call" and x.operands[0].value == x.address + 5).operands[0].value)
        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg("edi"))
        self.encode -= reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate()).operands[1].value
        reader.get_cond(lambda x: x.opcode == "and" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate(0xFFFFF000))
        self.encode &= 0xFFFFF000
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate(0x14))
        self.encode += 0x14
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("edi"))
        self.vm_struct = long(self.encode + reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate()).operands[1].value)
        self.encode_in_vm_struct = reader.get_cond(lambda x: x.opcode == "cmp" and x.operands[0].is_reg("eax") and x.operands[1].is_memory() and (x.operands[1].base == "edi" or x.operands[1].index == "edi") and x.operands[1].scale == 0).operands[1].offset
        jnz = reader.get_cond(lambda x: x.opcode == "jnz").operands[0].value
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())
        reader.get_cond(lambda x: x.address == jnz and x.opcode == "mov" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and (x.operands[0].base == "edi" or x.operands[0].index == "edi") and x.operands[0].offset == self.encode_in_vm_struct and x.operands[0].scale == 0)
        self.handlers_count = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ecx") and x.operands[1].is_immediate()).operands[1].value
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())
        try:
            self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and x.operands[0].base == "edi" and x.operands[0].index == "ecx" and x.operands[0].scale == 4).operands[0].offset + 4
        except cleaner.CleanerException, e:
            # Are they trying to confuse us?
            reader.address = reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate()).operands[0].value
            self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and x.operands[0].base == "edi" and x.operands[0].index == "ecx" and x.operands[0].scale == 4).operands[0].offset + 4
            
        while reader.get().opcode != "jnz":
            pass    
        res = reader.get()
        while res.opcode != "jnz":
            res = reader.get()
        self.main_handler_address = res.next

### Old handlers
##class VMInit(VMHandler):
##    cache = {}
##    def __init__(self, reader):
##        reader.get_cond(lambda x: x.opcode == "pusha")
##        self.regs = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
##        reader.get_cond(lambda x: x.opcode == "pushf")
##        self.regs += ["flags"]
##        reader.get_cond(lambda x: x.opcode == "cld")
##        #reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("eax"))
##        self.encode = utils.uint32(reader.get_cond(lambda x: x.opcode == "call" and x.operands[0].value == x.address + 5).operands[0].value)
##        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg("edi"))
##        self.encode -= reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate()).operands[1].value
##        #reader.get_cond(lambda x: x.opcode == "and" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate(0xFFFFF000))
##        #self.encode &= 0xFFFFF000
##        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("edi"))
##        #reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate(0x14))
##        #self.encode += 0x14
##        self.vm_struct = long(self.encode + reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg("edi") and x.operands[1].is_immediate()).operands[1].value)
##        self.encode_in_vm_struct = reader.get_cond(lambda x: x.opcode == "cmp" and x.operands[0].is_reg("eax") and x.operands[1].is_memory() and (x.operands[1].base == "edi" or x.operands[1].index == "edi") and x.operands[1].scale == 0).operands[1].offset
##        jnz = reader.get_cond(lambda x: x.opcode == "jnz").operands[0].value
##        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())
##        reader.get_cond(lambda x: x.address == jnz and x.opcode == "mov" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and (x.operands[0].base == "edi" or x.operands[0].index == "edi") and x.operands[0].offset == self.encode_in_vm_struct and x.operands[0].scale == 0)
##        self.handlers_count = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ecx") and x.operands[1].is_immediate()).operands[1].value
##        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())
##        try:
##            self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and x.operands[0].base == "edi" and x.operands[0].index == "ecx" and x.operands[0].scale == 4).operands[0].offset + 4
##        except cleaner.CleanerException, e:
##            # Are they trying to confuse us?
##            reader.address = reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate()).operands[0].value
##            self.handlers_in_vm_struct = reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg("eax") and x.operands[0].is_memory() and x.operands[0].base == "edi" and x.operands[0].index == "ecx" and x.operands[0].scale == 4).operands[0].offset + 4
##            
##        while reader.get().opcode != "jnz":
##            pass    
##        res = reader.get()
##        while res.opcode != "jnz":
##            res = reader.get()
##        self.main_handler_address = res.next


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
        try:
            try:
                self.before_operation = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg(value_reg) and x.operands[1].is_reg(key_reg)).opcode
            except cleaner.CleanerException, e:
                # In old version they didn't have lodsw, so try with size 2
                if self.size == 4:
                    self.size = 2
                    real_size = 4
                    value_reg, key_reg = self.REGISTERS[self.size]
                self.before_operation = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg(value_reg) and x.operands[1].is_reg(key_reg)).opcode
            res = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg() and x.operands[0].is_reg(value_reg) and x.operands[1].is_immediate())
            self.first_operation = (res.opcode, res.operands[1].value)
            res = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[0].is_reg() and x.operands[0].is_reg(value_reg) and x.operands[1].is_immediate())
            self.second_operation = (res.opcode, res.operands[1].value)
            self.after_operation = reader.get_cond(lambda x: x.opcode in ("add", "xor", "sub") and x.operands[1].is_reg(value_reg) and x.operands[0].is_reg(key_reg)).opcode
            self.encrypted = True
        except cleaner.CleanerException, e:
            self.encrypted = False
            self.size = real_size
            reader.address = current_address

    def decode(self, bytes_reader, key):
        value = self.read(bytes_reader)
        if not self.encrypted:
            return value
        value = vminstruction.VMReadInfo.do_operation(self.before_operation, value, key.key, self.size)
        value = vminstruction.VMReadInfo.do_operation(self.first_operation[0], value, self.first_operation[1], self.size)
        value = vminstruction.VMReadInfo.do_operation(self.second_operation[0], value, self.second_operation[1], self.size)
        key.key = (key.key & ((~((1<<(self.size * 8))-1))&((1<<32)-1))) | vminstruction.VMReadInfo.do_operation(self.after_operation, key.key, value, self.size)
        return value

class VMMainHandler(VMHandler):
    cache = {}
    def __init__(self, reader):
        self.read = VMReadInfo(reader)
        if self.read.size != 1:
            raise cleaner.CleanerException("Invalid size for main handler reader")
        reader.get_cond(lambda x: str(x) == "movzx eax, al")
        reader.get_cond(lambda x: str(x) == "jmp dword [edi+eax*4]")

class VMOpcodeHandler(VMHandler):
    def __init__(self, reader):
        try:
            self.read = VMReadInfo(reader)
        except cleaner.CleanerException, e:
            self.read = None

        self.insts = []
        
        while True:
            inst = reader.get()
            if inst.opcode == "lodsb":
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
    def __init__(self, executable, vm_info):
        clean = cleaner.Cleaner(executable)
        fix_handlers = executable.read_dword(vm_info.init_handler.vm_struct + vm_info.init_handler.encode_in_vm_struct) != vm_info.init_handler.encode

        self.handlers = {}
        handlers_to_process = Queue.Queue()
        # Let's find all the handlers now
        for i in xrange(vm_info.init_handler.handlers_in_vm_struct / 4, vm_info.init_handler.handlers_in_vm_struct / 4 + vm_info.init_handler.handlers_count):
            handler_address = executable.read_dword(vm_info.init_handler.vm_struct + i * 4)
            if fix_handlers:
                handler_address = long(handler_address + vm_info.init_handler.encode)
            self.handlers[i] = VMOpcodeHandler(clean.get_reader(handler_address))
            handlers_to_process.put(self.handlers[i])

        variables = {}
        processed = []
        while not handlers_to_process.empty():
            handler = handlers_to_process.get()
            # Try to match with HANDLERS
            matches = cischandlers.find_matches(handler, variables)
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
                if handler.read != None:
                    if len(handler.insts) == 148:
                        handler.assign_name("UKNOWNCHECK")
                        continue
                    elif len(handler.insts) == 150:
                        handler.assign_name("UKNOWNCHECK")
                        continue
                    else:
                        print handler.insts
                        raise Exception("Undetected handler")
                # Detect math operation
                operation_name = cischandlers.find_math_operation(handler)

                try:
                    assert operation_name != None
                except:
                    for inst in handler.insts:
                        print hex(inst.address)
                        print inst
                    raise
                handler.assign_name(operation_name)

        # Good, we have handlers now
            
                
                        

class VMInfo(object):
    cache = {}
    def __init__(self, executable, vm_address):
        clean = cleaner.Cleaner(executable)
        clean.set_option("ignore_jumps", False)
        self.init_handler = VMInit(clean.get_reader(vm_address))
        clean.set_option("ignore_jumps", True)
        self.main_handler = VMMainHandler(clean.get_reader(self.init_handler.main_handler_address))
        self.handlers = VMHandlers(executable, self)

    @classmethod
    def get_vm_info(cls, executable, address):
        if cls.cache.has_key(address):
            return cls.cache[address]
        #try:
        res = cls(executable, address)
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
        
class VMFunction(object):
    def __init__(self, executable, push_inst, jmp_inst):
        self.executable = executable
        assert push_inst.opcode == "push" and push_inst.operands[0].is_immediate()
        assert jmp_inst.opcode == "jmp" and jmp_inst.operands[0].is_immediate()
        vm_address = jmp_inst.operands[0].value
        vm_code_address = push_inst.operands[0].value
        print "Getting VM %08X %08X" % (vm_address, vm_code_address)

        self.vm_info = VMInfo.get_vm_info(executable, vm_address)
        assert self.vm_info != None

        
        addresses_to_explore = Queue.Queue()
        starts = []
        instructions = {}
        instructions_size = {}
        
        # Kinda hackish, but we are looking for the start, and the code is layout like this:
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
        # And we are looking for the jump to label1

        # Start address is the address of push address2/jmp and end address is the address of vmcode
        real_vm_code_address = long(vm_code_address + self.vm_info.init_handler.encode)
        self.code_address = real_vm_code_address
        vm_code_end = push_inst.address 
        start_address = real_vm_code_address
        i = 0
        end_address = start_address
        while True:
            i += 1
            assert i < 0x1000
            try:
                jmp = executable.get_instruction(start_address)
            except:
                start_address -= 1
                continue
            if jmp.opcode == "jmp" and jmp.operands[0].is_immediate() and jmp_inst.address <= jmp.operands[0].value <= jmp_inst.address + 0x20:
                break
            start_address -= 1
        start_address += jmp.size

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put((real_vm_code_address, vm_code_address))
        starts.append(real_vm_code_address)
        while start_address != end_address:
            push = executable.get_instruction(start_address)
            if push.opcode != "push":
                push = executable.get_instruction(push.next)
            assert push.opcode == "push" and push.operands[0].is_immediate()
            jmp = executable.get_instruction(push.next)
            assert jmp.opcode == "jmp" and jmp.operands[0].is_immediate(vm_address)
            addresses_to_explore.put((long(push.operands[0].value + self.vm_info.init_handler.encode), push.operands[0].value))
            starts.append(long(push.operands[0].value + self.vm_info.init_handler.encode))
            start_address = jmp.next
        to_print = False
        while not addresses_to_explore.empty():
            next_labled = True
            address, key = addresses_to_explore.get()
            key = VMKey(key)
            if instructions.has_key(address):
                instructions[address].set_info("labled", True)
                continue
            bytes_reader = vminstruction.BytesReader(executable, address)
            while bytes_reader.address != vm_code_end:
                # TODO: Do a method to do this
                address = bytes_reader.address
                func = self.vm_info.main_handler.read.decode(bytes_reader, key)
                assert self.vm_info.handlers.handlers.has_key(func)
                instructions_size[address] = 1
                if self.vm_info.handlers.handlers[func].read != None:
                    instructions_size[address] += self.vm_info.handlers.handlers[func].read.size
                inst = self.vm_info.handlers.handlers[func].get_vm_instruction(bytes_reader, key)
                
                inst.address = address
                inst.set_info("labled", next_labled)
                next_labled = False                    

                if inst.name in ("JMP", "JMPIF"):
                    inst.args[0] += bytes_reader.address
                    inst.args[0] &= 0xffffffff
                    
                if inst.name == "JMP":
                    next_labled = True
                    bytes_reader.address = inst.args[0]
                    key.reset()
                elif inst.name == "JMPIF":
                    addresses_to_explore.put((inst.args[0], 0))
                elif inst.name == "RESETKEY":
                    key.reset()                

                instructions[inst.address] = inst

                if instructions.has_key(bytes_reader.address):
                    if next_labled:
                        instructions[bytes_reader.address].set_info("labled", True)
                    break

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

    def clean(self):
        TEMPLATES = [r"codevirtualizer\cisc_pre.txt", r"codevirtualizer\cisc.txt", r"ag_templates.txt", r"codevirtualizer\cisc.txt", r"ag_templates.txt", r"templates_final.txt"]

        # Clean nops
        i = 0
        while i < len(self.instructions):
            if self.instructions[i].name == "NOP":
                self.instructions[i:i+1] = []
            i += 1

        for template in TEMPLATES:
            templates.Templates.get_template(template).clean(self.instructions)

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

        code = ""#"use32 org 0x%08X\n" % base_address
        code_base = code
        section_counter = 0
        next_section = 0
        jb_count = 0
        last_jump = 0
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
                
                # Check reg
                for i in xrange(4):
                    registers[reader.get_cond(lambda x: x.name == "POPDWORDREG").args[0]] = regs.pop()
                reader.get_cond(lambda x: x.name == "SETUNKNOWN")
                for i in xrange(4):
                    registers[reader.get_cond(lambda x: x.name == "POPDWORDREG").args[0]] = regs.pop()

                reader.get_cond(lambda x: x.name == "POPF") # flags
                assert regs.pop() == "flags"
                
                reader.get_cond(lambda x: x.name == "ADDDWORDESP" and x.args[0] == 4)
            elif section.end:
                continue

            inst = reader.get()
            while inst:
                is_call = False
                if inst.name.startswith("PUSHDWORD"):
                    reader.push()
                    try:
                        next = reader.get_cond(lambda x: x.name == "JMP" and sections[x.args[0]].end)
                        sectioncode += inst.to_asm(registers).replace("push ", "jmp ") + "\n"
                        last_jump = inst.args[0]
                        break
                    except vminstruction.ReaderException:
                        pass
                    finally:
                        reader.pop()
                elif inst.name == "PUSHWITHENCODE":
                    next = reader.get()
                    if next.name == "JMP":
                        assert sections[next.args[0]].end
                        asminst = self.executable.get_instruction(long(inst.args[0] + self.vm_info.init_handler.encode))                    
                        asminst_after = self.executable.get_instruction(asminst.next)
                        assert asminst_after.opcode == "push"
                        assert asminst_after.operands[0].is_immediate()
                        sectioncode += "\n".join(["db 0x%x" % ord(x) for x in asminst.bytes]) + "\n"
                        next_section = long(asminst_after.operands[0].value + self.vm_info.init_handler.encode)
                        break
                    elif next.name.startswith("PUSHDWORD"):
                        nextnext = reader.get_cond(lambda x: x.name == "JMP" and sections[x.args[0]].end)
                        sectioncode += next.to_asm(registers).replace("push ", "call ") + "\n"
                        break
                    else:
                        assert False

                if inst.name == "MOVENCODEREG":
                    inst = vminstruction.VMInstruction("MOVDWORDREG", inst.args[0], long(self.vm_info.init_handler.encode))
                elif inst.name == "JMP" and not sections[inst.args[0]].end:
                    inst = vminstruction.VMInstruction("JMPLABEL", inst.args[0])
                elif inst.name in vminstruction.CONDITIONAL_JUMPS:
                    inst = vminstruction.VMInstruction(inst.name + "LABEL", inst.args[0])
                elif inst.name.endswith("ADDRESS") and inst.name[:-len("ADDRESS")] in vminstruction.CONDITIONAL_JUMPS:
                    assert sections[inst.args[1]].end 
                    inst = vminstruction.VMInstruction(inst.name[:-len("ADDRESS")], inst.args[0])
                if inst.name == "SETRETN":
                    next = reader.get_cond(lambda x: x.name == "JMP" and sections[x.args[0]].end)
                    sectioncode += "ret %d\n" % inst.args[0]
                    break
                elif inst.name == "JMP": # jmp to end
                    sectioncode += "ret\n"
                    break
                else:
                    sectioncode += inst.to_asm(registers) + "\n"
                inst = reader.get()
            code += sectioncode
            
        if section_counter == 1:
            index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
            # Deal with anti-debugging
            if index != -1:
                code = code_base + code[code.find("\n", index+1)+1:]
        code = code.replace("push eax\npush ecx\npush edx\npush ebx\npush ebx\npush ebp\npush esi\npush edi", "pushad")
        code = code.replace("pop edi\npop esi\npop ebp\npop ebx\npop ebx\npop edx\npop ecx\npop eax", "popad")
        #print code
        self.code = code[:-1]
        return self.code

    def compile_code(self, address = None):
        code = self.get_code()
        if address == None:
            address = self.code_address
        compiled_code = instruction.Assembler(self.executable.mode).assemble(code, address)
        return address, compiled_code        
        
    
        
    def printfunc(self):
        for inst in self.instructions:
            print inst

def get_vm(executable, address):
    push_inst = executable.get_instruction(address)
    jmp_inst = executable.get_instruction(push_inst.next)
    vm = VMFunction(executable, push_inst, jmp_inst)
    vm.clean()
    return vm
        
def get_vm_code(executable, push_inst, jmp_inst):
    vm = VMFunction(executable, push_inst, jmp_inst)
    #print "Cleaning vm.."
    vm.clean()
    #vm.printfunc()
    #print "Converting to asm..."
    try:
        return vm.get_code()
    except:
        vm.printfunc()
        raise
    
def get_compiled_vm_code(executable, push_inst, jmp_inst, address = None):
    vm = VMFunction(executable, push_inst, jmp_inst)
    vm.clean()
    code = vm.get_code()
    if address == None:
        address = vm.code_address
    #print code
    code = ("use32 org 0x%08X\n" % address) + code
    source = tempfile.NamedTemporaryFile("wb", delete = False)
    source.write(code)
    source.close()

    # Ugly hack to get temporary file name
    output = tempfile.NamedTemporaryFile("wb", delete = False)
    output.close()
    os.unlink(output.name)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    fasm = subprocess.Popen([r"vms\fasm.exe", source.name, output.name], stdout = subprocess.PIPE, stderr = subprocess.STDOUT, startupinfo=startupinfo)
    if fasm.wait() != 0:
        raise Exception(fasm.stdout.read())
    print fasm.stdout.read()
    compiled_code = open(output.name, "rb").read()
    os.unlink(output.name)
    os.unlink(source.name)  
    
    return address, compiled_code

def fix_vms(pe, code_section = 0, vms_section = 3):
    vms = []
    code_section_start = pe.sections[code_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
    code_section_end = code_section_start + pe.sections[code_section].Misc_VirtualSize
    vms_section_start = pe.sections[vms_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
    vms_section_end = vms_section_start + pe.sections[vms_section].Misc_VirtualSize
    exe = executable.ToExecutable(pe)
    for address in xrange(code_section_start, code_section_end):
        if exe.read_byte(address) in (0xe9, 0xeb): # Jump
            if exe.read_byte(address) == 0xe9:
                jmp_address = exe.read_dword(address + 1) + address + 5
            else:
                jmp_address = exe.read_byte(address + 1) + address + 2
            if vms_section_start <= jmp_address <= vms_section_end:
                push_inst = exe.get_instruction(jmp_address)
                jmp_inst = exe.get_instruction(push_inst.next)
                if not (push_inst.opcode == "push" and push_inst.operands[0].is_immediate()): continue
                if not (jmp_inst.opcode == "jmp" and jmp_inst.operands[0].is_immediate()): continue
                print hex(address)
                vm = get_vm(exe, jmp_address)
                try:
                    code = vm.get_code()
                except:
                    vm.printfunc()
                    raise
                last_line = code.splitlines()[-1]
                assert last_line.startswith("jmp ")
                end_address = int(last_line.split()[1], 16)
                code_address, compiled_code = vm.compile_code(address + 0x12)
                assert end_address - code_address > len(compiled_code)
                if end_address - code_address - 0x12 != len(compiled_code) - 2:
                    print "Warning: Code size is different %d" % (end_address - code_address - 0x12 - (len(compiled_code) - 2))
                exe.write(address, "\xeb\x10")
                exe.write(code_address, compiled_code)
                #addressd, compil vm.compile_code(address + 0x12)
                
