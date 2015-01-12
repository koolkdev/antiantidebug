import debugger
import instruction
import cleaner
import struct
import pefile
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

def get_vm(debugger, addr, write_at, as_at):
    vm = vmtools.VMS["FISH"].get_vm(debugger.get_as_mapped_file(), addr)
    vm.code = fix_code(debugger, vm.code)
    print vm.code, hex(write_at)
    address, compiled_code = vm.compile_code()
    debugger.process.write(address, compiled_code)
    debugger.thread.set_pc(address)
    assert compiled_code[-2:] == "\xFF\xE0" # jmp eax/rax
    debugger.go(address + len(compiled_code) - 2)

    address, compiled_code = vm.compile_code(as_at)
    debugger.process.write(write_at, compiled_code)
    return write_at + len(compiled_code)


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


def get_clean_code(d, address, filter):
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    func = instruction.Function(cc, address, filter=filter)
    return func

def get_all_blocks(func):
    blocks = [func.start_block]
    i = 0
    while i < len(blocks):
        if blocks[i].next is not None and blocks[i].next not in blocks:
            blocks.append(blocks[i].next)
        if blocks[i].next_cond is not None and blocks[i].next_cond not in blocks:
            blocks.append(blocks[i].next_cond)
        i += 1
    return blocks

def find_jmp_eax(d, func):
    arch = d.get_as_mapped_file().get_arch()
    blocks = get_all_blocks(func)
    found = False
    address = None
    value = None
    for block in blocks:
        if block.next is None and str(block.instructions[-1]) == arch.translate("jmp {R:ax}"):
            assert not found
            found = True
            address = block.instructions[-1].address
            if block.instructions[-2].opcode == "mov":
                assert block.instructions[-2].operands[0].is_reg(block.instructions[-1].operands[0].reg) and block.instructions[-2].operands[1].is_immediate()
                value = block.instructions[-2].operands[1].value
            else:
                assert block.instructions[-2].opcode == "add" and block.instructions[-2].operands[0].is_reg(block.instructions[-1].operands[0].reg) and block.instructions[-2].operands[1].is_reg(arch.reg_native("bp"))
                assert block.instructions[-3].opcode == "mov" and block.instructions[-3].operands[0].is_reg(block.instructions[-1].operands[0].reg) and block.instructions[-3].operands[1].is_immediate()
                reg = arch.reg_native("bp")
                reg_value = d.thread.get_register(reg[0].upper() + reg[1:])
                value = block.instructions[-3].operands[1].value + reg_value
    assert found
    return address, value



def write_function(d, func, write_to, as_at):
    #print hex(func.get_end_block().instructions[-1].address)
    #cc.set_option("end_address", get_next(func.get_end_block().instructions[-1]))
    #cc.set_option("ignore_jumps", False)
    #address = d.thread.get_pc()
    blocks = get_all_blocks(func)
    code = ""
    """
    for block in blocks:
        code = "\n".join([str(x) for x in block.instructions])
        code_length = len(instruction.Assembler(d.get_as_mapped_file().mode).assemble(code, block.address))
        if block.next is not None:
            if block.next.address - (block.address + code_length) >= 2:
                code += "\njmp 0x%x" % block.next.address
        code = fix_code(d, code)g"
        print hex(block.address)
        print code
        d.get_as_mapped_file().write(block.address, instruction.Assembler(d.get_as_mapped_file().mode).assemble(code, block.address))
    """
    asm = instruction.Assembler(d.get_as_mapped_file().mode)
    fix_jumps = []
    block_at = {}
    as_at -= write_to
    for block in blocks:
        block_at[block.address] = write_to + as_at
        lines = [str(x) for x in block.instructions]
        jmps = None
        save = 0
        if block.next is not None:
            cond = None
            save = 1
            if block.next_cond is not None:
                jmp_type, dst = lines[-1].split(" ")
                lines = lines[:-1]
                assert jmp_type.startswith("j")
                assert int(dst, 16) == block.next_cond.address
                cond = jmp_type, block.next_cond.address
                save = 2
            jmps = (cond, block.next.address)
        if lines:
            code = "\n".join(lines)
            code = fix_code(d, code)
            # print hex(block.address-d.get_base_address())
            # print code
            comp = asm.assemble(code, write_to + as_at)
            d.get_as_mapped_file().write(write_to, comp)
            write_to += len(comp)
        if jmps is not None:
            fix_jumps.append((write_to, jmps))
            write_to += save * 6
    for at, (cond, target) in fix_jumps:
        if cond is not None:
            comp = asm.assemble("%s 0x%x" % (cond[0], block_at[cond[1]]), at + as_at)
            d.get_as_mapped_file().write(at, comp)
            at += len(comp)
        comp = asm.assemble("jmp 0x%x" % block_at[target], at + as_at)
        d.get_as_mapped_file().write(at, comp)
        at += len(comp)

    return write_to
#
# def skip_fake_calls(d, address):
#     inst = d.get_instruction(address)
#     if d.get_instruction(inst.next).operands[0].value == inst.next + 5:
#         # mov     ecx, 37D0h
#         # call    $+5
#         # pop     eax
#         # add     eax, 0Eh
#         # mov     [eax], ecx
#         # jmp     loc_13550EE
#         # mov     eax, ebx ; skipped
#         # jmp     [..]
#         return address
#     elif inst.operands[0].value == inst.address + 8:
#

# call    sub_436033
# db  20h
# pop     edi
# retn
# #
# pop     edi
# mov     [esp+4], edi
# add     dword ptr [esp+4], 15h
# inc     edi
# push    edi
# retn


viseted_decoding = {}
changed_mems = []
def skip_code_decoding(d, address):
    inst = d.get_instruction(address)
    if inst.opcode == "call" and inst.operands[0].is_immediate():
        if inst.operands[0].value > inst.address + 50:
            return inst.next, inst
        ninst = d.get_instruction(inst.operands[0].value)
        while ninst.opcode not in ("call", "push", "pop"):
            ninst = d.get_instruction(ninst.next)
        if ninst.opcode != "pop":
            return inst.next, inst
    if address in viseted_decoding:
        return viseted_decoding[address]
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    reader = cc.get_reader(address)
    arch = d.get_as_mapped_file().get_arch()
    try:
        print hex(address)
        print d.get_instruction(address)
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

    first_inst = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg() and x.operands[1].is_memory())
    r = arch.reg_dword(first_inst.operands[0].reg)
    op1 = reader.get_cond(lambda x: x.opcode in ("add", "sub", "xor") and x.operands[0].is_reg(r) and x.operands[1].is_immediate())
    op2 = reader.get_cond(lambda x: x.opcode in ("add", "sub", "xor") and x.operands[0].is_reg(r) and x.operands[1].is_immediate())
    op3 = reader.get_cond(lambda x: x.opcode in ("add", "sub", "xor") and x.operands[0].is_reg(r) and x.operands[1].is_immediate())
    reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_memory() and x.operands[1].is_reg(r))

    if zero_reg:
        search_reg = arch.reg_native(next.operands[0].reg)
    else:
        search_reg = mov_inst.operands[0].reg
    try:
        reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg(search_reg) and x.operands[1].is_immediate(4))
    except:
        num1op = reader.get_cond(lambda x: x.opcode in ("add", "sub", "dec", "inc") and x.operands[0].is_reg(search_reg))
        num2op = reader.get_cond(lambda x: x.opcode in ("add", "sub", "dec", "inc") and x.operands[0].is_reg(search_reg))
        num = 0
        for op in (num1op, num2op):
            if op.opcode == "add":
                num += op.operands[1].value
            elif op.opcode == "sub":
                num += -op.operands[1].value
            elif op.opcode == "inc":
                num += 1
            elif op.opcode == "dec":
                num += -1
        assert num == -4
    last_inst = reader.get()
    if zero_reg:
        assert last_inst.opcode == "cmp" and last_inst.operands[0].is_reg(arch.reg_dword(next.operands[0].reg)) and last_inst.operands[1].is_immediate()
        size = (1<<32) - last_inst.operands[1].value
    else:
        assert last_inst.opcode == "dec" and last_inst.operands[0].is_reg(arch.reg_native(next.operands[0].reg))
    reader.get_cond(lambda x: x.opcode == "jnz")
    # print hex(size)
    print hex(end_address)
    print hex(end_address-size)

    f = d.get_as_mapped_file()
    # Do the op
    data = f.read(end_address-size, size)
    changed_mems.append((end_address-size, data))
    ndata = ""
    addr = end_address-size
    for i in xrange(0, size, 4):
        num = struct.unpack("<L", data[i:i+4])[0]
        for op in (op1, op2, op3):
            if op.opcode == "add":
                num += op.operands[1].value
            elif op.opcode == "sub":
                num -= op.operands[1].value
            elif op.opcode == "xor":
                num ^= op.operands[1].value
            num &= 0xffffffff
        ndata += struct.pack("<L", num)
        addr += 4
    f.write(end_address-size, ndata)


    # ctx = d.thread.get_context()
    # d.thread.set_pc(address)
    # d.go(end_address-size, True)
    # d.thread.set_context(ctx)
    viseted_decoding[address] = end_address - size

    #d.get_as_mapped_file().write(address, instruction.Assembler(arch.native_size()*8).assemble("jmp 0x%x" % viseted_decoding[address], address))
    return viseted_decoding[address]
    # reader = cc.get_reader(end_address-size)
    # while True:
    #     inst = reader.get()
    #     print hex(inst.address)
    #     print inst

def restore_mems(d):
    global changed_mems
    for address, mem in changed_mems[::-1]:
        d.process.write(address, mem)
    changed_mems = []

def follow(binary, vm="FISH"):
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

    #d.thread.set_pc(skip_code_decoding(d, d.thread.get_pc()))
    #d.thread.set_pc(skip_code_decoding(d, d.thread.get_pc()))

    #return d
    print "----------------"
    def filter(address):
        return skip_code_decoding(d, address)

    pe = pefile.PE(data=d.process.read(d.get_base_address(), 0x1000))
    end = d.get_base_address() + pe.sections[-1].VirtualAddress + pe.sections[-1].Misc
    write_to = d.process.malloc(0x30000)
    end -= write_to
    org = write_to

    for i in xrange(2):
        func = get_clean_code(d, d.thread.get_pc(), filter)
        jmp_eax_address, jmp_value = find_jmp_eax(d, func)
        write_to = write_function(d, func, write_to, write_to + end)
        restore_mems(d)
        print d.go(jmp_eax_address, True)
        write_to = get_vm(d, jmp_value, write_to, write_to + end)
        #print d.go(write_to-2)
        d.step()


    # write_to = clean_code(d, d.get_base_address()+0x905C, filter, write_to, write_to + end)
    # write_to = clean_code(d, d.get_base_address()+0xd8a2, filter, write_to, write_to + end)
    #d.thread.set_pc(write_to)
    #while True:
    #    print hex(d.thread.get_pc())
    #    print d.step()
    #d.go()

    d.new_section = d.process.read(org, 0x30000)
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
