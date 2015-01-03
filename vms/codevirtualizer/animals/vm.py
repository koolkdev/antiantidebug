from themida import cleaner
from vms import vminstruction
from vms import templates

import handlers_decompiler
import handlers_parser
import fish_handlers_cleaner
import fish_handlers
import vm_encoding

import instruction
import Queue

import sys

try:
    import progressbar
    PROGRESSBAR = True
except ImportError:
    PROGRESSBAR = False

class VMHandler(object):
    def __init__(self, reader):
        pass

class VMInit(VMHandler):
    cache = {}
    def __init__(self, vm_info, file, address):
        clean = cleaner.Cleaner(file)
        #clean.set_option("fixOperationConstantThruRegOnStack", True)
        clean.set_option("fixPush_allowConstants", True)
        clean.set_option("ignore_jumps", False)
        org_address = address
        if file.mode == 32:
            address = cleaner.JunkSkipper(file).get_next_real_instruction(address).address
        reader = clean.get_reader(address)
        mode = file.get_arch()
        # pushf
        #reader.get_cond(lambda x: x.opcode == "pushf")  # In new version the pushf is before the jump
        self.regs = ["flags"]
        # pusha
        #reader.get_cond(lambda x: x.opcode == "pusha") # In new version it is splitted
        if file.mode == 64:
            self.base_address = reader.get_cond(lambda x: x.opcode == "call" and x.operands[0].value == x.address + 5).operands[0].value
            registers = 15
        else:
            registers = 8

        #pusha_regs = ["eax", "ecx", "edx", "ebx", "ebx", "ebp", "esi", "edi"]
        for i in xrange(registers):
            self.regs.append(reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg()).operands[0].reg)

        if file.mode == 64:
            # Now get the result of the call and put the last register
            # mov rcx, qword [rsp+0x78]
            reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("rcx") and x.operands[1].is_memory() and x.operands[1].base == "rsp" and x.operands[1].index is None and x.operands[1].offset == 0x78)
            # mov qword [rsp+0x78], rax
            self.regs.insert(1, reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_reg() and x.operands[0].is_memory() and x.operands[0].base == "rsp" and x.operands[0].index is None and x.operands[0].offset == 0x78).operands[1].reg)
        else:
            # call $+5
            self.base_address = reader.get_cond(lambda x: x.opcode == "call" and x.operands[0].value == x.address + 5).operands[0].value
            # pop ecx
            reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg("ecx"))

        # sub ecx, X
        self.base_address -= reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg(mode.reg_native("cx")) and x.operands[1].is_immediate()).operands[1].value # Get the address of the start of main handler
        assert self.base_address == org_address
        # sub ecx, X
        self.base_address -= reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg(mode.reg_native("cx")) and x.operands[1].is_immediate()).operands[1].value
        # mov ebp, X
        self.vm_struct = self.base_address + reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebp") and x.operands[1].is_immediate()).operands[1].value
        # add ebp, ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg(mode.reg_native("bp")) and x.operands[1].is_reg(mode.reg_native("cx"))) # Get the address of the start of main handler

        # push ecx
        reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg(mode.reg_native("cx")))
        # mov ecx, 1
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ecx") and x.operands[1].is_immediate(1))
        # mov ebx, X
        vm_info.struct_fields["LOCK"] = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate()).operands[1].value
        # xor eax, eax
        lock_loop_start = reader.get_cond(lambda x: x.opcode == "xor" and x.operands[0].is_reg("eax") and x.operands[1].is_reg("eax")).address
        # cmpxchg [ebp+ebx], ecx
        reader.get_cond(lambda x: x.opcode == "cmpxchg" and x.operands[1].is_reg("ecx") and x.operands[0].is_memory() and ((x.operands[0].base == mode.reg_native("bp") and x.operands[0].index == mode.reg_native("bx")) or (x.operands[0].index == mode.reg_native("bp") and x.operands[0].base == mode.reg_native("bx"))) and x.operands[0].offset == 0 and x.operands[0].scale == 0)
        # jz lock_loop_end
        lock_loop_end = reader.get_cond(lambda x: x.opcode == "jz").operands[0].value
        # pause
        reader.get_cond(lambda x: x.opcode == "pause")
        # jmp lock_loop_start
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate(lock_loop_start))
        # pop ecx
        reader.get_cond(lambda x: x.address == lock_loop_end and x.opcode == "pop" and x.operands[0].is_reg(mode.reg_native("cx")))

        # mov ebx, X
        vm_info.struct_fields["BASE_ADDRESS"] = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate()).operands[1].value
        # mov [ebp+ebx], ecx
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_reg(mode.reg_native("cx")) and x.operands[0].is_memory() and ((x.operands[0].base == mode.reg_native("bp") and x.operands[0].index == mode.reg_native("bx")) or (x.operands[0].index == mode.reg_native("bp") and x.operands[0].base == mode.reg_native("bx"))) and x.operands[0].offset == 0 and x.operands[0].scale == 0)

        if file.mode == 32:
            # mov ebx, X
            vm_info.struct_fields["ORIGINAL_BASE_ADDRESS"] = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate()).operands[1].value
            # mov [ebp+ebx], X
            self.original_base_address = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_immediate() and x.operands[0].is_memory() and ((x.operands[0].base == mode.reg_native("bp") and x.operands[0].index == mode.reg_native("bx")) or (x.operands[0].index == mode.reg_native("bp") and x.operands[0].base == mode.reg_native("bx"))) and x.operands[0].offset == 0 and x.operands[0].scale == 0).operands[1].value

        # mov ebx, X
        vm_info.struct_fields["EIP"] = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate()).operands[1].value
        # mov eax, [esp+0x28]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_memory() and x.operands[1].base == mode.reg_native("sp") and x.operands[1].index is None and x.operands[1].offset == ((len(self.regs) + 1) * mode.native_size()) and x.operands[1].scale == 0)
        # add eax, ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_reg(mode.reg_native("cx")))
        # mov [ebp+ebx], eax
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_reg(mode.reg_native("ax")) and x.operands[0].is_memory() and ((x.operands[0].base == mode.reg_native("bp") and x.operands[0].index == mode.reg_native("bx")) or (x.operands[0].index == mode.reg_native("bp") and x.operands[0].base == mode.reg_native("bx"))) and x.operands[0].offset == 0 and x.operands[0].scale == 0)


        # mov eax, X
        self.handlers_address = self.base_address + reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_immediate()).operands[1].value
        # add eax ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_reg(mode.reg_native("cx")))
        # mov ebx, X
        vm_info.struct_fields["HANDLERS"] = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate()).operands[1].value
        # mov edx, [ebp+ebx]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("dx")) and x.operands[1].is_memory() and ((x.operands[1].base == mode.reg_native("bp") and x.operands[1].index == mode.reg_native("bx")) or (x.operands[1].index == mode.reg_native("bp") and x.operands[1].base == mode.reg_native("bx"))) and x.operands[1].offset == 0 and x.operands[1].scale == 0)
        # cmp edx, eax
        reader.get_cond(lambda x: x.opcode == "cmp" and x.operands[0].is_reg(mode.reg_native("dx")) and x.operands[1].is_reg(mode.reg_native("ax")))
        # jz after_handlers_init
        after_handlers_init = reader.get_cond(lambda x: x.opcode == "jz").operands[0].value


        # push ebx
        reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg(mode.reg_native("bx")))
        # mov ebx, X
        self.handlers_count = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate() and (x.operands[1].value % mode.native_size()) == 0).operands[1].value / mode.native_size()
        # shr ebx, 2
        reader.get_cond(lambda x: x.opcode == "shr" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate(mode.native_size()/4+1)) # 2 for 32bit, 3 for 64bit
        # push eax
        reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg(mode.reg_native("ax")))

        # test ebx, ebx
        init_next_handler = reader.get_cond(lambda x: x.opcode == "test" and x.operands[0].is_reg(mode.reg_native("bx")) and x.operands[1].is_reg(mode.reg_native("bx"))).address
        # jz handlers_init_end
        handlers_init_end = reader.get_cond(lambda x: x.opcode == "jz").operands[0].value

        # add [eax], ecx
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[1].is_reg(mode.reg_native("cx")) and x.operands[0].is_memory() and x.operands[0].base == mode.reg_native("ax") and x.operands[0].index is None and x.operands[0].offset == 0 and x.operands[0].scale == 0)
        # add eax, 4
        reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_immediate(mode.native_size()))
        # dec ebx
        reader.get_cond(lambda x: x.opcode == "dec" and x.operands[0].is_reg("ebx")) # or (x.opcode == "sub" and x.operands[0].is_reg("ebx") and x.operands[1].is_immediate(1))) # TODO fix cleaner
        # jmp init_next_handler
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate(init_next_handler))

        # pop eax
        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(mode.reg_native("ax")))
        # pop ebx
        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(mode.reg_native("bx")))
        # mov [ebp+ebx], eax
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_reg(mode.reg_native("ax")) and x.operands[0].is_memory() and ((x.operands[0].base == mode.reg_native("bp") and x.operands[0].index == mode.reg_native("bx")) or (x.operands[0].index == mode.reg_native("bp") and x.operands[0].base == mode.reg_native("bx"))) and x.operands[0].offset == 0 and x.operands[0].scale == 0)
        # mov ebx, [esp+0x24]
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("bx")) and x.operands[1].is_memory() and x.operands[1].base == mode.reg_native("sp") and x.operands[1].index is None and x.operands[1].offset == (len(self.regs) * mode.native_size()) and x.operands[1].scale == 0)
        # shl ebx, 2
        reader.get_cond(lambda x: x.opcode == "shl" and x.operands[0].is_reg(mode.reg_native("bx")) and x.operands[1].is_immediate(mode.native_size()/4+1))
        # add eax, ebx
        init_next_handler = reader.get_cond(lambda x: x.opcode == "add" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_reg(mode.reg_native("bx"))).address
        # jmp [eax]
        reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_memory() and x.operands[0].base == mode.reg_native("ax") and x.operands[0].index is None and x.operands[0].offset == 0 and x.operands[0].scale == 0)



class VMOpcodeHandler(VMHandler):
    def __init__(self, handler):
        self.handler = handler
        self.info = None
        self.decode = None

class VMHandlers(object):
    def __init__(self, file, vm_info):
        #clean = cleaner.Cleaner(executable)
        fix_handlers = file.read_dword(vm_info.init_handler.vm_struct + vm_info.struct_fields["HANDLERS"]) != vm_info.init_handler.handlers_address
        self.mode = file.mode
        arch = file.get_arch()

        self.handlers = {}
        addrs = {}
        # Let's find all the handlers now
        print "Decompiling handlers... (%d handlers)" % vm_info.init_handler.handlers_count
        if PROGRESSBAR:
            prog = progressbar.ProgressBar(maxval=vm_info.init_handler.handlers_count, fd=sys.stdout).start()
        for i in xrange(vm_info.init_handler.handlers_count):
            if PROGRESSBAR:
                prog.update(i)
            handler_address = file.read_pointer(vm_info.init_handler.handlers_address + i * arch.native_size())
            if fix_handlers:
                handler_address = handler_address + vm_info.init_handler.base_address
            #if handler_address == 0x4219f9L:
            func = handlers_decompiler.Handler(instruction.Function(file, handler_address))
            self.handlers[i] = VMOpcodeHandler(func)
            addrs[i] = handler_address
        if PROGRESSBAR:
            prog.finish()
        print "Decompiling handlers... SUCCESS"

        fields = dict(vm_info.struct_fields)

        fish_handlers_cleaner.clean_junk_field(self.handlers.values(), fields, arch)
        fish_handlers_cleaner.clean_junk_check(self.handlers.values(), fields, arch)
        if self.mode == 64:
            fish_handlers_cleaner.fix_64_junk_bool_field(self.handlers.values(), fields)

        parser = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_basic.txt", self.mode)
        print "Analyzing handlers... PASS 1/2"
        if PROGRESSBAR: prog.start()
        for i in xrange(vm_info.init_handler.handlers_count):
            if PROGRESSBAR: prog.update(i)
            parser.clean_handler(self.handlers[i].handler, fields)
        if PROGRESSBAR: prog.finish()

        parser = handlers_parser.HandlerParser.get_default_parser()
        print "Looking for RESET_KEYS...",
        found = False
        for handler in self.handlers.itervalues():
            handler_info = fish_handlers.match_handlers(parser, handler.handler, fields, [fish_handlers.RESET_KEYS], arch)
            if handler_info is not None:
                handler.info = handler_info
                assert not found
                found = True
        assert found
        print "SUCCESS"

        parser_pre = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_encoding_pre.txt", self.mode)
        parser = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_encoding.txt", self.mode)
        parser_final = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_final.txt", self.mode)
        print "Analyzing handlers... PASS 2/2"
        if PROGRESSBAR: prog.start()
        for i in xrange(vm_info.init_handler.handlers_count):
            if PROGRESSBAR: prog.update(i)
            parser_pre.clean_handler(self.handlers[i].handler, fields)
            self.handlers[i].decode = vm_encoding.get_reading_decoding_info(self.handlers[i].handler, fields, arch)
            parser.clean_handler(self.handlers[i].handler, fields)
            fish_handlers_cleaner.fix_encoding_values(self.handlers[i], fields)
            self.handlers[i].handler.optimize_instructions()
            self.handlers[i].handler.clean_instructions()
            parser_final.clean_handler(self.handlers[i].handler, fields)
        if PROGRESSBAR: prog.finish()


        print "Detecting handlers...",
        for handler in self.handlers.itervalues():
            if handler.info is None:
                handler_info = fish_handlers.match_handlers(parser, handler.handler, fields, fish_handlers.HANDLERS, arch)
                if handler_info is None:
                    handler.handler.print_instructions()
                    raise Exception("Failed to detect handler")
                handler.info = handler_info
        print "SUCCESS"


        # for index, handler in self.handlers.iteritems():
        #     print "---------------------------------------------------"
        #     print hex(index)
        #     print hex(addrs[index])
        #     handler.handler.print_instructions()
        # assert False

        # Good, we have handlers now

class VMInfo(object):
    cache = {}
    def __init__(self, file, vm_address):
        print "Parsing FISH%d VM at 0x%08x" % (file.mode, vm_address)
        self.struct_fields = {}
        self.regs_fields = {}
        self.init_handler = VMInit(self, file, vm_address)
        self.handlers = VMHandlers(file, self)

    @classmethod
    def get_vm_info(cls, file, address):
        if cls.cache.has_key((file, address)):
            return cls.cache[(file, address)]
        #try:
        res = cls(file, address)
        #except cleaner.CleanerException, e:
        #    res = None

        cls.cache[(file, address)] = res
        return res

class VMFunctionSection(object):
    def __init__(self, address):
        self.address = address
        self.start = False
        self.instructions = []


class VMFunctionJumper(object):
    def __init__(self, file, address):
        mode = file.get_arch()
        clean = cleaner.Cleaner(file)
        #clean.set_option("fixOperationConstantThruRegOnStack", True)
        clean.set_option("fixPush_allowConstants", True)
        clean.set_option("ignore_jumps", False)
        if file.mode == 32:
            address = cleaner.JunkSkipper(file).get_next_real_instruction(address).address
        reader = clean.get_reader(address)
        # pushf
        reader.get_cond(lambda x: x.opcode == mode.translate("pushf{SB}"))
        # push first_handler
        self.first_handler = reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_immediate()).operands[0].value
        # push vm_code_address
        self.vm_code_address = reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_immediate()).operands[0].value
        # Now switch between pushf and vm_code_address (so it will be as in the order of the old versions)
        reader.get_cond(lambda x: str(x) == mode.translate("push {R:ax}"))
        reader.get_cond(lambda x: str(x) == mode.translate("push {R:bx}"))
        reader.get_cond(lambda x: str(x) == mode.translate("mov {R:ax}, {S} [{R:sp}+0x{N:0x4}]"))
        reader.get_cond(lambda x: str(x) == mode.translate("mov {R:bx}, {S} [{R:sp}+0x{N:0x2}]"))
        reader.get_cond(lambda x: str(x) == mode.translate("mov {S} [{R:sp}+0x{N:0x2}], {R:ax}"))
        reader.get_cond(lambda x: str(x) == mode.translate("mov {S} [{R:sp}+0x{N:0x4}], {R:bx}"))
        reader.get_cond(lambda x: str(x) == mode.translate("pop {R:bx}"))
        reader.get_cond(lambda x: str(x) == mode.translate("pop {R:ax}"))
        self.vm_address = reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate()).operands[0].value

class VMFunction(object):
    def __init__(self, file, jumper):
        self.file = file
        arch = self.file.get_arch()
        self.mode = file.mode

        vm_address = jumper.vm_address
        vm_code_address = jumper.vm_code_address
        first_handler = jumper.first_handler

        self.vm_info = VMInfo.get_vm_info(file, vm_address)
        assert self.vm_info != None

        addresses_to_explore = Queue.Queue()
        starts = []
        instructions = {}
        instructions_list = []

        # Start address is the address of push address2/jmp and end address is the address of vmcode
        real_vm_code_address = vm_code_address + self.vm_info.init_handler.base_address
        self.code_address = real_vm_code_address

        print ("Reading VMFunction at 0x%08x..." % self.code_address),

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put((real_vm_code_address, first_handler))
        starts.append(real_vm_code_address)

        while not addresses_to_explore.empty():
            next_labeled = True
            address, handler = addresses_to_explore.get()
            state = vm_encoding.new_fish_state(address, file.read)
            if instructions.has_key(address):
                instructions[address].set_info("labled", True)
                continue

            while handler is not None:
                if instructions.has_key(state.address):
                    if next_labeled:
                        instructions[state.address].set_info("labled", True)
                    break

                h = self.vm_info.handlers.handlers[handler]
                handler_reader = h.info.reader(h.info, h.decode.decode(state), arch)

                inst = handler_reader.get_instruction()

                inst.address = state.address
                inst.set_info("labled", next_labeled)
                next_labeled = False

                if inst.name == "JMP_UNKNOWN":
                    # Jump to an unknown instruction
                    assert handler_reader.params["ADDRS_COUNT"] not in (1,2) # TODO
                    inst.args[0] += self.vm_info.init_handler.base_address
                    i = file.get_instruction(inst.args[0])
                    jumper = VMFunctionJumper(file, i.next)
                    addresses_to_explore.put((jumper.vm_code_address + self.vm_info.init_handler.base_address, jumper.first_handler))
                    starts.append(jumper.vm_code_address + self.vm_info.init_handler.base_address)
                elif inst.name == "JMP":
                    state.update_ip(inst.args[0])
                    inst.args[0] = state.address
                    handler = inst.args[1]
                    inst.args = inst.args[:1]
                    instructions[inst.address] = inst
                    instructions_list.append(inst)
                    next_labeled = True
                    continue
                elif inst.name in ("JZ", "JNZ", "JA", "JAE", "JB", "JBE", "JG", "JGE", "JL", "JLE", "JNO", "JNP", "JNS", "JO", "JP", "JS"):
                    state.update_ip(inst.args[0])
                    inst.args[0] = state.address
                    addresses_to_explore.put((inst.args[0], inst.args[1]))
                    inst.args = inst.args[:1]
                    state.address = inst.address
                elif inst.name.endswith("_IMM") and inst.name[:-len("_IMM")] in ("JMP", "JZ", "JNZ", "JA", "JAE", "JB", "JBE", "JG", "JGE", "JL", "JLE", "JNO", "JNP", "JNS", "JO", "JP", "JS"):
                    inst.args[0] += self.vm_info.init_handler.base_address
                    inst.name = inst.name[:-len("IMM")] + "RELIMM"
                elif inst.name in ("CALL_IMM_NEXT", "CALL_VAR_NEXT", "CALL_MEMVAR_NEXT"):
                    if inst.name == "CALL_IMM_NEXT":
                        inst.args[0] += self.vm_info.init_handler.base_address
                        inst.name == "CALL_RELIMM"
                    jumper = VMFunctionJumper(file, inst.args[1] + self.vm_info.init_handler.base_address)
                    addresses_to_explore.put((jumper.vm_code_address + self.vm_info.init_handler.base_address, jumper.first_handler))
                    starts.append(jumper.vm_code_address + self.vm_info.init_handler.base_address)
                    inst.args = inst.args[:-1]
                    inst.name = inst.name[:-len("_NEXT")]
                elif inst.name == "ADD_VAR_BASEADDRESS":
                    inst.args.append(self.vm_info.init_handler.base_address)
                elif inst.name == "RESET_KEYS":
                    state.reset()


                handler = handler_reader.get_next_handler()
                if handler is not None:
                    state.update_ip(handler_reader.get_size())

                instructions[inst.address] = inst
                instructions_list.append(inst)
        print "SUCCESS"

        if not self.vm_info.regs_fields:
            reader = vminstruction.VMInstructionsReader(instructions_list)
            reader.get_cond(lambda x: x.name == "RESET_FLAGS")
            try:
                reader.get_cond(lambda x: x.name == "RESET_KEYS")
            except vminstruction.ReaderException:
                self.vm_info.regs_fields["SP"] = reader.get_cond(lambda x: x.name == "MOV_VAR_SP").args[0]
                reader.get_cond(lambda x: x.name == "RESET_KEYS")
            else:
                self.vm_info.regs_fields["SP"] = reader.get_cond(lambda x: x.name == "MOV_VAR_SP").args[0]
            regs = list(self.vm_info.init_handler.regs[::-1])
            for reg in regs:
                if reg == "flags":
                    self.vm_info.regs_fields["FLAGS"] = reader.get_cond(lambda x: x.name == "POP_VAR").args[0]
                else:
                    reg = reg.upper()
                    if not reg[1].isdigit():
                        reg = reg[1:]
                    self.vm_info.regs_fields[reg] = reader.get_cond(lambda x: x.name == arch.translate("POP_{SU}_VAR")).args[0]
            reader.get_cond(lambda x: x.name == "ADD_SP_IMM" and x.args[0] == arch.native_size() * 2)

        self.instructions = []
        for address in sorted(instructions.keys()):
            if instructions[address].info["labled"]:
                if starts.count(address):
                    label = vminstruction.VMInstruction("STARTLABEL", address)
                else:
                    label = vminstruction.VMInstruction("LABEL", address)
                label.address = address
                self.instructions.append(label)
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
        TEMPLATES = ["fish_00_regs.txt", "fish_01_vm.txt", "fish_02_misc.txt", "fish_03_vars.txt", "fish_04_memvars.txt", "fish_05_fix_pop.txt", "fish_06_rep.txt"]
        print "Processing VMFunction (%d instructions)..." % len(self.instructions)

        vars = dict(self.vm_info.regs_fields)
        vars["IS_REG"] = lambda x: x in self.vm_info.regs_fields.values()

        for template in TEMPLATES:
            print ("Applying %s," % template),
            templates.Templates.get_template(r"codevirtualizer\animals\%s" % template, self.mode).clean(self.instructions, vars)
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
        if self.code is not None:
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

        code = ""
        section_counter = 0
        next_section = 0
        registers = {v: k.lower() for k, v in self.vm_info.regs_fields.iteritems()}

        for address in sorted(sections.keys()):
            if next_section:
                assert next_section == address
                next_section = 0
            section = sections[address]
            sectioncode = ""
            reader = vminstruction.VMInstructionsReader(section.instructions)

            if section.start:
                if section_counter == 0:
                    reader.get_cond(lambda x: x.name == "RESET_FLAGS")

                # if section_counter == 1:
                #     index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
                #     # Deal with anti-debugging
                #     if index != -1:
                #         code = code_base + code[code.find("\n", index+1)+1:]
                section_counter += 1

                reader.get_cond(lambda x: x.name == "START_VM")

            inst = reader.get()
            stop = False

            while inst:
                if inst.name == "END_VM":
                    inst = reader.get()
                    if inst.name == "JMP_UNKNOWN":
                        sectioncode += str(self.file.get_instruction(inst.args[0])) + "\n"
                        # Stop
                        assert reader.get() is None
                        break
                    elif inst.name.split("_")[0] in ("JMP", "CALL", "RET"):
                        stop = True
                    else:
                        assert inst.name.split("_")[0] in vminstruction.CONDITIONAL_JUMPS
                elif inst.name == "_NOP":
                    inst.name = "NOP"
                elif inst.name == "JMP" or inst.name in vminstruction.CONDITIONAL_JUMPS:
                    inst.name += "_LABEL"

                sectioncode += inst.to_asm(registers, self.mode) + "\n"
                if stop:
                    assert reader.get() is None
                    break

                inst = reader.get()
            code += sectioncode

        # if section_counter == 1:
        #     index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
        #     # Deal with anti-debugging
        #     if index != -1:
        #         code = code_base + code[code.find("\n", index+1)+1:]

        self.code = code[:-1]
        return self.code

    def compile_code(self, address = None, relocs = False):
        code = self.get_code()
        if address is None:
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
