from vms import vminstruction
from vms import templates
from vms import vm
import instruction
try:
    import progressbar
    PROGRESSBAR = True
except ImportError:
    PROGRESSBAR = False

import handlers_common
import handlers_32
import handlers_64

import Queue

class VMHandler(object):
    def __init__(self, reader):
        pass

class VMInit(VMHandler):
    def __init__(self, file, address):
        print "Reading VMInit...",
        mode = file.get_arch()
        reader = file.get_reader(address)
        if file.mode == 32:
            registers = 8 + 1
        else:
            registers = 16 + 1

        self.regs = []
        for i in xrange(registers):
            inst = reader.get_cond(lambda x: (x.opcode == "push" and x.operands[0].is_reg()) or x.opcode == mode.translate("pushf{SB}"))
            if inst.opcode == "push":
                self.regs.append(inst.operands[0].reg)
            else:
                self.regs.append("flags")
        self.pushed = registers

        self.unknown_address = reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_memory() and x.operands[0].base is None and x.operands[0].index is None).operands[0].offset

        if file.mode == 32:
            reader.get_cond(lambda x: str(x) == "push 0x0")
        else:
            reader.get_cond(lambda x: str(x) == "mov rax, 0x0")
            reader.get_cond(lambda x: str(x) == "mov r13, rax")
            reader.get_cond(lambda x: str(x) == "push rax")
        self.pushed += 2

        # mov esi, [esp+0x30]/[rsp+0xA0]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("esi") and x.operands[1].is_memory() and x.operands[1].base == mode.reg_native("sp") and x.operands[1].offset == (self.pushed + 1) * mode.pointer_size())
        # mov ebp, esp
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("bp")) and x.operands[1].is_reg(mode.reg_native("sp")))
        # sub esp, 0xc0/0x140
        if file.mode == 32:
            s = 0xc0
        else:
            s = 0x140
        reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg(mode.reg_native("sp")) and x.operands[1].is_immediate(s))
        if file.mode == 64:
            reader.get_cond(lambda x: str(x) == "and rsp, -0x10")
        # mov edi, esp
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("di")) and x.operands[1].is_reg(mode.reg_native("sp")))

        self.advance_si_address = reader.address

        if file.mode == 64:
            #lea r12, [0x403596]
            self.handlers_address = reader.get_cond(lambda x: x.opcode == "lea" and x.operands[0].is_reg("r12") and x.operands[1].is_memory() and x.operands[1].base is None and x.operands[1].index is None).operands[1].offset
            reader.get_cond(lambda x: str(x) == "mov rax, 0x0")
            reader.get_cond(lambda x: str(x) == "add rsi, rax")
        else:
            self.handlers_address = None

        #add rsi, qword [rbp]
        reader.get_cond(lambda x: str(x) == mode.translate("add {R:si}, {S} [{R:bp}]"))

        self.main_handler_address = reader.address
        print "SUCCESS"


class VMReadInfo(vminstruction.VMReadInfo):
    READ_SIZES = \
        {1:
            [
                "mov al, byte [{R:si}]",
                "movzx eax, byte [{R:si}]",
            ],
        2:
            [
                "mov ax, word [{R:si}]",
                "movzx eax, word [{R:si}]",
            ],
        4:
            [
                "mov eax, dword [{R:si}]",
            ],
        8:
            [
                "mov rax, qword [{R:si}]",
            ]
        }

    INC_SIZES_BYTE = "inc {R:si}"
    INC_SIZES = [
        "lea {R:si}, [{R:si}+0x%x]",
        "add {R:si}, 0x%x",
        "sub {R:si}, -0x%x"
    ]
    INC_SIZES_SUB = "sub {R:si}, 0x%x"

    def __init__(self, reader):
        vminstruction.VMReadInfo.__init__(self, reader)
        current_address = reader.address
        inst_str = str(reader.get())
        self.end = False
        self.extend_size = 0
        mode = reader.file.get_arch()
        for size, insts in self.READ_SIZES.iteritems():
            for inst in insts:
                if inst_str == mode.translate(inst):
                    self.size = size
                    break
            if self.size:
                break

        if self.size == 0:
            reader.address = current_address
            self.end = True
            return

        self.continue_read(reader)

        if self.size == 1:
            current_address = reader.address
            try:
                reader.get_cond(lambda x: x.opcode == "cbw")
                self.extend_size = 2
                self.continue_read(reader)
            except instruction.ReaderException:
                reader.address = current_address

        if self.size == 2 or self.extend_size == 2:
            current_address = reader.address
            try:
                reader.get_cond(lambda x: x.opcode == "cwde")
                self.extend_size = 4
                self.continue_read(reader)
            except instruction.ReaderException:
                reader.address = current_address

        if self.size == 4 or self.extend_size == 4:
            current_address = reader.address
            try:
                reader.get_cond(lambda x: x.opcode == "cdqe")
                self.extend_size = 8
                self.continue_read(reader)
            except instruction.ReaderException:
                reader.address = current_address

    def continue_read(self, reader):
        if self.end:
            return
        current_address = reader.address
        mode = reader.file.get_arch()
        inst_str = str(reader.get())
        if self.size == 1 and inst_str == mode.translate(self.INC_SIZES_BYTE):
            self.end = True
            return
        for inst in self.INC_SIZES:
            if inst_str == mode.translate(inst % self.size):
                self.end = True
                return
        if inst_str == mode.translate(self.INC_SIZES_SUB % ((-self.size) & ((1 << mode.mode) - 1))):
            self.end = True
            return
        reader.address = current_address

    def read(self, bytes_reader):
        value = super(VMReadInfo, self).read(bytes_reader)
        if self.extend_size:
            size = self.size
            while size < self.extend_size:
                if value >> ((size*8)-1):
                    value |= ((~0) & ((1 << (size*8)) - 1)) << (size*8)
                size *= 2
        return value

class VMMainHandler(VMHandler):
    def __init__(self, file, address, init_handler):
        print "Reading VMMainHandler...",
        reader = file.get_reader(address)
        mode = file.get_arch()

        self.read = VMReadInfo(reader)

        reader.get_cond(lambda x: str(x) == mode.translate("movzx {R:ax}, al"))
        if not self.read.end:
            self.read.continue_read(reader)

        if file.mode == 32:
            init_handler.handlers_address = reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_memory() and x.operands[0].base is None and x.operands[0].index == "eax" and x.operands[0].scale == 4).operands[0].offset
        else:
            reader.get_cond(lambda x: str(x) == "jmp qword [r12+rax*8]")

        print "SUCCESS"

class VMOpcodeHandler(VMHandler):
    def __init__(self, reader):
        self.address = reader.address
        self.insts = []
        self.read = VMReadInfo(reader)
        if self.read.size == 0:
            self.read = None

        while True:
            if self.read is not None and not self.read.end:
                self.read.continue_read(reader)
            inst = reader.get()
            #print "0x%x: %s" % (inst.address, str(inst))
            if inst.opcode == "jmp" and inst.operands[0].is_immediate():
                # TODO: The jump can be to three places:
                # Main handler
                # Advance si
                # Check stack
                break
            self.insts.append(inst)
            if inst.opcode == "ret":
                break


    def assign_name(self, name):
        self.name = name
        #del self.insts

    def get_vm_instruction(self, bytes_reader):
        if self.read is not None:
            return vminstruction.VMInstruction(self.name, self.read.read(bytes_reader))
        return vminstruction.VMInstruction(self.name)
            
class VMHandlers(object):
    def __init__(self, file, vm_info):
        self.file = file
        self.vm_info = vm_info
        self.handlers = {}
        self.handlers_by_address = {}

        found = False
        # Find ret
        mode = self.file.get_arch()
        for i in xrange(0x100):
            handler_address = self.file.read_pointer(self.vm_info.init_handler.handlers_address + i * mode.pointer_size())
            try:
                reader = self.file.get_reader(handler_address)
                reader.get_cond(lambda x: str(x) == mode.translate("mov {R:sp}, {R:bp}"))
                print "a"
                # Dummy pops
                for j in xrange(self.vm_info.init_handler.pushed - len(self.vm_info.init_handler.regs)):
                    reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg())

                rev_regs = self.vm_info.init_handler.regs[::-1]
                for reg in rev_regs:
                    if reg == "flags":
                        reader.get_cond(lambda x: str(x) == mode.translate("popf{SB}"))
                    elif reg == "rsp":
                        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg())
                    else:
                        try:
                            reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(reg))
                        except instruction.ReaderException:
                            assert rev_regs.count(reg) == 2
                            reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg())
                reader.get_cond(lambda x: str(x) == "ret")
            except instruction.ReaderException:
                continue

            handler = VMOpcodeHandler(self.file.get_reader(handler_address))
            handler.assign_name("RETURN")
            self.handlers[i] = handler
            self.handlers_by_address[handler_address] = handler
            found = True
            break
        assert found

    def get_handler(self, index):
        if index in self.handlers:
            return self.handlers[index]

        mode = self.file.get_arch()
        handler_address = self.file.read_pointer(self.vm_info.init_handler.handlers_address + index * mode.pointer_size())
        if handler_address in self.handlers_by_address:
            self.handlers[index] = self.handlers_by_address[handler_address]
            return self.handlers_by_address[handler_address]

        handler = VMOpcodeHandler(self.file.get_reader(handler_address))

        # Try to match with HANDLERS
        handler_name = handlers_common.match_handler(mode, handlers_common.HANDLERS, handler)
        # if handler_name is None:
        # if file.mode == 32:
        #     matches += handlers_common.find_matches(mode, handlers_32.HANDLERS, handler)
        # else:
        #     matches += handlers_common.find_matches(mode, handlers_64.HANDLERS, handler)
        if handler_name is None:
            for inst in handler.insts:
                print inst
            handler_name = handlers_common.match_handler(mode, handlers_common.HANDLERS, handler)
            assert False

        handler.assign_name(handler_name)

        self.handlers[index] = handler
        return handler
                        

class VMInfo(vm.VMInfo):
    cache = {}
    def __init__(self, file, vm_address):
        print "Parsing VMP%d VM at 0x%08x" % (file.mode, vm_address)
        self.init_handler = VMInit(file, vm_address)
        self.main_handler = VMMainHandler(file, self.init_handler.main_handler_address, self.init_handler)
        self.handlers = VMHandlers(file, self)

    
class VMFunctionSection(object):
    def __init__(self, address):
        self.address = address
        self.start = False
        self.end = False
        self.instructions = [] 
    

class VMFunctionJumper(vm.VMFunctionJumper):
    def __init__(self, file, address):
        push_inst = file.get_instruction(address)
        call_inst = file.get_instruction(push_inst.next)
        assert push_inst.opcode == "push" and push_inst.operands[0].is_immediate()
        assert call_inst.opcode == "call" and call_inst.operands[0].is_immediate()
        self.vm_code_address = push_inst.operands[0].value
        self.vm_address = call_inst.operands[0].value
        self.ret_address = call_inst.next

    def get_vm_address(self):
        return self.vm_address


class VMFunction(vm.VMFunction):
    def __init__(self, file, vm_info, jumper):
        self.mode = file.mode
        self.file = file
        vm_code_address = jumper.vm_code_address

        self.vm_info = vm_info
        
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
        #real_vm_code_address = long(vm_code_address + self.vm_info.init_handler.encode + self.vm_info.init_handler.encode_address_high_dword)
        self.code_address = vm_code_address

        print ("Reading VMFunction at 0x%08x..." % self.code_address),

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put(vm_code_address)
        starts.append(vm_code_address)

        to_print = False
        while not addresses_to_explore.empty():
            next_labeled = True
            address = addresses_to_explore.get()
            print "@@@@"
            print hex(address)
            if instructions.has_key(address):
                instructions[address].set_info("labled", True)
                continue
            bytes_reader = vminstruction.BytesReader(file, address)
            section_instructions = []
            while True:
                if instructions.has_key(bytes_reader.address):
                    if next_labeled:
                        instructions[bytes_reader.address].set_info("labled", True)
                    break

                # TODO: Do a method to do this
                address = bytes_reader.address
                func = self.vm_info.main_handler.read.read(bytes_reader)
                handler = self.vm_info.handlers.get_handler(func)
                instructions_size[address] = 1
                if handler.read is not None:
                    instructions_size[address] += handler.read.size
                inst = handler.get_vm_instruction(bytes_reader)

                inst.address = address
                inst.set_info("labled", next_labeled)
                next_labeled = False

                #if inst.name == "STACK_JMP":
                #    break
                if inst.name == "PUSH_DWORD_IMM" and 0x403000 < inst.args[0] < 0x405000:
                    addresses_to_explore.put(inst.args[0])
                # if inst.name in ("JMP", "JMPIF"):
                #     inst.args[0] += bytes_reader.address
                #     inst.args[0] &= (1 << self.mode) - 1
                #
                # if inst.name == "JMP":
                #     next_labeled = True
                #     bytes_reader.address = inst.args[0]
                #     key.reset()
                # elif inst.name == "JMPIF":
                #     addresses_to_explore.put((inst.args[0], 0))
                # elif inst.name == "RESETKEY":
                #     key.reset()
                #     # It isn't really an opcode, so don't store it
                #     continue
                # elif inst.name == "PUSH_ENCODED":
                #     try:
                #         jumper = VMFunctionJumper(file, long(inst.args[0] + self.vm_info.init_handler.encode))
                #     except:
                #         tinst = file.get_instruction(long(inst.args[0] + self.vm_info.init_handler.encode))
                #         jumper = VMFunctionJumper(file, tinst.next)
                #     jmp_vm_code_address = long(jumper.vm_code_address + self.vm_info.init_handler.encode + self.vm_info.init_handler.encode_address_high_dword)
                #     addresses_to_explore.put((jmp_vm_code_address, jumper.vm_code_address))
                #     starts.append(jmp_vm_code_address)
                # elif inst.name in ("ADD_DX_REALLOC", "STACK_ADD_REALLOC"): # TODO: Properly support reallocation
                #     inst.name += "_VALUE"
                #     inst.args = [self.vm_info.handlers.realloc_offset]

                instructions[inst.address] = inst
                section_instructions.append(inst)
                #print inst
                if inst.name == "RETURN":
                    break
                elif inst.name == "STACK_JMP":
                    break
            self._clean_section(section_instructions)
            for inst in section_instructions:
                print inst
            print "------------------------------------"
        print "SUCCESS"
        assert False


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

    def _clean_section(self, instructions):
        TEMPLATES = ["vmp_00_clean.txt"]
        vars = {}
        vars["SIZE_TO_NUM"] = lambda x: {"BYTE": 1, "WORD": 2, "DWORD": 4, "QWORD": 8}[x]
        for template in TEMPLATES:
            templates.Templates.get_template(r"vmprotect\%s" % template, self.mode).clean(instructions, vars)
        return instruction

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
        section_counter = 0
        next_section = 0
        registers = None

        integrity_used = False

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
                    if integrity_used:
                        # TODO: Find the end in a proper way...
                        index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
                        if index != -1:
                            code = code[code.find("\n", index+1)+1:]
                section_counter += 1

                regs = list(self.vm_info.init_handler.regs)

                # For older version
                #reader.get_cond(lambda x: x.name == "POPF") # flags
                #assert regs.pop() == "flags"

                pop_reg = "POP_%s_REG" % native_size_word
                # Check reg
                if self.mode == 32:
                    if self.vm_info.init_handler.old_version:
                        reader.get_cond(lambda x: x.name == pop_reg and x.args[0] == 0x7) # POPF
                        assert regs.pop() == "flags"
                    for i in xrange(4):
                        registers[reader.get_cond(lambda x: x.name == pop_reg).args[0]] = regs.pop()
                    reader.get_cond(lambda x: x.name == "SET_CHECK_CX_REG")  # TODO: Verify that it is ecx?
                    for i in xrange(4):
                        registers[reader.get_cond(lambda x: x.name == pop_reg).args[0]] = regs.pop()
                    if not self.vm_info.init_handler.old_version:
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
                    # This vm instruction only used in anti-dump/integrity-test
                    assert section_counter == 0
                    integrity_used = True
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
            if integrity_used:
                # TODO: Find the end in a proper way...
                index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
                if index != -1:
                    code = code[code.find("\n", index+1)+1:]

        if self.mode == 32:
            code = code.replace("push eax\npush ecx\npush edx\npush ebx\npush ebx\npush ebp\npush esi\npush edi", "pushad")
            code = code.replace("pop edi\npop esi\npop ebp\npop ebx\npop ebx\npop edx\npop ecx\npop eax", "popad")
            code = code.replace("mov esp, ebp\npop ebp", "leave")
        else:
            code = code.replace("mov rsp, rbp\npop rbp", "leave")
        #print code
        self.code = code[:-1]
        return self.code

    def printfunc(self):
        for inst in self.instructions:
            print inst
