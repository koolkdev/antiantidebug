import handlers_parser

def clean_junk_field(handlers, fields, arch):
    blacklist = set(fields.values())
    candidates = set()
    cparams = handlers_parser.Params({}, {})
    parser = handlers_parser.HandlerParser.get_default_parser()
    parser.groups["SIMPLE_MATH"] = ["+", "-", "^"]

    for handler in handlers:
        for inst in handler.handler.instructions:
            params = cparams.copy()
            if parser.match_expression(inst, arch.translate("*({SU}*)({R:bp} + $N[OFFSET]) = 0x0"), params):
                blacklist.add(params.vars["OFFSET"].value)
            elif parser.match_expression(inst, arch.translate("*({SU}*)({R:bp} + $N[OFFSET]) $G[SIMPLE_MATH:OP]= $[X]"), params):
                candidates.add(params.vars["OFFSET"].value)

    junk_offset = list(candidates.difference(blacklist))
    assert len(junk_offset) == 1
    junk_offset, = junk_offset

    fields["JUNK"] = junk_offset
    cparams = handlers_parser.Params(fields, {})

    for handler in handlers:
        for inst in handler.handler.instructions:
            params = cparams.copy()
            if parser.match_expression(inst, arch.translate("*({SU}*)({R:bp} + ?O[JUNK]) $G[SIMPLE_MATH:OP]= $[X]"), params):
                handler.handler.make_unvisible(inst)
                handler.handler.optimize_instructions()
                handler.handler.clean_instructions()
                break

def fix_64_junk_bool_field(handlers, fields):
    parser = handlers_parser.HandlerParser.get_default_parser()

    lines = ["If(($[X] == 0x3))",
             "    *(BYTE*)(rbp + $O[RESET_HIGH_DWORD_BOOL]) = ($[Y1] | $[Y2])"]

    def fix_func(handler, instructions_container, index, params):
        nparams = params.copy()
        if parser.match_instructions(instructions_container.instructions, index, lines, 0, nparams)[0]:
            params.update_global(nparams)
            parser.replace_instructions(handler, instructions_container.instructions[index], 0, 1, [parser.create_macro_result("VMStructByte($O[RESET_HIGH_DWORD_BOOL]) = 0x1", params)])
            return True
        return False

    for handler in handlers:
        parser.clean_handler(handler.handler, fields, handler.parameters, [fix_func])

    assert "RESET_HIGH_DWORD_BOOL" in fields


def clean_junk_check(handlers, fields, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()
    parser.groups["SIMPLE_MATH"] = ["+", "-", "^"]

    lines = ["If(($[X] == 0x0))",
             "    $V[VAR] = Flags(Compare($[V1], $[V2]))",
             arch.translate("    *({SU}*)({R:bp} + $O[ENCODED_VALUE_3]) = ((~((*({SU}*)({R:bp} + $O[ENCODED_VALUE_1]) $G[SIMPLE_MATH:OP3] *({SU}*)({R:bp} + ?O[JUNK])) $G[SIMPLE_MATH:OP1] $N[NUMBER1])) $G[SIMPLE_MATH:OP2] $N[NUMBER2])")]

    def fix_func(handler, instructions_container, index, params):
        nparams = params.copy()
        if parser.match_instructions(instructions_container.instructions, index, lines, 0, nparams)[0]:
            params.update_global(nparams)
            parser.replace_instructions(handler, instructions_container.instructions[index], 0, 1, [parser.create_macro_result("$[VAR] = FlagsOfCompareRandom()", nparams)])
            return True
        return False

    for handler in handlers:
        parser.clean_handler(handler.handler, fields, handler.parameters, [fix_func])

    assert "ENCODED_VALUE_3" in fields

def simple_optimization(handler, instructions_container, index, params):
    olen = len(instructions_container.instructions)
    if index + 1 >= olen:
        return False
    handler._optimize_instructions(instructions_container.instructions[index:index+2], {})
    handler.clean_instructions()
    return olen != len(instructions_container.instructions)