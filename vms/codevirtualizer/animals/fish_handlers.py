from collections import namedtuple
import vms.vminstruction as vminstruction
import handlers_parser

HandlerMatch = namedtuple("HandlerMatch", ["match_func", "reader"])


class HandlerInfo(object):
    def __init__(self):
        self.params = {}
        self.vars = {}
        self.read_info = []
        self.reader = None

    def get_size(self):
        return self.vars["OPCODE_SIZE"]


class HandlerReader(object):
    def __init__(self, info, params):
        self.info = info
        self.params = params

    def get_name(self):
        pass

    def get_params(self):
        return []

    def get_instruction(self):
        return vminstruction.VMInstruction(self.get_name(), self.get_parms())

    def get_next_handler(self):
        if "NEXT_HANDLER" in self.parameters:
            return self.parameters["NEXT_HANDLER"]
        else:
            return None


def create_handler_reader_class(get_name_func, get_params_func=None):
    class GenericHandlerReader(object):
        def get_name(self):
            return get_name_func(self)

        def get_params(self):
            if get_params_func is None:
                return []
            else:
                return get_params_func(self)
    return GenericHandlerReader

def create_string_op_handler_reader(op_name):
    class StringOpHandlerReader(object):
        def get_name(self):
            return op_name + {1: "B", 2: "W", 4: "D", 8: "Q"}[self.info.vars["SIZE"]]
    return StringOpHandlerReader

def match_lines(parser, instructions, index, params, lines, arch):
    nparams = params.copy()
    match, index, lines_index = parser.match_instructions(instructions, index, [arch.translate(l) for l in lines], 0, nparams)
    if not match or lines_index != len(lines):
        return False, index
    params.update(nparams)
    return True, index

def lines_matcher(lines):
    def _match_lines(parser, instructions, index, params, arch, info):
        return match_lines(parser, instructions, index, params, lines, arch)
    return _match_lines

def update_keys(parser, instructions, index, params, arch, info):
    while index < len(instructions):
        if str(instructions[index]).startswith("UpdateKey"):
            index += 1
        else:
            break
    return True, index

def any_order(funcs, with_keys=False):
    def _match_funcs(parser, instructions, index, params, arch, info):
        left = list(funcs)
        nparams = params.copy()
        while len(left) > 0:
            if with_keys:
                match, index = update_keys(parser, instructions, index, nparams, arch, info)
            for func in left:
                match, nindex = func(parser, instructions, index, nparams, arch, info)
                if match:
                    index = nindex
                    left.remove(func)
                    break
            if not match:
                return False, index
        if with_keys:
            match, index = update_keys(parser, instructions, index, nparams, arch, info)
        params.update(nparams)
        return True, index
    return _match_funcs

def lines_matcher_any_order(lines):
    return any_order([lines_matcher([x]) for x in lines])

def any_order_with_key_updates(funcs):
    return any_order(funcs, True)

def only_64(func):
    def _func(parser, instructions, index, params, arch, info):
        if arch.native_size() == 8:
            return func(parser, instructions, index, params, arch, info)
        else:
            return True, index
    return _func

def match_funcs(funcs):
    def _func(parser, instructions, index, params, arch, info):
        nparams = params.copy()
        for func in funcs:
            match, index = func(parser, instructions, index, nparams, arch, info)
            if not match:
                return False, index
        params.update(nparams)
        return True, index
    return _func

def match_condition(cond_line, funcs):
    def _func(parser, instructions, index, params, arch, info):
        if index >= len(instructions):
            return False, index
        nparams = params.copy()
        if not parser.match_expression(instructions[index], arch.translate(cond_line), nparams):
            return False, index
        nindex = 0
        insts = instructions[index].instructions
        for func in funcs:
            match, nindex = func(parser, insts, nindex, nparams, arch, info)
            if not match:
                return False, index
        if len(insts) != nindex:
            return False, index
        params.update(nparams)
        return True, index+1
    return _func

def match_one(funcs):
    def _func(parser, instructions, index, params, arch, info):
        nparams = params.copy()
        for func in funcs:
            match, nindex = func(parser, instructions, index, nparams, arch, info)
            if match:
                params.update(nparams)
                return match, nindex
        return False, index
    return _func

def at_start(func):
    def _func(parser, instructions, index, params, arch, info):
        match, nindex = func(parser, instructions, 0, params, arch, info)
        return match, index
    return _func


UPDATE_IP_AND_JUMP = lines_matcher(\
    [
        "UpdateEip($H[OPCODE_SIZE])",
        "JumpToHandler(ReadParameterWord($P[NEXT_HANDLER], $[DECODE_NEXT_HANDLER]))"
    ])

UPDATE_IP_AND_JUMP_PARAM = lines_matcher(\
    [
        "UpdateEip(ReadParameterDword($P[JUMP_VALUE], None))",
        "JumpToHandler(ReadParameterWord($P[JUMP_HANDLER], $[DECODE_JUMP_HANDLER]))"
    ])

VM_INIT = HandlerMatch(match_funcs([lines_matcher(\
    [
        "VMStructFieldDword($O[KEY1]) = 0x0",
        "VMStructFieldDword($O[KEY2]) = 0x0",
        "VMStructFieldDword($O[KEY3]) = 0x0",
        "VMStructFieldDword($O[KEY4]) = 0x0",
        "VMStructFieldDword($O[KEY5]) = 0x0",
        "VMStructFieldWord($O[UNKNOWN_WORD]) = 0x0",
        "VMStructFieldByte($O[ACC_BYTE]) = 0x0",
        "VMStructFieldDword($O[KEY6]) = 0x0"
    ]), UPDATE_IP_AND_JUMP]),
    create_handler_reader_class(lambda x: "VM_INIT"))


COPY_STACK_RETURN = HandlerMatch(match_funcs([lines_matcher([
            "Std()" # Only line because of the decompiler unable to decompile loop
        ])]),
        create_handler_reader_class(lambda x: "COPY_STACK_RETURN"))


def string_op(lines):
    def _func(parser, instructions, index, params, arch, info):
        parser.groups["SIZES"] = ["BYTE", "WORD", "DWORD"]
        parser.groups["SIZES2"] = ["Byte", "Word", "Dword"]
        parser.groups["SIZES_NUM"] = ["1", "2", "4"]
        if arch.native_size() == 8:
            parser.groups["SIZES"].append("QWORD")
            parser.groups["SIZES2"].append("Qword")
            parser.groups["SIZES_NUM"].append("8")
        match, index = match_lines(parser, instructions, index, params, lines, arch)
        if not match:
            return False, index
        sizes = []
        if "SIZE" in params.vars:
            sizes.append({"BYTE": 1, "WORD": 2, "DWORD": 4, "QWORD": 8}[params.vars["SIZE"].value])
        if "SIZE2" in params.vars:
            sizes.append({"BYTE": 1, "WORD": 2, "DWORD": 4, "QWORD": 8}[params.vars["SIZE"].value.upper()])
        if "SIZE_NUM" in params.vars:
            sizes.append(int(params.vars["SIZE_NUM"].value))
        if sizes:
            size = sizes[0]
            for s in sizes[1:]:
                if s != size:
                    return False, index
            if "SIZE" in info.vars:
                if info.vars["SIZE"] != size:
                    return False, index
            else:
                info.vars["SIZE"] = size
        return True, index
    return _func


READ_SI = string_op(["$V[VAR_SI_OFFSET] = VMStructOffset(ReadParameterWord($P[SI_OFFSET], None))"])
READ_DI = string_op(["$V[VAR_DI_OFFSET] = VMStructOffset(ReadParameterWord($P[DI_OFFSET], None))"])

UPDATE_SI_DI = match_one([string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None)) & 0x400) | (VMStructFieldDword($O[FLAGS]) & 0x400)) != 0x0))",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_SI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_SI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"]),
                          string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None)) & 0x400) | (VMStructFieldDword($O[FLAGS]) & 0x400)) != 0x0))",
         "    *({SU}*)$V[VAR_SI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_SI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])])

UPDATE_DI = string_op(
        ["If(((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None)) & 0x400) != 0x0))",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

UPDATE_DI2 = string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None)) & 0x400) | (VMStructFieldDword($O[FLAGS]) & 0x400)) != 0x0))",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

UPDATE_SI = string_op(
        ["If(((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None)) & 0x400) != 0x0))",
         "    *({SU}*)$V[VAR_SI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_SI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

MOVS_MAIN = string_op(["*($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[DI_OFFSET], None)) = *($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[SI_OFFSET], None))"])

# BUG, it seems to be wrong..

SCAS_MAIN = match_one([string_op(["$V[VAR_DI] = VMStructField{SS}(ReadParameterWord($P[DI_OFFSET], None))",
                                  "$V[VAR_AX] = VMStructField{SS}(ReadParameterWord($P[AX_OFFSET], None))",
                                  "*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX]"]),
                       string_op(["$V[VAR_AX] = VMStructField{SS}(ReadParameterWord($P[AX_OFFSET], None))",
                                  "$V[VAR_DI] = VMStructField{SS}(ReadParameterWord($P[DI_OFFSET], None))",
                                  "*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX]"])])

SCAS_UPDATE_FLAGS_1 = string_op(["var_1 = Flags(*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX])"])

SCAS_UPDATE_FLAGS_2 = string_op(["If((ReadParameterByte($P[UPDATE_FLAGS], None) != 0x0))",
                                 "    VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET], None)) = var_1"])

SCAS_UPDATE_FLAGS = string_op(["If((ReadParameterByte($P[UPDATE_FLAGS], None) != 0x0))",
                               "    VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET], None)) = Flags(*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX])"])
CMPS_UPDATE_FLAGS_1 = string_op(["If((ReadParameterByte($P[UPDATE_FLAGS], None) != 0x0))",
                                 "    VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET], None)) = Flags(Compare(*($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[SI_OFFSET], None)), *($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[DI_OFFSET], None))))"])

CMPS_UPDATE_FLAGS_2 = string_op(["If((ReadParameterByte($P[UPDATE_FLAGS], None) != 0x0))",
                                 "    VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET], None)) = Flags(Compare(*($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[DI_OFFSET], None)), *($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[SI_OFFSET], None))))"])

STOS_MAIN = string_op(["*($G[SIZES:SIZE]*)*({SU}*)$V[VAR_DI_OFFSET] = VMStructField$G[SIZES2:SIZE2](ReadParameterWord($P[AX_OFFSET], None))"])

LODS_MAIN = string_op(["VMStructField$G[SIZES2:SIZE2](ReadParameterWord($P[AX_OFFSET], None)) = *($G[SIZES:SIZE]*)*({SU}*)$V[VAR_SI_OFFSET]"])


MOVS = HandlerMatch(match_funcs([
    update_keys,
    MOVS_MAIN,
    update_keys,
    match_one([match_funcs([READ_SI, READ_DI]), match_funcs([READ_DI, READ_SI])]),
    UPDATE_SI_DI,
    update_keys,
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("MOVS"))

SCAS_1 = match_funcs([
    update_keys,
    SCAS_MAIN,
    update_keys,
    READ_DI,
    UPDATE_DI2,
    update_keys,
    SCAS_UPDATE_FLAGS,
    update_keys,
    UPDATE_IP_AND_JUMP
])

SCAS_2 = match_funcs([
    update_keys,
    SCAS_MAIN,
    SCAS_UPDATE_FLAGS_1,
    update_keys,
    READ_DI,
    UPDATE_DI2,
    update_keys,
    SCAS_UPDATE_FLAGS_2,
    update_keys,
    UPDATE_IP_AND_JUMP
])

SCAS = HandlerMatch(match_one([SCAS_1, SCAS_2]), create_string_op_handler_reader("SCAS"))

LODS = HandlerMatch(match_funcs([
    update_keys,
    READ_SI,
    update_keys,
    LODS_MAIN,
    update_keys,
    UPDATE_SI,
    update_keys,
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("SCAS"))

STOS = HandlerMatch(match_funcs([
    update_keys,
    READ_DI,
    update_keys,
    STOS_MAIN,
    update_keys,
    UPDATE_DI,
    update_keys,
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("SCAS"))

CMPS = HandlerMatch(match_funcs([
    update_keys,
    match_one([match_funcs([READ_SI, READ_DI]), match_funcs([READ_DI, READ_SI])]),
    UPDATE_SI_DI,
    update_keys,
    match_one([CMPS_UPDATE_FLAGS_1, CMPS_UPDATE_FLAGS_2]),
    update_keys,
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("SCAS"))

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
        "$V[VAR_%d] = ReadParameterByte(%s, $[DECODE_%d])" % (index, param_name, index),
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
        "VMStructField{SS}(%s) = EncodedValue(ReadParameterDword(%s, $[DECODE_%d]))" % (var_name, param_name, index)
    ]
    return lines_matcher(lines)

def read_acc_byte(index, param_name=None):
    if param_name is None:
        param_name = "$N[P_%d]" % index
    else:
        param_name = "$P[%s]" % param_name
    lines = [
        "UpdateAccByte(SimpleOperation($[OP_%d], ReadParameterByte(%s, $[DECODE_%d])))" % (index, param_name, index)
    ]
    return lines_matcher(lines)

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
    return lines_matcher(["If((ReadParameterByte($P[%s_LOAD_HIGH_DWORD], None) != 0x0))" % (name, ),
                          "    VMStructFieldQword($U[%s_VALUE]) = EncodedValue(((ReadParameterDword($P[%s_HIGH_DWORD], $[DECODE_%s]) << 0x20) | DecodedValue(VMStructFieldQword($U[%s_VALUE]))))" % (name, name, name, name)])


RESET_ZERO_HIGH_DWORD_BOOL = lines_matcher(["VMStructFieldByte($O[ZERO_HIGH_DWORD_BOOL]) = 0x0"])

def binary_math_op(op_name, op, read_flag=False):
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))" % (op_name,),
                                           ])] +
                           (read_flag and [lines_matcher(["var_1 = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None))"])] or []) +
                            duplicate_by_size(["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (op_name, ),
                                               "    $V[%s_VAR_DST] = ($V[%s_VAR_DST] %s $V[%s_VAR_SRC])" % (op_name, op_name, op, op_name),
                                               "    var_1 = Flags(($V[%s_VAR_DST] %s $V[%s_VAR_SRC]))" % (op_name, op, op_name)]) +
                           [lines_matcher(["VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_DST])" % (op_name,)])])

def binary_compare_op(op_name, op, read_flag=False):
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
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
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
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
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "var_1 = Flags(($V[%s_VAR_DST] %s $V[%s_VAR_SRC]))" % (op_name, op, op_name),
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue(($V[%s_VAR_DST] %s $V[%s_VAR_SRC]))" % (op_name, op, op_name)])])

def binary_mov_op():
    op_name = "MOV"
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))" % (op_name,),
                                           "var_1 = Flags(($V[%s_VAR_SRC] + $V[%s_VAR_SRC]))" % (op_name, op_name),
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_SRC])" % (op_name,)])])

UPDATE_FLAGS = lines_matcher(["If((ReadParameterByte($P[UPDATE_FLAGS], None) != 0x0))",
                              "    VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None)) = var_1"])


UPDATE_RESULT = match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) != $H[OPERATION_CMP]))",
    [match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) != $H[OPERATION_TEST]))",
         [
             lines_matcher_any_order(
                 ["$V[RESULT_VAR] = DecodedValue(VMStructField{SS}($U[RESULT]))",
                  "$V[RESULT_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))",
                  "$V[RESULT_VAR_ADDRESS] = DecodedValue(VMStructField{SS}($U[DST_ADDRESS]))"]),
             lines_matcher(
                 ["If(($V[RESULT_VAR_SIZE] == 0x1))",
                  "    *(BYTE*)$V[RESULT_VAR_ADDRESS] = $V[RESULT_VAR]",
                  "If(($V[RESULT_VAR_SIZE] == 0x2))",
                  "    *(WORD*)$V[RESULT_VAR_ADDRESS] = $V[RESULT_VAR]"]),
             match_condition("If(($V[RESULT_VAR_SIZE] == 0x3))",
                [
                  lines_matcher(["*(DWORD*)$V[RESULT_VAR_ADDRESS] = $V[RESULT_VAR]"]),
                  only_64(lines_matcher(
                    ["$V[RESULT_VAR] = VMStructFieldByte($O[ZERO_HIGH_DWORD_BOOL])",
                     "If(($V[RESULT_VAR] != 0x0))",
                     "    $V[RESULT_VAR_ADDRESS] = ($V[RESULT_VAR_ADDRESS] + 0x4)",
                     "    *(DWORD*)$V[RESULT_VAR_ADDRESS] = 0x0"]))
                ]),
             only_64(lines_matcher(
                ["If(($V[RESULT_VAR_SIZE] == 0x4))",
                 "    *(QWORD*)$V[RESULT_VAR_ADDRESS] = $V[RESULT_VAR]"])),

         ])
    ])

COMMON_BINARY_OP = HandlerMatch(match_funcs([
    any_order_with_key_updates([read_acc_byte(1, "OPERATION"), read_encoded_param(2), read_encoded_param(3), read_two_nibbles(4), read_two_nibbles(5)]),
    any_order_with_key_updates([RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("DST", True), read_memvar_and_keep_address("DST"),
                                only_64(load_high_dword("SRC")), read_var("SRC"), read_memvar("SRC")]),
    # TODO as switch
    any_order_with_key_updates([binary_math_op("ADD", "+"), binary_math_op("SUB", "-"),
                                binary_math_op("XOR", "^"), binary_math_op("AND", "&"), binary_math_op("OR", "|"),
                                binary_math_op("SHL", "<<", True), binary_math_op("SHR", ">>", True),
                                binary_math_op("ROL", "rol", True), binary_math_op("ROR", "ror", True),
                                binary_math_op("RCL", "rcl", True), binary_math_op("RCR", "rcr", True),
                                binary_compare_op("CMP", "Compare"), binary_compare_op("TEST", "Test"),
                                binary_movzx_movsx_op("MOVZX"), binary_movzx_movsx_op("MOVSX"),
                                binary_mul_op(), binary_mov_op()
                                ]),
    # Now give the names for the parameters
    at_start(any_order_with_key_updates([read_acc_byte(6, "OPERATION"),
                                         read_encoded_param(7, "SRC_VALUE"), read_encoded_param(8, "DST_VALUE"),
                                         read_two_nibbles(9, "SRC_TYPE_AND_SIZE", ("SRC_TYPE", "SRC_SIZE")),
                                         read_two_nibbles(10, "DST_TYPE_AND_SIZE", ("DST_TYPE", "DST_SIZE"))])),
    any_order_with_key_updates([UPDATE_FLAGS, UPDATE_RESULT]),
    UPDATE_IP_AND_JUMP
    ]), None) # TODO

def unary_math_op(op_name, op, read_flag=False):
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["$V[%s_VAR_VALUE] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))" % (op_name,),
                                           "$V[%s_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))" % (op_name,),
                                           ])] +
                           (read_flag and [lines_matcher(["var_1 = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET], None))"])] or []) +
                            duplicate_by_size(["If(($V[%s_SIZE_VAR] == 0x@LOGSIZE@))" % (op_name, ),
                                               "    $V[%s_VAR_VALUE] = (%s$V[%s_VAR_VALUE])" % (op_name, op, op_name),
                                               "    var_1 = Flags((%s$V[%s_VAR_VALUE]))" % (op, op_name)]) +
                           [lines_matcher(["VMStructField{SS}($U[RESULT]) = EncodedValue($V[%s_VAR_VALUE])" % (op_name,)])])

def unary_math_not():
    op_name = "NOT"
    return match_condition("If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_%s]))" % (op_name,),
                           [lines_matcher(["var_1 = RandomFlags()",
                                           "VMStructField{SS}($U[RESULT]) = EncodedValue((~DecodedValue(VMStructField{SS}($U[DST_VALUE]))))"])])

COMMON_UNARY_OP = HandlerMatch(match_funcs([
    any_order_with_key_updates([read_acc_byte(1, "OPERATION"), read_encoded_param(2, "VALUE", "DST_VALUE"),
                                read_two_nibbles(4, "TYPE_AND_SIZE", ("DST_TYPE", "DST_SIZE"))]),
    any_order_with_key_updates([RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("DST", True), read_memvar_and_keep_address("DST")]),
    # TODO as switch
    any_order_with_key_updates([unary_math_op("INC", "++", True), unary_math_op("DEC", "--", True),
                                unary_math_op("NEG", "-"), unary_math_not(),
                                ]),
    any_order_with_key_updates([UPDATE_FLAGS, UPDATE_RESULT]),
    UPDATE_IP_AND_JUMP
    ]), None) # TODO

PUSH_POP_MAIN = lines_matcher(["If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_PUSH]))",
                               "    If(($V[SIZE_VAR] == 0x2))",
                               "        PushWord($V[VALUE])",
                               "    Else",
                               "        Push($V[VALUE])",
                               "If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_POP]))",
                               "    $V[VALUE] = DecodedValue(VMStructField{SS}($U[VALUE_ADDRESS]))",
                               "    If(($V[SIZE_VAR] == 0x2))",
                               "        *(WORD*)$V[VALUE] = PopWord()",
                               "    Else",
                               "        *({SU}*)$V[VALUE] = Pop()"])

# BUG: Pop word doesn't seem to work...
PUSH_POP_UPDATE_STACK = lines_matcher(["If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_PUSH]))",
                                       "    If((LOW_NIBBLE(DecodedValueByte(VMStructFieldByte($U[VALUE_SIZE]))) == 0x2))",
                                       "        *({SU}*)$V[SP_OFFSET] -= 0x2",
                                       "    Else",
                                       "        *({SU}*)$V[SP_OFFSET] -= 0x{N}",
                                       "If((DecodedAccByte($[DECODE_ACC_1], $[DECODE_ACC_2]) == $H[OPERATION_POP]))",
                                       "    If((DecodedValue(VMStructField{SS}($U[VALUE_ADDRESS])) != $V[SP_OFFSET]))",
                                       "        *({SU}*)$V[SP_OFFSET] += 0x{N}"])

PUSH_POP = HandlerMatch(match_funcs([
    any_order_with_key_updates([read_acc_byte(1, "OPERATION"), read_encoded_param(2, "VALUE", "VALUE_VALUE"),
                                read_two_nibbles(3, "TYPE_AND_SIZE", ("VALUE_TYPE", "VALUE_SIZE"))]),
    any_order_with_key_updates([RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("VALUE", True), read_memvar_and_keep_address("VALUE")]),
    lines_matcher(["$V[VALUE] = DecodedValue(VMStructField{SS}($U[VALUE_VALUE]))"]),
    update_keys,
    lines_matcher(["$V[SIZE_VAR] = LOW_NIBBLE(DecodedValueByte(VMStructFieldByte($U[VALUE_SIZE])))"]),
    update_keys,
    PUSH_POP_MAIN,
    update_keys,
    lines_matcher(["$V[SP_OFFSET] = VMStructOffset(ReadParameterWord($P[SP_OFFSET], None))"]),
    update_keys,
    PUSH_POP_UPDATE_STACK,
    update_keys,
    UPDATE_IP_AND_JUMP
    ]), None)

XCHG_OPERATION_0 = lines_matcher_any_order(["$V[XCHG_VAR_DST] = DecodedValue(VMStructField{SS}($U[DST_VALUE]))",
                                            "$V[XCHG_VAR_SIZE] = DecodedValueByte(VMStructFieldByte($U[DST_SIZE]))",
                                            "$V[XCHG_VAR_SRC_ADDRESS] = DecodedValue(VMStructField{SS}($U[SRC_ADDRESS]))"])

XCHG_OPERATION = match_funcs(
    duplicate_by_size(["If(($V[XCHG_SIZE_VAR] == 0x@LOGSIZE@))",
                       "    *({SU:@SIZE@}*)$V[XCHG_VAR_SRC_ADDRESS] = $V[XCHG_VAR_DST]"]) +
    [lines_matcher(["$V[XCHG_VAR_SRC] = DecodedValue(VMStructField{SS}($U[SRC_VALUE]))",
                    "$V[XCHG_VAR_DST_ADDRESS] = DecodedValue(VMStructField{SS}($U[DST_ADDRESS]))"])] +
    duplicate_by_size(["If(($V[XCHG_SIZE_VAR] == 0x@LOGSIZE@))",
                       "    *({SU:@SIZE@}*)$V[XCHG_VAR_DST_ADDRESS] = $V[XCHG_VAR_SRC]"]))

XCHG_T = [RESET_ZERO_HIGH_DWORD_BOOL, read_var_and_keep_address("DST", True), read_memvar_and_keep_address("DST"),
          read_var_and_keep_address("SRC"), read_memvar_and_keep_address("SRC")]

# There isn't key updates in xchg, but we will do it with key updates because sometime afte reading two nibbles,
# there is and UpdateKey for Key1 which we don'e handle.
XCHG = HandlerMatch(match_funcs([
    any_order_with_key_updates([read_encoded_param(2), read_encoded_param(3), read_two_nibbles(4), read_two_nibbles(5)]),
    # Because it may confused between SRC and DST
    match_one([match_funcs([any_order(XCHG_T), XCHG_OPERATION_0]),
               match_funcs([any_order(XCHG_T[::-1]), XCHG_OPERATION_0])]),
    # Now give the names for the parameters
    at_start(any_order_with_key_updates([read_encoded_param(7, "SRC_VALUE"), read_encoded_param(8, "DST_VALUE"),
                                         read_two_nibbles(9, "SRC_TYPE_AND_SIZE", ("SRC_TYPE", "SRC_SIZE")),
                                         read_two_nibbles(10, "DST_TYPE_AND_SIZE", ("DST_TYPE", "DST_SIZE"))])),
    XCHG_OPERATION,
    UPDATE_IP_AND_JUMP
    ]), None)


POP_RET = match_funcs([
    lines_matcher(["VMStructFieldDword(?O[LOCK]) = 0x0"]),
    only_64(lines_matcher(["{R:%s} = Pop()" % reg for reg in ["r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]])),
    lines_matcher(["{R:%s} = Pop()" % reg for reg in ["di", "si", "bp", "bx", "dx", "cx" ,"ax"]]),
    lines_matcher(["Return(0)"]),
])

JMP_MEMVAR = HandlerMatch(match_funcs([
    lines_matcher(["*({SU}*)(ReadParameterWord($P[STACK_RETURN_OFFSET], None) + SP) = *({SU}*)VMStructField{SS}(ReadParameterWord($P[VAR], None))"]),
    POP_RET,
]), create_handler_reader_class(lambda x: "JMP_MEMVAR", lambda x: [x.params["VAR"]]))

JMP_VAR = HandlerMatch(match_funcs([
    lines_matcher(["*({SU}*)(ReadParameterWord($P[STACK_RETURN_OFFSET], None) + SP) = VMStructField{SS}(ReadParameterWord($P[VAR], None))"]),
    POP_RET,
]), create_handler_reader_class(lambda x: "JMP_VAR", lambda x: [x.params["VAR"]]))

JMP_IMM = HandlerMatch(match_funcs([
    lines_matcher(["*({SU}*)(ReadParameterWord($P[STACK_RETURN_OFFSET], None) + SP) = (ReadParameterDword($P[IMM], None) + VMStructField{SS}(?O[BASE_ADDRESS]))"]),
    POP_RET,
]), create_handler_reader_class(lambda x: "JMP_IMM", lambda x: [x.params["IMM"]]))

CALL = HandlerMatch(match_funcs([
    lines_matcher(
        ["$V[VAR_CALL_TYPE] = ReadParameterByte($P[CALL_TYPE], None)",
         "If(($V[VAR_CALL_TYPE] == $H[CALL_TYPE_IMM]))",
         "    $V[VAR_STACK] = (ReadParameterWord($P[STACK_RETURN_OFFSET], None) + SP)",
         "    *({SU}*)$V[VAR_STACK] = (ReadParameterDword($P[VALUE], None) + VMStructField{SS}(?O[BASE_ADDRESS]))",
         "If((($V[VAR_CALL_TYPE] == $H[CALL_TYPE_VAL]) || ($V[VAR_CALL_TYPE] == $H[CALL_TYPE_MEMVAL])))",
         "    $V[VAR_VALUE] = VMStructField{SS}(ReadParameterWord($P[VALUE], None))",
         "    If(($V[VAR_CALL_TYPE] == $H[CALL_TYPE_MEMVAL]))",
         "        $V[VAR_VALUE] = *({SU}*)$V[VAR_VALUE]",
         "    $V[VAR_STACK] = (ReadParameterWord($P[STACK_RETURN_OFFSET], None) + SP)",
         "    *({SU}*)$V[VAR_STACK] = $V[VAR_VALUE]",
         "*({SU}*)($V[VAR_STACK] + 0x{N}) = (ReadParameterDword($P[RETURN_ADDRESS], None) + VMStructField{SS}(?O[BASE_ADDRESS]))"]),
    POP_RET
]), create_handler_reader_class(lambda x: "CALL_%s_NEXT" % x.params["CALL_TYPE"], lambda x: [x.params["VALUE"], x.params["RETURN_ADDRESS"]]))

JMP = HandlerMatch(UPDATE_IP_AND_JUMP_PARAM, None)

UNK_JMP_IMM = HandlerMatch(match_funcs([
    lines_matcher([
        "$V[ADDRS_COUNT] = ReadParameterByte($P[ADDRS_COUNT], None)",
        "If((($V[ADDRS_COUNT] == 0x1) || ($V[ADDRS_COUNT] == 0x2)))",
        "    If((*({SU}*)(ReadParameterByte($P[ADDRESS_OFFSET_1], None) + (ReadParameterDword($P[IMM], None) + VMStructField{SS}(?O[BASE_ADDRESS]))) != (ReadParameterDword($P[TARGET_ADDRESS], None) + VMStructField{SS}(?O[BASE_ADDRESS]))))",
        "        $V[BASE_ADDRESS] = VMStructField{SS}(?O[BASE_ADDRESS])",
        "        $V[ADDRESS_ADDRESS] = ((ReadParameterByte($P[ADDRESS_OFFSET_1], None) + ReadParameterDword($P[IMM], None)) + $V[BASE_ADDRESS])",
        "        *({SU}*)$V[ADDRESS_ADDRESS] -= VMStructField{SS}($[UNK_ADDRESS_OFFSET])",
        "        *({SU}*)$V[ADDRESS_ADDRESS] += VMStructField{SS}(?O[BASE_ADDRESS])",
        "        If((ReadParameterByte($P[ADDRS_COUNT], None) == 0x2))",
        "            $V[ADDRESS_ADDRESS] = ((ReadParameterByte($P[ADDRESS_OFFSET_2], None) + ReadParameterDword($P[IMM], None)) + $V[BASE_ADDRESS])",
        "            *({SU}*)$V[ADDRESS_ADDRESS] -= VMStructField{SS}($[UNK_ADDRESS_OFFSET])",
        "            *({SU}*)$V[ADDRESS_ADDRESS] += VMStructField{SS}(?O[BASE_ADDRESS])",
    ]),
    JMP_IMM.match_func
]), None)

MOV_VAR_UNKVAR = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR], None)) = VMStructField{SS}($O[UNK_VAR])"]),
    UPDATE_IP_AND_JUMP,
]), None)

MOV_VAR_SP = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR], None)) = SP"]),
    UPDATE_IP_AND_JUMP,
]), None)

UNK_CALLS = HandlerMatch(match_funcs([lines_matcher([
    "Push(VMStructField{SS}(ReadParameterWord($P[P1], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P2], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P3], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P4], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P5], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P6], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P7], None)))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P8], None)))",
    "Push(VMStructOffset(0x0))",
    "Push(VMStructOffset(0x0))"])
]), None)

ADD_VAR_BASEADDRESS = HandlerMatch(match_funcs([
    update_keys,
    lines_matcher(["VMStructField{SS}($N[VAR]) = EncodedValue(ReadParameterDword($P[VAR], $[DECODE_VAR]))",
                   "VMStructField{SS}((DecodedValue(VMStructField{SS}($N[VAR])) & 0xFFFF)) += VMStructField{SS}(?O[BASE_ADDRESS])"]),
    UPDATE_IP_AND_JUMP,
]), None)

ADD_VAR_IMM = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR], None)) += ReadParameterByte($P[IMM], None)"]),
    UPDATE_IP_AND_JUMP,
]), None)


NOP = HandlerMatch(match_funcs([
    UPDATE_IP_AND_JUMP,
]), None)


#("ja", "jae", "jb", "jbe", "jz", "jg", "jge", "jl", "jle", "jnz", "jno", "jnp", "jns", "jo", "jp" ,"js")

JZ = lines_matcher(["If((($V[CHECK_TYPE] == $H[CHECK_TYPE_JZ]) || ($V[CHECK_TYPE] == $H[CHECK_TYPE_JLE])))",
                    "    If(($V[FLAGS] & 0x40))",
                    "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1",
                    "    $V[FLAGS] = $V[FLAGS]"])

JNZ = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JNZ]))",
                     "    $V[FLAGS] = ($V[FLAGS] & 0x40)",
                     "    If((!$V[FLAGS]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JA = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JA]))",
                    "    $V[FLAGS2] = $V[FLAGS]",
                    "    $V[FLAGS] = ($V[FLAGS] & 0x40)",
                    "    If((!$V[FLAGS]))",
                    "        If((!($V[FLAGS2] & 0x1)))",
                    "            VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JAE = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JAE]))",
                     "    $V[FLAGS] = ($V[FLAGS] & 0x1)",
                     "    If((!$V[FLAGS]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JB = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JB]))",
                    "    $V[FLAGS] = ($V[FLAGS] & 0x1)",
                    "    If($V[FLAGS])",
                    "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JBE = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JBE]))",
                     "    $V[FLAGS2] = $V[FLAGS]",
                     "    $V[FLAGS] = ($V[FLAGS] & 0x40)",
                     "    If($V[FLAGS])",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1",
                     "    If(($V[FLAGS2] & 0x1))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JG = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JG]))",
                    "    If((!($V[FLAGS] & 0x40)))",
                    "        $V[FLAGS2] = (($V[FLAGS] & 0x800) >> 0xB)",
                    "        $V[FLAGS] = (($V[FLAGS] & 0x80) >> 0x7)",
                    "        If(($V[FLAGS] == $V[FLAGS2]))",
                    "            VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JGE = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JGE]))",
                     "    $V[FLAGS2] = (($V[FLAGS] & 0x800) >> 0xB)",
                     "    $V[FLAGS] = (($V[FLAGS] & 0x80) >> 0x7)",
                     "    If(($V[FLAGS] == $V[FLAGS2]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JL = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JL]))",
                    "    $V[FLAGS2] = (($V[FLAGS] & 0x800) >> 0xB)",
                    "    $V[FLAGS] = (($V[FLAGS] & 0x80) >> 0x7)",
                    "    If(($V[FLAGS] != $V[FLAGS2]))",
                    "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JLE = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JLE]))",
                     "    If(($V[FLAGS] & 0x40))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1",
                     "    $V[FLAGS2] = (($V[FLAGS] & 0x800) >> 0xB)",
                     "    $V[FLAGS] = (($V[FLAGS] & 0x80) >> 0x7)",
                     "    If(($V[FLAGS] != $V[FLAGS2]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JNO = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JNO]))",
                     "    $V[FLAGS] = ($V[FLAGS] & 0x800)",
                     "    If((!$V[FLAGS]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JNP = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JNP]))",
                     "    $V[FLAGS] = ($V[FLAGS] & 0x4)",
                     "    If((!$V[FLAGS]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JNS = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JNS]))",
                     "    $V[FLAGS] = ($V[FLAGS] & 0x80)",
                     "    If((!$V[FLAGS]))",
                     "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JO = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JO]))",
                    "    $V[FLAGS] = ($V[FLAGS] & 0x800)",
                    "    If($V[FLAGS])",
                    "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JP = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JP]))",
                    "    $V[FLAGS] = ($V[FLAGS] & 0x4)",
                    "    If($V[FLAGS])",
                    "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JS = lines_matcher(["If(($V[CHECK_TYPE] == $H[CHECK_TYPE_JS]))",
                    "    If(($V[FLAGS] & 0x80))",
                    "        VMStructFieldByte($O[TAKE_JUMP]) = 0x1"])

JCC = match_funcs([
    lines_matcher([
        "VMStructFieldByte($O[TAKE_JUMP]) = 0x0",
        "$V[FLAGS] = VMStructFieldDword(ReadParameterWord($P[FLAGS_OFFSET], None))",
        "$V[CHECK_TYPE] = ReadParameterByte($P[CHECK_TYPE], None)"
    ]),
    JZ, JNZ, JA, JAE, JB, JBE, JG, JGE, JL, JLE, JNO, JNP, JNS, JO, JP, JS])

JCC_INSIDE = HandlerMatch(match_funcs([
    JCC,
    match_condition("If((VMStructFieldByte($O[TAKE_JUMP]) != 0x0))", [UPDATE_IP_AND_JUMP_PARAM]),
    UPDATE_IP_AND_JUMP,
]), None)

JCC_OUTSIDE = HandlerMatch(match_funcs([
    JCC,
    match_condition("If((VMStructFieldByte($O[TAKE_JUMP]) != 0x0))", [JMP_IMM.match_func]),
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[SP_OFFSET], None)) += $H[STACK_CLEAR_SIZE]"]),
    UPDATE_IP_AND_JUMP,
]), None)

PUSH_VAR = HandlerMatch(match_funcs([
    any_order_with_key_updates([lines_matcher(["Push(VMStructField{SS}(ReadParameterWord($P[VAR], None)))"]),
                   lines_matcher(["VMStructField{SS}(ReadParameterWord($P[SP_OFFSET], None)) -= 0x{N}"])]),
    UPDATE_IP_AND_JUMP,
]), None)

POP_VAR = HandlerMatch(match_funcs([
    any_order_with_key_updates([lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR], None)) = Pop()"]),
                   lines_matcher(["VMStructField{SS}(ReadParameterWord($P[SP_OFFSET], None)) += 0x{N}"])]),
    UPDATE_IP_AND_JUMP,
]), None)


CLC = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_CLC]))",
                     "    *(DWORD*)$V[FLAGS_OFFSET] &= (~0x1)"])

CLD = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_CLD]))",
                     "    $V[FLAGS2] = (~0x400)",
                     "    *(DWORD*)$V[FLAGS_OFFSET] &= $V[FLAGS2]",
                     "    VMStructFieldDword(?O[FLAGS]) &= $V[FLAGS2]"])

CLI = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_CLI]))",
                     "    $V[FLAGS2] = (~0x200)",
                     "    *(DWORD*)$V[FLAGS_OFFSET] &= $V[FLAGS2]",
                     "    VMStructFieldDword(?O[FLAGS]) &= $V[FLAGS2]"])

CMC = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_CMC]))",
                     "    If(((*(DWORD*)$V[FLAGS_OFFSET] & 0x1) != 0x0))",
                     "        *(DWORD*)$V[FLAGS_OFFSET] &= (~0x1)",
                     "    Else",
                     "        *(DWORD*)$V[FLAGS_OFFSET] |= 0x1"])

STC = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_STC]))",
                     "    *(DWORD*)$V[FLAGS_OFFSET] |= 0x1"])

STD = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_STD]))",
                     "    *(DWORD*)$V[FLAGS_OFFSET] |= 0x400",
                     "    VMStructFieldDword(?O[FLAGS]) |= 0x400"])

STI = lines_matcher(["If(($V[FLAGS_OP] == $H[FLAGS_OP_STI]))",
                     "    *(DWORD*)$V[FLAGS_OFFSET] |= 0x200",
                     "    VMStructFieldDword(?O[FLAGS]) |= 0x200"])

FLAGS_OP = HandlerMatch(match_funcs([
    lines_matcher([
        "$V[FLAGS_OFFSET] = VMStructOffset(ReadParameterWord($P[FLAGS_OFFSET], None))",
        "$V[FLAGS_OP] = ReadParameterByte($P[FLAGS_OP], None)"
    ]),
    CLC, CLD, CLI, CMC, STC, STD, STI,
    UPDATE_IP_AND_JUMP]), None)

RESET_FLAGS = HandlerMatch(match_funcs([
    lines_matcher(["VMStructFieldDword($O[FLAGS]) = 0x0"]),
    UPDATE_IP_AND_JUMP,
]), None)

HANDLERS = [VM_INIT,
            COPY_STACK_RETURN,
            MOVS,
            LODS,
            STOS,
            SCAS,
            CMPS,
            COMMON_BINARY_OP,
            JMP,
            JMP_IMM,
            JMP_VAR,
            JMP_MEMVAR,
            JCC_INSIDE,
            JCC_OUTSIDE,
            CALL,
            MOV_VAR_UNKVAR,
            MOV_VAR_SP,
            ADD_VAR_BASEADDRESS,
            ADD_VAR_IMM,
            PUSH_VAR,
            POP_VAR,
            PUSH_POP,
            NOP,
            UNK_CALLS,
            FLAGS_OP,
            RESET_FLAGS,
            UNK_JMP_IMM,
            XCHG,
            COMMON_UNARY_OP,
            ]


def match_handlers(parser, handler, fields, handlers, arch):
    instructions = handler.get_instructions()
    for h in handlers:
        index = 0
        params = handlers_parser.Params(fields)
        info = HandlerInfo()
        match, index = h.match_func(parser, instructions, index, params, arch, info)
        if not match or index != len(instructions):
            continue
        info.params.update(params.parameters)
        info.vars.update(params.handler_vars)
        # TODO: read_info
        info.reader = h.reader

        fields.update(params.fields)
        return info
    return None