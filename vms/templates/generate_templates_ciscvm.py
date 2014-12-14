import generate_opcodes
from collections import namedtuple

OperandPos = namedtuple("OperandPos", ["pos", "operand"])
ARGS = ["X", "Y", "Z", "A", "B", "C"]
def generate_templates(mode):
    templates_file = open(r"files\codevirtualizer\cisc\cisc_templates_%d.txt" % mode, "w")
    mov_templates_file = open(r"files\codevirtualizer\cisc\cisc_templates_mov_%d.txt" % mode, "w")
    
    templates_file.write("OPTION RUN_ONCE\n\n")
    mov_templates_file.write("OPTION RUN_ONCE\n\n")
    
    # Sometimes MOVZX_DWORD_BYTE can be detected as MOVZX_QWORD_BYTE because of the obfuscator, so this is for fixing that
    if mode == 64:
        templates_file.write("DEFINE_GROUP _MOVZX_DWORD_BYTE MOVZX_DWORD_BYTE MOVZX_QWORD_BYTE\n\n")
    
    for opcode in generate_opcodes.iterate_opcodes(mode):
        operand1 = OperandPos(1, opcode.operand1)
        operand2 = OperandPos(2, opcode.operand2)
        operand3 = OperandPos(3, opcode.operand3)
        operation = opcode.name.split("_")[0]
        if operation in ("MOV"):
            # PUSH SIZE2 ARG2
            # POP SIZE1 ARG1
            instructions = [(["PUSH", opcode.size2, operand2], None),
                            (["POP", opcode.size1, operand1], None)]
        elif operation in ("ADD", "SUB", "XOR", "AND", "OR", "BT", "BTR", "BTS", "BTC", "SBB", "ADC", "SHL", "SHR", "SAR", "ROL", "ROR", "RCR", "RCL", "IMULTWO"):
            # PUSH SIZE1 ARG1
            # PUSH SIZE2 ARG2
            # OP SIZE1
            # POP SIZE1 ARG1
            instructions = [(["PUSH", opcode.size1, operand1], None),
                            (["PUSH", opcode.size2, operand2], None),
                            ([opcode.opcode, opcode.size1], None),
                            (["POP", opcode.size1, operand1], None)]
        elif operation in ("MOVSX", "MOVZX"):
            # PUSH SIZE1 ARG2
            # PUSH SIZE1 ARG1
            # OP SIZE1,SIZE2
            # POP SIZE1 ARG1
            instructions = [(["PUSH", opcode.size1, operand2], None),
                            (["PUSH", opcode.size1, operand1], None),
                            ([opcode.opcode, opcode.size1, opcode.size2], None),
                            (["POP", opcode.size1, operand1], None)]
        elif operation in ("NEG", "NOT", "BSWAP"):
            # PUSH SIZE1 ARG1
            # OP SIZE1
            # POP_MATH_RESULT
            instructions = [(["PUSH", opcode.size1, operand1], None),
                            ([opcode.opcode, opcode.size1], None),
                            (["POP_MATH_RESULT"], None)]
        elif operation in ("CMP", "TEST"):
            # CMP/TEST
            # PUSH SIZE1 ARG1
            # PUSH SIZE2 ARG2
            # OP SIZE1
            instructions = [(["PUSH", opcode.size1, operand1], None),
                            (["PUSH", opcode.size2, operand2], None),
                            ([opcode.opcode, opcode.size1], None)]
        elif operation in ("INC", "DEC"):
            # PUSH SIZE1 ARG1
            # PUSH SIZE1 IMM(0x1)
            # OP SIZE1
            # POP SIZE1 ARG1
            instructions = [(["PUSH", opcode.size1, operand1], None),
                            (["PUSH", opcode.size1, "IMM"], ["0x1"]),
                            ([opcode.opcode, opcode.size1], None),
                            (["POP", opcode.size1, operand1], None)]
        elif operation in ("XCHG"):
            # All the things that mov will fail to operate on
            if (generate_opcodes.is_mem(opcode.operand2) and "MEMSP" in opcode.operand2.name and "IMM" in opcode.operand2.name) or \
                (generate_opcodes.is_reg(opcode.operand2) and opcode.operand2.name == "SP") or \
                (generate_opcodes.is_reg(opcode.operand2) and opcode.size2.size == 4 and mode == 64): # This because in xchg there isn't ZERO_HIGH_STACK, so it won't be changed to mov
                # Need to fix memory.. it didn't collapse to mov
                # PUSH SIZE1 ARG1
                # PUSH SIZE2 ARG2
                # POP SIZE1 ARG1
                # POP SIZE2 ARG2
                instructions = [(["PUSH", opcode.size1, operand1], None),
                                (["PUSH", opcode.size2, operand2], None),
                                (["POP", opcode.size1, operand1], None),
                                (["POP", opcode.size2, operand2], None)]
            else:
                # PUSH SIZE1 ARG1
                # MOV SIZE1 ARG1 ARG2
                # POP SIZE2 ARG2
                instructions = [(["PUSH", opcode.size1, operand1], None),
                                (["MOV", opcode.size1, operand1, operand2], None),
                                (["POP", opcode.size2, operand2], None)]
        elif operation in ("LEA"):
            # PUSH_ADDRESS ARG2
            # POP SIZE1 ARG1
            instructions = [(["PUSH", "ADDRESS", operand2], None),
                            (["POP", opcode.size1, operand1], None)]
        elif operation in ("MUL", "IMUL"):
            # PUSH SIZE1 REG X
            # PUSH SIZE1 ARG1
            # OP SIZE1
            # POP SIZE1 REG X 
            # STACK_POP SIZE1 REG[HIGH if byte] X
            instructions = [(["PUSH", opcode.size1, "REG"], ["ARG1"]),
                            (["PUSH", opcode.size1, operand1], None),
                            ([opcode.opcode, opcode.size1], None),
                            (["POP", opcode.size1, "REG"], ["ARG1"])]
            if opcode.size1.size == 1:
                instructions.append((["STACK", "POP", opcode.size1, "REGHIGH"], ["ARG1"]))
            else:
                instructions.append((["STACK", "POP", opcode.size1, "REG"], ["ARG2"]))
        elif operation in ("DIV", "IDIV"):
            # STACK_PUSH [SIZE1 if byte/word] X
            # PUSH SIZE1 REG Y
            # PUSH SIZE1 ARG1 
            # OP SIZE1
            # POP SIZE1 REG Y 
            # STACK_POP SIZE1 REG[HIGH if byte] X
            if opcode.size1.size <= 2:
                instructions = [(["STACK", "PUSH", opcode.size1, "REG"], ["ARG1"])]
            else:
                instructions = [(["STACK", "PUSH", "REG"], ["ARG1"])]
            instructions += [(["PUSH", opcode.size1, "REG"], ["ARG2"]),
                            (["PUSH", opcode.size1, operand1], None),
                            ([opcode.opcode, opcode.size1], None),
                            (["POP", opcode.size1, "REG"], ["ARG2"])]
            if opcode.size1.size == 1:
                instructions.append((["STACK", "POP", opcode.size1, "REGHIGH"], ["ARG1"]))
            else:
                instructions.append((["STACK", "POP", opcode.size1, "REG"], ["ARG1"]))
        elif operation in ("IMULTHREE"):
            # MOV SIZE1 ARG1 ARG2
            # IMULTWO SIZE1 ARG1 ARG3
            instructions = [(["MOV", opcode.size1, operand1, operand2], None),
                            (["IMULTWO", opcode.size1, operand1, operand3], None)]
        else:
            continue
        
        template_lines = []
        stack_pos = 0
        for inst in instructions:
            line = ""
            args = []
            is_push = False
            is_pop = False
            is_mov = False
            op_size = None
            ops = 0
            for part in inst[0]:
                part_value = "x"
                if type(part) is str:
                    part_value = part
                elif type(part) is generate_opcodes.Opcode:
                    part_value = operation
                elif type(part) is generate_opcodes.Size:
                    part_value = part.name
                elif type(part) is OperandPos:
                    ops += 1
                    part_value = part.operand.name
                    s = 0
                    if part.pos > 1:
                        s += opcode.operand1.args
                        if part.pos > 2:
                            s += opcode.operand2.args
                    args.extend([ARGS[s+i] for i in xrange(part.operand.args)])
                    if stack_pos != 0 and (is_push or (is_mov and ops == 2)):
                        if "MEMSP" in part_value:
                            if part_value.endswith("IMM"):
                                part_value += "_FIXED"
                            else:
                                part_value += "IMM"
                            args.append("0x%x" % stack_pos)
                        elif part_value == "SP":
                            part_value += "_FIXED"
                else:
                    assert False
                
                if part_value == "PUSH":
                    assert not is_push and not is_pop and not is_mov
                    is_push = True
                elif part_value == "POP":
                    assert not is_push and not is_pop and not is_mov
                    is_pop = True
                elif part_value == "MOV":
                    assert not is_push and not is_pop and not is_mov
                    is_mov = True
                elif (is_push or is_pop) and part_value in ("BYTE", "WORD", "DWORD", "QWORD"):
                    assert op_size is None
                    if part_value == "BYTE":
                        op_size = 1
                    elif part_value == "WORD":
                        op_size = 2
                    elif part_value == "DWORD":
                        op_size = 4
                    elif part_value == "QWORD":
                        op_size = 8 
                if line:
                    line += "_"
                line += part_value
                
            if inst[1] is not None:
                assert not args
                args = inst[1]
            org_line = line
            if mode == 64:
                line = line.replace("PUSH_DWORD_SP", "PUSH_QWORD_SP")
                line = line.replace("POP_DWORD_SP", "POP_QWORD_SP")
                if line == "MOVZX_DWORD_BYTE":
                    line = "^_MOVZX_DWORD_BYTE" # The group we defined earlier
                        
            template_lines.append((line, args))
            if mode == 64 and operation != "XCHG":
                if line == "POP_DWORD_REG":
                    template_lines.append(("STACK_ZERO_REG_HIGH_DWORD", args))
                elif org_line == "POP_DWORD_SP":
                    template_lines.append(("STACK_ZERO_SP_HIGH_DWORD", args))
                
                
            if op_size is None or op_size > 2:
                op_size = mode >> 3
            elif op_size == 1:
                op_size = 2
            if is_push:
                stack_pos += op_size
            elif is_pop:
                stack_pos -= op_size
        
        if operation == "MOV":
            file = mov_templates_file
        else:
            file = templates_file
        file.write("DEFINE_TEMPLATE\n")
        for line, args in template_lines:
            file.write(line)
            for arg in args:
                file.write(" ")
                file.write(arg)
            file.write("\n")
        file.write("=>\n")
        t = 0
        if opcode.operand1 is not None:
            t += opcode.operand1.args
            if opcode.operand2 is not None:
                t += opcode.operand2.args
                if opcode.operand3 is not None:
                    t += opcode.operand3.args
        file.write(opcode.name)
        for i in xrange(t):
            file.write(" ")
            file.write(ARGS[i])
        file.write("\n\n")
        #print template_lines
    templates_file.close()
    mov_templates_file.close()
    
generate_templates(32)
generate_templates(64)