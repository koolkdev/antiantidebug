from common_handlers import *
import tiger_handlers
import fish_handlers

def create_string_from_params(name, vars, state_params, global_params, arch):
    ns = name
    for var in re.findall("\{([\w:]+)\}", name):
        t, n = var.split(":")
        if t == "S" or t == "SS": # Size [stack]
            nvar = None
            for var_name, value in global_params.iteritems():
                if var_name.startswith("SIZE_") and value == state_params[n]:
                    nvar = var_name[len("SIZE_"):]
                    break
            if t == "SS":
                if nvar != "WORD":
                    nvar = arch.translate("{SU}")
        elif t == "T" or t == "AT": # [Arg] type
            nvar = state_params[n]
            if t == "T" and n == "DST_TYPE" and not (name.startswith("POP_") or name.startswith("PUSH_")):
                # If should have store result right after
                assert state_params["DST_TYPE"] == state_params["DST_OFFSET_TYPE"] and state_params["DST_VALUE"] == state_params["DST_OFFSET_VALUE"]
            if t == "AT" and nvar == "MEMVAR":
                nvar = "VAR"
        elif t == "O": # Operation
            nvar = vars[n]
        else:
            raise Exception("Invalid var: %s" % var)
        ns = ns.replace("{%s}" % var, nvar)
    return ns

def create_dolphin_handler_reader_class(name, params=[], vars=[]):
    class GenericHandlerReader(HandlerReader):
        def get_name(self):
            return create_string_from_params(name, self.info.vars, self.state.params, self.global_vars, self.arch)

        def get_params(self):
            nparams = []
            for param_source, param_type, param_name in params:
                param_type = create_string_from_params(param_type, self.info.vars, self.state.params, self.global_vars, self.arch)
                if param_source == "STATE":
                    param_value = self.state.params[param_name]
                elif param_source == "PARAM":
                    param_value = self.params[param_name]
                nparams.append((param_type, param_value))
            return nparams

        def update_state(self):
            for var_name, var_value in vars:
                self.state.params[var_name] = self.params.get(var_value, var_value)

    return GenericHandlerReader

def set_var(func, name, value):
    def _func(parser, instructions, index, params, arch, info):
        match, nindex = func(parser, instructions, index, params, arch, info)
        if match:
            assert params.set_handler_var_value(name, value)
            return match, nindex
        return match, index
    return _func

def match_math_operations(name, op, is_compare=False, is_unary=False, load_flags=False, has_8bit=True):
    sizes = []
    if has_8bit:
        sizes.append("BYTE")
    sizes.append("WORD")
    sizes.append("DWORD")
    lines = []
    if load_flags:
        lines.append("flags = var_1")
    if is_unary:
        main_op = "(%s$V[VAR_DST])" % op
    elif is_compare:
        main_op = "%s($V[VAR_DST], $V[VAR_SRC])" % op
    else:
        main_op = "($V[VAR_DST] %s $V[VAR_SRC])" % op
    if not is_compare:
        lines.append("$V[VAR_DST] = %s" % main_op)
    lines.append("var_1 = Flags(%s)" % main_op)
    funcs = []
    for size in sizes:
        funcs.append(lines_matcher(["If(($V[VAR_DST_SIZE] == $R[SIZE_%s]))" % size] + ["    " + x for x in lines]))
    funcs.append(only_64(lines_matcher(["If(($V[VAR_DST_SIZE] == $R[SIZE_QWORD]))"] + ["    " + x for x in lines])))
    return set_var(match_funcs(funcs), "OPERATION", name)

DST_LOAD = lines_matcher(["$V[VAR_DST] = VMStructField{SS}($O[DST_VALUE])"])
SRC_LOAD = lines_matcher(["$V[VAR_SRC] = VMStructField{SS}($O[SRC_VALUE])"])
SRC_SIZE_LOAD = lines_matcher(["$V[VAR_SRC_SIZE] = VMStructFieldByte($O[SRC_SIZE])"])
DST_SIZE_LOAD = lines_matcher(["$V[VAR_DST_SIZE] = VMStructFieldByte($O[DST_SIZE])"])
STORE_RESULT_LINE = lines_matcher(["VMStructField{SS}($O[OP_RESULT]) = $V[VAR_DST]"])
LOAD_RESULT = lines_matcher(["$V[VAR_RESULT] = VMStructField{SS}($O[OP_RESULT])"])
LOAD_FLAGS = lines_matcher(["var_1 = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET]))"])
DST_OFFSET_LOAD = lines_matcher(["$V[VAR_DST_OFFSET] = VMStructField{SS}($O[DST_OFFSET])"])

update_flags = lines_matcher([
    "If((ReadParameterByte($P[UPDATE_FLAGS]) != 0x0))",
    "    VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = var_1"
])

update_random_flags = lines_matcher([
    "If((ReadParameterByte($P[UPDATE_FLAGS]) != 0x0))",
    "    VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = RandomFlags()"
])

POST_OPERATIONS = match_funcs([
    STORE_RESULT_LINE,
    update_flags,
    UPDATE_IP_AND_JUMP
])

def binary_op(name, op):
    return match_math_operations(name, op)

def binary_compare_op(name, op):
    return match_math_operations(name, op, is_compare=True)

def binary_mul_op(name, op):
    return match_math_operations(name, op, has_8bit=False)

COMMON_BINARY_OP = HandlerMatch(match_funcs([
    DST_LOAD,
    SRC_LOAD,
    DST_SIZE_LOAD,
    match_one([
        binary_op("ADD", "+"), binary_op("SUB", "-"),
        binary_op("XOR", "^"), binary_op("AND", "&"),
        binary_op("OR", "|"), binary_mul_op("IMUL", "*"),
        binary_compare_op("CMP", "Compare"), binary_compare_op("TEST", "Test"),
    ]),
    POST_OPERATIONS
]), create_dolphin_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{T:DST_TYPE}_{T:SRC_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE"), ("STATE", "{AT:SRC_TYPE}", "SRC_VALUE")]))

def binary_flags_op(name, op):
    return match_math_operations(name, op, load_flags=True)

COMMON_BINARY_OP_FLAGS = HandlerMatch(match_funcs([
    LOAD_FLAGS,
    DST_LOAD,
    SRC_LOAD,
    DST_SIZE_LOAD,
    match_one([
        binary_flags_op("ROL", "rol"), binary_flags_op("ROR", "ror"),
        binary_flags_op("RCL", "rcl"), binary_flags_op("RCR", "rcr"),
        binary_flags_op("SHL", "<<"), binary_flags_op("SHR", ">>"),
    ]),
    POST_OPERATIONS
]), create_dolphin_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{T:DST_TYPE}_{T:SRC_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE"), ("STATE", "{AT:SRC_TYPE}", "SRC_VALUE")]))

def unary_op(name, op):
    return match_math_operations(name, op, load_flags=True, is_unary=True)

COMMON_UNARY_OP = HandlerMatch(match_funcs([
    DST_LOAD,
    LOAD_FLAGS,
    DST_SIZE_LOAD,
    match_one([
        unary_op("INC", "++"), unary_op("DEC", "--")
    ]),
    POST_OPERATIONS
]), create_dolphin_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{T:DST_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE")]))

NEG = HandlerMatch(match_funcs([
    DST_LOAD,
    DST_SIZE_LOAD,
    match_math_operations("NEG", "-", is_unary=True),
    POST_OPERATIONS
]), create_dolphin_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{T:DST_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE")]))

NOT = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}($O[OP_RESULT]) = (~VMStructField{SS}($O[DST_VALUE]))"]),
    update_random_flags,
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("NOT_{S:DST_SIZE}_{T:DST_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE")]))

MOV = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}($O[OP_RESULT]) = VMStructField{SS}($O[SRC_VALUE])"]),
    update_random_flags,
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("MOV_{S:DST_SIZE}_{T:DST_OFFSET_TYPE}_{T:SRC_TYPE}",
                                        [("STATE", "{AT:DST_OFFSET_TYPE}", "DST_VALUE"), ("STATE", "{AT:SRC_TYPE}", "SRC_VALUE")]))

def movzx_movsx(name, operation):
    sizes = ["BYTE", "WORD"]
    lines = ["If(($V[VAR_SRC_SIZE] == $R[SIZE_{SIZE}]))",
            "    $V[VAR_DST] = (%s{SIZE})$V[VAR_SRC]" % operation]
    return set_var(match_funcs([lines_matcher([line.format(SIZE=size) for line in lines]) for size in sizes]), "OPERATION", name)

MOVZX_MOVSX = HandlerMatch(match_funcs([
    DST_LOAD,
    SRC_LOAD,
    SRC_SIZE_LOAD,
    match_one([
        movzx_movsx("MOVZX", ""), movzx_movsx("MOVSX", "S")
    ]),
    STORE_RESULT_LINE,
    update_random_flags,
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{S:SRC_SIZE}_{T:DST_TYPE}_{T:SRC_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE"), ("STATE", "{AT:SRC_TYPE}", "SRC_VALUE")]))

PUSH = HandlerMatch(match_funcs([
    DST_LOAD,
    lines_matcher([
        "$V[VAR_SP] = VMStructOffset(ReadParameterWord($P[SP_OFFSET]))",
        "If((VMStructFieldByte($O[DST_SIZE]) == $R[SIZE_WORD]))",
        "    PushWord($V[VAR_DST])",
        "    *({SU}*)$V[VAR_SP] -= 0x2",
        "Else",
        "    Push($V[VAR_DST])",
        "    *({SU}*)$V[VAR_SP] -= 0x{N}",
    ]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("PUSH_{SS:DST_SIZE}_{T:DST_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE")]))

POP = HandlerMatch(match_funcs([
    DST_SIZE_LOAD,
    DST_OFFSET_LOAD,
    lines_matcher([
        "$V[VAR_SP] = VMStructOffset(ReadParameterWord($P[SP_OFFSET]))",
        "If(($V[VAR_SP] == $V[VAR_DST_OFFSET]))",
        "    $V[VAR_SP] = 0x0",
        "If(($V[VAR_DST_SIZE] == $R[SIZE_WORD]))",
        "    *(WORD*)$V[VAR_DST_OFFSET] = PopWord()",
        "    If(($V[VAR_SP] != 0x0))",
        "        *({SU}*)$V[VAR_SP] += 0x2",
        "If(($V[VAR_DST_SIZE] != $R[SIZE_WORD]))",
        "    *({SU}*)$V[VAR_DST_OFFSET] = Pop()",
        "    If(($V[VAR_SP] != 0x0))",
        "        *({SU}*)$V[VAR_SP] += 0x{N}",
    ]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("POP_{SS:DST_SIZE}_{T:DST_TYPE}",
                                        [("STATE", "{AT:DST_TYPE}", "DST_VALUE")]))

STORE_RESULT = HandlerMatch(match_funcs([
    LOAD_RESULT,
    DST_OFFSET_LOAD,
    DST_SIZE_LOAD,
    lines_matcher([
        "If(($V[VAR_DST_SIZE] == $R[SIZE_BYTE]))",
        "    *(BYTE*)$V[VAR_DST_OFFSET] = $V[VAR_RESULT]",
        "If(($V[VAR_DST_SIZE] == $R[SIZE_WORD]))",
        "    *(WORD*)$V[VAR_DST_OFFSET] = $V[VAR_RESULT]",
    ]),
    match_condition("If(($V[VAR_DST_SIZE] == $R[SIZE_DWORD]))", [
        lines_matcher(["*(DWORD*)$V[VAR_DST_OFFSET] = $V[VAR_RESULT]"]),
        only_64(lines_matcher([
             "If((VMStructFieldByte($O[ZERO_HIGH_DWORD]) != 0x0))",
             "    $V[VAR_DST_OFFSET] = ($V[VAR_DST_OFFSET] + 0x4)",
             "    *(DWORD*)$V[VAR_DST_OFFSET] = 0x0"]))
    ]),
    only_32(lines_matcher([
        "If(($V[VAR_DST_SIZE] == $R[SIZE_QWORD]))",
        "    *(DWORD*)$V[VAR_DST_OFFSET] = $V[VAR_RESULT]",
    ])),
    only_64(lines_matcher([
        "If(($V[VAR_DST_SIZE] == $R[SIZE_QWORD]))",
        "    *(QWORD*)$V[VAR_DST_OFFSET] = $V[VAR_RESULT]",
    ])),
    UPDATE_IP_AND_JUMP
]), create_handler_reader_class("STORE_RESULT"))

def match_load_memvar_value(var_name, param_name):
    pre_lines = ["$V[VAR_ADDRESS] = VMStructField{SS}((ReadParameterWord($P[%s]) & 0xFFFF))" % param_name,
                 "$V[VAR_SIZE] = ReadParameterByte($P[SIZE])"]
    post_lines = ["VMStructField{SS}(?O[%s]) = $V[VAR_ADDRESS]" % var_name]
    lines = ["If(($V[VAR_SIZE] == $R[SIZE_{SIZE}]))",
            "    $V[VAR_ADDRESS] = *({SIZE}*)$V[VAR_ADDRESS]"]
    return match_funcs([lines_matcher(pre_lines)] + \
        [lines_matcher([line.format(SIZE=size) for line in lines]) for size in ["BYTE", "WORD", "DWORD"]] + \
        [only_64(lines_matcher([line.format(SIZE="QWORD") for line in lines])),
        lines_matcher(post_lines)])

LOAD_SRC_IMM = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(?O[SRC_VALUE]) = ReadParameterDword($P[SRC_VALUE])"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_SRC_IMM", [("PARAM", "IMM", "SRC_VALUE")], [("SRC_TYPE", "IMM"), ("SRC_VALUE", "SRC_VALUE")]))

# BUGBUG
LOAD_SRC_QWORD_IMM = HandlerMatch(match_funcs([
    lines_matcher(["$V[VAR_VALUE] = ReadParameterQword($P[SRC_VALUE])"]),
    match_one([
        lines_matcher(["VMStructField{SS}($O[SRC_VALUE]) = (ReadParameterDword($P[SRC_VALUE]) | ((($V[VAR_VALUE] >> 0x20) + $V[VAR_VALUE]) << 0x20))"]),
        lines_matcher(["VMStructField{SS}($O[SRC_VALUE]) = (ReadParameterDword($P[SRC_VALUE]) | ((($V[VAR_VALUE] >> 0x20) - $V[VAR_VALUE]) << 0x20))"])
    ]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_SRC_QWORD_IMM", [("PARAM", "IMM", "SRC_VALUE")], [("SRC_TYPE", "IMM"), ("SRC_VALUE", "SRC_VALUE")]))

LOAD_SRC_VAR = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(?O[SRC_VALUE]) = VMStructField{SS}((ReadParameterWord($P[SRC_VALUE]) & 0xFFFF))"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_SRC_VAR", [("PARAM", "VAR", "SRC_VALUE")], [("SRC_TYPE", "VAR"), ("SRC_VALUE", "SRC_VALUE")]))

# TODO: We are ignoring the size right now
LOAD_SRC_MEMVAR = HandlerMatch(match_funcs([
    match_load_memvar_value("SRC_VALUE", "SRC_VALUE"),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_SRC_MEMVAR", [("PARAM", "VAR", "SRC_VALUE")], [("SRC_TYPE", "MEMVAR"), ("SRC_VALUE", "SRC_VALUE")]))

LOAD_SRC_SIZE = HandlerMatch(match_funcs([
    lines_matcher(["VMStructFieldByte(?O[SRC_SIZE]) = ReadParameterByte($P[SRC_SIZE])"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_SRC_SIZE", [("PARAM", "SIZE", "SRC_SIZE")], [("SRC_SIZE", "SRC_SIZE")]))

LOAD_DST_IMM = HandlerMatch(match_funcs([
    only_64(lines_matcher(["VMStructFieldByte($O[ZERO_HIGH_DWORD]) = 0x0"])),
    lines_matcher(["VMStructField{SS}(?O[DST_VALUE]) = ReadParameterDword($P[DST_VALUE])"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_DST_IMM", [("PARAM", "IMM", "DST_VALUE")], [("DST_TYPE", "IMM"), ("DST_VALUE", "DST_VALUE")]))

LOAD_DST_VAR = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(?O[DST_VALUE]) = VMStructField{SS}((ReadParameterWord($P[DST_VALUE]) & 0xFFFF))"]),
    only_64(lines_matcher(["VMStructFieldByte($O[ZERO_HIGH_DWORD]) = 0x1"])),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_DST_VAR", [("PARAM", "VAR", "DST_VALUE")], [("DST_TYPE", "VAR"), ("DST_VALUE", "DST_VALUE")]))

LOAD_DST_MEMVAR = HandlerMatch(match_funcs([
    only_64(lines_matcher(["VMStructFieldByte($O[ZERO_HIGH_DWORD]) = 0x0"])),
    match_load_memvar_value("DST_VALUE", "DST_VALUE"),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_DST_MEMVAR", [("PARAM", "VAR", "DST_VALUE")], [("DST_TYPE", "MEMVAR"), ("DST_VALUE", "DST_VALUE")]))

LOAD_DST_SIZE = HandlerMatch(match_funcs([
    lines_matcher(["VMStructFieldByte(?O[DST_SIZE]) = ReadParameterByte($P[DST_SIZE])"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_DST_SIZE", [("PARAM", "SIZE", "DST_SIZE")], [("DST_SIZE", "DST_SIZE")]))

LOAD_DST_OFFSET_VAR = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}($O[DST_OFFSET]) = VMStructOffset((ReadParameterWord($P[DST_VALUE]) & 0xFFFF))"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_DST_OFFSET_VAR", [("PARAM", "VAR", "DST_VALUE")], [("DST_OFFSET_TYPE", "VAR"), ("DST_OFFSET_VALUE", "DST_VALUE")]))

LOAD_DST_OFFSET_MEMVAR = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(?O[DST_OFFSET]) = VMStructField{SS}((ReadParameterWord($P[DST_VALUE]) & 0xFFFF))"]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("LOAD_DST_OFFSET_MEMVAR", [("PARAM", "VAR", "DST_VALUE")], [("DST_OFFSET_TYPE", "MEMVAR"), ("DST_OFFSET_VALUE", "DST_VALUE")]))

ADD_VAR_BASEADDRESS = HandlerMatch(match_funcs([
    lines_matcher([
        "VMStructField{SS}($O[DST_OFFSET]) = VMStructOffset((ReadParameterWord($P[DST_VALUE]) & 0xFFFF))",
        "*({SU}*)VMStructField{SS}($O[DST_OFFSET]) += VMStructField{SS}(?O[BASE_ADDRESS])",
    ]),
    UPDATE_IP_AND_JUMP
]), create_dolphin_handler_reader_class("ADD_VAR_BASEADDRESS", [("PARAM", "VAR", "DST_VALUE")], [("DST_OFFSET_TYPE", "INVALID"), ("DST_OFFSET_VALUE", "INVALID")]))

# Deprecated
RESET_KEYS_OLD = HandlerMatch(match_funcs([lines_matcher(\
    [
        "VMStructFieldDword($O[KEY_DECODE]) = 0x0",
        "VMStructFieldDword($O[KEY_COND]) = 0x0",
        "VMStructFieldDword($O[KEY_UNUSED]) = 0x0",
    ]), UPDATE_IP_AND_JUMP]),
    create_handler_reader_class("RESET_KEYS"))

HANDLERS = [
    PUSH,
    POP,
    COMMON_UNARY_OP,
    NEG,
    NOT,
    COMMON_BINARY_OP,
    COMMON_BINARY_OP_FLAGS,
    MOVZX_MOVSX,
    MOV,
    STORE_RESULT,
    LOAD_SRC_IMM,
    LOAD_SRC_QWORD_IMM,
    LOAD_SRC_VAR,
    LOAD_SRC_MEMVAR,
    LOAD_SRC_SIZE,
    LOAD_DST_IMM,
    LOAD_DST_VAR,
    LOAD_DST_MEMVAR,
    LOAD_DST_SIZE,
    LOAD_DST_OFFSET_VAR,
    LOAD_DST_OFFSET_MEMVAR,
    ADD_VAR_BASEADDRESS,
    fish_handlers.FLAGS_OP,
    tiger_handlers.CALL,
    tiger_handlers.MOVS,
    tiger_handlers.CMPS,
    tiger_handlers.SCAS,
    tiger_handlers.NOP,
    tiger_handlers.UNKNOWN_JUNK
    ] + COMMON_HANDLERS

