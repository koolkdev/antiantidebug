import debugger
import instruction
from themida import cleaner
from vms.codevirtualizer.cisc import vm
import antidebugging

import re

#def unpack(binary):
#


def find_ret(debugger):
    current_address = debugger.thread.get_pc()
    inst = debugger.get_instruction(current_address)
    while inst.opcode != "ret":
        current_address += inst.length
        if inst.opcode.startswith("j") and inst.operands[0].is_immediate() and inst.operands[0].value > current_address:
            current_address = inst.operands[0].value
        inst = debugger.get_instruction(current_address)
    return current_address

def find_cmp_PE(debugger):
    current_address = debugger.thread.get_pc()
    inst = debugger.get_instruction(current_address)
    i = 0
    while not (inst.opcode == "cmp" and inst.operands[1].is_immediate() and inst.operands[1].value == 0x4550):
        if i > 100:
            return None
        i += 1
        current_address += inst.length
        if inst.opcode == "jmp" and inst.operands[0].is_immediate() and inst.operands[0].value > current_address:
            current_address = inst.operands[0].value
        inst = debugger.get_instruction(current_address)
    return current_address
    

def follow_until(debugger, stop, ignore_not_jmps = False, ignore = 0):
    inst = debugger.get_instruction()
    while True:
        #print "%X: %s" % (inst.address, inst)
        next = inst.next
        if inst.opcode == "jmp":
            next = inst.operands[0].value
        elif not ignore_not_jmps and inst.opcode == "call":
           next = inst.operands[0].value
        elif inst.opcode == stop:
            if ignore == 0:
                return inst.address
            ignore -= 1
#        elif not ignore_not_jmps and inst.operands[0].is_immediate() and inst.operands[0].is_address and inst.operands[0].value != inst.next:
#            print inst
#            return None
        inst = debugger.get_instruction(next)

def get_instruction_ignore_jumps(debugger, address):
    inst = debugger.get_instruction(address)
    while True:
        if inst.opcode != "jmp":
            return inst
        inst = debugger.get_instruction(inst.operands[0].value)
	
def old_follow(binary):
    d = debugger.Debugger()
    first = d.start(binary)
    assert first.opcode == "sub" and first.operands[0].is_reg("esp") and first.operands[1].is_immediate(4)
    
    res = d.go(find_ret(d))
    assert str(d.step()) == "mov eax, 0x0"
    d.go(follow_until(d, "popa", True, 1))
    res = d.step()
    if res.opcode == "call":
        exceptions = True
    else:
        exceptions = False
    if exceptions:
        res = d.step()
        assert str(res) == "push dword fs:[0x0]"
        [d.step() for i in xrange(4)]
        res = d.step()
        assert res.opcode == "sti"
        # We don't want to debug the exception handler..
        d.stepover()
    d.step(); d.step()
    assert str(d.step()) == "mov eax, ebp"
    d.pc(); d.pc()
    [d.stepover() for i in xrange(5)]
    # Find next jnz
    inst = d.step()
    while inst.opcode != "jnz":
        inst = d.step()
    # Go until next opcode with hw bp, because it is going to change
    assert str(d.go(inst.address + inst.length, True)) == "mov eax, 0x48692121"
    d.go(find_cmp_PE(d))
    res = d.step()
    assert res.opcode == "jz"
    d.go(res.operands[0].value)
    d.go(find_cmp_PE(d))
    res = d.step()
    assert res.opcode == "jz"
    res = d.go(res.operands[0].value)
    assert str(res) == "xchg eax, esi"
    inst = d.step()
    if exceptions:
        while inst.opcode != "jz":
            inst = d.step()
        res = d.step()
        assert str(res) == "mov eax, eax"
        d.step()
        
    """res = d.go(follow_until(d, "jnz"))
    assert not exceptions or str(get_instruction_ignore_jumps(d, res.next)) == "sti"
    d.go(res.next)
    
    res = d.go(follow_until(d, "jnz"))
    assert not exceptions or str(get_instruction_ignore_jumps(d, res.next)) == "sti"
    d.go(res.next)

    if not exceptions:
        res = d.go(follow_until(d, "jnz"))
        assert not exceptions or str(get_instruction_ignore_jumps(d, res.next)) == "sti"
        d.go(res.next)"""

    # GOTO jmp eax
    inst = d.stepover()
    saw = []
    while True:
        if str(inst) == "jmp eax":
            break
        elif inst.opcode == "jnz":
            if exceptions:
                if saw.count(inst) > 0:
                    assert False
                if str(get_instruction_ignore_jumps(d, inst.next)) == "sti": 
                    inst = d.go(inst.next)
                else:
                    saw.append(inst.address)
                    inst = d.step()
            else:
                if saw.count(inst.address) > 0:
                    # Go to the last
                    inst = d.go(d.get_instruction(saw[-1]).next)
                    saw = []
                else:
                    saw.append(inst.address)
                    inst = d.step()           
        elif inst.opcode == "call" and inst.operands[0].is_immediate():
            inst = d.step()
        else:
            inst = d.stepover()
            
    d.step()
    cc = cleaner.Cleaner(d.get_as_mapped_file())
    cc.set_option("fixOperationConstantThruRegOnStack", True)
    cc.set_option("fixPush_allowConstants", True)
    res = cc.get_clean_instruction(d.thread.get_pc())
    jmp_to_vm = d.get_instruction(res.next)
    first_vm = vm.get_vm_code(d.get_as_mapped_file(), res, jmp_to_vm)
    
    add_ebp, xor_with = [int(x, 16) for x in re.match(r".+\nmov eax, dword \[ebp\+0x(\w+)\]\nxor eax, 0x(\w+)\nadd eax, ebp\njmp eax$", first_vm, re.S).groups()]
    value = ((d.process.read_dword((d.thread.get_register("Ebp") + add_ebp) % (1<<32)) ^ xor_with) + d.thread.get_register("Ebp")) % (1<<32)
    
    inst = d.go(value)
    saw = []
    while True:
        if inst.opcode == "mov" and inst.operands[1].is_immediate(0x52) and inst.operands[0].is_memory() and inst.operands[0].base == "ebp":
            break
        elif inst.opcode == "jnz":
            if exceptions:
                if saw.count(inst) > 0:
                    assert False
                if str(get_instruction_ignore_jumps(d, inst.next)) == "sti": 
                    inst = d.go(inst.next)
                else:
                    saw.append(inst.address)
                    inst = d.step()
            else:
                if saw.count(inst.address) > 0:
                    # Go to the last
                    inst = d.go(d.get_instruction(saw[-1]).next)
                    saw = []
                else:
                    saw.append(inst.address)
                    inst = d.step()           
        elif inst.opcode == "call" and inst.operands[0].is_immediate():
            inst = d.step()
        else:
            inst = d.stepover()

    print inst
    while True:
        print inst
        #if inst.opcode == "mov" and inst.operands[1].is_immediate(0x52) and inst.operands[0].is_memory() and inst.operands[0].base == "ebp":
        #    break
        if inst.opcode == "jnz":
            if exceptions:
                if saw.count(inst) > 0:
                    assert False
                if str(get_instruction_ignore_jumps(d, inst.next)) == "sti": 
                    inst = d.go(inst.next)
                else:
                    saw.append(inst.address)
                    inst = d.step()
            else:
                if saw.count(inst.address) > 0:
                    # Go to the last
                    inst = d.go(d.get_instruction(saw[-1]).next)
                    saw = []
                else:
                    saw.append(inst.address)
                    inst = d.step()           
        elif inst.opcode == "call" and inst.operands[0].is_immediate():
            inst = d.step()
        else:
            inst = d.stepover()
    return d

def get_vm(debugger):
    cc = cleaner.Cleaner(debugger.get_as_mapped_file())
    #cc.set_option("fixOperationConstantThruRegOnStack", True)
    #cc.set_option("fixPush_allowConstants", True)

    cc.set_option("ignore_jumps", False)

    #clean = cleaner.Cleaner(debugger)
    #reader = clean.get_reader(debugger.thread.get_pc())
    #while True:
    #    print reader.get()

    reader = cc.get_reader(debugger.thread.get_pc())
    subesp = reader.get_cond(lambda x: ((x.opcode == "push" and x.operands[0].size == 4) or (x.opcode == "sub" and x.operands[0].is_reg("esp") and x.operands[1].is_immediate(4))))
    push1 = reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg())
    push2 = reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg())
    movimm = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(push1.operands[0].reg) and x.operands[1].is_immediate())
    movesp = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(push2.operands[0].reg) and x.operands[1].is_reg("esp"))
    mov = reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_memory() and (x.operands[0].base == push2.operands[0].reg or x.operands[0].index == push2.operands[0].reg) and (x.operands[0].base is None or x.operands[0].index is None) and x.operands[0].offset == 8 and x.operands[1].is_reg(push1.operands[0].reg))
    pop2 = reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(push2.operands[0].reg))
    pop1 = reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(push1.operands[0].reg))
    jmp_to_vm = reader.get_cond(lambda x: x.opcode == "jmp" and x.operands[0].is_immediate())

    #first_vm = vm.get_vm_code(debugger, res, jmp_to_vm)
    #print first_vm
    #assert first_vm.endswith("\njmp eax")

    #first_vm = first_vm[first_vm.rfind("mov eax, dword [ebp+0x"):]
    #add_ebp, xor_with = [int(x, 16) for x in re.match(r"mov eax, dword \[ebp\+0x(\w+)\].+xor eax, 0x(\w+).+add eax, ebp.+jmp eax$", first_vm, re.S).groups()]
    #value = ((debugger.process.read_dword((debugger.thread.get_register("Ebp") + add_ebp) % (1<<32)) ^ xor_with) + debugger.thread.get_register("Ebp")) % (1<<32)
    vm = vm.VMFunction(debugger.get_as_mapped_file(), movimm.operands[1].value, jmp_to_vm.operands[0].value)
    vm.clean()
    #print vm.get_code()
    address, compiled_code = vm.compile_code()
    #print compiled_code.encode("hex")
    debugger.process.write(address, compiled_code)
    debugger.thread.set_pc(address)
    assert compiled_code[-2:] == "\xFF\xE0" # jmp eax
    return vm.get_code(), address + len(compiled_code) - 2

def goto_jmp_eax(debugger):
    print "Looking for jmp eax"
    cc = cleaner.Cleaner(debugger.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    inst = cc.get_clean_instruction(debugger.thread.get_pc())    
    exceptions = False
    saw = []
    loop_detector = []
    while True:
        #print "0x%08X: %s" % (inst.address, inst)
        if str(inst) == "jmp eax":
            break
        #print "0x%x: %s" % (inst.address, str(inst))
        if inst.opcode == "sti":
            exceptions = True
        if inst.opcode == "jnz":
            if exceptions:
                if saw.count(inst) > 0:
                    assert False
                if str(get_instruction_ignore_jumps(debugger, inst.next)) == "sti": 
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
            inst = cc.get_clean_instruction(inst.address)
            continue
        if inst.opcode.startswith("j") or inst.opcode == "ret":
            inst = debugger.go(inst.address)
            inst = debugger.step()
            loop_detector = []
            inst = cc.get_clean_instruction(inst.address)
        else:
            inst = cc.get_clean_instruction(inst.next)

        if loop_detector.count(inst.address) != 0:
            inst = debugger.go(inst.address)
            inst = cc.get_clean_instruction(inst.address)
            loop_detector = []
        loop_detector.append(inst.address)


    debugger.go(inst.address)
    print "Found jmp eax"

def new_goto_jmp_eax(debugger):
    print "Looking for jmp eax"
    cc = cleaner.Cleaner(debugger.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    try_address = debugger.thread.get_pc()
    inst = cc.get_clean_instruction(debugger.thread.get_pc())    
    exceptions = False
    saw = []
    old_inst = inst
    while True:
        #print "0x%08X: %s" % (inst.address, inst)
        if str(inst) == "jmp eax":
            break
        #print inst
        if inst == None:
            inst = debugger.go(try_address)
            continue
        old_inst = inst
        if inst.opcode == "sti":
            exceptions = True
        if str(inst) == "in eax, dx":
            debugger.go(inst.address)
            inst = debugger.step()
            try_address = inst.address
            inst = cc.get_clean_instruction(inst.address)
            continue
        if inst.opcode == "jnz":
            if exceptions:
                if saw.count(inst) > 0:
                    assert False
                if str(get_instruction_ignore_jumps(debugger, inst.next)) == "sti":
                    inst = debugger.go(inst.next)
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
            try_address = inst.address
            inst = cc.get_clean_instruction(inst.address)
            continue
        if inst.opcode.startswith("j") or inst.opcode == "ret":
            inst = debugger.go(inst.address)
            inst = debugger.step()
            try_address = inst.address
            inst = cc.get_clean_instruction(inst.address)
        else:
            try_address = inst.next
            inst = cc.get_clean_instruction(inst.next)
            
    debugger.go(inst.address)
    print "Found jmp eax"
    

def follow(binary):
    d = debugger.Debugger()
    d.start(binary)
    antidebugging.hide_IsDebuggerPresent(d)
    antidebugging.hide_ZwSetInformationThread(d)
    antidebugging.hide_CheckRemoteDebuggerPresent(d)
    # Check for vm
    d.handle_illegal_instruction(True)
    illegal_instruction = d.go()
    d.handle_illegal_instruction(False)
    assert d.process.read(illegal_instruction.address, 4) == "0f3f070b".decode("hex")
    inst = d.go(illegal_instruction.address + 4)
    while str(inst) != "cmp ebx, 0xffffffff":
        inst = d.step()
    next_jmp = d.step()
    assert next_jmp.opcode == "jz"
    inst = d.step()
    while str(inst) != "in eax, dx":
        inst = d.step()
    # let their instruction handler handle it
    assert str(d.step()) == "add esp, 0x4"
    #return d
    while True:
        if str(inst) == "cmp esi, 0xa":
            break
        if inst.opcode == "call" and not inst.operands[0].is_immediate():
            inst = d.stepover()
        else:
            inst = d.step()
    jmp = d.step()
    assert jmp.opcode == "jz"
    inst = d.go(jmp.operands[0].value)
    i = 0
    while True:
        goto_jmp_eax(d)
        d.step()
        print hex(d.thread.get_pc())
        vmcode, jmp_eax_address = get_vm(d)
        #print vmcode
        #if vmcode.find("push 0x0\npush 0x0\npush 0x11\npush 0xFFFFFFFE\ncall eax") != -1:
        #    print "Skipping bad call"
        #    while str(d.stepover()) != "push 0xfffffffe":
        #        pass
        #    call = d.step()
        #    d.thread.set_pc(call.next) # Skip call eax
        #    d.thread.set_register('Esp', d.thread.get_register('Esp')+0x10)
        #    print d.go(0x7616b0e6)
        #    break
        #if i == 24:
        #    break
        print "Going to jmp eax"
        d.go(jmp_eax_address)
        print "Got to there"
        d.step()
        print i
        if i == 35:
            break
        i += 1
    #d.go()
    
    #address, compiled_code = vm.get_compiled_vm_code(d, res, jmp_to_vm)
    #d.process.write(address, compiled_code)
    #d.thread.set_pc(address)
    return d

def new_follow(binary):
    d = debugger.Debugger()
    first = d.start(binary)
    antidebugging.hide_IsDebuggerPresent(d)
    antidebugging.hide_ZwSetInformationThread(d)
    antidebugging.hide_CheckRemoteDebuggerPresent(d)
    d.go()
    assert first.opcode == "sub" and first.operands[0].is_reg("esp") and first.operands[1].is_immediate(4)
    
    res = d.go(find_ret(d))
    assert str(d.step()) == "mov eax, 0x0"
    d.go(follow_until(d, "popa", True, 1))
    res = d.step()
    if res.opcode == "call":
        exceptions = True
    else:
        exceptions = False
    if exceptions:
        res = d.step()
        assert str(res) == "push dword fs:[0x0]"
        [d.step() for i in xrange(4)]
        res = d.step()
        assert res.opcode == "sti"
        # We don't want to debug the exception handler..
        d.stepover()
    d.step(); d.step()
    assert str(d.step()) == "mov eax, ebp"
    d.pc(); d.pc()
    [d.stepover() for i in xrange(5)]
    # Find next jnz
    inst = d.step()
    while inst.opcode != "jnz":
        inst = d.step()
    # Go until next opcode with hw bp, because it is going to change
    assert str(d.go(inst.address + inst.length, True)) == "mov eax, 0x48692121"
    d.go(find_cmp_PE(d))
    res = d.step()
    assert res.opcode == "jz"
    d.go(res.operands[0].value)
    d.go(find_cmp_PE(d))
    res = d.step()
    assert res.opcode == "jz"
    res = d.go(res.operands[0].value)
    assert str(res) == "xchg eax, esi"
    inst = d.step()
    if exceptions:
        while inst.opcode != "jz":
            inst = d.step()
        res = d.step()
        assert str(res) == "mov eax, eax"
        inst = d.step()
    i = 0
    while True:
        goto_jmp_eax(d)
        d.step()
        print hex(d.thread.get_pc())
        vmcode, jmp_eax_address = get_vm(d)
        print vmcode
        #if vmcode.find("push 0x0\npush 0x0\npush 0x11\npush 0xFFFFFFFE\ncall eax") != -1:
        #    print "Skipping bad call"
        #    while str(d.stepover()) != "push 0xfffffffe":
        #        pass
        #    call = d.step()
        #    d.thread.set_pc(call.next) # Skip call eax
        #    d.thread.set_register('Esp', d.thread.get_register('Esp')+0x10)
        #    print d.go(0x7616b0e6)
        #    break
        #if i == 24:
        #    break
        print "Going to jmp eax"
        d.go(jmp_eax_address)
        print "Got to there"
        d.step()
        print i
        #if i == 31:
        #    break
        i += 1
    #d.go()
    
    #address, compiled_code = vm.get_compiled_vm_code(d, res, jmp_to_vm)
    #d.process.write(address, compiled_code)
    #d.thread.set_pc(address)
    return d

def get_debugger(binary):
    d = debugger.Debugger()
    first = d.start(binary)
    antidebugging.hide_IsDebuggerPresent(d)
    antidebugging.hide_ZwSetInformationThread(d)
    antidebugging.hide_CheckRemoteDebuggerPresent(d)
    return d
    
#def follow(binary):
#    d = debugger.Debugger()
#    d.start(binary)
#    print d.go(d.process.resolve_label("ntdll!ZwSetInformationThread"))
#    return d
    
def run_clean(debugger):
    cc = cleaner.Cleaner(debugger.get_as_mapped_file())
    cc.set_option("ignore_calls", True)
    inst = cc.get_clean_instruction(debugger.thread.get_pc())
    while True:
        print "0x%08X: %s" % (inst.address, inst)
        inst = cc.get_clean_instruction(inst.next)
        
def do(binary):
    follow(binary).dump(True)
