from common_handlers import *

def create_string_from_params(name, params):
    ns = name
    for var in re.findall("\{([\w:]+)\}", name):
        t, n = var.split(":")
        if t == "S":  # Size
            nvar = {1: "BYTE", 2: "WORD", 4: "DWORD", 8: "QWORD"}[params[n]]
        elif t == "T":  # Type
            nvar = params[n]
        elif t == "AT":  # Arg type
            nvar = params[n]
            if nvar == "MEMVAR":
                nvar = "VAR"
        elif t == "O":  # Operation
            nvar = params[n]
        else:
            raise Exception("Invalid var: %s" % var)
        ns = ns.replace("{%s}" % var, nvar)
    return ns


def create_tiger_handler_reader_class(name, params=[]):
    class GenericHandlerReader(HandlerReader):
        def get_name(self):
            return create_string_from_params(name, self.info.vars)

        def get_params(self):
            return [(create_string_from_params(x, self.info.vars), self.params[y]) for x, y in params]

    return GenericHandlerReader


def optional(func, param_name=None):
    def _func(parser, instructions, index, params, arch, info):
        match, nindex = func(parser, instructions, index, params, arch, info)
        if match:
            index = nindex
            new_val = 1
        else:
            new_val = 0
        if param_name is not None:
            if not params.set_handler_var_value(param_name, new_val):
                return False, index
        return True, index
    return _func

# TODO: Remove info
def dst_load(name="DST"):
    def _func(parser, instructions, index, params, arch, info):
        if index >= len(instructions):
            return False, index
        if ("%s_LOADED" % name) in params.handler_vars and params.handler_vars["%s_LOADED" % name]:
            # Don't try to load dst again
            return True, index
        nparams = params.copy()
        if parser.match_expression(instructions[index], arch.translate("$V[%s_VAR] = VMStructField{SS}(ReadParameterWord($P[%s_VALUE]))" % (name, name)), nparams):
            dst_type = "MEMVAR"
        elif parser.match_expression(instructions[index], "$V[%s_VAR] = VMStructOffset(ReadParameterWord($P[%s_VALUE]))" % (name, name), nparams):
            dst_type = "VAR"
        else:
            return False, index
        if not nparams.set_handler_var_value("%s_TYPE" % name, dst_type):
            return False, index
        if not nparams.set_handler_var_value("%s_LOADED" % name, 1):
            return False
        params.update(nparams)
        return True, index+1
    return _func


def src_load(parser, instructions, index, params, arch, info):
    if index >= len(instructions):
        return False, index
    if "SRC_LOADED" in params.handler_vars and params.handler_vars["SRC_LOADED"]:
        # Don't try to load src again
        return True, index
    parser.groups["WORD_SIZE"] = ["BYTE", "WORD", "DWORD", "QWORD"]
    parser.groups["FIELD_SIZE"] = ["VMStructFieldByte", "VMStructFieldWord", "VMStructFieldDword", "VMStructFieldQword"]
    parser.groups["READ_SIZE"] = ["ReadParameterByte", "ReadParameterWord", "ReadParameterDword"]
    nparams = params.copy()
    if parser.match_expression(instructions[index], arch.translate("$V[SRC_VAR] = *($G[WORD_SIZE:WORD_SRC]*)VMStructField{SS}(ReadParameterWord($P[SRC_VALUE]))"), nparams):
        src_type = "MEMVAR"
        size = 1 << parser.groups["WORD_SIZE"].index(nparams.vars["WORD_SRC"].value)
    elif parser.match_expression(instructions[index], "$V[SRC_VAR] = $G[FIELD_SIZE:FIELD_SRC](ReadParameterWord($P[SRC_VALUE]))", nparams):
        src_type = "VAR"
        size = 1 << parser.groups["FIELD_SIZE"].index(nparams.vars["FIELD_SRC"].value)
    elif parser.match_expression(instructions[index], "$V[SRC_VAR] = $G[READ_SIZE:READ_SRC]($P[SRC_VALUE])", nparams):
        src_type = "IMM"
        size = 1 << parser.groups["READ_SIZE"].index(nparams.vars["READ_SRC"].value)
    else:
        return False, index
    if not nparams.set_handler_var_value("SRC_TYPE", src_type):
        return False, index
    if not nparams.set_handler_var_value("SRC_SIZE", size):
        return False, index
    if not nparams.set_handler_var_value("SRC_LOADED", 1):
        return False
    params.update(nparams)
    return True, index+1


def split_expression(expr):
    if isinstance(expr, handlers_parser.SetValueOperation):
        fmt = expr.get_format()
        s = fmt.split(" ")
        if len(s) != 3:
            return None
        return expr.lvalue, s[1], expr.rvalue, s[2][:s[2].find("{")]
    return None


def match_dst_operation(name="DST"):
    def _func(parser, expr, params, arch):
        parser.groups["WORD_SIZE"] = ["BYTE", "WORD", "DWORD", "QWORD"]
        parser.groups["FIELD_SIZE"] = ["VMStructFieldByte", "VMStructFieldWord", "VMStructFieldDword", "VMStructFieldQword"]
        nparams = params.copy()
        if ("%s_LOADED" % name) in params.handler_vars and params.handler_vars["%s_LOADED" % name]:
            if parser.match_expression(expr, "*($G[WORD_SIZE:WORD_%s]*)$V[%s_VAR]" % (name, name), nparams):
                size = 1 << parser.groups["WORD_SIZE"].index(nparams.vars["WORD_%s" % name].value)
            else:
                return False
            if not nparams.set_handler_var_value("%s_SIZE" % name, size):
                return False
        else:
            if parser.match_expression(expr, arch.translate("*($G[WORD_SIZE:WORD_%s]*)VMStructField{SS}(ReadParameterWord($P[%s_VALUE]))" % (name, name)), nparams):
                dst_type = "MEMVAR"
                size = 1 << parser.groups["WORD_SIZE"].index(nparams.vars["WORD_%s" % name].value)
            elif parser.match_expression(expr, "$G[FIELD_SIZE:FIELD_%s](ReadParameterWord($P[%s_VALUE]))" % (name, name), nparams):
                dst_type = "VAR"
                size = 1 << parser.groups["FIELD_SIZE"].index(nparams.vars["FIELD_%s" % name].value)
            else:
                return False
            if not nparams.set_handler_var_value("%s_TYPE" % name, dst_type):
                return False
            if not nparams.set_handler_var_value("%s_SIZE" % name, size):
                return False
            if not nparams.set_handler_var_value("%s_LOADED" % name, 0):
                return False
        params.update(nparams)
        return True
    return _func


def match_src_operation(name="SRC"):
    def _func(parser, expr, params, arch):
        parser.groups["WORD_SIZE"] = ["BYTE", "WORD", "DWORD", "QWORD"]
        parser.groups["FIELD_SIZE"] = ["VMStructFieldByte", "VMStructFieldWord", "VMStructFieldDword", "VMStructFieldQword"]
        parser.groups["READ_SIZE"] = ["ReadParameterByte", "ReadParameterWord", "ReadParameterDword"]
        nparams = params.copy()
        if ("%s_LOADED" % name) in params.handler_vars and params.handler_vars["%s_LOADED" % name]:
            if not parser.match_expression(expr, "$V[%s_VAR]" % name, nparams):
                return False
        else:
            if parser.match_expression(expr, arch.translate("*($G[WORD_SIZE:WORD_%s]*)VMStructField{SS}(ReadParameterWord($P[%s_VALUE]))" % (name, name)), nparams):
                src_type = "MEMVAR"
                size = 1 << parser.groups["WORD_SIZE"].index(nparams.vars["WORD_%s" % name].value)
            elif parser.match_expression(expr, "$G[FIELD_SIZE:FIELD_%s](ReadParameterWord($P[%s_VALUE]))" % (name, name), nparams):
                src_type = "VAR"
                size = 1 << parser.groups["FIELD_SIZE"].index(nparams.vars["FIELD_%s" % name].value)
            elif parser.match_expression(expr, "$G[READ_SIZE:READ_%s]($P[%s_VALUE])" % (name, name), nparams):
                src_type = "IMM"
                size = 1 << parser.groups["READ_SIZE"].index(nparams.vars["READ_%s" % name].value)
            else:
                return False
            if not nparams.set_handler_var_value("%s_TYPE" % name, src_type):
                return False
            if not nparams.set_handler_var_value("%s_SIZE" % name, size):
                return False
            if not nparams.set_handler_var_value("%s_LOADED" % name, 0):
                return False
        params.update(nparams)
        return True
    return _func

def match_set_value(name, lvalue_match, op, rvalue_match, op_post=""):
    def _func(parser, instructions, index, params, arch, info):
        if index >= len(instructions):
            return False, index
        nparams = params.copy()
        res = split_expression(instructions[index])
        if res is None:
            return False, index
        lvalue, real_op, rvalue, real_op_post = res
        if op + "=" != real_op:
            return False, index
        if op_post != real_op_post:
            return False, index
        if not lvalue_match(parser, lvalue, nparams, arch):
            return False, index
        if not rvalue_match(parser, rvalue, nparams, arch):
            return False, index
        nparams.set_handler_var_value("MAIN_LINE", str(instructions[index]))
        nparams.set_handler_var_value("OPERATION", name)
        params.update(nparams)
        return True, index+1
    return _func


def match_binary_expression(name, op):
    return match_set_value(name, match_dst_operation(), op, match_src_operation())


def zero_high_dword(name="DST"):
    def _func(parser, instructions, index, params, arch, info):
        if index >= len(instructions):
            return False, index
        if ("%s_LOADED" % name) not in params.handler_vars or not params.handler_vars["%s_LOADED" % name]:
            return False, index
        if not parser.match_expression(instructions[index], "*(DWORD*)($V[%s_VAR] + 0x4) = 0x0" % name, params):
            return False, index
        return True, index+1
    return _func


def update_flags(parser, instructions, index, params, arch, info):
    if index >= len(instructions):
        return False, index
    if not parser.match_expression(instructions[index], arch.translate("VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = Flags(%s)" % params.handler_vars["MAIN_LINE"]), params):
        return False, index
    return True, index+1

def new_update_flags(parser, instructions, index, params, arch, info):
    lines = ["If((ReadParameterByte($P[UPDATE_FLAGS]) != 0x0))",
             "    VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = Flags(%s)" % params.handler_vars["MAIN_LINE"]]
    return match_lines(parser, instructions, index, params, lines, arch)


ZERO_HIGH_DWORD = only_64(optional(zero_high_dword(), "ZERO_HIGH_DWORD"))

POST_OPERATIONS = match_funcs([
    ZERO_HIGH_DWORD,
    optional(match_one([update_flags, new_update_flags]), "UPDATE_FLAGS"),
    UPDATE_IP_AND_JUMP
])

LOAD_FLAGS = lines_matcher(["flags = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET]))"])


def with_flags(func):
    return match_funcs([LOAD_FLAGS, func])

COMMON_BINARY_OP_MAIN = match_one(
    [match_binary_expression("ADD", "+"), match_binary_expression("SUB", "-"),
     match_binary_expression("XOR", "^"), match_binary_expression("AND", "&"),
     match_binary_expression("OR", "|"),
     with_flags(match_binary_expression("ROL", "rol")), with_flags(match_binary_expression("ROR", "ror")),
     with_flags(match_binary_expression("RCL", "rcl")), with_flags(match_binary_expression("RCR", "rcr"))])

COMMON_BINARY_OP_READER = create_tiger_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{T:DST_TYPE}_{T:SRC_TYPE}",
                                                            [("{AT:DST_TYPE}", "DST_VALUE"), ("{AT:SRC_TYPE}", "SRC_VALUE")])

COMMON_BINARY_OP = HandlerMatch(match_funcs([
    # We can't always distinguish between src and dst, so try both
    match_one([
        match_funcs([
            optional(dst_load()),
            optional(src_load),
            COMMON_BINARY_OP_MAIN,
        ]),
        match_funcs([
            optional(src_load),
            optional(dst_load()),
            COMMON_BINARY_OP_MAIN,
        ]),
    ]),
    POST_OPERATIONS
]), COMMON_BINARY_OP_READER)


def update_flags_cond_shl_shr(parser, instructions, index, params, arch, info):
    if index >= len(instructions):
        return False, index
    if not parser.match_expression(instructions[index], arch.translate("var_1 = Flags(%s)" % params.handler_vars["MAIN_LINE"]), params):
        return False, index
    return True, index+1

SHL_SHR_MAIN = match_funcs([
    only_32(match_condition("If((($V[SRC_VAR] & 0x1F) != 0x0))", [
                               match_one([match_binary_expression("SHL", "<<"), match_binary_expression("SHR", ">>")]),
                               optional(update_flags_cond_shl_shr, "UPDATE_FLAGS")])),
    only_64(match_condition("If((($V[SRC_VAR] & 0x3F) != 0x0))", [
                               match_one([match_binary_expression("SHL", "<<"), match_binary_expression("SHR", ">>")]),
                               optional(update_flags_cond_shl_shr, "UPDATE_FLAGS")])),
    ])

SHL_SHR = HandlerMatch(match_funcs([
    # We can't always distinguish between src and dst, so try both
    match_one([
        match_funcs([
            optional(dst_load()),
            src_load,
            SHL_SHR_MAIN,
        ]),
        match_funcs([
            src_load,
            optional(dst_load()),
            SHL_SHR_MAIN,
        ]),
    ]),
    optional(match_condition("Else", [
        lines_matcher(["var_1 = VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET]))"])
    ]), "UPDATE_FLAGS"),
    ZERO_HIGH_DWORD,
    optional(match_one([
        lines_matcher(["VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = var_1"]),
        update_flags_cond(lines_matcher(["VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = var_1"]))]),
        "UPDATE_FLAGS"),
    UPDATE_IP_AND_JUMP
]), COMMON_BINARY_OP_READER)

def match_comp(name, op):
    def _func(parser, instructions, index, params, arch, info):
        if index >= len(instructions):
            return False, index
        nparams = params.copy()
        if not parser.match_expression(instructions[index], arch.translate("VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = Flags(%s($[DST], $[SRC]))" % op), nparams):
            if not match_lines(parser, instructions, index, nparams, ["If((ReadParameterByte($P[UPDATE_FLAGS]) != 0x0))",
                                                                     "    VMStructField{SS}(ReadParameterWord($P[FLAGS_OFFSET])) = Flags(%s($[DST], $[SRC]))" % op], arch)[0]:
                return False, index
        if not match_dst_operation()(parser, nparams.vars["DST"], nparams, arch):
            return False, index
        # Should not be immediate
        if not match_src_operation()(parser, nparams.vars["SRC"], nparams, arch):
            return False, index
        nparams.set_handler_var_value("OPERATION", name)
        params.update(nparams)
        return True, index+1
    return _func

CMP_TEST = HandlerMatch(match_funcs([
    match_one([match_comp("CMP", "Compare"), match_comp("TEST", "Test")]),
    UPDATE_IP_AND_JUMP
]), COMMON_BINARY_OP_READER)

MOV = HandlerMatch(match_funcs([
    optional(dst_load()),
    match_binary_expression("MOV", ""),
    ZERO_HIGH_DWORD,
    UPDATE_IP_AND_JUMP
]), COMMON_BINARY_OP_READER)

MOV_QWORD = HandlerMatch(match_funcs([
    dst_load(),
    lines_matcher(["*(QWORD*)$V[DST_VAR] = (ReadParameterQword($P[SRC_VALUE]) & 0xFFFFFFFF)",
                   "*(DWORD*)($V[DST_VAR] + 0x4) = (ReadParameterQword($P[SRC_VALUE]) >> 0x20)"]),
    UPDATE_IP_AND_JUMP
]), create_tiger_handler_reader_class("MOV_QWORD_{T:DST_TYPE}_IMM",
                                      [("{AT:DST_TYPE}", "DST_VALUE"), ("IMM", "SRC_VALUE")]))


def match_movzx_movsx(name, op):
    def _func(parser, instructions, index, params, arch, info):
        if index >= len(instructions):
            return False, index
        parser.groups["WORD_SIZE"] = ["BYTE", "WORD", "DWORD", "QWORD"]
        nparams = params.copy()
        if not parser.match_expression(instructions[index], "$[DST] = (%s$G[WORD_SIZE:WORD_OP])$[SRC]" % op, nparams):
            return False, index
        if not match_dst_operation()(parser, nparams.vars["DST"], nparams, arch):
            return False, index
        # Should not be immediate
        if not match_src_operation()(parser, nparams.vars["SRC"], nparams, arch):
            return False, index
        size = 1 << parser.groups["WORD_SIZE"].index(nparams.vars["WORD_OP"].value)
        if nparams.handler_vars["SRC_SIZE"] < size:
            return False, index
        nparams.handler_vars["SRC_SIZE"] = size
        nparams.set_handler_var_value("OPERATION", name)
        params.update(nparams)
        return True, index+1
    return _func

MOVZX_MOVSX = HandlerMatch(match_funcs([
    optional(dst_load()),
    match_one([match_movzx_movsx("MOVZX", ""), match_movzx_movsx("MOVSX", "S")]),
    ZERO_HIGH_DWORD,
    UPDATE_IP_AND_JUMP
]), create_tiger_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{S:SRC_SIZE}_{T:DST_TYPE}_{T:SRC_TYPE}",
                                      [("{AT:DST_TYPE}", "DST_VALUE"), ("{AT:SRC_TYPE}", "SRC_VALUE")]))


def match_mul(parser, expr, params, arch):
    nparams = params.copy()
    if not parser.match_expression(expr, "($[DST] * $[SRC])", nparams):
        return False
    if not match_src_operation()(parser, nparams.vars["SRC"], nparams, arch):
        return False
    if nparams.handler_vars["SRC_LOADED"]:
        if not parser.match_expression(nparams.vars["DST"], "$V[DST_VAL]", nparams):
            return False
    elif nparams.handler_vars["DST_LOADED"]:
        if not parser.match_expression(nparams.vars["DST"], arch.translate("*({SU}*)$V[DST_VAR]"), nparams):
            return False
    else:
        if not match_dst_operation()(parser, nparams.vars["DST"], nparams, arch):
            return False
    # Because this is the flags in mul
    nparams.set_handler_var_value("MAIN_LINE", str(expr))
    params.update(nparams)
    return True

IMUL = HandlerMatch(match_funcs([
    match_one([
        match_funcs([
            dst_load(),
            src_load,
            lines_matcher(["$V[DST_VAL] = *({SU}*)$V[DST_VAR]"])
        ]),
        match_funcs([
            src_load,
            dst_load(),
            lines_matcher(["$V[DST_VAL] = *({SU}*)$V[DST_VAR]"])
        ]),
        dst_load()  # At last, after both not matched, try to just load dst
    ]),
    match_set_value("IMUL", match_dst_operation(), "", match_mul),
    POST_OPERATIONS,
]), COMMON_BINARY_OP_READER)

def match_unary_expression(name, op):
    return match_set_value(name, match_dst_operation(), "", match_dst_operation(), op)

COMMON_UNARY_OP = HandlerMatch(match_funcs([
    optional(dst_load(), "DST_LOADED"),
    optional(LOAD_FLAGS, "LOAD_FLAGS"), # It may be only with inc or dec
    match_one([match_unary_expression("INC", "++"), match_unary_expression("DEC", "--"),
               match_unary_expression("NEG", "-"), match_unary_expression("NOT", "~")]),
    POST_OPERATIONS
]), create_tiger_handler_reader_class("{O:OPERATION}_{S:DST_SIZE}_{T:DST_TYPE}",
                                      [("{AT:DST_TYPE}", "DST_VALUE")]))



def match_pop_expr(parser, expr, params, arch):
    parser.groups["POP_SIZE"] = ["Pop", "PopWord"]
    nparams = params.copy()
    if parser.match_expression(expr, "$G[POP_SIZE:POP]()", nparams):
        if nparams.vars["POP"].value == "PopWord":
            size = 2
        else:
            size = arch.native_size()
    else:
        return False
    if not nparams.set_handler_var_value("DST_SIZE", size):
        return False
    params.update(nparams)
    return True

MATCH_POP = match_set_value("POP", match_dst_operation(), "", match_pop_expr)

POP = HandlerMatch(match_funcs([
    dst_load(),
    MATCH_POP,
    match_one([
        lines_matcher(["$V[SP_OFFSET] = VMStructOffset(ReadParameterWord($P[SP_OFFSET]))",
                       "If(($V[VAR_DST] != $V[SP_OFFSET]))",
                       "    *({SU}*)$V[SP_OFFSET] += $H[DST_SIZE_NUM]"]),
        lines_matcher(["$V[VAR_DST2] = $V[VAR_DST]", # if $V[SP_OFFSET] == $V[VAR_DST]
                       "$V[SP_OFFSET] = VMStructOffset(ReadParameterWord($P[SP_OFFSET]))",
                       "If(($V[VAR_DST2] != $V[SP_OFFSET]))",
                       "    *({SU}*)$V[SP_OFFSET] += $H[DST_SIZE_NUM]"]),
        ]),
    only_32(lambda parser, instructions, index, params, arch, info: (params.handler_vars["DST_SIZE"] == params.handler_vars["DST_SIZE_NUM"], index)),
    only_64(lambda parser, instructions, index, params, arch, info: (0x8 == params.handler_vars["DST_SIZE_NUM"], index)),
    UPDATE_IP_AND_JUMP
]), create_tiger_handler_reader_class("POP_{S:DST_SIZE}_{T:DST_TYPE}",
                                      [("{AT:DST_TYPE}", "DST_VALUE")]))

def match_push(parser, instructions, index, params, arch, info):
    if index >= len(instructions):
        return False, index
    parser.groups["PUSH_SIZE"] = ["Push", "PushWord"]
    nparams = params.copy()
    if parser.match_expression(instructions[index], "$G[PUSH_SIZE:PUSH]($[DST])", nparams):
        if nparams.vars["PUSH"].value == "PushWord":
            size = 2
        else:
            size = arch.native_size()
    else:
        return False, index
    if not match_src_operation("DST")(parser, nparams.vars["DST"], nparams, arch):
        return False, index
    if nparams.handler_vars["DST_SIZE"] > size:
        return False, index
    nparams.handler_vars["DST_SIZE"] = size
    params.update(nparams)
    return True, index+1

PUSH = HandlerMatch(match_funcs([
    match_push,
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[SP_OFFSET])) -= $H[DST_SIZE_NUM]"]),
    lambda parser, instructions, index, params, arch, info: (params.handler_vars["DST_SIZE"] == params.handler_vars["DST_SIZE_NUM"], index),
    UPDATE_IP_AND_JUMP
]), create_tiger_handler_reader_class("PUSH_{S:DST_SIZE}_{T:DST_TYPE}",
                                      [("{AT:DST_TYPE}", "DST_VALUE")]))

def match_temp_var(parser, expr, params, arch):
    return parser.match_expression(expr, "$V[TEMP_VAR]", params)

XCHG_MAIN = match_funcs([
    match_set_value("XCHG", match_temp_var, "", match_dst_operation()),
    match_set_value("XCHG", match_dst_operation(), "", match_dst_operation("SRC")),
    match_set_value("XCHG", match_dst_operation("SRC"), "", match_temp_var),
])

XCHG = HandlerMatch(match_funcs([
    match_one([
        match_funcs([
            dst_load(),
            dst_load("SRC"),
            XCHG_MAIN,
        ]),
        match_funcs([
            dst_load("SRC"),
            dst_load(),
            XCHG_MAIN,
        ]),
    ]),
    # All the options...
    # TODO: I don't save that info, but I am not using it anyway on the other hand
    only_64(match_one([
        match_funcs([
            zero_high_dword("SRC"),
            zero_high_dword(),
        ]),
        match_funcs([
            zero_high_dword(),
            zero_high_dword("SRC"),
        ]),
        match_funcs([
            zero_high_dword("SRC"),
        ]),
        match_funcs([
            zero_high_dword(),
        ]),
        match_funcs([])
    ])),
    UPDATE_IP_AND_JUMP
]), create_tiger_handler_reader_class("XCHG_{S:DST_SIZE}_{T:DST_TYPE}_{T:SRC_TYPE}",
                                      [("{AT:DST_TYPE}", "DST_VALUE"), ("{AT:SRC_TYPE}", "SRC_VALUE")]))

def match_str_expr(line):
    def _func(parser, expr, params, arch):
        return parser.match_expression(expr, arch.translate(line), params)
    return _func

def match_call_dst(parser, expr, params, arch):
    if parser.match_expression(expr, arch.translate("(ReadParameterDword($P[DST_VALUE]) + VMStructField{SS}(?O[BASE_ADDRESS]))"), params):
        params.set_handler_var_value("DST_TYPE", "RELIMM")
        return True
    else:
        return match_dst_operation()(parser, expr, params, arch)

CALL = HandlerMatch(match_funcs([
    lines_matcher(["$V[VAR_STACK] = (ReadParameterWord($P[STACK_RETURN_OFFSET]) + SP)"]),
    match_set_value("CALL", match_str_expr("*({SU}*)$V[VAR_STACK]"), "", match_call_dst),
    lines_matcher(["*({SU}*)($V[VAR_STACK] + 0x{N}) = (ReadParameterDword($P[RETURN_ADDRESS]) + VMStructField{SS}(?O[BASE_ADDRESS]))"]),
    POP_RET
]), create_tiger_handler_reader_class("CALL_{T:DST_TYPE}_NEXT",
                                      [("{AT:DST_TYPE}", "DST_VALUE"), ("RELIMM", "RETURN_ADDRESS")]))

# Deprecated
RESET_KEYS_OLD = HandlerMatch(match_funcs([lines_matcher(\
    [
        "VMStructFieldDword($O[KEY_DECODE]) = 0x0",
        "VMStructFieldDword($O[KEY_COND]) = 0x0",
        "VMStructFieldDword($O[UNK_DWORD_1]) = 0x0",
        "VMStructFieldDword($O[VALUE_DWORD]) = 0x0",
        "VMStructFieldDword($O[VALUE_DWORD_HIGH]) = 0x0",
        "VMStructFieldWord($O[VALUE_WORD_1]) = 0x0",
        "VMStructFieldWord($O[VALUE_WORD_2]) = 0x0",
        "VMStructFieldWord($O[UNK_WORD]) = 0x0",
        "VMStructFieldDword($O[KEY_SPECIAL]) = 0x0",
        "VMStructFieldDword($O[KEY_DECODE_POST]) = 0x0"
    ]), UPDATE_IP_AND_JUMP]),
    create_handler_reader_class("RESET_KEYS"))

MOVS = HandlerMatch(match_funcs([
    MOVS_MAIN,
    match_one([match_funcs([READ_SI, READ_DI]), match_funcs([READ_DI, READ_SI])]),
    UPDATE_SI_DI(False),
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("MOVS"))

BUG_SCAS_1 = match_funcs([
    BUG_SCAS_MAIN,
    READ_DI,
    UPDATE_DI3,
    optional(match_one([update_flags_cond(BUG_SCAS_UPDATE_FLAGS), BUG_SCAS_UPDATE_FLAGS]), "UPDATE_FLAGS"),
    UPDATE_IP_AND_JUMP
])

BUG_SCAS_2 = match_funcs([
    BUG_SCAS_MAIN,
    optional(BUG_SCAS_UPDATE_FLAGS_1, "UPDATE_FLAGS"),
    READ_DI,
    UPDATE_DI3,
    optional(match_one([update_flags_cond(BUG_SCAS_UPDATE_FLAGS_2), BUG_SCAS_UPDATE_FLAGS_2]), "UPDATE_FLAGS"),
    UPDATE_IP_AND_JUMP
])

SCAS_1 = match_funcs([
    READ_DI,
    UPDATE_DI2,
    optional(match_one([update_flags_cond(SCAS_UPDATE_FLAGS), SCAS_UPDATE_FLAGS]), "UPDATE_FLAGS"),
    UPDATE_IP_AND_JUMP
])

SCAS = HandlerMatch(match_one([SCAS_1, BUG_SCAS_1, BUG_SCAS_2]), create_string_op_handler_reader("SCAS"))

CMPS = HandlerMatch(match_funcs([
    match_one([match_funcs([READ_SI, READ_DI]), match_funcs([READ_DI, READ_SI])]),
    UPDATE_SI_DI(False),
    optional(match_one([update_flags_cond(CMPS_UPDATE_FLAGS_1), update_flags_cond(CMPS_UPDATE_FLAGS_2), CMPS_UPDATE_FLAGS_1, CMPS_UPDATE_FLAGS_2]), "UPDATE_FLAGS"),
    UPDATE_IP_AND_JUMP
    ]), create_string_op_handler_reader("CMPS"))


CLC = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_CLC]))", [disable_flag(0x1)])
CMC = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_CMC]))",
                      [match_condition("If(((*(DWORD*)$V[FLAGS_OFFSET] & 0x1) != 0x0))", [disable_flag(0x1)]),
                       match_condition("Else", [enable_flag(0x1, False), lines_matcher(["VMStructFieldDword($O[FLAGS]) &= 0x1"])])]) # Bug
STC = match_condition("If(($V[FLAGS_OP] == $H[FLAGS_OP_STC]))", [enable_flag(0x1)])

FLAGS_OP = HandlerMatch(match_funcs([
    lines_matcher([
        "$V[FLAGS_OFFSET] = VMStructOffset(ReadParameterWord($P[FLAGS_OFFSET]))",
        "$V[FLAGS_OP] = ReadParameterByte($P[FLAGS_OP])"
    ]),
    CLC, CLD, CLI, CMC, STC, STD, STI,
    UPDATE_IP_AND_JUMP]), create_handler_reader_class("{O:FLAGS_OP}"))


ADD_VAR_BASEADDRESS = HandlerMatch(match_funcs([
    lines_matcher(["VMStructField{SS}(ReadParameterWord($P[VAR])) += VMStructField{SS}(?O[BASE_ADDRESS])"]),
    UPDATE_IP_AND_JUMP,
]), create_handler_reader_class("ADD_VAR_BASEADDRESS", [("VAR", "VAR")]))


# Some are really nops, but maybe some are invalid generated handlers? (For example in my tests, "test" opcode
# without a jump after it translated to this.
NOP = HandlerMatch(UPDATE_IP_AND_JUMP, create_handler_reader_class("NOP"))

UNKNOWN_SET = HandlerMatch(match_funcs([
    lines_matcher([
        "VMStructField{SS}(ReadParameterWord($P[A1])) = VMStructField{SS}(ReadParameterWord($P[A2]))",
        "VMStructField{SS}(ReadParameterWord($P[A3])) = VMStructField{SS}(ReadParameterWord($P[A4]))",
        "VMStructField{SS}(ReadParameterWord($P[A5])) = VMStructField{SS}(ReadParameterWord($P[A6]))",
        "VMStructField{SS}(ReadParameterWord($P[A7])) = VMStructField{SS}(ReadParameterWord($P[A8]))",
        "VMStructField{SS}(ReadParameterWord($P[A9])) = VMStructField{SS}(ReadParameterWord($P[A10]))",
        "VMStructField{SS}(ReadParameterWord($P[A11])) = VMStructField{SS}(ReadParameterWord($P[A12]))",
    ]),
    only_64(optional(lines_matcher([
        "VMStructField{SS}(ReadParameterWord($P[A13])) = VMStructField{SS}(ReadParameterWord($P[A14]))",
        "VMStructField{SS}(ReadParameterWord($P[A15])) = VMStructField{SS}(ReadParameterWord($P[A16]))",
    ]))),
    UPDATE_IP_AND_JUMP
]), create_handler_reader_class("SHUFFLE_VM_STRUCT"))

UNKNOWN_JUNK = HandlerMatch(match_funcs([
    lines_matcher(["Push(SP)"]),
    lambda parser, instructions, index, params, arch, info: (True, len(instructions)),
]), None)

HANDLERS = [
    CALL,
    PUSH,
    IMUL,
    COMMON_UNARY_OP,
    POP,
    XCHG,
    COMMON_BINARY_OP,
    MOVZX_MOVSX,
    MOV,
    MOV_QWORD,
    SHL_SHR,
    CMP_TEST,
    FLAGS_OP,
    MOVS,
    CMPS,
    SCAS,
    ADD_VAR_BASEADDRESS,
    NOP,
    UNKNOWN_SET,
    UNKNOWN_JUNK
    ] + COMMON_HANDLERS