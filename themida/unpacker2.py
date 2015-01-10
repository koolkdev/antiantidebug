import debugger
import instruction
import cleaner
from vms import vmtools

def get_call_value(inst):
    if inst.opcode == "call" and inst.operands[0].is_immediate():
        return inst.operands[0].value
    return None

def get_jump_value(inst):
    if inst.opcode == "jmp" and inst.operands[0].is_immediate():
        return inst.operands[0].value
    return None


def get_next(inst, ignore_jcc=False):
    if inst.opcode == "jmp":
        if inst.operands[0].is_immediate():
            return inst.operands[0].value
        return None
    elif inst.opcode.startswith("j"):
        if not ignore_jcc:
            return None
    return inst.next

def go_to_condition_simple(d, cond):
    inst = d.get_instruction()
    while not cond(inst):
        inst = d.get_instruction(get_next(inst, True))
    return d.go(inst.address)

def go_to_condition_follow_all(d, cond):
    inst = d.get_instruction()
    while not cond(inst):
        inst = d.step()
    return inst

def step_00_go_to_first_decryptor_func(d):
    for i in xrange(3):
        inst = d.step()
    assert get_call_value(inst) is not None
    d.step()

def step_01_skip_first_decryptor_func(d):
    func = instruction.Function(d.get_as_mapped_file(), d.thread.get_pc())
    last_inst = func.get_end_block().instructions[-1]
    assert last_inst.opcode == "ret"
    d.go(last_inst.address)
    d.step()

def step_02_skip_decompression_secureengine_func(d):
    func = instruction.Function(d.get_as_mapped_file(), d.thread.get_pc(), lambda x: (x.opcode == "mov" and x.operands[0].is_memory() and x.operands[1].is_immediate(0xe9)))
    last_inst = func.get_end_block().instructions[-1]
    d.go(last_inst.address)
    inst = d.step()
    if d.get_as_mapped_file().mode == 32:
        # Skip STI
        assert inst.opcode == "popad"
        inst = d.step()
        assert get_call_value(inst) is not None
        inst = d.step()
        for i in xrange(6):
            inst = d.get_instruction(inst.next)
    else:
        # Skip pops
        for i in xrange(8):
            assert inst.opcode == "pop"
            inst = d.step()
    assert get_jump_value(inst) is not None
    inst = d.go(get_jump_value(inst))
    assert get_jump_value(inst) is not None
    d.step()

def step_03_skip_decoding(d):
    data = d.get_as_mapped_file().read(d.thread.get_pc(), 0x5000)
    # Search for decoded mov eax, 48692121. it is the first opcode after decoding
    d.go(d.thread.get_pc() + data.index("B922226A49".decode("hex")), True)


def step_04_skip_pe_start_search(d):
    inst = go_to_condition_simple(d, lambda x: x.opcode == "cmp" and x.operands[0].is_memory() and x.operands[1].is_immediate(0x5A4D))
    for i in xrange(4):
        inst = d.get_instruction(inst.next)
    assert inst.opcode == "cmp" and inst.operands[0].is_memory() and inst.operands[1].is_immediate(0x4550)
    inst = d.get_instruction(inst.next)
    # jz ...
    assert inst.opcode == "jz"
    d.go(inst.operands[0].value)
    inst = go_to_condition_simple(d, lambda x: x.opcode == "cmp" and x.operands[0].is_memory() and x.operands[1].is_immediate(0x5A4D))
    inst = d.get_instruction(inst.next)
    # jz ...
    assert inst.opcode == "jz"
    inst = d.get_instruction(inst.operands[0].value)
    for i in xrange(2):
        inst = d.get_instruction(inst.next)
    assert inst.opcode == "cmp" and inst.operands[0].is_memory() and inst.operands[1].is_immediate(0x4550)
    inst = d.get_instruction(inst.next)
    # jz ...
    assert inst.opcode == "jz"
    d.go(inst.operands[0].value)

    go_to_condition_follow_all(d, lambda x: str(x) == "test cl, cl")

    if d.get_as_mapped_file().mode == 32:
        go_to_condition_follow_all(d, lambda x: str(x) == "mov eax, eax")
        d.step()
    else:
        go_to_condition_follow_all(d, lambda x: str(x) == "mov eax, 0x1")
        go_to_condition_follow_all(d, lambda x: x.opcode == "mov" and x.operands[0].is_memory() and x.operands[1].is_reg("eax"))
        d.step()
        # In 64 bit it is still not the end of the junked code

def get_cleaner(d):
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    cc.set_option("fixDoubleStackOperation", True)
    cc.set_option("fixPush_allowConstants", True)
    return cc

def print_clean(c, address):
    inst = c.get_instruction(address)
    while True:
        print inst
        inst = c.get_instruction(inst.next)

def get_instruction_ignore_jumps(debugger, address):
    inst = debugger.get_instruction(address)
    while True:
        if inst.opcode != "jmp":
            return inst
        inst = debugger.get_instruction(inst.operands[0].value)

def goto_jmp_eax(debugger):
    print "Looking for jmp eax"
    arch = debugger.get_as_mapped_file().get_arch()
    target = arch.translate("jmp {R:ax}")
    if arch.native_size() == 8:
        stop = "nop"
    else:
        stop = "sti"
    cc = cleaner.Cleaner(debugger.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    inst = cc.get_instruction(debugger.thread.get_pc())
    exceptions = False
    saw = []
    loop_detector = []
    while True:
        if str(inst) == target:
            break
        if inst.opcode == stop: # in 64bit mode
            exceptions = True
        if inst.opcode == "jnz":
            if exceptions:
                if saw.count(inst) > 0:
                    assert False
                if str(get_instruction_ignore_jumps(debugger, inst.next)) == stop:
                    inst = debugger.go(inst.next)
                else:
                    if saw.count(inst.address) > 0:
                        # Go to the last
                        inst = debugger.go(debugger.get_instruction(saw[-1]).next)
                        saw = []
                    else:
                        saw.append(inst.address)
                        isnt = debugger.go(inst.address)
                        inst = debugger.step()
            else:
                if saw.count(inst.address) > 0:
                    # Go to the last
                    inst = debugger.go(debugger.get_instruction(saw[-1]).next)
                    saw = []
                else:
                    saw.append(inst.address)
                    isnt = debugger.go(inst.address)
                    inst = debugger.step()
            loop_detector = []
            inst = cc.get_instruction(inst.address)
            continue
        if inst.opcode.startswith("j") or inst.opcode == "ret":
            inst = debugger.go(inst.address)
            inst = debugger.step()
            loop_detector = []
            inst = cc.get_instruction(inst.address)
        else:
            inst = cc.get_instruction(inst.next)

        if loop_detector.count(inst.address) != 0:
            inst = debugger.go(inst.address)
            inst = cc.get_instruction(inst.address)
            loop_detector = []
        loop_detector.append(inst.address)


    debugger.go(inst.address)
    print "Found jmp eax"

def fix_code(debugger, code):
    arch = debugger.get_as_mapped_file().get_arch()
    reg = arch.reg_native("bp")
    reg_value = debugger.thread.get_register(reg[0].upper() + reg[1:])
    while (reg + "+") in code:
        start = code.index(reg + "+")
        end = code.index("]", start)
        part = code[start:end]
        code = code[:start] + "?0x%x" % (eval(part, {reg:reg_value}) & ((1<<(arch.native_size()*8))-1)) + code[end:]
    return code

def get_vm(debugger):
    vm = vmtools.VMS["FISH"].get_vm(debugger.get_as_mapped_file(), debugger.thread.get_pc())
    vm.code = fix_code(debugger, vm.code)
    address, compiled_code = vm.compile_code()
    debugger.process.write(address, compiled_code)
    debugger.thread.set_pc(address)
    assert compiled_code[-2:] == "\xFF\xE0" # jmp eax/rax
    return vm.get_code(), address + len(compiled_code) - 2


def clean_code_until(d, address, condition):
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    #cc.set_option("ignore_calls", True)
    #print hex(func.get_end_block().instructions[-1].address)
    #cc.set_option("end_address", get_next(func.get_end_block().instructions[-1]))
    cc.set_option("ignore_jumps", False)
    #address = d.thread.get_pc()
    code = ""
    func = instruction.Function(cc, address, condition)
    blocks = [func.start_block]
    i = 0
    while i < len(blocks):
        if blocks[i].next is not None and blocks[i].next not in blocks:
            blocks.append(blocks[i].next)
        if blocks[i].next_cond is not None and blocks[i].next_cond not in blocks:
            blocks.append(blocks[i].next_cond)
        i += 1
    for block in blocks:
        code = "\n".join([str(x) for x in block.instructions])
        code_length = len(instruction.Assembler(d.get_as_mapped_file().mode).assemble(code, block.address))
        if block.next is not None:
            code += "\njmp 0x%x" % block.next.address
        code = fix_code(d, code)
        d.get_as_mapped_file().write(block.address, instruction.Assembler(d.get_as_mapped_file().mode).assemble(code, block.address))
    nfunc = instruction.Function(d.get_as_mapped_file(), address, condition)
    inst = nfunc.get_end_block().instructions[-1]
    return get_next(inst)


def clean_code(d, address, filter):
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    #cc.set_option("ignore_calls", True)
    #print hex(func.get_end_block().instructions[-1].address)
    #cc.set_option("end_address", get_next(func.get_end_block().instructions[-1]))
    #cc.set_option("ignore_jumps", False)
    #address = d.thread.get_pc()
    code = ""
    func = instruction.Function(cc, address, filter=filter)
    blocks = [func.start_block]
    i = 0
    while i < len(blocks):
        if blocks[i].next is not None and blocks[i].next not in blocks:
            blocks.append(blocks[i].next)
        if blocks[i].next_cond is not None and blocks[i].next_cond not in blocks:
            blocks.append(blocks[i].next_cond)
        i += 1
    print hex(address)
    for block in blocks:
        code = "\n".join([str(x) for x in block.instructions])
        code_length = len(instruction.Assembler(d.get_as_mapped_file().mode).assemble(code, block.address))
        if block.next is not None:
            if block.next.address - (block.address + code_length) >= 2:
                code += "\njmp 0x%x" % block.next.address
        code = fix_code(d, code)
        print hex(block.address)
        print code
        d.get_as_mapped_file().write(block.address, instruction.Assembler(d.get_as_mapped_file().mode).assemble(code, block.address))

viseted_decoding = {}
def skip_code_decoding(d, address):
    if address in viseted_decoding:
        return viseted_decoding[address]
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    reader = cc.get_reader(address)
    arch = d.get_as_mapped_file().get_arch()
    try:
        end_address = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg("eax") and x.operands[1].is_immediate()).operands[1].value
        reader.get_cond(lambda x: str(x) == arch.translate("push {R:ax}"))
        # The second oeprand is the address of add {R:...}, [rsp]
        mov_inst = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg() and x.operands[1].is_immediate())
        if arch.native_size() == 4:
            try:
                reader.get_cond(lambda x: x.opcode == "sti")
            except cleaner.CleanerException:
                pass
        end_address += mov_inst.operands[1].value + 4
        reader.get_cond(lambda x: str(x) == arch.translate("add {R:%s}, {S} [{R:sp}]" % mov_inst.operands[0].reg))
        reader.get_cond(lambda x: str(x) == arch.translate("add {R:sp}, 0x{N}"))
    except cleaner.CleanerException:
        viseted_decoding[address] = address
        return address
    if arch.native_size() == 4:
        try:
            reader.get_cond(lambda x: x.opcode == "sti")
        except cleaner.CleanerException:
            pass

    next = reader.get()
    size = None
    assert next.operands[0] != None and next.operands[0].is_reg()
    if (next.opcode == "mov" and next.operands[1].is_immediate(0)) or \
            (next.opcode in ("xor", "sub")) and next.operands[1].is_reg(next.operands[0].reg):
        zero_reg = True
    elif next.opcode== "mov" and next.operands[1].is_immediate():
        zero_reg = False
        size = next.operands[1].value * 4
    last_inst = None
    inst = reader.get()
    while inst.opcode != "jnz":
        last_inst = inst
        inst = reader.get()
    if zero_reg:
        assert last_inst.opcode == "cmp" and last_inst.operands[0].is_reg(arch.reg_dword(next.operands[0].reg)) and last_inst.operands[1].is_immediate()
        size = (1<<32) - last_inst.operands[1].value
    else:
        assert last_inst.opcode == "dec" and last_inst.operands[0].is_reg(arch.reg_native(next.operands[0].reg))
    # print hex(size)
    print hex(end_address)
    print hex(end_address-size)

    ctx = d.thread.get_context()
    d.thread.set_pc(address)
    d.go(end_address-size, True)
    d.thread.set_context(ctx)
    viseted_decoding[address] = end_address - size
    #d.get_as_mapped_file().write(address, instruction.Assembler(arch.native_size()*8).assemble("jmp 0x%x" % viseted_decoding[address], address))
    return viseted_decoding[address]
    # reader = cc.get_reader(end_address-size)
    # while True:
    #     inst = reader.get()
    #     print hex(inst.address)
    #     print inst


def follow(binary):
    d = debugger.Debugger()
    d.start(binary)
    step_00_go_to_first_decryptor_func(d)
    step_01_skip_first_decryptor_func(d)
    inst = d.get_instruction()
    if get_jump_value(inst) is not None:
        pass
    else:
        step_02_skip_decompression_secureengine_func(d)
    assert get_jump_value(d.get_instruction()) is not None
    d.step()
    step_03_skip_decoding(d)
    step_04_skip_pe_start_search(d)

    # while True:
    #     goto_jmp_eax(d)
    #     d.step()
    #     vmcode, jmp_eax_address = get_vm(d)
    #     print vmcode
    #     print "Going to jmp eax"
    #     d.go(jmp_eax_address)
    #     print "Got to there"
    #     d.step()

    #skip_code_decoding(d)
    #skip_code_decoding(d)

    print "----------------"
    def filter(address):
        return skip_code_decoding(d, address)
    clean_code(d, d.thread.get_pc(), filter)

    return d

    """
    reader = get_cleaner(d).get_reader(d.thread.get_pc())
    inst = reader.get()
    while inst.opcode != "jnz":
        inst = reader.get()
    d.go(inst.next)
    """

    #print_clean(get_cleaner(d), d.thread.get_pc())
    return d

def do_file(filename):
    follow(filename).dump(filename[:-4] + ".dumped.exe")

def do(binary):
    do_file(binary)
