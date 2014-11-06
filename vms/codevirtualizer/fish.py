import utils
from themida import cleaner
from vms import vminstruction
from vms import templates
from vms.codevirtualizer import fishhandlers
import instruction
import Queue

import os
import tempfile
import subprocess

class VMHandler(object):
    def __init__(self, reader):
        pass
        
class VMStructField(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size
        
class VMStructFieldDword(VMStructField):
    def __init__(self, name):
        VMStructField.__init__(self, name, 4)

class VMStruct(object):
    def __init__(self):
        self.fields = {}
        
    def add_field(self, offset, field):
        # TODO: verify
        self.fields[offset] = field
        
    def get_field(self, offset):
        return self.fields.get(offset)
        
    def get_field_offset_by_name(self, name):
        for offset, field in self.fields.iteritems():
            if field.name == name:
                return offset
        return None
        
class VMInit(VMHandler):
    cache = {}
    def __init__(self, vm_info, executable, address):
        clean = cleaner.Cleaner(executable)
        clean.set_option("fixOperationConstantThruRegOnStack", True)
        clean.set_option("fixPush_allowConstants", True)
        clean.set_option("ignore_jumps", False)
        reader = clean.get_reader(cleaner.JunkSkipper(executable).get_next_real_instruction(address).address)
        # pushf
        #reader.get_cond(lambda x: x.opcode == "pushf")  # In new version the pushf is before the jump
        self.regs = ["flags"]
        # pusha
        #reader.get_cond(lambda x: x.opcode == "pusha") # In new version it is splitted
        pusha_regs = ["eax", "ecx", "edx", "ebx", "ebx", "ebp", "esi", "edi"]
        for reg in pusha_regs:
            reader.get_cond(lambda x: x.opcode == "push" and x.operand1.is_reg(reg))
            self.regs.append(reg)
        # call $+5
        self.base_address = reader.get_cond(lambda x: x.opcode == "call" and x.operand1.value == x.address + 5).operand1.value
        # pop ecx
        reader.get_cond(lambda x: x.opcode == "pop" and x.operand1.is_reg("ecx"))
        # sub ecx, X
        self.base_address -= reader.get_cond(lambda x: x.opcode == "sub" and x.operand1.is_reg("ecx") and x.operand2.is_immediate()).operand2.value # Get the address of the start of main handler
        assert self.base_address == address
        # sub ecx, X
        self.base_address -= reader.get_cond(lambda x: x.opcode == "sub" and x.operand1.is_reg("ecx") and x.operand2.is_immediate()).operand2.value
        # mov ebp, X
        self.vm_struct = self.base_address + reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebp") and x.operand2.is_immediate()).operand2.value
        # add ebp, ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operand1.is_reg("ebp") and x.operand2.is_reg("ecx")) # Get the address of the start of main handler
        
        # push ecx
        reader.get_cond(lambda x: x.opcode == "push" and x.operand1.is_reg("ecx"))
        # mov ecx, 1
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ecx") and x.operand2.is_immediate(1))
        # mov ebx, X
        vm_info.struct.add_field(reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_immediate()).operand2.value, VMStructFieldDword("LOCK"))
        # xor eax, eax
        lock_loop_start = reader.get_cond(lambda x: x.opcode == "xor" and x.operand1.is_reg("eax") and x.operand2.is_reg("eax")).address
        # cmpxchg [ebp+ebx], ecx
        reader.get_cond(lambda x: x.opcode == "cmpxchg" and x.operand2.is_reg("ecx") and x.operand1.is_memory() and x.operand1.base == "ebp" and x.operand1.index == "ebx" and x.operand1.displacement == 0 and x.operand1.scale == 0)
        # jz lock_loop_end
        lock_loop_end = reader.get_cond(lambda x: x.opcode == "jz").operand1.value
        # pause
        reader.get_cond(lambda x: x.bytes == "\xF3\x90") # TODO
        # jmp lock_loop_start
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operand1.is_immediate(lock_loop_start))
        # pop ecx
        reader.get_cond(lambda x: x.address == lock_loop_end and x.opcode == "pop" and x.operand1.is_reg("ecx"))
        
        # mov ebx, X
        vm_info.struct.add_field(reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_immediate()).operand2.value, VMStructFieldDword("BASE_ADDRESS"))
        # mov [ebp+ebx], ecx
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand2.is_reg("ecx") and x.operand1.is_memory() and x.operand1.base == "ebp" and x.operand1.index == "ebx" and x.operand1.displacement == 0 and x.operand1.scale == 0)
        
        # mov ebx, X
        vm_info.struct.add_field(reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_immediate()).operand2.value, VMStructFieldDword("BASE_ADDRESS"))
        # mov [ebp+ebx], X
        self.original_base_address = reader.get_cond(lambda x: x.opcode == "mov" and x.operand2.is_immediate() and x.operand1.is_memory() and x.operand1.base == "ebp" and x.operand1.index == "ebx" and x.operand1.displacement == 0 and x.operand1.scale == 0).operand2.value
        
        # mov ebx, X
        vm_info.struct.add_field(reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_immediate()).operand2.value, VMStructFieldDword("EIP"))
        # mov eax, [esp+0x28]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("eax") and x.operand2.is_memory() and x.operand2.base == "esp" and x.operand2.index == None and x.operand2.displacement == 0x28 and x.operand2.scale == 0)
        # add eax, ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operand1.is_reg("eax") and x.operand2.is_reg("ecx"))
        # mov [ebp+ebx], eax
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand2.is_reg("eax") and x.operand1.is_memory() and x.operand1.base == "ebp" and x.operand1.index == "ebx" and x.operand1.displacement == 0 and x.operand1.scale == 0)
        
        
        # mov eax, X
        self.handlers_address = self.base_address + reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("eax") and x.operand2.is_immediate()).operand2.value
        # add eax ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operand1.is_reg("eax") and x.operand2.is_reg("ecx"))
        # mov ebx, X
        vm_info.struct.add_field(reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_immediate()).operand2.value, VMStructFieldDword("HANDLERS_ADDRESS"))
        # mov edx, [ebp+ebx]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("edx") and x.operand2.is_memory() and x.operand2.base == "ebp" and x.operand2.index == "ebx" and x.operand2.displacement == 0 and x.operand2.scale == 0)
        # cmp edx, eax
        reader.get_cond(lambda x: x.opcode == "cmp" and x.operand1.is_reg("edx") and x.operand2.is_reg("eax"))
        # jz after_handlers_init
        after_handlers_init = reader.get_cond(lambda x: x.opcode == "jz").operand1.value
        
        
        # push ebx
        reader.get_cond(lambda x: x.opcode == "push" and x.operand1.is_reg("ebx"))        
        # mov ebx, X
        self.handlers_count = reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_immediate() and (x.operand2.value % 4) == 0).operand2.value >> 2
        # shr ebx, 2
        reader.get_cond(lambda x: x.opcode == "shr" and x.operand1.is_reg("ebx") and x.operand2.is_immediate(2))
        # push eax
        reader.get_cond(lambda x: x.opcode == "push" and x.operand1.is_reg("eax")) 
        
        # test ebx, ebx
        init_next_handler = reader.get_cond(lambda x: x.opcode == "test" and x.operand1.is_reg("ebx") and x.operand2.is_reg("ebx")).address
        # jz handlers_init_end
        handlers_init_end = reader.get_cond(lambda x: x.opcode == "jz").operand1.value
        
        # add [eax], ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operand2.is_reg("ecx") and x.operand1.is_memory() and x.operand1.base == "eax" and x.operand1.index == None and x.operand1.displacement == 0 and x.operand1.scale == 0)
        # add eax, 4
        reader.get_cond(lambda x: x.opcode == "add" and x.operand1.is_reg("eax") and x.operand2.is_immediate(4))
        # dec ebx
        reader.get_cond(lambda x: (x.opcode == "dec" and x.operand1.is_reg("ebx")) or (x.opcode == "sub" and x.operand1.is_reg("ebx") and x.operand2.is_immediate(1))) # TODO fix cleaner
        # jmp init_next_handler
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operand1.is_immediate(init_next_handler))

        # pop eax
        reader.get_cond(lambda x: x.opcode == "pop" and x.operand1.is_reg("eax"))
        # pop ebx
        reader.get_cond(lambda x: x.opcode == "pop" and x.operand1.is_reg("ebx"))
        # mov [ebp+ebx], eax
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand2.is_reg("eax") and x.operand1.is_memory() and x.operand1.base == "ebp" and x.operand1.index == "ebx" and x.operand1.displacement == 0 and x.operand1.scale == 0)
        # mov ebx, [esp+0x24]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operand1.is_reg("ebx") and x.operand2.is_memory() and x.operand2.base == "esp" and x.operand2.index == None and x.operand2.displacement == 0x24 and x.operand2.scale == 0)
        # shl ebx, 2
        reader.get_cond(lambda x: x.opcode == "shl" and x.operand1.is_reg("ebx") and x.operand2.is_immediate(2))
        # add eax, ebx
        init_next_handler = reader.get_cond(lambda x: x.opcode == "add" and x.operand1.is_reg("eax") and x.operand2.is_reg("ebx")).address
        # jmp [eax]
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operand1.is_memory() and x.operand1.base == "eax" and x.operand1.index == None and x.operand1.displacement == 0 and x.operand1.scale == 0)        



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
        #clean = cleaner.Cleaner(executable)
        fix_handlers = executable.read_dword(vm_info.init_handler.vm_struct + vm_info.struct.get_field_offset_by_name("HANDLERS_ADDRESS")) != vm_info.init_handler.handlers_address

        self.handlers = {}
        handlers_to_process = Queue.Queue()
        # Let's find all the handlers now
        for i in xrange(vm_info.init_handler.handlers_count):
            handler_address = executable.read_dword(vm_info.init_handler.handlers_address + i * 4)
            if fix_handlers:
                handler_address = handler_address + vm_info.init_handler.base_address
            print hex(handler_address)
            func = fishhandlers.get_handler(instruction.Function(exe,handler_address))
            fishhandlers.print_instructions(func)
            #self.handlers[i] = VMOpcodeHandler(executable.get_reader(handler_address))
            #handlers_to_process.put(self.handlers[i])
        assert False
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
        self.struct = VMStruct()
        self.init_handler = VMInit(self, executable, vm_address)
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


class VMFunctionJumper(object):
    def __init__(self, executable, address):
        clean = cleaner.Cleaner(executable)
        clean.set_option("fixOperationConstantThruRegOnStack", True)
        clean.set_option("fixPush_allowConstants", True)
        clean.set_option("ignore_jumps", False)
        reader = clean.get_reader(cleaner.JunkSkipper(executable).get_next_real_instruction(address).address)
        # pushf
        reader.get_cond(lambda x: x.opcode == "pushf")
        # push first_handler
        self.first_handler = reader.get_cond(lambda x: x.opcode == "push" and x.operand1.is_immediate()).operand1.value
        # push vm_code_address
        self.vm_code_address = reader.get_cond(lambda x: x.opcode == "push" and x.operand1.is_immediate()).operand1.value
        # Now switch between pushf and vm_code_address (so it will be as in the order of the old versions)
        reader.get_cond(lambda x: str(x) == "push eax")
        reader.get_cond(lambda x: str(x) == "push ebx")
        reader.get_cond(lambda x: str(x) == "mov eax, [esp+0x10]")
        reader.get_cond(lambda x: str(x) == "mov ebx, [esp+0x8]")
        reader.get_cond(lambda x: str(x) == "mov dword [esp+0x8], eax")
        reader.get_cond(lambda x: str(x) == "mov dword [esp+0x10], ebx")
        reader.get_cond(lambda x: str(x) == "pop ebx")
        reader.get_cond(lambda x: str(x) == "pop eax")
        self.vm_address = reader.get_cond(lambda x: x.opcode == "jmp" and x.operand1.is_immediate()).operand1.value
        self.end = reader.address
      
class VMFunction(object):
    def __init__(self, executable, jumper):
        self.executable = executable

        vm_address = jumper.vm_address
        vm_code_address = jumper.vm_code_address
        first_handler = jumper.first_handler
        print "Getting VM %08X %08X" % (vm_address, vm_code_address)

        self.vm_info = VMInfo.get_vm_info(executable, vm_address)
        assert self.vm_info != None
        assert False
        
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
            if jmp.opcode == "jmp" and jmp.operand1.is_immediate() and jumper.end <= jmp.operand1.value <= jumper.end + 0x20:
                break
            start_address -= 1
        start_address += jmp.length

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put((real_vm_code_address, vm_code_address))
        starts.append(real_vm_code_address)
        while start_address != end_address:
            push = executable.get_instruction(start_address)
            if push.opcode != "push":
                push = executable.get_instruction(push.next)
            assert push.opcode == "push" and push.operand1.is_immediate()
            jmp = executable.get_instruction(push.next)
            assert jmp.opcode == "jmp" and jmp.operand1.is_immediate(vm_address)
            addresses_to_explore.put((long(push.operand1.value + self.vm_info.init_handler.encode), push.operand1.value))
            starts.append(long(push.operand1.value + self.vm_info.init_handler.encode))
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
        TEMPLATES = [r"codevirtualizer\cisc_pre.txt", r"codevirtualizer\cisc.txt", r"ag_templates.txt", r"codevirtualizer\cisc.txt", r"ag_templates.txt"]

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
                        assert asminst_after.operand1.is_immediate()
                        sectioncode += "\n".join(["db 0x%x" % ord(x) for x in asminst.bytes]) + "\n"
                        next_section = long(asminst_after.operand1.value + self.vm_info.init_handler.encode)
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
        code = code.replace("push eax\npush ecx\npush edx\npush ebx\npush ebx\npush ebp\npush esi\npush edi", "pusha")
        code = code.replace("pop edi\npop esi\npop ebp\npop ebx\npop ebx\npop edx\npop ecx\npop eax", "popa")
        #print code
        self.code = code[:-1]
        return self.code

    def compile_code(self, address = None):
        code = self.get_code()
        if address == None:
            address = self.code_address
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
        #print fasm.stdout.read()
        compiled_code = open(output.name, "rb").read()
        os.unlink(output.name)
        os.unlink(source.name)  
        
        return address, compiled_code        
        
    
        
    def printfunc(self):
        for inst in self.instructions:
            print inst

def get_vm(executable, address):
    vm = VMFunction(executable, VMFunctionJumper(executable, address))
    #vm.clean()
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
                if not (push_inst.opcode == "push" and push_inst.operand1.is_immediate()): continue
                if not (jmp_inst.opcode == "jmp" and jmp_inst.operand1.is_immediate()): continue
                print hex(address)
                vm = get_vm(exe, jmp_address)
                code = vm.get_code()
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
                
