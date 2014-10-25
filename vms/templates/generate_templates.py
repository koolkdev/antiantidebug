ARGUMENTS = ["X", "Y", "Z", "A", "B", "C"]


# Some of the combinations may be wrong, but I don't care sooo much
# TODO: add mul/imul/div/idiv/bswap
# TODO: Use the new template generation
# TODO: ESP changes
# TODO: support div/mul for bytes/words
MOV_OPERAND = [("MOV", "mov")]
TWO_OPERANDS_MATH = [("ADD", "add"), ("SUB", "sub"), ("XOR", "xor"), ("AND", "and"), ("OR", "or"), ("BT", "bt"), ("BTR", "btr"), ("BTS", "bts"), ("BTC", "btc"), ("SBB", "sbb"), ("ADC", "adc")]
ONE_OPERAND_MATH = [("NEG", "neg"), ("NOT", "not")]
ONE_OPERAND_REG_ONLY = [("BSWAP", "bswap")]
ONE_OPERAND_MATH_FAKE_TWO = [("DEC", "dec"), ("INC", "inc")]
TWO_OPERANDS_COMPARE = [("CMP", "cmp"), ("TEST", "test")]
TWO_OPERANDS_MATH_FIRST_REGISTER = [("IMULTWO", "imul")]
IMULTHREE_GROUP = [("IMULTHREE", "imul")]
TWO_OPERANDS_SHL_SHR = [("SHL", "shl"), ("SHR", "shr"), ("SAR", "sar"), ("ROL", "rol"), ("ROR", "ror"), ("RCR", "rcr"), ("RCL", "rcl")]
MUL_IMUL = [("MUL", "mul"), ("IMUL", "imul")]
DIV_IDIV = [("DIV", "div"), ("IDIV", "idiv")]
MOVZX_MOVSX = [("MOVZX", "movzx"), ("MOVSX", "movsx")]
XCHG_GROUP = [("XCHG", "xchg")]
PUSHPOP_GROUP = [("PUSH", "push"), ("POP", "pop")]
LEA_GROUP = [("LEA", "lea") ]

def check_types_for_group_two_operands(first_type, second_type, third_type):
    if third_type != second_type:
        return False
    if first_type != second_type:
        return False
    if first_type in SPECIAL_TYPES or second_type in SPECIAL_TYPES:
        return False
    return True

def check_types_for_group_one_operand_not_byte(first_type, second_type, third_type):
    if third_type != second_type:
        return False
    if first_type != second_type:
        return False
    if first_type == TYPES[BYTE]:
        return False
    if first_type in SPECIAL_TYPES or second_type in SPECIAL_TYPES:
        return False
    return True

def check_args_for_group_two_operands(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand in SPECIALS or second_operand in SPECIALS:
        return False
    if first_operand in MEMORIES and second_operand in MEMORIES:
        return False
    if first_operand in CONSTANT:
        return False

    return True

def check_args_for_group_two_operands_mov(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand in SPECIALS or (second_operand in SPECIALS and second_operand[0] != "ESPFIXED"):
        return False
    if first_operand in MEMORIES and second_operand in MEMORIES:
        return False
    if first_operand in CONSTANT:
        return False

    return True
    
def check_args_for_group_one_operand(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand != None:
        return False
    if first_operand in SPECIALS:
        return False
    if first_operand in CONSTANT:
        return False
    return True
    
def check_args_for_group_one_operand_any(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand != None:
        return False
    if first_operand in SPECIALS:
        return False
    return True
    
def check_args_for_group_two_operands_first_register(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand in SPECIALS or second_operand in SPECIALS:
        return False
    if not first_operand in first_type[3]:
        return False
    
    return True
    
def check_args_for_group_two_operands_first_register_second_memory(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand in SPECIALS or second_operand in SPECIALS:
        return False
    if not first_operand in first_type[3]:
        return False
    if not second_operand in MEMORIES:
        return False
    return True

def check_types_for_group_shlshr(first_type, second_type, third_type):
    if third_type != second_type:
        return False
    if second_type != TYPES[BYTE]:
        return False
    if first_type in SPECIAL_TYPES or second_type in SPECIAL_TYPES:
        return False
    return True
    
def check_args_for_group_shlshr(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand in CONSTANT:
        return False
    if first_operand in SPECIALS:
        return False
    if second_operand in MEMORIES or (second_operand in second_type[3] and second_operand != TYPES[BYTE][3][BYTE_CL]):
        return False
    return True

def check_types_for_group_movzx_movsx(first_type, second_type, third_type):
    if third_type != second_type:
        return False
    if first_type[1] != second_type[1]:
        return False
    if first_type in SPECIAL_TYPES or not second_type in SPECIAL_TYPES:
        return False
    return True
    
# MOVZX is buggy in winlicense, since it reads dword instead a byte, so it can crash when reading from an address
# is it different in vmprotect? if it is, we will need to implement it in another way
def check_args_for_group_movzx_movsx(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand not in first_type[3]:
        return False
    if second_operand not in second_type[3] and second_operand not in MEMORIES:
        return False
    return True

def check_args_for_group_imulthree(first_operand, second_operand, third_operand, first_type, second_type, third_type): 
    if first_operand == None or second_operand == None or third_operand == None:
        return False
    if first_type in SPECIAL_TYPES or second_type in SPECIAL_TYPES or third_type in SPECIAL_TYPES:
        return False  
    if first_operand in CONSTANT or second_operand in CONSTANT or not third_operand in CONSTANT:
        return False
    if first_operand in MEMORIES:
        return False
    return True

def check_args_for_group_xchg(first_operand, second_operand, third_operand, first_type, second_type, third_type):
    if third_operand != None:
        return False
    if first_operand == None or second_operand == None:
        return False
    if first_operand in SPECIALS or second_operand in SPECIALS:
        return False
    if first_operand in MEMORIES and second_operand in MEMORIES:
        return False
    if first_operand in CONSTANT or second_operand in CONSTANT:
        return False
    return True
   
   
# TODO: Do a list of, so don't merge them
NONE = -1
FIRST_ARG = 1
SECOND_ARG = 2
THIRD_ARG = 4
POP_FIXED = 8
PUSH_FIXED = 16



GROUP = 0

DWORD = 0
WORD = 1
BYTE = 2

WORD_AS_DWORD = 3
BYTE_AS_DWORD = 4
BYTE_AS_WORD = 5

SEGMENTS = [("", ""),
            ("FS", "fs:")]

_MEMORIES = [("V", 1, "[|0x$0]", True),
            ("REGV", 1, "[|#0]", True),
            ("REGPLUSV", 2, "[|#0+0x$1]", True),
            ("REGREGV", 2, "[|#0+#1]", True),
            ("REGREGPLUSV", 3, "[|#0+#1+0x$2]", True),
            ("REGMULV", 2, "[|#0*0x$1]", True),
            ("REGMULPLUSV", 3, "[|#0*0x$1+0x$2]", True),
            ("REGMULREGV", 3, "[|#0*0x$1+#2]", True),
            ("REGMULREGPLUSV", 4, "[|#0*0x$1+#2+0x$3]", True),
            
            ("ESPV", 0, "[|esp]", False),
            ("ESPPLUSV", 1, "[|esp+0x$0]", False),
            ("REGESPV", 1, "[|#0+esp]", False),
            ("REGESPPLUSV", 2, "[|#0+esp+0x$1]", False),
            ("REGESPMULV", 2, "[|#0*0x$1+esp]", False),
            ("REGMULESPPLUSV", 3, "[|#0*0x$1+esp+0x$2]", False)]
            
MEMORIES = []        
for segment in SEGMENTS:
    for memory in _MEMORIES:
        MEMORIES.append((segment[0] + memory[0], memory[1], memory[2].replace("|", segment[1]), memory[3]))
        
CONSTANT = [("", 1, "0x$0", True)]

BYTE_CL = 2
        
TYPES = [("DWORD", "DWORD", "dword",
            [("REG", 1, "#0", True),
            ("ESP", 0, "esp", True),
            ("ESPFIXED", 0, "invalid", True)]),
        ("WORD", "WORD", "word",
            [("REG", 1, "@0", True),
            ("ESP", 0, "sp", True),
            ("ESPFIXED", 0, "invalid", True)]),
        ("BYTE", "BYTE", "byte", 
            [("REG", 1, "~0", True),
            ("REG2ND", 1, "!0", True),
            ("REG", 1, "cl", True)]),
        ("WORD", "DWORD", "word",
            [("REG", 1, "@0", True),
            ("ESP", 0, "sp", True)]),
        ("BYTE", "DWORD", "byte",
            [("REG", 1, "~0", True),
            ("ASBYTEREG2ND", 1, "!0", True)]),
        ("BYTE", "WORD", "byte",
            [("REG", 1, "~0", True),
            ("ASBYTEREG2ND", 1, "!0", True)])
        ]
         
         

SPECIAL_TYPES = [TYPES[WORD_AS_DWORD],
                 TYPES[BYTE_AS_DWORD],
                 TYPES[BYTE_AS_WORD]]
                 
SPECIALS = [TYPES[BYTE][3][BYTE_CL],
            TYPES[DWORD][3][2],
            TYPES[WORD][3][2]]

GROUPS = [
            ("MOV_OPERAND", MOV_OPERAND,
                [("PUSH", [SECOND_ARG]),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_two_operands,
                 check_args_for_group_two_operands_mov,
                 False),
            ("TWO_OPERANDS_MATH", TWO_OPERANDS_MATH,
                [("PUSH", [FIRST_ARG]),
                 ("PUSH", [SECOND_ARG | PUSH_FIXED]),
                 ("", GROUP),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_two_operands,
                 check_args_for_group_two_operands,
                 False),
            ("ONE_OPERAND_MATH", ONE_OPERAND_MATH,
                [("PUSH", [FIRST_ARG]),
                 ("", GROUP),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_two_operands,
                 check_args_for_group_one_operand,
                 False),
            ("ONE_OPERAND_MATH_FAKE_TWO", ONE_OPERAND_MATH_FAKE_TWO,
                [("PUSH", [FIRST_ARG]),
                 ("PUSHDWORD", "1"),
                 ("", GROUP),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_two_operands,
                 check_args_for_group_one_operand,
                 False),
            ("TWO_OPERANDS_COMPARE", TWO_OPERANDS_COMPARE,
                [("PUSH", [FIRST_ARG]),
                 ("PUSH", [SECOND_ARG | PUSH_FIXED]),
                 ("", GROUP)],
                 check_types_for_group_two_operands,
                 check_args_for_group_two_operands,
                 False),
            ("TWO_OPERANDS_MATH_FIRST_REGISTER", TWO_OPERANDS_MATH_FIRST_REGISTER,
                [("PUSH", [FIRST_ARG]),
                 ("PUSH", [SECOND_ARG | PUSH_FIXED]),
                 ("", GROUP),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_two_operands,
                 check_args_for_group_two_operands_first_register,
                 False),
            ("TWO_OPERANDS_SHL_SHR", TWO_OPERANDS_SHL_SHR,
                [("PUSH", [FIRST_ARG]),
                 ("PUSH", [SECOND_ARG | PUSH_FIXED]),
                 ("", GROUP),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_shlshr,
                 check_args_for_group_shlshr,
                 False),
            ("MOVZX_MOVSX", MOVZX_MOVSX,
                [("PUSH", [SECOND_ARG]),
                 ("PUSH", [FIRST_ARG | PUSH_FIXED]),
                 ("", GROUP),
                 ("POP", [FIRST_ARG | POP_FIXED])],
                 check_types_for_group_movzx_movsx,
                 check_args_for_group_movzx_movsx,
                 True),
            ("IMULTHREE_GROUP", IMULTHREE_GROUP,
                [("MOV", [FIRST_ARG, SECOND_ARG]),
                 ("IMULTWO", [FIRST_ARG, THIRD_ARG])],
                 check_types_for_group_two_operands,
                 check_args_for_group_imulthree,
                 False),
            ("XCHG_GROUP", XCHG_GROUP,
                [("PUSH", [FIRST_ARG]),
                 ("MOV", [FIRST_ARG, SECOND_ARG | PUSH_FIXED]),
                 ("POP", [SECOND_ARG | POP_FIXED])],
                 check_types_for_group_two_operands,
                 check_args_for_group_xchg,
                 False),
            # TODO: Add support for byte/word!!
            ("MUL_IMUL", MUL_IMUL,
                [("PUSHDWORDREG", "MY1"),
                 ("PUSH", [FIRST_ARG | PUSH_FIXED]),
                 ("", GROUP),
                 ("POPDWORDREG", "MY1"),
                 ("POPDWORDREG", "MY2")],
                 check_types_for_group_two_operands,
                 check_args_for_group_one_operand,
                 False),
            ("DIV_IDIV", DIV_IDIV,
                [("PUSHDWORDREG", "MY1"),
                 ("PUSHDWORDREG", "MY2"),
                 ("PUSH", [FIRST_ARG | PUSH_FIXED]),
                 ("", GROUP),
                 ("POPDWORDREG", "MY2"),
                 ("POPDWORDREG", "MY1")],
                 check_types_for_group_two_operands,
                 check_args_for_group_one_operand,
                 False),
            ("PUSHPOP_GROUP", PUSHPOP_GROUP,
                None,
                check_types_for_group_one_operand_not_byte,
                check_args_for_group_one_operand_any,
                False),
            ("LEA_GROUP", LEA_GROUP,
                None,
                check_types_for_group_one_operand_not_byte,
                check_args_for_group_two_operands_first_register_second_memory,
                False),
                ]

templates = []
JMPS = "JMP JA JNB JB JE JG JGE JL JLE JBE JNO JPO JNS JO JPE JS JNE JCXZ LOOP LOOPE".split(" ")

TOLOWEROPS = ["CLC", "CMC", "STD", "CLD", "STC", "STI", "PUSHF", "POPF"]

REPS = ["LODSB", "LODSW", "LODSD", "MOVSB", "MOVSW", "MOVSD", "STOSB", "STOSW", "STOSD"]
REPSE = ["CMPSB", "CMPSW", "CMPSD", "SCASB", "SCASW", "SCASD"]

instructions = [
"LABEL &0:"
]

for jmp in JMPS:
    instructions.append("%sLABEL %s &0" % (jmp, jmp.lower()))
    instructions.append("%s %s 0x$0" % (jmp, jmp.lower()))
    
for rep in REPS:
    instructions.append("%s %s" % (rep, rep.lower()))
    instructions.append("REP%s rep %s" % (rep, rep.lower()))
for rep in REPSE:
    instructions.append("%s %s" % (rep, rep.lower()))
    instructions.append("REPE%s rep %s" % (rep, rep.lower()))
    instructions.append("REPNE%s repe %s" % (rep, rep.lower()))

for op in TOLOWEROPS:
    instructions.append("%s %s" % (op, op.lower()))
    
groups = []
for first_type in TYPES:
    for second_type in TYPES:
        for third_type in TYPES:
            possibles_arg1 = MEMORIES + CONSTANT + first_type[3] + [None]
            possibles_arg2 = MEMORIES + CONSTANT + second_type[3] + [None]
            possibles_arg3 = MEMORIES + CONSTANT + third_type[3] + [None]
            group_possibles_arg1 = list(possibles_arg1)
            group_possibles_arg2 = list(possibles_arg2)
            group_possibles_arg3 = list(possibles_arg3)
            group_possibles_arg1 = list(set(group_possibles_arg1))
            group_possibles_arg2 = list(set(group_possibles_arg2))
            group_possibles_arg3 = list(set(group_possibles_arg3))
            for group in GROUPS:
                if group[3](first_type, second_type, third_type):
                    if group[5]:
                        type_name = first_type[0] + "_" + second_type[0]
                    else:
                        type_name = first_type[0]
                    group_code = group[0] + "_" + type_name + "\n"
                    group_code += " ".join([x[0] + type_name for x in group[1]])
                    groups.append(group_code)
                    for arg1 in group_possibles_arg1:
                        for arg2 in group_possibles_arg2:
                            for arg3 in group_possibles_arg3:
                                if group[4](arg1, arg2, arg3, first_type, second_type, third_type):
                                    # It is possible arguments
                                    if arg2 != None and arg2[0] != "":
                                        template_name_end = arg1[0] + "_" + arg2[0]
                                    else:
                                        template_name_end = arg1[0]
                                    template_script = ""
                                    has_group_name = False
                                    if group[2]:
                                        for template_line in group[2]:
                                            if isinstance(template_line[1], list):
                                                args = []
                                                first = True
                                                template_script += template_line[0]
                                                for arg in template_line[1]:
                                                    if arg & FIRST_ARG:
                                                        type = first_type
                                                        arg_obj = arg1
                                                        args_before = 0
                                                    elif arg & SECOND_ARG:
                                                        type = second_type
                                                        arg_obj = arg2
                                                        args_before = arg1[1]
                                                    elif arg & THIRD_ARG:
                                                        type = third_type
                                                        arg_obj = arg3
                                                        args_before = arg1[1] + arg2[1]
                                                        
                                                    if first:
                                                        template_script += type[1]
                                                        first = False
                                                    elif not (arg & THIRD_ARG):
                                                        template_script += "_"
                                                    
                                                    #if pushes and arg_obj[0] == "ESPV" or arg_obj[0] == "ESPPLUSV" or arg_obj[0] == "ESP:
                                                    args += [ARGUMENTS[i + args_before] for i in xrange(arg_obj[1])]
                                                    
                                                    template_arg = arg_obj[0]
                                                     
                                                    if (arg & PUSH_FIXED) or (arg & POP_FIXED):
                                                        for segment in SEGMENTS:
                                                            if arg_obj[0] == segment[0] + "ESPV":
                                                                template_arg = segment[0] + "ESPPLUSV"
                                                                args += [("F%d" % args_before)]
                                                                break
                                                            elif arg_obj[0] == segment[0] + "ESPPLUSV":
                                                                template_arg = segment[0] + "ESPPLUSFIXEDV"
                                                                args += [("F%d" % args_before)]
                                                                break
                                                            elif arg_obj[0] == segment[0] + "REGESPV":
                                                                template_arg = segment[0] + "REGESPPLUSV"
                                                                args += [("F%d" % args_before)]
                                                                break
                                                            elif arg_obj[0] == segment[0] + "REGESPPLUSV":
                                                                template_arg = segment[0] + "REGESPPLUSFIXEDV"
                                                                args += [("F%d" % args_before)]
                                                                break
                                                            elif arg & PUSH_FIXED:
                                                                if arg_obj[0] == segment[0] + "ESP":
                                                                    template_arg = segment[0] + "ESPFIXED"
                                                                    break
                                                    
                                                    template_script += template_arg
                                                    
                                                    """
                                                        # TODO: Count pushs
                                                        if template_line[0] == "PUSH" and group[2].index(template_line) == 1 and (arg2[0] == "ESPV" or arg2[0] == "ESPPLUSV"): # Fix for the case esp releated 
                                                            if arg2[0] == "ESPV":
                                                                line = line[:-1] + "PLUSV 4"
                                                            else:
                                                                line += "FIXED"
                                                        template_script += line
                                                        if arg2[2] != 0:
                                                            template_script += " " + " ".join([ARGUMENTS[arg1[2] + i] for i in xrange(arg2[2])])
                                                        
                                                    """
                                                if args:
                                                    template_script += " " + " ".join(args)
                                                template_script += "\n"
                                            elif template_line[1] == GROUP:
                                                template_script += "&I=^" + group[0] + "_" + type_name + "\n"
                                                has_group_name = True
                                            else:
                                                # ??
                                                template_script += template_line[0] + " " + template_line[1] + "\n"
                                        template_script += "=>\n"
                                        if has_group_name:
                                            template_script += "*I*" + template_name_end
                                        else:
                                            assert len(group[1]) == 1
                                            template_script += group[1][0][0] + type_name + template_name_end
                                        
                                        if arg1[1] != 0:
                                            template_script += " " + " ".join([ARGUMENTS[i] for i in xrange(arg1[1])])
                                        if arg2 != None and arg2[1] != 0:
                                            template_script += " " + " ".join([ARGUMENTS[arg1[1] + i] for i in xrange(arg2[1])])
                                        if arg3 != None and arg3[1] != 0:
                                            template_script += " " + " ".join([ARGUMENTS[arg1[1] + arg2[1] + i] for i in xrange(arg3[1])])
                                    #print "================"
                                    #print template_script
                                    arg1res = arg1[2]
                                    #print arg1res
                                    if arg2 == None:
                                        arg2res = None
                                    else:
                                        arg2res = arg2[2].replace("0x","XX")
                                        for i in xrange(arg2[1]):
                                            arg2res = arg2res.replace(str(i), chr(i))
                                        for i in xrange(arg2[1]):
                                            arg2res = arg2res.replace(chr(i), str(i+arg1[1]))
                                        arg2res = arg2res.replace("XX","0x")
                                    if arg3 == None:
                                        arg3res = None
                                    else:
                                        arg3res = arg3[2].replace("0x","XX")
                                        for i in xrange(arg3[1]):
                                            arg3res = arg3res.replace(str(i), chr(i))
                                        for i in xrange(arg3[1]):
                                            arg3res = arg3res.replace(chr(i), str(i+arg1[1]+arg2[1]))
                                        arg3res = arg3res.replace("XX","0x")
                                    if arg1 in MEMORIES:
                                        arg1res = first_type[2] + " " + arg1res
                                    if arg2 in MEMORIES:
                                        arg2res = second_type[2] + " " + arg2res
                                    if arg3 in MEMORIES:
                                        arg3res = third_type[2] + " " + arg3res
                                    for instruction in group[1]:
                                        instruction_line = instruction[1]
                                        if arg1res != None:
                                            instruction_line += " " + arg1res
                                            if arg2res != None:
                                                instruction_line += ", " + arg2res
                                                if arg3res != None:
                                                    instruction_line += ", " + arg3res
                                                   
                                        instruction_line = instruction[0] + type_name + template_name_end + " " + instruction_line
                                        instructions.append(instruction_line)
                                        #print instruction_line
                                    #if group[6](arg1, arg2):
                                    if template_script:
                                        templates.append(template_script)
    
                    
templates_file = open(r"files\ag_templates.txt", "wb")
# Generate templates
templates_file.write(("\n".join(groups) + "\n\n" + "\n\n".join(templates)).replace("\n","\r\n"))


instructions_file = open("ag_instructions.txt", "wb")
# Generate instructions...
instructions_file.write("\n".join(instructions).replace("\n","\r\n"))
