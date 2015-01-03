import utils
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

import os
import sys
import tempfile
import subprocess

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
        print "Decompiling handlers..."
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
        print "Analyzing with handlers_basic.txt..."
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
        print "Analyzing with handlers_encoding.txt..."
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


        for handler in self.handlers.itervalues():
            if handler.info is None:
                handler_info = fish_handlers.match_handlers(parser, handler.handler, fields, fish_handlers.HANDLERS, arch)
                if handler_info is None:
                    handler.handler.print_instructions()
                    raise Exception("Failed to detect handler")
                handler.info = handler_info


        # for index, handler in self.handlers.iteritems():
        #     print "---------------------------------------------------"
        #     #if handler.name:
        #     #    print handler.name
        #     #    print "@@@@@@@@@@@@@@@@@@@@@"
        #     print hex(addrs[index])
        #     handler.handler.print_instructions()
        # assert False

        # Good, we have handlers now

class VMInfo(object):
    cache = {}
    def __init__(self, file, vm_address):
        self.struct_fields = {}
        self.init_handler = VMInit(self, file, vm_address)
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
        self.end = reader.address

class VMFunction(object):
    def __init__(self, file, jumper):
        self.file = file

        vm_address = jumper.vm_address
        vm_code_address = jumper.vm_code_address
        first_handler = jumper.first_handler
        print "Getting VM %08X %08X" % (vm_address, vm_code_address)

        self.vm_info = VMInfo.get_vm_info(file, vm_address)
        assert self.vm_info != None

        addresses_to_explore = Queue.Queue()
        starts = []
        instructions = {}
        instructions_size = {}

        # Start address is the address of push address2/jmp and end address is the address of vmcode
        real_vm_code_address = vm_code_address + self.vm_info.init_handler.base_address
        self.code_address = real_vm_code_address

        print ("Reading VMFunction at 0x%08x..." % self.code_address),

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put((real_vm_code_address, first_handler))
        starts.append(real_vm_code_address)

        to_print = False
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
                handler_reader = h.info.reader(h.info, h.decode.decode(state))

                inst = handler_reader.get_instruction()

                inst.address = state.address
                inst.set_info("labled", next_labeled)
                next_labeled = False

                if inst.name == "JMP_UNKNOWN":
                    # Jump to an unknown instruction
                    assert handler_reader.params["ADDRS_COUNT"] not in (1,2) # TODO
                    address = inst.args[0] + self.vm_info.init_handler.base_address
                    i = file.get_instruction(address)
                    jumper = VMFunctionJumper(file, i.next)
                    addresses_to_explore.put((jumper.vm_code_address + self.vm_info.init_handler.base_address, jumper.first_handler))
                elif inst.name == "JMP":
                    state.update_ip(inst.args[0])
                    inst.args[0] = state.address
                    handler = inst.args[1]
                    inst.args = inst.args[:1]
                    instructions[inst.address] = inst
                    #print inst
                    continue
                elif inst.name in ("JZ", "JNZ", "JA", "JAE", "JB", "JBE", "JG", "JGE", "JL", "JLE", "JNO", "JNP", "JNS", "JO", "JP", "JS"):
                    state.update_ip(inst.args[0])
                    inst.args[0] = state.address
                    addresses_to_explore.put((inst.args[0], inst.args[1]))
                    inst.args = inst.args[:1]
                    state.address = inst.address
                elif inst.name in ("CALL_IMM_NEXT", "CALL_VAR_NEXT", "CALL_MEMVAR_NEXT"):
                    if inst.name == "CALL_IMM_NEXT":
                        inst.args[0] += self.vm_info.init_handler.base_address
                    jumper = VMFunctionJumper(file, inst.args[1] + self.vm_info.init_handler.base_address)
                    addresses_to_explore.put((jumper.vm_code_address + self.vm_info.init_handler.base_address, jumper.first_handler))
                    inst.args = inst.args[:-1]
                    inst.name = inst.name[:-len("_NEXT")]
                elif inst.name == "RESET_KEYS":
                    state.reset()




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
                #     push = file.get_instruction(long(inst.args[0] + self.vm_info.init_handler.encode))
                #     if push.opcode != "push":
                #         push = file.get_instruction(push.next)
                #     assert push.opcode == "push" and push.operands[0].is_immediate()
                #     jmp = file.get_instruction(push.next)
                #     assert jmp.opcode == "jmp" and jmp.operands[0].is_immediate(vm_address)
                #     jmp_vm_code_address = long(push.operands[0].value + self.vm_info.init_handler.encode + self.vm_info.init_handler.encode_address_high_dword)
                #     addresses_to_explore.put((jmp_vm_code_address, push.operands[0].value))
                #     starts.append(jmp_vm_code_address)
                # elif inst.name in ("ADD_DX_REALLOC", "STACK_ADD_REALLOC"): # TODO: Properly support reallocation
                #     inst.name += "_VALUE"
                #     inst.args = [self.vm_info.handlers.realloc_offset]

                handler = handler_reader.get_next_handler()
                #print handler
                if handler is not None:
                    state.update_ip(handler_reader.get_size())

                instructions[inst.address] = inst
                #print inst
        print "SUCCESS"

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
                        asminst = self.file.get_instruction(long(inst.args[0] + self.vm_info.init_handler.encode))
                        asminst_after = self.file.get_instruction(asminst.next)
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

def get_vm(file, address):
    vm = VMFunction(file, VMFunctionJumper(file, address))
    #vm.clean()
    return vm

def get_vm_code(file, push_inst, jmp_inst):
    vm = VMFunction(file, push_inst, jmp_inst)
    #print "Cleaning vm.."
    vm.clean()
    #vm.printfunc()
    #print "Converting to asm..."
    try:
        return vm.get_code()
    except:
        vm.printfunc()
        raise

def get_compiled_vm_code(file, push_inst, jmp_inst, address = None):
    vm = VMFunction(file, push_inst, jmp_inst)
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

"""
def fix_vms(pe, code_section = 0, vms_section = 3):
    vms = []
    code_section_start = pe.sections[code_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
    code_section_end = code_section_start + pe.sections[code_section].Misc_VirtualSize
    vms_section_start = pe.sections[vms_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
    vms_section_end = vms_section_start + pe.sections[vms_section].Misc_VirtualSize
    exe = MappeFile..ToExecutable(pe)
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
"""
