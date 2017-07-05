from common_handlers import *
import re


def create_string_from_params(name, params, arch):
    ns = name
    for var in re.findall("\{([\w:]+)\}", name):
        t, n = var.split(":")
        if t == "S": # Size
            nvar = ["BYTE", "WORD", "DWORD", "QWORD"][(params[n]&0xf)-1]
            # Hack for movzx/movsx
            if ns.startswith("MOVZX_") or ns.startswith("MOVSX_"):
                nvar += "_" + ["BYTE", "WORD", "DWORD", "QWORD"][(params[n.replace("DST", "SRC")]&0xf)-1]
        elif t == "SS": # Size stack
            if (params[n]&0xf) == 0x2:
                nvar = "WORD"
            else:
                nvar = arch.translate("{SU}")
        elif t == "T": # Type
            nvar = ["VAR", "MEMVAR", "IMM"][(params[n]>>4)-1]
        elif t == "AT": # Arg type
            nvar = ["VAR", "VAR", "IMM"][(params[n]>>4)-1]
        elif t == "O": # Operation
            nvar = params[n]
            assert type(nvar) is str
        else:
            raise Exception("Invalid var: %s" % var)
        ns = ns.replace("{%s}" % var, nvar)
    return ns


def create_fish_handler_reader_class(name, params=[]):
    class GenericHandlerReader(HandlerReader):
        def get_name(self):
            return create_string_from_params(name, self.params, self.arch)

        def get_params(self):
            ret = []
            for arg_type, arg_name in params:
                arg_value = self.params[arg_name]
                # Hack for 64bit numbers
                if self.arch.native_size() == 8 and \
                        arg_name == "SRC_VALUE" and "SRC_LOAD_HIGH_DWORD" in self.params and self.params["SRC_LOAD_HIGH_DWORD"]:
                    arg_value |= self.params["SRC_HIGH_DWORD"] << 0x20
                ret.append((create_string_from_params(arg_type, self.params, self.arch), arg_value))
            return ret

    return GenericHandlerReader


# Deprecated
RESET_KEYS_OLD = HandlerMatch(match_funcs([lines_matcher(\
    [
        "VMStructFieldDword($O[KEY_DECODE]) = 0x0",
        "VMStructFieldDword($O[KEY_COND]) = 0x0",
        "VMStructFieldDword($O[KEY_REGULAR_1]) = 0x0",
        "VMStructFieldDword($O[KEY_REGULAR_2]) = 0x0",
        "VMStructFieldDword($O[KEY_UNUSED]) = 0x0",
        "VMStructFieldWord($O[UNKNOWN_WORD]) = 0x0",
        "VMStructFieldByte($O[VALUE_BYTE]) = 0x0",
        "VMStructFieldDword($O[KEY_SPECIAL]) = 0x0"
    ]), UPDATE_IP_AND_JUMP]),
    create_handler_reader_class("RESET_KEYS"))

MOVS = HandlerMatch(match_funcs([
    MOVS_MAIN,
    match_one([match_funcs([READ_SI, READ_DI]), match_funcs([READ_DI, READ_SI])]),
    UPDATE_SI_DI(True),
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("MOVS"))

BUG_SCAS_1 = match_funcs([
    BUG_SCAS_MAIN,
    READ_DI,
    UPDATE_DI2,
    update_flags_cond(BUG_SCAS_UPDATE_FLAGS),
    UPDATE_IP_AND_JUMP
])

BUG_SCAS_2 = match_funcs([
    BUG_SCAS_MAIN,
    BUG_SCAS_UPDATE_FLAGS_1,
    READ_DI,
    UPDATE_DI2,
    update_flags_cond(BUG_SCAS_UPDATE_FLAGS_2),
    UPDATE_IP_AND_JUMP
])

SCAS_1 = match_funcs([
    READ_DI,
    UPDATE_DI2,
    update_flags_cond(SCAS_UPDATE_FLAGS),
    UPDATE_IP_AND_JUMP
])

SCAS = HandlerMatch(match_one([SCAS_1, BUG_SCAS_1, BUG_SCAS_2]), create_string_op_handler_reader("SCAS"))

CMPS = HandlerMatch(match_funcs([
    match_one([match_funcs([READ_SI, READ_DI]), match_funcs([READ_DI, READ_SI])]),
    UPDATE_SI_DI(True),
    match_one([update_flags_cond(CMPS_UPDATE_FLAGS_1), update_flags_cond(CMPS_UPDATE_FLAGS_2)]),
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("CMPS"))


CLC = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_CLC]))", [disable_flag(0x1, False)])
CMC = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_CMC]))",
                      [match_condition("If(((*(DWORD*)$V[FLAGS_OFFSET] & 0x1) != 0x0))", [disable_flag(0x1, False)]),
                       match_condition("Else", [enable_flag(0x1, False)])])
STC = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_STC]))", [enable_flag(0x1, False)])

FLAGS_OP = HandlerMatch(match_funcs([
    lines_matcher([
        "$V[FLAGS_OFFSET] = VMStructOffset(ReadParameterWord($P[FLAGS_OFFSET]))",
        "$V[FLAGS_OP] = ReadParameterByte($P[FLAGS_OP])"
    ]),
    CLC, CLD, CLI, CMC, STC, STD, STI,
    UPDATE_IP_AND_JUMP]), create_handler_reader_class("{O:FLAGS_OP}"))

def read_two_nibbles(index, param_name=None, var_names=None):
    if param_name is None:
        param_name = "$N[P_%d]" % index
    else:
        param_name = "$P[%s]" % param_name
    if var_names is None:
        var_names = ("$N[OFFSET1_%d]" % index, "$N[OFFSET2_%d]" % index)
    else:
        var_names = ("$U[%s]" % var_names[0], "$U[%s]" % var_names[1])
    lines = [
        "$V[VAR_%d] = ReadParameterByte(%s)" % (index, param_name),
        "VMStructFieldByte(%s) = EncodedValueByte(HIGH_NIBBLE($V[VAR_%d]))" % (var_names[0], index),
        "VMStructFieldByte(%s) = EncodedValueByte(LOW_NIBBLE($V[VAR_%d]))" % (var_names[1], index),
    ]
    return lines_matcher(lines)

def read_encoded_param(index, param_name=None, var_name=None):
    if var_name is None and param_name is None:
        var_name = "$N[OFFSET_%d]" % index
    else:
        if var_name is None:
            var_name = "$U[%s]" % param_name
        else:
            var_name = "$U[%s]" % var_name
    if param_name is None:
        param_name = "$N[P_%d]" % index
    else:
        param_name = "$P[%s]" % param_name
    lines = [
        "VMStructField{SS}(%s) = EncodedValue(ReadParameterDword(%s))" % (var_name, param_name)
    ]
    return lines_matcher(lines)

# def read_acc_byte(index, param_name=None):
#     if param_name is None:
#         param_name = "$N[P_%d]" % index
#     else:
#         param_name = "$P[%s]" % param_name
#     lines = [
#         "UpdateAccByte(ReadParameterByte(%s))" % (param_name, )
#     ]
#     return lines_matcher(lines)

def duplicate_by_size(lines):
    funcs = [lines_matcher([l.replace("@SIZE@", str(1<<i)).replace("@LOGSIZE@", str(i+1)) for l in lines]) for i in xrange(4)]
    funcs[-1] = only_64(funcs[-1])
    return funcs

def read_memvar_and_keep_address(name):
    return match_condition("If((DecodedValueByte(VMStructFieldByte($U[%s_TYPE])) == 0x2))" % (name, ),
                           [lines_matcher(["$V[%s_SIZE_VAR] = DecodedValueByte(VMStructFieldByte($U[%s_SIZE]))" % (name, name),
                                           "$V[%s_ADDRESS_VAR_2] = VMStructField{SS}((DecodedValue(VMStructField{SS}($U[%s_VALUE])) & 0xFFFF))" % (name, name),
                                           "VMStructField{SS}($U[%s_ADDRESS]) = EncodedValue($V[%s_ADDRESS_VAR_2])" % (name, name)])] +
                            duplicate_by_size(["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (name, ),
                                               "    $V[%s_ADDRESS_VAR_2] = *({SU:@SIZE@}*)$V[%s_ADDRESS_VAR_2]" % (name, name)]) +
                           [lines_matcher(["VMStructField{SS}($U[%s_VALUE]) = EncodedValue($V[%s_ADDRESS_VAR_2])" % (name, name)])])


def read_var_and_keep_address(name, dest_var=False):
    conds = [lines_matcher(["$V[%s_ADDRESS_VAR_1] = VMStructOffset((DecodedValue(VMStructField{SS}($U[%s_VALUE])) & 0xFFFF))" % (name, name),
                            "VMStructField{SS}($U[%s_ADDRESS]) = EncodedValue($V[%s_ADDRESS_VAR_1])" % (name, name),
                            "VMStructField{SS}($U[%s_VALUE]) = EncodedValue(*({SU}*)$V[%s_ADDRESS_VAR_1])" % (name, name)])]
    if dest_var:
        conds.append(only_64(lines_matcher(["If((DecodedValueByte(VMStructFieldByte($U[%s_SIZE])) == 0x3))" % (name, ),
                                            "    VMStructFieldByte($O[ZERO_HIGH_DWORD_BOOL]) = 0x1"])))
    return match_condition("If((DecodedValueByte(VMStructFieldByte($U[%s_TYPE])) == 0x1))" % (name, ), conds)

def read_memvar(name):
    return match_condition("If((DecodedValueByte(VMStructFieldByte($U[%s_TYPE])) == 0x2))" % (name, ),
                           [lines_matcher(["$V[%s_SIZE_VAR] = DecodedValueByte(VMStructFieldByte($U[%s_SIZE]))" % (name, name),
                                           "$V[%s_ADDRESS_VAR_2] = VMStructField{SS}((DecodedValue(VMStructField{SS}($U[%s_VALUE])) & 0xFFFF))" % (name, name)])] +
                            duplicate_by_size(["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (name, ),
                                               "    $V[%s_ADDRESS_VAR_2] = *({SU:@SIZE@}*)$V[%s_ADDRESS_VAR_2]" % (name, name)]) +
                           [lines_matcher(["VMStructField{SS}($U[%s_VALUE]) = EncodedValue($V[%s_ADDRESS_VAR_2])" % (name, name)])])

def read_var(name):
    return lines_matcher(["If((DecodedValueByte(VMStructFieldByte($U[%s_TYPE])) == 0x1))" % (name, ),
                          "    VMStructField{SS}($U[%s_VALUE]) = EncodedValue(VMStructField{SS}((DecodedValue(VMStructField{SS}($U[%s_VALUE])) & 0xFFFF)))" % (name, name)])


def load_high_dword(name):
    return lines_matcher(["If((ReadParameterByte($P[%s_LOAD_HIGH_DWORD]) != 0x0))" % (name, ),
                          "    VMStructFieldQword($U[%s_VALUE]) = EncodedValue(((ReadParameterDword($P[%s_HIGH_DWORD]) << 0x20) | DecodedValue(VMStructFieldQword($U[%s_VALUE]))))" % (name, name, name)])


RESET_ZERO_HIGH_DWORD_BOOL = lines_matcher(["VMStructFieldByte($O[ZERO_HIGH_DWORD_BOOL]) = 0x0"])

def binary_math_op(op_name, op, read_flag=False):
    main_lines = ["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (op_name, )]
    if read_flag:
        main_lines += ["    flags = var_1"]
    main_lines += ["    $V[%s_VAR_DST] = ($V[%s_VAR_DST] %s $V[%s_VAR_SRC])" % (op_name, op_name, op, op_name),
                   "    var_1 = Flags(($V[%s_VAR_DST] %s $V[%s_VAR_SRC]))" % (op_name, op, op_name)]
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))" % (op_name,),
                                           ])] +
                           (read_flag and [lines_matcher(["var_1 = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET]))"])] or []) +
                           duplicate_by_size(main_lines) +
                           [lines_matcher(["VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_DST])" % (op_name,)])])

def binary_compare_op(op_name, op, read_flag=False):
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))" % (op_name,),
                                           ])] +
                            duplicate_by_size(["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (op_name, ),
                                               "    var_1 = Flags(%s($V[%s_VAR_DST], $V[%s_VAR_SRC]))" % (op, op_name, op_name)]) +
                           [lines_matcher(["VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_DST])" % (op_name,)])])

def binary_movzx_movsx_op(op_name):
    if op_name == "MOVSX":
        letter = "S"
    else:
        letter = ""
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[SRC_SIZE]))" % (op_name,),
                                           ]),
                            lines_matcher(["If(($V[%s_SIZE_VAR] == 0x1))" % (op_name, ),
                                           "    $V[%s_VAR_DST] = (%sBYTE)$V[%s_VAR_SRC]" % (op_name, letter, op_name)]),
                            lines_matcher(["If(($V[%s_SIZE_VAR] == 0x2))" % (op_name, ),
                                           "    $V[%s_VAR_DST] = (%sWORD)$V[%s_VAR_SRC]" % (op_name, letter, op_name)]),
                            only_64(lines_matcher(["If(($V[%s_SIZE_VAR] == 0x3))" % (op_name, ),
                                                   "    $V[%s_VAR_DST] = $V[%s_VAR_SRC]" % (op_name, op_name)])),
                            lines_matcher(["var_1 = Flags(($V[%s_VAR_SRC] + $V[%s_VAR_DST]))" % (op_name, op_name),
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_DST])" % (op_name,)])])

def binary_mul_op():
    op_name = "IMUL"
    op = "*"
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "var_1 = Flags(($V[%s_VAR_DST] %s $V[%s_VAR_SRC]))" % (op_name, op, op_name),
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue(($V[%s_VAR_DST] %s $V[%s_VAR_SRC]))" % (op_name, op, op_name)])])

def binary_mov_op():
    op_name = "MOV"
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "var_1 = Flags(($V[%s_VAR_SRC] + $V[%s_VAR_SRC]))" % (op_name, op_name),
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_SRC])" % (op_name,)])])

UPDATE_FLAGS = lines_matcher(["If((ReadParameterByte($P[UPDATE_FLAGS]) != 0x0))",
                              "    VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = var_1"])


def set_value(dst_address_var, src_var, size_var, zero_high_word_bool="VMStructFieldByte($O[ZERO_HIGH_DWORD_BOOL])", invert_bool_test=False):
    return match_funcs([
         lines_matcher(
             ["If(($V[%s] == 0x1))" % size_var,
              "    *(BYTE*)$V[%s] = $V[%s]" % (dst_address_var, src_var),
              "If(($V[%s] == 0x2))" % size_var,
              "    *(WORD*)$V[%s] = $V[%s]" % (dst_address_var, src_var)]),
         match_condition("If(($V[%s] == 0x3))" % size_var,
            [
              lines_matcher(["*(DWORD*)$V[%s] = $V[%s]" % (dst_address_var, src_var)]),
              only_64(lines_matcher(
                ["$V[%s] = %s" % (src_var, zero_high_word_bool),
                 "If(($V[%s] %s))" % (src_var, invert_bool_test and "== 0x1" or "!= 0x0"),
                 "    $V[%s] = ($V[%s] + 0x4)" % (dst_address_var, dst_address_var),
                 "    *(DWORD*)$V[%s] = 0x0" % dst_address_var]))
            ]),
         only_64(lines_matcher(
            ["If(($V[%s] == 0x4))" % size_var,
             "    *(QWORD*)$V[%s] = $V[%s]" % (dst_address_var, src_var)])),
    ])

UPDATE_RESULT = match_condition("If((ReadParameterByte($P[OPERATION]) != $H[OPERATION_CMP]))",
    [match_condition("If((ReadParameterByte($P[OPERATION]) != $H[OPERATION_TEST]))",
         [
             lines_matcher_any_order(
                 ["$V[RESULT_VAR] = DecodedValue(VMStructField{SS}($U[RESULT]))",
                  "$V[RESULT_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))",
                  "$V[RESULT_VAR_ADDRESS] = DecodedValue(VMStructField{SS}($U[DST_ADDRESS]))"]),
             set_value("RESULT_VAR_ADDRESS", "RESULT_VAR", "RESULT_VAR_SIZE")
         ])
    ])

COMMON_BINARY_OP = HandlerMatch(match_funcs([
    any_order([read_encoded_param(2), read_encoded_param(3), read_two_nibbles(4), read_two_nibbles(5)]),
    any_order([RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("DST", True), read_memvar_and_keep_address("DST"),
               only_64(load_high_dword("SRC")), read_var("SRC"), read_memvar("SRC")]),
    # TODO as switch
    any_order([binary_math_op("ADD", "+"), binary_math_op("SUB", "-"),
               binary_math_op("XOR", "^"), binary_math_op("AND", "&"), binary_math_op("OR", "|"),
               binary_math_op("SHL", "<<", True), binary_math_op("SHR", ">>", True),
               binary_math_op("ROL", "rol", True), binary_math_op("ROR", "ror", True),
               binary_math_op("RCL", "rcl", True), binary_math_op("RCR", "rcr", True),
               binary_compare_op("CMP", "Compare"), binary_compare_op("TEST", "Test"),
               binary_movzx_movsx_op("MOVZX"), binary_movzx_movsx_op("MOVSX"),
               binary_mul_op(), binary_mov_op()
               ]),
    # Now give the names for the parameters
    at_start(any_order([read_encoded_param(7, "SRC_VALUE"), read_encoded_param(8, "DST_VALUE"),
                        read_two_nibbles(9, "SRC_TYPE_AND_SIZE", ("SRC_TYPE", "SRC_SIZE")),
                        read_two_nibbles(10, "DST_TYPE_AND_SIZE", ("DST_TYPE", "DST_SIZE"))])),
    any_order([UPDATE_FLAGS, UPDATE_RESULT]),
    UPDATE_IP_AND_JUMP
    ]), create_fish_handler_reader_class("{O:OPERATION}_{S:DST_TYPE_AND_SIZE}_{T:DST_TYPE_AND_SIZE}_{T:SRC_TYPE_AND_SIZE}",
                                         [("{AT:DST_TYPE_AND_SIZE}", "DST_VALUE"), ("{AT:SRC_TYPE_AND_SIZE}", "SRC_VALUE")]))

def unary_math_op(op_name, op, read_flag=False):
    main_lines = ["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (op_name, )]
    if read_flag:
        main_lines += ["    flags = var_1"]
    main_lines += ["    $V[%s_VAR_VALUE] = (%s$V[%s_VAR_VALUE])" % (op_name, op, op_name),
                   "    var_1 = Flags((%s$V[%s_VAR_VALUE]))" % (op, op_name)]
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_VALUE] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))" % (op_name,),
                                           ])] +
                           (read_flag and [lines_matcher(["var_1 = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET]))"])] or []) +
                           duplicate_by_size(main_lines) +
                           [lines_matcher(["VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_VALUE])" % (op_name,)])])

def unary_math_not():
    op_name = "NOT"
    return match_condition("If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["var_1 = RandomFlags()",
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue((~DecodedValue(VMStructField{SS}($U[DST_VALUE]))))"])])

COMMON_UNARY_OP = HandlerMatch(match_funcs([
    any_order([read_encoded_param(2, "VALUE", "DST_VALUE"),
               read_two_nibbles(4, "TYPE_AND_SIZE", ("DST_TYPE", "DST_SIZE"))]),
    any_order([RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("DST", True), read_memvar_and_keep_address("DST")]),
    # TODO as switch
    any_order([unary_math_op("INC", "++", True), unary_math_op("DEC", "--", True),
               unary_math_op("NEG", "-"), unary_math_not(),
               ]),
    any_order([UPDATE_FLAGS, UPDATE_RESULT]),
    UPDATE_IP_AND_JUMP
    ]), create_fish_handler_reader_class("{O:OPERATION}_{S:TYPE_AND_SIZE}_{T:TYPE_AND_SIZE}",
                                         [("{AT:TYPE_AND_SIZE}", "VALUE")]))

PUSH_POP_MAIN = lines_matcher(["If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_PUSH]))",
                               "    If(($V[SIZE_VAR] == 0x2))",
                               "        PushWord($V[VALUE])",
                               "    Else",
                               "        Push($V[VALUE])",
                               "If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_POP]))",
                               "    $V[VALUE] = DecodedValue(VMStructField{SS}($U[VALUE_ADDRESS]))",
                               "    If(($V[SIZE_VAR] == 0x2))",
                               "        *(WORD*)$V[VALUE] = PopWord()",
                               "    Else",
                               "        *({SU}*)$V[VALUE] = Pop()"])

# BUG: Pop word doesn't seem to work...
PUSH_POP_UPDATE_STACK_OLD = lines_matcher(["If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_PUSH]))",
                                       "    If((LOW_NIBBLE(DecodedValueByte(VMStructFieldByte($U[VALUE_SIZE]))) == 0x2))",
                                       "        *({SU}*)$V[SP_OFFSET] -= 0x2",
                                       "    Else",
                                       "        *({SU}*)$V[SP_OFFSET] -= 0x{N}",
                                       "If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_POP]))",
                                       "    If((DecodedValue(VMStructField{SS}($U[VALUE_ADDRESS])) != $V[SP_OFFSET]))",
                                       "        *({SU}*)$V[SP_OFFSET] += 0x{N}"])

# Fixed in newer versions
PUSH_POP_UPDATE_STACK = lines_matcher(["If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_PUSH]))",
                                       "    If(($V[SIZE_VAR2] == 0x2))",
                                       "        *({SU}*)$V[SP_OFFSET] -= 0x2",
                                       "    Else",
                                       "        *({SU}*)$V[SP_OFFSET] -= 0x{N}",
                                       "If((ReadParameterByte($P[OPERATION]) == $H[OPERATION_POP]))",
                                       "    If((DecodedValue(VMStructField{SS}($U[VALUE_ADDRESS])) != $V[SP_OFFSET]))",
                                       "        If(($V[SIZE_VAR2] == 0x2))",
                                       "            *({SU}*)$V[SP_OFFSET] += 0x2",
                                       "        Else",
                                       "            *({SU}*)$V[SP_OFFSET] += 0x{N}",
                                       ])

PUSH_POP = HandlerMatch(match_funcs([
    any_order([read_encoded_param(2, "VALUE", "VALUE_VALUE"),
               read_two_nibbles(3, "TYPE_AND_SIZE", ("VALUE_TYPE", "VALUE_SIZE"))]),
    any_order([RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("VALUE", True), read_memvar_and_keep_address("VALUE")]),
    lines_matcher(["$V[VALUE] = DecodedValue(VMStructField{SS}($U[VALUE_VALUE]))"]),
    lines_matcher(["$V[SIZE_VAR] = LOW_NIBBLE(DecodedValueByte(VMStructFieldByte($U[VALUE_SIZE])))"]),
    PUSH_POP_MAIN,
    match_one([match_funcs([
        any_order([lines_matcher(["$V[SP_OFFSET] = VMStructOffset(ReadParameterWord($P[SP_OFFSET]))"]),
                   lines_matcher(["$V[SIZE_VAR2] = LOW_NIBBLE(DecodedValueByte(VMStructFieldByte($U[VALUE_SIZE])))"])]),
        PUSH_POP_UPDATE_STACK,
        ]),
        match_funcs([lines_matcher(["$V[SP_OFFSET] = VMStructOffset(ReadParameterWord($P[SP_OFFSET]))"]),
                     PUSH_POP_UPDATE_STACK_OLD]),
        ]),
    UPDATE_IP_AND_JUMP
    ]), create_fish_handler_reader_class("{O:OPERATION}_{SS:TYPE_AND_SIZE}_{T:TYPE_AND_SIZE}",
                                         [("{AT:TYPE_AND_SIZE}", "VALUE")]))

XCHG_OPERATION_0 = lines_matcher_any_order(["$V[XCHG_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))",
                                            "$V[XCHG_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))",
                                            "$V[XCHG_VAR_SRC_ADDRESS] = DecodedValue(VMStructField{SS}($U[SRC_ADDRESS]))"])

XCHG_OPERATION_OLD = match_funcs(
    duplicate_by_size(["If(($V[XCHG_SIZE_VAR] == 0x@LOGSIZE@))",
                       "    *({SU:@SIZE@}*)$V[XCHG_VAR_SRC_ADDRESS] = $V[XCHG_VAR_DST]"]) +
    [lines_matcher(["$V[XCHG_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))",
                    "$V[XCHG_VAR_DST_ADDRESS] = DecodedValue(VMStructField{SS}($U[DST_ADDRESS]))"])] +
    duplicate_by_size(["If(($V[XCHG_SIZE_VAR] == 0x@LOGSIZE@))",
                       "    *({SU:@SIZE@}*)$V[XCHG_VAR_DST_ADDRESS] = $V[XCHG_VAR_SRC]"]))

XCHG_OPERATION = match_funcs([
    # BUG: It doesn't use ZERO_HIGH_DWORD_BOOL and use random thing instead...
    set_value("XCHG_VAR_SRC_ADDRESS", "XCHG_VAR_DST", "XCHG_SIZE_VAR", "DecodedValueByte(VMStructFieldByte($U[SRC_TYPE]))", invert_bool_test=True),
    lines_matcher(["$V[XCHG_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))",
                    "$V[XCHG_VAR_DST_ADDRESS] = DecodedValue(VMStructField{SS}($U[DST_ADDRESS]))"]),
    set_value("XCHG_VAR_DST_ADDRESS", "XCHG_VAR_SRC", "XCHG_SIZE_VAR", "DecodedValueByte(VMStructFieldByte($U[DST_TYPE]))", invert_bool_test=True),
])

XCHG_T = [RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("DST", True), read_memvar_and_keep_address("DST"),
          read_var_and_keep_address("SRC"), read_memvar_and_keep_address("SRC")]

XCHG = HandlerMatch(match_funcs([
    any_order([read_encoded_param(2), read_encoded_param(3), read_two_nibbles(4), read_two_nibbles(5)]),
    # Because it may confused between SRC and DST
    match_one([match_funcs([any_order(XCHG_T), XCHG_OPERATION_0]),
               match_funcs([any_order(XCHG_T[::-1]), XCHG_OPERATION_0])]),
    # Now give the names for the parameters
    at_start(any_order([read_encoded_param(7, "SRC_VALUE"), read_encoded_param(8, "DST_VALUE"),
                        read_two_nibbles(9, "SRC_TYPE_AND_SIZE", ("SRC_TYPE", "SRC_SIZE")),
                        read_two_nibbles(10, "DST_TYPE_AND_SIZE", ("DST_TYPE", "DST_SIZE"))])),
    match_one([XCHG_OPERATION_OLD, XCHG_OPERATION]),
    UPDATE_IP_AND_JUMP
    ]), create_fish_handler_reader_class("XCHG_{S:DST_TYPE_AND_SIZE}_{T:DST_TYPE_AND_SIZE}_{T:SRC_TYPE_AND_SIZE}",
                                         [("{AT:DST_TYPE_AND_SIZE}", "DST_VALUE"), ("{AT:SRC_TYPE_AND_SIZE}", "SRC_VALUE")]))



CALL = HandlerMatch(match_funcs([
    lines_matcher(
        ["$V[VAR_CALL_TYPE] = ReadParameterByte($P[CALL_TYPE])",
         "If(($V[VAR_CALL_TYPE] == $H[CALL_TYPE_RELIMM]))",
         "    $V[VAR_STACK] = (ReadParameterWord($P[STACK_RETURN_OFFSET]) + SP)",
         "    *({SU}*)$V[VAR_STACK] = (ReadParameterDword($P[VALUE]) + VMStructField{SS}(?O[BASE_ADDRESS]))",
         "If((($V[VAR_CALL_TYPE] == $H[CALL_TYPE_VAR]) || ($V[VAR_CALL_TYPE] == $H[CALL_TYPE_MEMVAR])))",
         "    $V[VAR_VALUE] = VMStructField{SS}(ReadParameterWord($P[VALUE]))",
         "    If(($V[VAR_CALL_TYPE] == $H[CALL_TYPE_MEMVAR]))",
         "        $V[VAR_VALUE] = *({SU}*)$V[VAR_VALUE]",
         "    $V[VAR_STACK] = (ReadParameterWord($P[STACK_RETURN_OFFSET]) + SP)",
         "    *({SU}*)$V[VAR_STACK] = $V[VAR_VALUE]",
         "*({SU}*)($V[VAR_STACK] + 0x{N}) = (ReadParameterDword($P[RETURN_ADDRESS]) + VMStructField{SS}(?O[BASE_ADDRESS]))"]),
    POP_RET
]), create_fish_handler_reader_class("CALL_{O:CALL_TYPE}_NEXT",
                                     [("{O:CALL_TYPE}", "VALUE"), ("RELIMM", "RETURN_ADDRESS")]))

ADD_VAR_BASEADDRESS = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}($N[VAR]) = EncodedValue(ReadParameterDword($P[VAR]))",
                   "VMStructField{SS}((DecodedValue(VMStructField{SS}($N[VAR])) & 0xFFFF)) += VMStructField{SS}(?O[BASE_ADDRESS])"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("ADD_VAR_BASEADDRESS", [("VAR", "VAR")]))

# Those aren't really nops, but handlers to update keys, which we parse and remove
NOP = HandlerMatch(UPDATE_IP_AND_JUMP, create_handler_reader_class("NOP"))

HANDLERS = [
    FLAGS_OP,
    MOVS,
    CMPS,
    SCAS,
    ADD_VAR_BASEADDRESS,
    COMMON_BINARY_OP,
    COMMON_UNARY_OP,
    PUSH_POP,
    XCHG,
    CALL,
    NOP,
] + COMMON_HANDLERS
