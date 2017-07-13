from themida import cleaner
from vms import vminstruction
from vms import templates
from vms import vm
from vms import vmtools

import mappedfile
import handlers_decompiler
import handlers_parser
import fish_keys
import fish_handlers_cleaner
import fish_handlers
import tiger_keys
import tiger_handlers_cleaner
import tiger_handlers
import dolphin_keys
import dolphin_handlers_cleaner
import dolphin_handlers
import common_keys
import common_handlers_cleaner
import common_handlers
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
        if file.mode == 64:
            try:
                # Saving RBP in new versions....
                # mov rax, [esp+0x50]
                reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_memory() and x.operands[1].base == mode.reg_native("sp") and x.operands[1].index is None and x.operands[1].offset == 0x50 and x.operands[1].scale == 0)
            except cleaner.CleanerException:
                pass
            else:
                # mov [rbp+rbx], rax
                reader.get_cond(lambda x: x.opcode == "mov" and x.operands[1].is_reg(mode.reg_native("ax")) and x.operands[0].is_memory() and ((x.operands[0].base == mode.reg_native("bp") and x.operands[0].index == mode.reg_native("bx")) or (x.operands[0].index == mode.reg_native("bp") and x.operands[0].base == mode.reg_native("bx"))) and x.operands[0].offset == 0 and x.operands[0].scale == 0)
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
        self.extra_info = {}

class VMHandlers(object):
    RESET_KEYS_OLD = None
    KEYS = []
    HANDLERS = None

    def __init__(self, file, vm_info):
        #clean = cleaner.Cleaner(executable)
        fix_handlers = file.read_pointer(vm_info.init_handler.vm_struct + vm_info.struct_fields["HANDLERS"]) != vm_info.init_handler.handlers_address
        self.mode = file.mode
        self.file = file
        arch = file.get_arch()

        self.handlers = {}
        self.handlers_count = vm_info.init_handler.handlers_count
        self.global_vars = {}
        funcs = []

        original_addresses = {}

        # The different vm main with the same handlers feature is new, so if it is used,
        # the other handler was new reset handler for sure
        self.old_reset_handler = False

        if PROGRESSBAR:
            self.prog = None

        already_parsed = False
        # Let's find all the handlers now
        print "Reading handlers... (%d handlers)" % self.handlers_count
        self._start_progress_bar()
        for i in xrange(vm_info.init_handler.handlers_count):
            handler_address = file.read_pointer(vm_info.init_handler.handlers_address + i * arch.native_size())
            if fix_handlers:
                handler_address = handler_address + vm_info.init_handler.base_address
            # Check if we already parsed this handler
            if handler_address in vm_info.handlers_cache:
                assert already_parsed or i == 0
                already_parsed = True
                self.handlers[i] = vm_info.handlers_cache[handler_address]
                # TODO: Check that it is consistent
                self.global_vars.update(self.handlers[i].info.global_vars)
            else:
                assert not already_parsed
                funcs.append(self._read_handler_function(handler_address))
                # If it is virtualized vm, we will get another address
                original_addresses[funcs[-1].address] = handler_address
            self._update_progress_bar()
        self._close_reader()

        if already_parsed:
            print "VM already parsed"
            return

        print "Reading handlers... SUCCESS"

        # TODO: Multithreaded

        print "Decompiling handlers..."
        self._start_progress_bar()
        for i in xrange(vm_info.init_handler.handlers_count):
            func = self._decompile_handler(funcs[i])
            self.handlers[i] = VMOpcodeHandler(func)
            self._update_progress_bar()
        print "Decompiling handlers... SUCCESS"

        self.fields = dict(vm_info.struct_fields)

        print "Preprocessing handlers...",
        self._preprocess_handlers()
        print "SUCCESS"


        parser = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_basic.txt", self.mode)
        print "Analyzing handlers... PASS 1/2"
        self._start_progress_bar()
        for i in xrange(vm_info.init_handler.handlers_count):
            parser.clean_handler(self.handlers[i].handler, self.fields)
            self._update_progress_bar()

        parser = handlers_parser.HandlerParser.get_default_parser()
        print "Looking for RESET_KEYS...",
        self._find_reset_keys_handler()

        print "SUCCESS"

        self.parser_encoding = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_encoding.txt", self.mode)
        self.parser_final = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_final.txt", self.mode)
        print "Analyzing handlers... PASS 2/2"
        self._start_progress_bar()
        for handler in self.handlers.itervalues():
            self._process_pre_decoding(handler)
            handler.decode = vm_encoding.get_reading_decoding_info(handler.handler, self.fields, arch)
            self._process_final(handler)
            self._update_progress_bar()

        print "Detecting handlers...",
        handlers_to_detect = [handler for handler in self.handlers.itervalues() if handler.info is None]
        while handlers_to_detect:
            undetected_handlers = []
            for handler in handlers_to_detect:
                handler.info = common_handlers.match_handlers(parser, handler.handler, self.fields, self.HANDLERS, arch, self.global_vars)
                if handler.info is None:
                    undetected_handlers.append(handler)
            if len(handlers_to_detect) == len(undetected_handlers):
                for handler in handlers_to_detect:
                    print "---------------------------------------------------"
                    handler.handler.print_instructions()
                    # handler.info = common_handlers.match_handlers(parser, handler.handler, self.fields, self.HANDLERS, arch, self.global_vars)
                raise Exception("Failed to detect handlers")
            handlers_to_detect = undetected_handlers
        print "SUCCESS"

        # Save the functions in the cache
        for i in xrange(len(self.handlers)):
            vm_info.handlers_cache[original_addresses[funcs[i].address]] = self.handlers[i]

        # for index, handler in self.handlers.iteritems():
        #     print "---------------------------------------------------"
        #     print hex(index)
        #     handler.handler.print_instructions()
        # assert False

        # Good, we have handlers now

    def _start_progress_bar(self):
        if PROGRESSBAR:
            if self.prog is None:
                self.prog = progressbar.ProgressBar(maxval=self.handlers_count, fd=sys.stdout)
            self.prog.start()
            self.prog_index = 0

    def _update_progress_bar(self):
        if PROGRESSBAR:
            self.prog_index += 1
            if self.prog_index == self.handlers_count:
                self.prog.finish()
            else:
                self.prog.update(self.prog_index)


    def _read_handler_function(self, address):
        return instruction.Function(self.file, address)

    def _close_reader(self):
        pass

    def _decompile_handler(self, func):
        return handlers_decompiler.Handler(func, False)

    def _preprocess_handlers(self):
        pass

    def _process_pre_decoding(self, handler):
        self.parser_encoding.clean_handler(handler.handler, self.fields)

    def _process_final(self, handler):
        handler.handler.optimize_instructions()
        handler.handler.clean_instructions()
        self.parser_final.clean_handler(handler.handler, self.fields)

    def _find_old_reset_keys_handler(self):
        parser = handlers_parser.HandlerParser.get_default_parser()
        found = False
        for handler in self.handlers.itervalues():
            handler_info = common_handlers.match_handlers(parser, handler.handler, self.fields, [self.RESET_KEYS_OLD], self.file.get_arch())
            if handler_info is not None:
                handler.info = handler_info
                assert not found
                found = True
        if found:
            self.old_reset_handler = True

    def _find_reset_keys_handler(self):
        self._find_old_reset_keys_handler()
        if not self.old_reset_handler:
            common_keys.find_keys(self.KEYS, self.handlers.values(), self.fields, self.file.get_arch())

    def create_state_old(self, address, read):
        pass

    def create_state_new(self, address, read):
        return common_keys.create_state(self.KEYS, address, read)

    def create_state(self, address, read):
        if self.old_reset_handler:
            return self.create_state_old(address, read)
        return self.create_state_new(address, read)


class ObfuscatedVMHandlers(VMHandlers):
    def __init__(self, file, vm_info):
        VMHandlers.__init__(self, file, vm_info)

    def _read_handler_function(self, address):
        return self.deobfuscate_function(instruction.Function(self.file, address))

    def deobfuscate_block(self, block):
        if len(block.instructions) == 0:
            return
        block_start = block.instructions[0].address
        def get_next_address(inst):
            if inst.opcode == "jmp" and inst.operands[0].is_immediate():
                return inst.operands[0].value
            return inst.next
        block_end = get_next_address(block.instructions[-1])
        self._reader = cleaner.Cleaner(self.file)
        self._reader.set_option("ignore_jumps", False)
        self._reader.set_option("ignore_nontop_jumps", True)
        self._reader.set_option("fix_inc_dec", False)
        self._reader.set_option("fixPush_allowConstants", True)
        self._reader.set_option("fixLods", False)
        self._reader.set_option("end_address", block_end)
        new_func = instruction.Function(self._reader, block_start, stop_condition=lambda inst: get_next_address(inst) == block_end)
        assert len(new_func.blocks) == 1
        new_block = new_func.blocks.values()[0]
        while len(block.instructions):
            block.instructions.pop()
        block.instructions.extend(new_block.instructions)

    def deobfuscate_function(self, function):
        for block in function.blocks.itervalues():
            self.deobfuscate_block(block)
        return function

    # def deobfuscate_last_block(self, function):
    #     block = function.start_block
    #     while block.next is not None:
    #         nblock = instruction.get_common_block(block.next, block.next_cond)
    #         if nblock is None:
    #             # Hack for memcpy
    #             block = block.next_cond
    #         else:
    #             block = nblock
    #     self.deobfuscate_block(block)
    #     return function

    def _close_reader(self):
        self._reader = None


class FISHVMHandlers(ObfuscatedVMHandlers):
    RESET_KEYS_OLD = fish_handlers.RESET_KEYS_OLD
    KEYS = fish_keys.KEYS
    HANDLERS = fish_handlers.HANDLERS

    def __init__(self, file, vm_info):
        self.fish_parser_encoding = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_encoding_fish.txt", file.mode)
        self.fish_encoding_parser = handlers_parser.HandlerParser.get_parser(r"handlers\fish_encoded_value.txt", file.mode)
        super(FISHVMHandlers, self).__init__(file, vm_info)

    def _decompile_handler(self, func):
        return handlers_decompiler.Handler(func, True)

    def _preprocess_handlers(self):
        fish_handlers_cleaner.clean_junk_field(self.handlers.values(), self.fields, self.file.get_arch())
        fish_handlers_cleaner.clean_junk_check(self.handlers.values(), self.fields, self.file.get_arch())
        fish_handlers_cleaner.clean_junk_field2(self.handlers.values(), self.fields, self.file.get_arch())
        if self.mode == 64:
            fish_handlers_cleaner.fix_64_junk_bool_field(self.handlers.values(), self.fields)

    def _process_pre_decoding(self, handler):
        VMHandlers._process_pre_decoding(self, handler)
        self.fish_parser_encoding.clean_handler(handler.handler, self.fields)

    def _process_final(self, handler):
        self.fish_encoding_parser.clean_handler(handler.handler, self.fields)
        fish_handlers_cleaner.fix_encoding_values(handler, self.fields)
        common_handlers_cleaner.fix_push_ret(handler.handler)
        VMHandlers._process_final(self, handler)
        common_handlers_cleaner.fix_jump_to_field(handler.handler, self.fields, self.file.get_arch())

    def create_state_old(self, address, read):
        return vm_encoding.new_fish_state(address, read)


class TIGERVMHandlers(ObfuscatedVMHandlers):
    RESET_KEYS_OLD = tiger_handlers.RESET_KEYS_OLD
    KEYS = tiger_keys.KEYS
    HANDLERS = tiger_handlers.HANDLERS

    def __init__(self, file, vm_info):
        self.tiger_parser_encoding = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_encoding_tiger.txt", file.mode)
        self.tiger_final_parser = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_final_tiger.txt", file.mode)
        self.xchg = {}
        super(TIGERVMHandlers, self).__init__(file, vm_info)

    def _process_pre_decoding(self, handler):
        tiger_handlers_cleaner.clean_get_speical_push_value_reg(handler.handler)
        VMHandlers._process_pre_decoding(self, handler)
        self.tiger_parser_encoding.clean_handler(handler.handler, self.fields)

    def _process_final(self, handler):
        VMHandlers._process_final(self, handler)
        common_handlers_cleaner.fix_push_ret(handler.handler)
        self.tiger_final_parser.clean_handler(handler.handler, self.fields)
        common_handlers_cleaner.fix_jump_to_field(handler.handler, self.fields, self.file.get_arch())
        handler.extra_info["xchg"] = tiger_handlers_cleaner.get_vars_xchg(handler.handler, self.file.get_arch())

    def create_state_old(self, address, read):
        return vm_encoding.new_tiger_state(address, read)

    def create_state_new(self, address, read):
        return common_keys.create_state(self.KEYS, address, read, vm_encoding.TIGERDecodingState)



class DOLPHINVMHandlers(ObfuscatedVMHandlers):
    RESET_KEYS_OLD = dolphin_handlers.RESET_KEYS_OLD
    KEYS = dolphin_keys.KEYS
    HANDLERS = dolphin_handlers.HANDLERS

    def __init__(self, file, vm_info):
        self.dolphin_parser_encoding = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_encoding_dolphin.txt", file.mode)
        #self.fish_encoding_parser = handlers_parser.HandlerParser.get_parser(r"handlers\fish_encoded_value.txt", file.mode)
        self.dolphin_final_parser = handlers_parser.HandlerParser.get_parser(r"handlers\handlers_final_dolphin.txt", file.mode)
        super(DOLPHINVMHandlers, self).__init__(file, vm_info)

    def _decompile_handler(self, func):
        return handlers_decompiler.Handler(func, True)

    def _preprocess_handlers(self):
        #fish_handlers_cleaner.clean_junk_field(self.handlers.values(), self.fields, self.file.get_arch())
        dolphin_handlers_cleaner.clean_junk_check(self.handlers.values(), self.fields, self.file.get_arch())
        dolphin_handlers_cleaner.clean_junk_flag(self.handlers.values(), self.fields, self.file.get_arch())
        # If some check weren't removed before the clean, remove them now
        # TODO: should we call clean_junk_flag again after that while something changed?
        # or we should change clean flag to work better (even before cleaning the junk check)
        dolphin_handlers_cleaner.clean_junk_check(self.handlers.values(), self.fields, self.file.get_arch())
        #if self.mode == 64:
        #    fish_handlers_cleaner.fix_64_junk_bool_field(self.handlers.values(), self.fields)

    def _process_pre_decoding(self, handler):
        VMHandlers._process_pre_decoding(self, handler)
        self.dolphin_parser_encoding.clean_handler(handler.handler, self.fields)
        dolphin_handlers_cleaner.fix_encoding_values(handler.handler, self.fields, self.file.get_arch())

    def _process_final(self, handler):
        #self.fish_encoding_parser.clean_handler(handler.handler, self.fields)
        #fish_handlers_cleaner.fix_encoding_values(handler, self.fields)
        self.dolphin_final_parser.clean_handler(handler.handler, self.fields)
        VMHandlers._process_final(self, handler)

    def _find_old_reset_keys_handler(self):
        # There wasn't change in the key, so use the new mechanism
        pass

    def create_state_old(self, address, read):
        return vm_encoding.new_dolphin_state(address, read)

    def create_state_new(self, address, read):
        return common_keys.create_state(self.KEYS, address, read, vm_encoding.DOLPHINDecodingState)


class SHARKVMHandlers(FISHVMHandlers):
    def _read_handler_function(self, address):
        inst = self.file.get_instruction(address)
        assert inst.opcode == "jmp" and inst.operands[0].is_immediate()
        naddress, bytes = vmtools.VMS["TIGER"].get_vm(self.file, inst.operands[0].value).compile_code()
        return instruction.Function(mappedfile.BytesMappedFile(bytes, naddress, self.file.mode), naddress)


class PUMAVMHandlers(TIGERVMHandlers):
    def _read_handler_function(self, address):
        inst = self.file.get_instruction(address)
        assert inst.opcode == "jmp" and inst.operands[0].is_immediate()
        naddress, bytes = vmtools.VMS["FISH"].get_vm(self.file, inst.operands[0].value).compile_code()
        return instruction.Function(mappedfile.BytesMappedFile(bytes, naddress, self.file.mode), naddress)


class EAGLEVMHandlers(FISHVMHandlers):
    def _read_handler_function(self, address):
        inst = self.file.get_instruction(address)
        assert inst.opcode == "jmp" and inst.operands[0].is_immediate()
        naddress, bytes = vmtools.VMS["DOLPHIN"].get_vm(self.file, inst.operands[0].value).compile_code()
        return instruction.Function(mappedfile.BytesMappedFile(bytes, naddress, self.file.mode), naddress)


class VMInfo(vm.VMInfo):
    handlers_cache = {}

    def __init__(self, file, vm_address, name, vm_handlers_cls):
        print "Parsing %s%d VM at 0x%08x" % (name, file.mode, vm_address)
        self.struct_fields = {}
        self.regs_fields = {}
        self.init_handler = VMInit(self, file, vm_address)
        self.handlers = vm_handlers_cls(file, self)


class FISHVMInfo(VMInfo):
    cache = {}
    handlers_cache = {}
    def __init__(self, file, vm_address):
        VMInfo.__init__(self, file, vm_address, "FISH", FISHVMHandlers)


class TIGERVMInfo(VMInfo):
    cache = {}
    handlers_cache = {}
    def __init__(self, file, vm_address):
        VMInfo.__init__(self, file, vm_address, "TIGER", TIGERVMHandlers)


class DOLPHINVMInfo(VMInfo):
    cache = {}
    handlers_cache = {}
    def __init__(self, file, vm_address):
        VMInfo.__init__(self, file, vm_address, "DOLPHIN", DOLPHINVMHandlers)


class SHARKVMInfo(VMInfo):
    cache = {}
    handlers_cache = {}
    def __init__(self, file, vm_address):
        VMInfo.__init__(self, file, vm_address, "SHARK", SHARKVMHandlers)


class PUMAVMInfo(VMInfo):
    cache = {}
    handlers_cache = {}
    def __init__(self, file, vm_address):
        VMInfo.__init__(self, file, vm_address, "PUMA", PUMAVMHandlers)


class EAGLEVMInfo(VMInfo):
    cache = {}
    handlers_cache = {}
    def __init__(self, file, vm_address):
        VMInfo.__init__(self, file, vm_address, "EAGLE", EAGLEVMHandlers)


class VMFunctionSection(object):
    def __init__(self, address):
        self.address = address
        self.start = False
        self.instructions = []


class VMFunctionJumper(vm.VMFunctionJumper):
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

    def get_vm_address(self):
        return self.vm_address


class VMFunction(vm.VMFunction):
    def __init__(self, file, vm_info, jumper):
        self.file = file
        arch = self.file.get_arch()
        self.mode = file.mode

        vm_code_address = jumper.vm_code_address
        first_handler = jumper.first_handler

        self.vm_info = vm_info

        addresses_to_explore = Queue.Queue()
        starts = []
        instructions = {}
        instructions_list = []

        self.integrity_used = False

        # Start address is the address of push address2/jmp and end address is the address of vmcode
        real_vm_code_address = vm_code_address + self.vm_info.init_handler.base_address
        self.code_address = real_vm_code_address

        print ("Reading VMFunction at 0x%08x..." % self.code_address),

        # Mark the start of the vm code as part that something is started in it
        addresses_to_explore.put((real_vm_code_address, first_handler, self.vm_info.handlers.create_state(real_vm_code_address, file.read)))
        starts.append(real_vm_code_address)

        # TODO: Check call IMM64

        while not addresses_to_explore.empty():
            next_labeled = True
            address, handler, state = addresses_to_explore.get()
            if instructions.has_key(address):
                instructions[address].set_info("labled", True)
                continue

            while handler is not None:
                if instructions.has_key(state.address):
                    if next_labeled:
                        instructions[state.address].set_info("labled", True)
                    break

                h = self.vm_info.handlers.handlers[handler]
                params = h.decode.decode(state)
                self._do_handler(h, params, state)
                handler_reader = h.info.reader(h.info, params, arch, state, self.vm_info.handlers.global_vars)

                inst = self._get_instruction(handler_reader.get_name(), handler_reader.get_params(), state)
                self._do_handler_end(h, params, state)

                inst.address = state.address
                inst.set_info("labled", next_labeled)
                next_labeled = False

                if inst.name == "JMP_UNKNOWN":
                    # Jump to an unknown instruction
                    assert handler_reader.params["ADDRS_COUNT"] not in (1,2) # TODO
                    i = file.get_instruction(inst.args[0])
                    jumper = VMFunctionJumper(file, i.next)
                    # Continue with current state
                    state.address = jumper.vm_code_address + self.vm_info.init_handler.base_address
                    addresses_to_explore.put((jumper.vm_code_address + self.vm_info.init_handler.base_address, jumper.first_handler, state))
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
                    addresses_to_explore.put((inst.args[0], inst.args[1], self.vm_info.handlers.create_state(inst.args[0], file.read)))
                    inst.args = inst.args[:1]
                    state.address = inst.address
                elif inst.name in ("CALL_RELIMM_NEXT", "CALL_VAR_NEXT", "CALL_MEMVAR_NEXT"):
                    jumper = VMFunctionJumper(file, inst.args[1])
                    # We continue with current state. But RESET_KEYS will probably be called anyway, since this call can use this same VM.
                    state.address = jumper.vm_code_address + self.vm_info.init_handler.base_address
                    addresses_to_explore.put((jumper.vm_code_address + self.vm_info.init_handler.base_address, jumper.first_handler, state))
                    starts.append(jumper.vm_code_address + self.vm_info.init_handler.base_address)
                    inst.args = inst.args[:-1]
                    inst.name = inst.name[:-len("_NEXT")]
                elif inst.name == "ADD_VAR_BASEADDRESS":
                    inst.args.append(self.vm_info.init_handler.base_address)
                elif self.vm_info.handlers.old_reset_handler and inst.name == "RESET_KEYS":
                    # In the new mechanism this call is part of the state decoder,
                    # because there may be key update alongside the keys reset
                    state.reset()
                elif inst.name == "MOV_VAR_UNKVAR":
                    # This vm instruction only used in anti-dump/integrity-test
                    # TODO: Check that in first section
                    self.integrity_used = True
                    inst.name = "MOV_%s_VAR_IMM" % file.get_arch().translate("{SU}")
                    inst.args.append(file.read_pointer(self.vm_info.init_handler.vm_struct + self.vm_info.handlers.fields["UNK_VAR"]))


                handler = handler_reader.get_next_handler()
                if handler is not None:
                    state.update_ip(handler_reader.get_size())

                instructions[inst.address] = inst
                instructions_list.append(inst)
        print "SUCCESS"

        self._process_instructions(instructions_list, instructions)

        if not self.vm_info.regs_fields:
            reader = vminstruction.VMInstructionsReader(instructions_list)
            try:
                reader.get_cond(lambda x: x.name == "RESET_FLAGS")
            except vminstruction.ReaderException:
                # It seems that sometimes the reset flags handler DOESN'T reset the flag, so it is detected as NOP and ignored
                # TODO: Check that the issue isn't at my code
                pass
            try:
                reader.get_cond(lambda x: x.name == "RESET_KEYS")
            except vminstruction.ReaderException:
                self.vm_info.regs_fields["SP"] = reader.get_cond(lambda x: x.name == "MOV_VAR_SP").args[0]
                reader.get_cond(lambda x: x.name == "RESET_KEYS")
            else:
                self.vm_info.regs_fields["SP"] = reader.get_cond(lambda x: x.name == "MOV_VAR_SP").args[0]
            regs = list(self.vm_info.init_handler.regs[::-1])
            assert regs[-1] == "flags"
            if reader.peek().name == arch.translate("POP_{SU}_VAR"):
                for reg in regs[:-1]:
                    reg = reg.upper()
                    if not reg[1].isdigit():
                        reg = reg[1:]
                    self.vm_info.regs_fields[reg] = reader.get_cond(lambda x: x.name == arch.translate("POP_{SU}_VAR")).args[0]
            elif self.file.mode == 32:
                # New shuffled registers reading..
                # Clean all the necessary things in order to parse the vm start
                # TODO: The temp var that is used to load the regs, shouldn't be used anywhere else. But it does
                # For example for this instruction: imul dword [esp + 5]. it doesn't implement this instruction, but it does
                # the part of esp+5, and it doesn't do anything with it. So I fail to convert it to assembly. I need to clean it out
                self._clean_vm_start(instructions_list, instructions)
                # Skip flags and fake esp reg
                for i in xrange(len(regs) - 2):
                    # MOV_DWORD_REG_MEMREGIMM REGVAR VAR
                    inst = reader.get_cond(lambda x: x.name == "MOV_DWORD_REG_MEMREGIMM" and x.args[1] == self.vm_info.regs_fields["SP"])
                    sp_offset = inst.args[2]
                    assert (sp_offset % 4) == 0 and 0 <= sp_offset / 4 < len(regs) - 1
                    reg = regs[sp_offset/4]
                    reg = reg.upper()
                    if not reg[1].isdigit():
                        reg = reg[1:]
                    self.vm_info.regs_fields[reg] = inst.args[0]
                # ADD_DWORD_VAR_IMM SP 0x20
                reader.get_cond(lambda x: x.name == "ADD_DWORD_VAR_IMM" and x.args[0] == self.vm_info.regs_fields["SP"] and  x.args[1] == (len(regs) - 1) * 4)
            else:
                assert False
            self.vm_info.regs_fields["FLAGS"] = reader.get_cond(lambda x: x.name == "POPF").args[0]
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
            # Don't add instructions that were removed during cleaning
            if instructions[address] in instructions_list:
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

    def _do_handler(self, handler, params, state):
        pass

    def _do_handler_end(self, handler, params, state):
        pass

    def _process_instructions(self, instructions, instructions_map):
        templates.Templates.get_template(r"codevirtualizer\animals\animals_00_clean.txt", self.mode).clean(instructions, update_instructions=instructions_map)

    def _clean_vm_start(self, instructions, instructions_map):
        templates.Templates.get_template(r"codevirtualizer\animals\animals_00_clean_vm_start.txt", self.mode).clean(instructions, update_instructions=instructions_map)

    def _get_instruction(self, name, args, state):
        nargs = []
        for arg_type, arg_value in args:
            if arg_type == "RELIMM":
                arg_value += self.vm_info.init_handler.base_address
            nargs.append(arg_value)
        return vminstruction.VMInstruction(name, *nargs)

    def _get_clean_templates(self):
        return ["animals_00_nums.txt", "animals_00_regs.txt", "animals_01_vm.txt", "animals_02_misc.txt", "animals_03_vars.txt", "animals_04_memvars.txt", "animals_05_fix_pop.txt", "animals_06_rep.txt"]

    # TODO: Base class
    def _clean(self):
        print "Processing VMFunction (%d instructions)..." % len(self.instructions)

        vars = dict(self.vm_info.regs_fields)
        vars["IS_REG"] = lambda x: x in self.vm_info.regs_fields.values() and self.vm_info.regs_fields["FLAGS"] != x

        for template in self._get_clean_templates():
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
                    try:
                        reader.get_cond(lambda x: x.name == "RESET_FLAGS")
                    except vminstruction.ReaderException:
                        # See the comment above abour RESET_FLAGS
                        pass

                if section_counter == 1:
                    code = cleaner.clean_animals_vm_code(code, self.file.get_arch())
                    if self.integrity_used:
                        # TODO: Find the end in a proper way...
                        index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
                        if index != -1:
                            code = code[code.find("\n", index+1)+1:]
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

        if section_counter == 1:
            code = cleaner.clean_animals_vm_code(code, self.file.get_arch())
            if self.integrity_used:
                # TODO: Find the end in a proper way...
                index = max(max(code.rfind("add esp, 0x"), code.rfind("pop esp")), code.rfind("mov esp, dword [esp]"))
                if index != -1:
                    code = code[code.find("\n", index+1)+1:]

        self.code = code[:-1]
        return self.code


    def printfunc(self):
        for inst in self.instructions:
            print inst


class FISHVMFunction(VMFunction):
    pass


class TIGERVMFunction(VMFunction):
    def _do_handler(self, handler, params, state):
        for src, dst in handler.extra_info["xchg"][0]:
            state.vars.xchg_vars(params[src], params[dst])

    def _do_handler_end(self, handler, params, state):
        for src, dst in handler.extra_info["xchg"][1]:
            state.vars.xchg_vars(params[src], params[dst])

    def _get_instruction(self, name, args, state):
        nargs = []
        for arg_type, arg_value in args:
            if arg_type == "VAR":
                arg_value = state.vars.get_real_var(arg_value)
            nargs.append((arg_type, arg_value))
        if name == "SHUFFLE_VM_STRUCT":
            # I am pretty sure that it does that
            # TODO: Do it proper (read it to move vars around)
            state.vars.reset()
        return VMFunction._get_instruction(self, name, nargs, state)

    def _get_clean_templates(self):
        return ["tiger_00_clean.txt"] + VMFunction._get_clean_templates(self)


class DOLPHINVMFunction(VMFunction):
    def _process_instructions(self, instructions, instructions_map):
        super(DOLPHINVMFunction, self)._process_instructions(instructions, instructions_map)
        templates.Templates.get_template(r"codevirtualizer\animals\dolphin_00_clean.txt", self.mode).clean(instructions, update_instructions=instructions_map)

    def _get_clean_templates(self):
        return VMFunction._get_clean_templates(self) + ["dolphin_01_xchg.txt"]
