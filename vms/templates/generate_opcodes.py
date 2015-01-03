from collections import namedtuple

Operand = namedtuple("Operand", ["name", "args", "value"])

# Native reg: ^
# Byte ~
# Byte high: !
# Word: @
# Dword: #
# Qword %
# Immediate; $
# = - native sp
# Label: &

# TODO:
# Generate mov/push segs

LABEL = [Operand("LABEL", 1, "&0")]
LABEL_DEF = [Operand("LABEL", 1, "&0:")]

SEGMENTS = [("", ""),
            ("FS", "fs:"),
            ("GS", "gs:")]

ADDRESSES = [Operand("IMM", 1, "[0x$0]"),
            Operand("RELIMM", 1, "[?0x$0]"),
            Operand("REG", 1, "[^0]"),
            Operand("REGIMM", 2, "[^0+0x$1]"),
            Operand("REGRELIMM", 2, "[^0+?0x$1]"),
            Operand("REGREG", 2, "[^0+^1]"),
            Operand("REGREGIMM", 3, "[^0+^1+0x$2]"),
            Operand("REGREGRELIMM", 3, "[^0+^1+?0x$2]"),
            Operand("REGMUL", 2, "[^0*$1]"),
            Operand("REGMULIMM", 3, "[^0*$1+0x$2]"),
            Operand("REGMULRELIMM", 3, "[^0*$1+?0x$2]"),
            Operand("REGREGMUL", 3, "[^0+^1*$2]"),
            Operand("REGREGMULIMM", 4, "[^0+^1*$2+0x$3]"),
            Operand("REGREGMULRELIMM", 4, "[^0+^1*$2+?0x$3]"),
            
            Operand("SP", 0, "[=]"),
            Operand("SPIMM", 1, "[=+0x$0]"),
            Operand("SPRELIMM", 1, "[=+?0x$0]"),
            Operand("SPREG", 1, "[=+^0]"),
            Operand("SPREGIMM", 2, "[=+^0+0x$1]"),
            Operand("SPREGRELIMM", 2, "[=+^0+?0x$1]"),
            Operand("SPREGMUL", 2, "[=+^0*$1]"),
            Operand("SPREGMULIMM", 3, "[=+^0*$1+0x$2]"),
            Operand("SPREGMULRELIMM", 3, "[=+^0*$1+?0x$2]")]
            
MEMORIES = []        
for segment in SEGMENTS:
    for memory in ADDRESSES:
        MEMORIES.append(Operand("MEM" + segment[0] + memory.name, memory.args, segment[1] + memory.value))
        
IMMEDIATE = [Operand("IMM", 1, "0x$0")]
REALLOC_IMMEDIATE = [Operand("RELIMM", 1, "?0x$0")]

Size = namedtuple("Size", ["name", "value", "size"])

SIZES = [Size("BYTE", "byte", 1),
         Size("WORD", "word", 2),
         Size("DWORD", "dword", 4),
         Size("QWORD", "qword", 8),
         None]
         
REGS = {1: [Operand("REG", 1, "~0"),
            Operand("REGHIGH", 1, "!0"),
            Operand("REG", 0, "cl"), # TODO: Or should we call it cl?
            Operand("SP", 0, "spl")],
        2: [Operand("REG", 1, "@0"),
            Operand("SP", 0, "sp")],
        4: [Operand("REG", 1, "#0"),
            Operand("SP", 0, "esp")],
        8: [Operand("REG", 1, "%0"),
            Operand("SP", 0, "rsp")]}
            
def is_cl(op):
    return op in REGS[1] and op.value == "cl"

def is_reg(op):
    return (op in REGS[1] and not is_cl(op)) or op in REGS[2] or op in REGS[4] or op in REGS[8]    

def is_valid_reg(mode, size, op):
    if not is_reg(op):
        return False
    if mode == 32 and op.name == "SP" and size.size == 1:
        return False
    return True
    
def is_mem(op):
    return op in MEMORIES

def is_valid_mem(mode, size, op):
    if not is_mem(op):
        return False
    if mode == 64 and "RELIMM" in op.name and op.name != "RELIMM" and "MEMRELIMM" not in op.name:
        return False
    return True

def is_imm(op):
    return op in IMMEDIATE

def is_relimm(op):
    return op in REALLOC_IMMEDIATE

def is_valid_relimm(mode, size, op):
    return mode == 32 and is_relimm(op) and size.size == 4
    
def is_valid_size(mode, size):
    return not (mode == 32 and size.size == 8)
    
def check_two_operands_sizes(mode, size1, size2, size3):
    if size2 is None or size3 is not None:
        return False
    if size1 != size2:
        return False
    return is_valid_size(mode, size1)
    
def check_two_operands_not_byte(mode, size1, size2, size3):
    if not check_two_operands_sizes(mode, size1, size2, size3):
        return False
    return size1.size != 1
    
def check_one_operand_size(mode, size1, size2, size3):
    if size1 is None or size2 is not None:
        return False
    return is_valid_size(mode, size1)
       
def check_one_operand_size_not_byte(mode, size1, size2, size3):
    if not check_one_operand_size(mode, size1, size2, size3):
        return False
    return size1.size != 1
       
def check_one_operand_size_byte(mode, size1, size2, size3):
    if not check_one_operand_size(mode, size1, size2, size3):
        return False
    return size1.size == 1
    
def check_none_operands(mode, size1, size2, size3):
    return size1 is None
    
def check_none_operands_and_32(mode, size1, size2, size3):
    return size1 is None and mode == 32

def check_none_operands_and_64(mode, size1, size2, size3):
    return size1 is None and mode == 64
    
def check_two_operands_types(mode, op1, op2, op3, size1, size2, size3):
    if not is_valid_reg(mode, size1, op1) and not is_valid_mem(mode, size1, op1):
        return False
    if not is_valid_reg(mode, size2, op2) and not is_valid_mem(mode, size2, op2) and not is_imm(op2) and not is_valid_relimm(mode, size2, op2):
        return False
    if is_mem(op1) and is_mem(op2):
        return False
    return True
    
def check_one_operand_type(mode, op1, op2, op3, size1, size2, size3):
    if not is_valid_reg(mode, size1, op1) and not is_valid_mem(mode, size1, op1):
        return False
    return True
    
def check_one_operand_type_any(mode, op1, op2, op3, size1, size2, size3):
    if not is_valid_reg(mode, size1, op1) and not is_valid_mem(mode, size1, op1) and not is_imm(op1) and not is_valid_relimm(mode, size1, op1):
        return False
    return True
    
def check_one_operand_type_imm(mode, op1, op2, op3, size1, size2, size3):
    return is_imm(op1)
    
def check_one_operand_reg_type(mode, op1, op2, op3, size1, size2, size3):
    if not is_valid_reg(mode, size1, op1):
        return False
    return True
    
def check_multwo_types(mode, op1, op2, op3, size1, size2, size3):
    if not is_valid_reg(mode, size1, op1):
        return False
    if not is_valid_reg(mode, size2, op2) and not is_valid_mem(mode, size2, op2) and not is_imm(op2):
        return False
    return True
    
def check_three_operands_not_byte(mode, size1, size2, size3):
    if size3 is None:
        return False
    if size1.size == 1:
        return False
    if size1.size != size2.size or size1.size != size3.size:
        return False
    return is_valid_size(mode, size1)
    
def check_multhree_types(mode, op1, op2, op3, size1, size2, size3):
    if not check_multwo_types(mode, op1, op2, op3, size1, size2, size3):
        return False
    if not is_imm(op3):
        return False
    return True
    
def check_shlshr_sizes(mode, size1, size2, size3):
    if size2 is None or size3 is not None:
        return False
    if size2.size != 1:
        return False
    return is_valid_size(mode, size1)
    
def check_shlshr_types(mode, op1, op2, op3, size1, size2, size3):
    if not is_valid_reg(mode, size1, op1) and not is_valid_mem(mode, size1, op1):
        return False
    if not is_imm(op2) and not is_cl(op2):
        return False
    return True
    
def check_movzx_movsx_sizes(mode, size1, size2, size3):
    if size2 is None or size3 is not None:
        return False
    if size1.size <= size2.size:
        return False
    if size2.size == 4:
        return False
    return is_valid_size(mode, size1)

def check_xchg_types(mode, op1, op2, op3, size1, size2, size3):
    if not check_two_operands_types(mode, op1, op2, op3, size1, size2, size3):
        return False
    if not is_valid_reg(mode, size2, op2) and not is_valid_mem(mode, size2, op2):
        return False  
    return True

def check_stack_sizes(mode, size1, size2, size3):
    if size1 is None or size2 is not None:
        return False
    if size1.size == 2:
        return True
    return size1.size == (mode >> 3)

def check_lea_types(mode, op1, op2, op3, size1, size2, size3):
    return is_valid_reg(mode, size1, op1) and op2 in ADDRESSES and (mode != 64 or "RELIMM" not in op2.name or op2.name == "RELIMM")

def check_jmps_sizes(mode, size1, size2, size3):
    if size1 is None or size2 is not None:
        return False
    return size1.size == (mode >> 3)

def check_jmp_types(mode, op1, op2, op3, size1, size2, size3):
    return is_valid_reg(mode, size1, op1) or is_valid_mem(mode, size1, op1) or is_imm(op1) or is_relimm(op1) or op1 in LABEL

def check_jcc_types(mode, op1, op2, op3, size1, size2, size3):
    return is_imm(op1) or is_relimm(op1) or op1 in LABEL

def check_label_type(mode, op1, op2, op3, size1, size2, size3):
    return op1 in LABEL_DEF
    

Opcode = namedtuple("Opcode", ["name", "format", "check_sizes", "check_types"])

OPCODES = []

OPCODES.extend

# ANY ANY
TWO_OPERANDS = ["mov", "add", "sub", "xor", "and", "or", "sbb", "adc", "cmp", "test"]
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{TYPE1}_{TYPE2}" % x.upper(), check_two_operands_sizes, check_two_operands_types) for x in TWO_OPERANDS])
# NOT BYTE
BT_MATH = ["bt", "btr", "bts", "btc"]
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{TYPE1}_{TYPE2}" % x.upper(), check_two_operands_not_byte, check_two_operands_types) for x in BT_MATH])
# ONE OPERAND
ONE_OPERAND = ["neg", "not", "dec", "inc", "mul", "imul", "div", "idiv"]
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{TYPE1}" % x.upper(), check_one_operand_size, check_one_operand_type) for x in ONE_OPERAND])
# ONE OPERAND REG NOT BYTE
OPCODES.extend([Opcode("bswap", "BSWAP_{SIZE1}_{TYPE1}", check_one_operand_size_not_byte, check_one_operand_reg_type)])
# NOT BYTE, FIRST REGISTER, SECOND NOT IMMEDIATE
OPCODES.extend([Opcode("imul", "IMUL_{SIZE1}_{TYPE1}_{TYPE2}", check_two_operands_not_byte, check_multwo_types)])
# NOT BYTE, FIRST REGISTER, SECOND NOT IMMEDIATE, THIRD IMMEDIATE
OPCODES.extend([Opcode("imul", "IMUL_{SIZE1}_{TYPE1}_{TYPE2}_{TYPE3}", check_three_operands_not_byte, check_multhree_types)])
# SECOND CL/IMM
TWO_OPERANDS_SHL_SHR = ["shl", "shr", "sar", "rol", "ror", "rcr", "rcl"]
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{TYPE1}_{TYPE2}" % x.upper(), check_shlshr_sizes, check_shlshr_types) for x in TWO_OPERANDS_SHL_SHR])
# DIFFERENT SIZES, FIRST REGISTER, SECOND NOT IMMEDIATE
MOVZX_MOVSX = ["movzx", "movsx"]
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{SIZE2}_{TYPE1}_{TYPE2}" % x.upper(), check_movzx_movsx_sizes, check_two_operands_types) for x in MOVZX_MOVSX])
# NOT IMMIDATE
OPCODES.extend([Opcode("xchg", "XCHG_{SIZE1}_{TYPE1}_{TYPE2}", check_two_operands_sizes, check_xchg_types)])
# JUST WORD/NATIVE
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{TYPE1}" % x.upper(), check_stack_sizes, check_one_operand_type_any) for x in ["push"]])
OPCODES.extend([Opcode(x, "%s_{SIZE1}_{TYPE1}" % x.upper(), check_stack_sizes, check_one_operand_type) for x in ["pop"]])
# FIRST REG (NO BYTE), SECOND ADDRESS
OPCODES.extend([Opcode("lea", "LEA_{SIZE1}_{TYPE1}_{TYPE2}", check_two_operands_not_byte, check_lea_types)])
# OPERAND REG/MEMORY/IMMEDIATE or LABEL
JMP_CALL = ["jmp", "call"]
OPCODES.extend([Opcode(x, "%s_{TYPE1}" % x.upper(), check_jmps_sizes, check_jmp_types) for x in JMP_CALL])
# OPERAND LABEL_DEF
OPCODES.extend([Opcode("label", "LABEL", check_jmps_sizes, check_label_type)])
# OPERAND IMMIDATE OR LABEL
CC_JMPS = ["ja", "jae", "jb", "jbe", "jz", "jg", "jge", "jl", "jle", "jnz", "jno", "jnp", "jns", "jo", "jp" ,"js", "jcxz", "loop", "loope", "loopne"]
OPCODES.extend([Opcode(x, "%s_{TYPE1}" % x.upper(), check_jmps_sizes, check_jcc_types) for x in CC_JMPS])
# NONE OPERANDS
SIMPLE_OPS = ["clc", "cmc", "std", "cld", "stc", "std", "cli", "sti", "pushf", "popf", "leave", "ret", "nop"]
OPCODES.extend([Opcode(x, "%s" % x.upper(), check_none_operands, None) for x in SIMPLE_OPS])
OPCODES.extend([Opcode(x, "%s" % x.upper(), check_none_operands_and_32, None) for x in ["pusha", "popa"]])
# RET ..
OPCODES.extend([Opcode("ret", "RET_{TYPE1}", check_one_operand_size_byte, check_one_operand_type_imm)])
# NONE OPERANDS
REPS = []
SIZES_LETTERS = "bwdq"
for op in ["lods"]:
        REPS.append(op)
for op in ["movs", "stos"]:
        REPS.append(op)
        REPS.append("rep %s" % op)
for op in ["cmps", "scas"]:
        REPS.append(op)
        REPS.append("repe %s" % op)
        REPS.append("repne %s" % op)
for size in SIZES_LETTERS:
    if size == "q":
        OPCODES.extend([Opcode("%s%s" % (x, size), "%s%s" % (x.replace(" ", "_").upper(), size.upper()), check_none_operands_and_64, None) for x in REPS])
    else:
        OPCODES.extend([Opcode("%s%s" % (x, size), "%s%s" % (x.replace(" ", "_").upper(), size.upper()), check_none_operands, None) for x in REPS])

OpcodeInfo = namedtuple("OpcodeInfo", ["name", "opcode", "size1", "size2", "size3", "operand1", "operand2", "operand3"])

def iterate_opcodes(mode):
    names0 = {}
    for size1 in SIZES:
        names1 = names0.copy()
        if size1 is not None:
            names1["SIZE1"] = size1.name
        if size1 is None:
            nsizes2 = [None]
        else:
            nsizes2 = SIZES
        for size2 in nsizes2:
            names2 = names1.copy()
            if size2 is not None:
                names2["SIZE2"] = size2.name
            if size2 is None:
                nsizes3 = [None]
            else:
                nsizes3 = SIZES
            for size3 in nsizes3:
                names3 = names2.copy()
                if size3 is not None:
                    names3["SIZE3"] = size3.name
                if size1 is None:
                    args1 = [None]
                else:
                    args1 = REGS[size1.size] + MEMORIES + IMMEDIATE + REALLOC_IMMEDIATE + ADDRESSES + LABEL + LABEL_DEF
                if size2 is None:
                    args2 = [None]
                else:
                    args2 = REGS[size2.size] + MEMORIES + IMMEDIATE + REALLOC_IMMEDIATE + ADDRESSES + LABEL + LABEL_DEF
                if size3 is None:
                    args3 = [None]
                else:
                    args3 = REGS[size3.size] + MEMORIES + IMMEDIATE + REALLOC_IMMEDIATE + ADDRESSES + LABEL + LABEL_DEF
                for opcode in OPCODES:
                    if opcode.check_sizes is None or opcode.check_sizes(mode, size1, size2, size3):
                        for arg1 in args1:
                            names4 = names3.copy()
                            if arg1 is not None:
                                names4["TYPE1"] = arg1.name
                            for arg2 in args2:
                                names5 = names4.copy()
                                if arg2 is not None:
                                    names5["TYPE2"] = arg2.name
                                for arg3 in args3:
                                    names6 = names5.copy()
                                    if arg3 is not None:
                                        names6["TYPE3"] = arg3.name
                                    if opcode.check_types is None or opcode.check_types(mode, arg1, arg2, arg3, size1, size2, size3):
                                        yield OpcodeInfo(opcode.format.format(**names6), opcode, size1, size2, size3, arg1, arg2, arg3)

                                    
                                    
                                