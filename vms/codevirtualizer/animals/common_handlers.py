from collections import namedtuple
import vms.vminstruction as vminstruction
import handlers_parser
import re

HandlerMatch = namedtuple("HandlerMatch", ["match_func", "reader"])


class HandlerInfo(object):
    def __init__(self):
        self.params = {}
        self.vars = {}
        self.read_info = []
        self.reader = None


class HandlerReader(object):
    def __init__(self, info, params, arch):
        self.info = info
        self.params = {}
        self.arch = arch
        for name, index in self.info.params.iteritems():
            self.params[name] = params[index]
        assert len(self.params) == len(params)
        for name, value in self.params.iteritems():
            for iname, ivalue in self.info.vars.iteritems():
                if ivalue == value and iname.startswith(name + "_"):
                    self.params[name] = iname[len(name) + 1:]
                    break

    def get_name(self):
        pass

    def get_params(self):
        return []

    def get_instruction(self):
        return vminstruction.VMInstruction(self.get_name(), *self.get_params())

    def get_next_handler(self):
        if "NEXT_HANDLER" in self.params:
            return self.params["NEXT_HANDLER"]
        else:
            return None

    def get_size(self):
        return self.info.vars["OPCODE_SIZE"]

def create_handler_reader_class(name, params=[]):
    def create_handler_name_from_params(reader):
        ns = name
        params = reader.params
        for var in re.findall("\{([\w:]+)\}", name):
            t, n = var.split(":")
            if t == "O": # Operation
                nvar = params[n]
                assert type(nvar) is str
            else:
                raise Exception("Invalid var: %s" % var)
            ns = ns.replace("{%s}" % var, nvar)
        return ns

    class GenericHandlerReader(HandlerReader):
        def get_name(self):
            return create_handler_name_from_params(self)

        def get_params(self):
            ret = []
            for x in params:
                ret.append(self.params[x])
                # Hack for 64bit numbers
                if self.arch.native_size() == 8 and \
                        x == "SRC_VALUE" and "SRC_LOAD_HIGH_DWORD" in self.params and self.params["SRC_LOAD_HIGH_DWORD"]:
                    ret[-1] |= self.params["SRC_HIGH_DWORD"] << 0x20
            return ret

    return GenericHandlerReader

def create_string_op_handler_reader(op_name):
    class StringOpHandlerReader(HandlerReader):
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

def any_order(funcs):
    def _match_funcs(parser, instructions, index, params, arch, info):
        left = list(funcs)
        nparams = params.copy()
        while len(left) > 0:
            for func in left:
                match, nindex = func(parser, instructions, index, nparams, arch, info)
                if match:
                    index = nindex
                    left.remove(func)
                    break
            if not match:
                return False, index
        params.update(nparams)
        return True, index
    return _match_funcs

def lines_matcher_any_order(lines):
    return any_order([lines_matcher([x]) for x in lines])

def only_32(func):
    def _func(parser, instructions, index, params, arch, info):
        if arch.native_size() == 4:
            return func(parser, instructions, index, params, arch, info)
        else:
            return True, index
    return _func

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
        "JumpToHandler(ReadParameterWord($P[NEXT_HANDLER]))"
    ])

UPDATE_IP_AND_JUMP_PARAM = lines_matcher(\
    [
        "UpdateEip(ReadParameterDword($P[JUMP_VALUE]))",
        "JumpToHandler(ReadParameterWord($P[JUMP_HANDLER]))"
    ])


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
            if not params.set_handler_var_value("SIZE", size):
                return False, index
        return True, index
    return _func


READ_SI = string_op(["$V[VAR_SI_OFFSET] = VMStructOffset(ReadParameterWord($P[SI_OFFSET]))"])
READ_DI = string_op(["$V[VAR_DI_OFFSET] = VMStructOffset(ReadParameterWord($P[DI_OFFSET]))"])

def UPDATE_SI_DI(fish):
    if fish:
        n = "Dword"
    else:
        n = "{SS}"
    return match_one([string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) & 0x400) | (VMStructField%s($O[FLAGS]) & 0x400)) != 0x0))" % n,
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_SI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_SI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"]),
                          string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) & 0x400) | (VMStructField%s($O[FLAGS]) & 0x400)) != 0x0))" % n,
         "    *({SU}*)$V[VAR_SI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_SI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])])

UPDATE_DI = string_op(
        ["If(((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) & 0x400) != 0x0))",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

UPDATE_DI2 = string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) & 0x400) | (VMStructFieldDword($O[FLAGS]) & 0x400)) != 0x0))",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

# For tiger
UPDATE_DI3 = string_op(
        ["If((((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) & 0x400) | (VMStructField{SS}($O[FLAGS]) & 0x400)) != 0x0))",
         "    *({SU}*)$V[VAR_DI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_DI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

UPDATE_SI = string_op(
        ["If(((VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) & 0x400) != 0x0))",
         "    *({SU}*)$V[VAR_SI_OFFSET] -= 0x$G[SIZES_NUM:SIZE_NUM]",
         "Else",
         "    *({SU}*)$V[VAR_SI_OFFSET] += 0x$G[SIZES_NUM:SIZE_NUM]"])

MOVS_MAIN = string_op(["*($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[DI_OFFSET])) = *($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[SI_OFFSET]))"])

# BUG, it seems to be wrong..

SCAS_MAIN = match_one([string_op(["$V[VAR_DI] = VMStructField{SS}(ReadParameterWord($P[DI_OFFSET]))",
                                  "$V[VAR_AX] = VMStructField{SS}(ReadParameterWord($P[AX_OFFSET]))",
                                  "*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX]"]),
                       string_op(["$V[VAR_AX] = VMStructField{SS}(ReadParameterWord($P[AX_OFFSET]))",
                                  "$V[VAR_DI] = VMStructField{SS}(ReadParameterWord($P[DI_OFFSET]))",
                                  "*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX]"])])

SCAS_UPDATE_FLAGS_1 = string_op(["var_1 = Flags(*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX])"])

SCAS_UPDATE_FLAGS_2 = string_op(["VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET])) = var_1"])

SCAS_UPDATE_FLAGS = string_op(["VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET])) = Flags(*($G[SIZES:SIZE]*)$V[VAR_DI] -= $V[VAR_AX])"])

CMPS_UPDATE_FLAGS_1 = string_op(["VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET])) = Flags(Compare(*($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[SI_OFFSET])), *($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[DI_OFFSET]))))"])

CMPS_UPDATE_FLAGS_2 = string_op(["VMStructField{SS}(ReadParameterWord($P[SET_FLAGS_OFFSET])) = Flags(Compare(*($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[DI_OFFSET])), *($G[SIZES:SIZE]*)VMStructField{SS}(ReadParameterWord($P[SI_OFFSET]))))"])

STOS_MAIN = string_op(["*($G[SIZES:SIZE]*)*({SU}*)$V[VAR_DI_OFFSET] = VMStructField$G[SIZES2:SIZE2](ReadParameterWord($P[AX_OFFSET]))"])

LODS_MAIN = string_op(["VMStructField$G[SIZES2:SIZE2](ReadParameterWord($P[AX_OFFSET])) = *($G[SIZES:SIZE]*)*({SU}*)$V[VAR_SI_OFFSET]"])


LODS = HandlerMatch(match_funcs([
    READ_SI,
    LODS_MAIN,
    UPDATE_SI,
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("LODS"))

STOS = HandlerMatch(match_funcs([
    READ_DI,
    STOS_MAIN,
    UPDATE_DI,
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("STOS"))

POP_RET = match_funcs([
    lines_matcher(["VMStructFieldDword(?O[LOCK]) = 0x0"]),
    only_64(lines_matcher(["{R:%s} = Pop()" % reg for reg in ["r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]])),
    lines_matcher(["{R:%s} = Pop()" % reg for reg in ["di", "si", "bp", "bx", "dx", "cx" ,"ax"]]),
    lines_matcher(["Return(0)"]),
])

# TODO: Decompilation wrong (var_edi should'nt be optimized)
RETURN = HandlerMatch(match_funcs([lines_matcher([
        "$V[STACK_MOVE_OFFSET] = ReadParameterDword($P[STACK_MOVE_OFFSET])",
        "$V[STACK_TO_MOVE] = (SP + $H[STACK_SIZE])",
        "Std()",
        "$V[STACK_COPY_SIZE] = $V[STACK_MOVE_OFFSET]",
        "If(($V[STACK_COPY_SIZE] != 0x0))",
        "    $V[STACK_COPY_SIZE] = $H[STACK_COPY_SIZE]",
        "MemCopy(($V[STACK_TO_MOVE] + $V[STACK_COPY_SIZE]), $V[STACK_TO_MOVE], $V[STACK_COPY_SIZE])",
        "SP += ReadParameterDword($P[STACK_MOVE_OFFSET])",
        "$V[VAR] = (SP + $H[STACK_RETURN_OFFSET])",
        "*({SU}*)($V[VAR] + 0x{N}) = *({SU}*)$V[VAR]",
    ]),
    POP_RET
    ]),
    create_handler_reader_class("RETURN", ["STACK_MOVE_OFFSET"]))

JMP_MEMVAR = HandlerMatch(match_funcs([
    lines_matcher(["*({SU}*)(ReadParameterWord($P[STACK_RETURN_OFFSET]) + SP) = *({SU}*)VMStructField{SS}(ReadParameterWord($P[VAR]))"]),
    POP_RET,
]), create_handler_reader_class("JMP_MEMVAR", ["VAR"]))

JMP_VAR = HandlerMatch(match_funcs([
    lines_matcher(["*({SU}*)(ReadParameterWord($P[STACK_RETURN_OFFSET]) + SP) = VMStructField{SS}(ReadParameterWord($P[VAR]))"]),
    POP_RET,
]), create_handler_reader_class("JMP_VAR", ["VAR"]))

JMP_IMM = HandlerMatch(match_funcs([
    lines_matcher(["*({SU}*)(ReadParameterWord($P[STACK_RETURN_OFFSET]) + SP) = (ReadParameterDword($P[IMM]) + VMStructField{SS}(?O[BASE_ADDRESS]))"]),
    POP_RET,
]), create_handler_reader_class("JMP_IMM", ["IMM"]))


JMP = HandlerMatch(UPDATE_IP_AND_JUMP_PARAM, create_handler_reader_class("JMP", ["JUMP_VALUE", "JUMP_HANDLER"]))

UNK_JMP_IMM = HandlerMatch(match_funcs([
    lines_matcher([
        "$V[ADDRS_COUNT] = ReadParameterByte($P[ADDRS_COUNT])",
        "If((($V[ADDRS_COUNT] == 0x1) || ($V[ADDRS_COUNT] == 0x2)))",
        "    If((*({SU}*)(ReadParameterByte($P[ADDRESS_OFFSET_1]) + (ReadParameterDword($P[IMM]) + VMStructField{SS}(?O[BASE_ADDRESS]))) != (ReadParameterDword($P[TARGET_ADDRESS]) + VMStructField{SS}(?O[BASE_ADDRESS]))))",
        "        $V[BASE_ADDRESS] = VMStructField{SS}(?O[BASE_ADDRESS])",
        "        $V[ADDRESS_ADDRESS] = ((ReadParameterByte($P[ADDRESS_OFFSET_1]) + ReadParameterDword($P[IMM])) + $V[BASE_ADDRESS])",
        "        *({SU}*)$V[ADDRESS_ADDRESS] -= VMStructField{SS}($[UNK_ADDRESS_OFFSET])",
        "        *({SU}*)$V[ADDRESS_ADDRESS] += VMStructField{SS}(?O[BASE_ADDRESS])",
        "        If((ReadParameterByte($P[ADDRS_COUNT]) == 0x2))",
        "            $V[ADDRESS_ADDRESS] = ((ReadParameterByte($P[ADDRESS_OFFSET_2]) + ReadParameterDword($P[IMM])) + $V[BASE_ADDRESS])",
        "            *({SU}*)$V[ADDRESS_ADDRESS] -= VMStructField{SS}($[UNK_ADDRESS_OFFSET])",
        "            *({SU}*)$V[ADDRESS_ADDRESS] += VMStructField{SS}(?O[BASE_ADDRESS])",
    ]),
    JMP_IMM.match_func
]), create_handler_reader_class("JMP_UNKNOWN", ["IMM"])) # TODO: When addrs count is 1 or 2

MOV_VAR_UNKVAR = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR])) = VMStructField{SS}($O[UNK_VAR])"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("{MOV_VAR_UNKVAR:}"))

MOV_VAR_SP = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR])) = SP"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("MOV_VAR_SP", ["VAR"]))

MOV_SP_VAR = HandlerMatch(match_funcs([
    lines_matcher(["SP = VMStructField{SS}(ReadParameterWord($P[VAR]))"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("MOV_SP_VAR", ["VAR"]))

UNK_CALLS = HandlerMatch(match_funcs([lines_matcher([
    "Push(VMStructField{SS}(ReadParameterWord($P[P1])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P2])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P3])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P4])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P5])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P6])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P7])))",
    "Push(VMStructField{SS}(ReadParameterWord($P[P8])))",
    "Push(VMStructOffset(0x0))",
    "Push(VMStructOffset(0x0))"])
]), create_handler_reader_class("{UNK_CALLS:}"))

ADD_SP_IMM = HandlerMatch(match_funcs([
    lines_matcher(["$V[VAR] = ReadParameterByte($P[IMM])",
                   "SP += $V[VAR]",
                   "VMStructField{SS}(ReadParameterWord($P[VAR])) += $V[VAR]"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("ADD_SP_IMM", ["IMM"]))


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
        "$V[FLAGS] = VMStructFieldDword(ReadParameterWord($P[FLAGS_OFFSET]))",
        "$V[CHECK_TYPE] = ReadParameterByte($P[CHECK_TYPE])"
    ]),
    JZ, JNZ, JA, JAE, JB, JBE, JG, JGE, JL, JLE, JNO, JNP, JNS, JO, JP, JS])

JCC_INSIDE = HandlerMatch(match_funcs([
    JCC,
    match_condition("If((VMStructFieldByte($O[TAKE_JUMP]) != 0x0))", [UPDATE_IP_AND_JUMP_PARAM]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("{O:CHECK_TYPE}", ["JUMP_VALUE", "JUMP_HANDLER"]))

JCC_OUTSIDE = HandlerMatch(match_funcs([
    JCC,
    match_condition("If((VMStructFieldByte($O[TAKE_JUMP]) != 0x0))", [JMP_IMM.match_func]),
    lines_matcher(["SP += $H[STACK_CLEAR_SIZE]",
                   "VMStructField{SS}(ReadParameterWord($P[SP_OFFSET])) += $H[STACK_CLEAR_SIZE]"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("{O:CHECK_TYPE}_IMM", ["IMM"]))

PUSHF = HandlerMatch(match_funcs([
    any_order([lines_matcher(["Push(VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])))"]),
               lines_matcher(["VMStructField{SS}(ReadParameterWord($P[SP_OFFSET])) -= 0x{N}"])]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("PUSHF"))

POPF = HandlerMatch(match_funcs([
    any_order([lines_matcher(["VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = Pop()"]),
               lines_matcher(["VMStructField{SS}(ReadParameterWord($P[SP_OFFSET])) += 0x{N}"])]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("POPF"))


def enable_flag(flag, update_flag=True):
    if update_flag:
        return lines_matcher([
            "*(DWORD*)$V[FLAGS_OFFSET] |= 0x%x" % flag,
            "VMStructFieldDword($O[FLAGS]) |= 0x%x" % flag
        ])
    else:
        return lines_matcher([
            "*(DWORD*)$V[FLAGS_OFFSET] |= 0x%x" % flag,
        ])


def disable_flag(flag, update_flag=True):
    if update_flag:
        return lines_matcher([
            "$V[FLAGS2] = (~0x%x)" % flag,
            "*(DWORD*)$V[FLAGS_OFFSET] &= $V[FLAGS2]",
            "VMStructFieldDword($O[FLAGS]) &= $V[FLAGS2]"
        ])
    else:
        return lines_matcher([
            "*(DWORD*)$V[FLAGS_OFFSET] &= (~0x%x)" % flag,
        ])


CLD = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_CLD]))", [disable_flag(0x400)])
CLI = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_CLI]))", [disable_flag(0x200)])

STD = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_STD]))", [enable_flag(0x400)])
STI = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_STI]))", [enable_flag(0x200)])


RESET_FLAGS = HandlerMatch(match_funcs([
    lines_matcher(["VMStructFieldDword($O[FLAGS]) = 0x0"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("RESET_FLAGS"))


COMMON_HANDLERS = [
    LODS,
    STOS,
    JMP,
    JMP_IMM,
    JMP_VAR,
    JMP_MEMVAR,
    JCC_INSIDE,
    JCC_OUTSIDE,
    MOV_VAR_UNKVAR,
    MOV_VAR_SP,
    MOV_SP_VAR,
    ADD_SP_IMM,
    PUSHF,
    POPF,
    UNK_CALLS,
    RESET_FLAGS,
    UNK_JMP_IMM,
    RETURN
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
        info.reader = h.reader

        fields.update(params.fields)
        return info
    return None