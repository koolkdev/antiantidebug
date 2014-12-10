import generate_opcodes

def generate_instructions(mode):
    if mode == 64:
        sp = "rsp"
        native = "%"
    else:
        sp = "esp"
        native = "#"
    def fix_operand(used, operand, size):
        s = operand.value.replace("=", sp).replace("^", native)
        if generate_opcodes.is_mem(operand):
            s = "%s %s" % (size.value, s)
        # little hackish code to fix arguments number
        s=s.replace("0x", "XX")
        for i in xrange(operand.args):
            s=s.replace(str(i), chr(i))
        for i in xrange(operand.args):
            s=s.replace(chr(i), str(used))
            used += 1
        s=s.replace("XX", "0x")
        return used, s
    instructions_file = open("instructions_%d.txt" % mode, "w")
    for opcode in generate_opcodes.iterate_opcodes(mode):
        line = "%s " % opcode.name
        if opcode.opcode.name != "label":
            line += "%s" % opcode.opcode.name
        if opcode.opcode.name == "push" and generate_opcodes.is_imm(opcode.operand1) and opcode.size1.size == 2:
            line += " word"
        used = 0
        if opcode.operand1 is not None:
            if opcode.opcode.name != "label":
                line += " "
            used, s = fix_operand(used, opcode.operand1, opcode.size1)
            line += "%s" % s
            if opcode.operand2 is not None:
                used, s = fix_operand(used, opcode.operand2, opcode.size2)
                line += ", %s" % s
                if opcode.operand3 is not None:
                    used, s = fix_operand(used, opcode.operand3, opcode.size3)
                    line += ", %s" % s
        instructions_file.write(line + "\n")
    instructions_file.close()
    
generate_instructions(32)
generate_instructions(64)