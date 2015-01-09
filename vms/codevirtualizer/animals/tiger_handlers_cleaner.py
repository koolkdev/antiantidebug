import handlers_parser

def get_vars_xchg(handler, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()
    xchg_fields_pre = []
    xchg_fields_post = []
    params = handlers_parser.Params({})
    xchg_line = arch.translate("XchgStructFields(VMStructField{SS}(ReadParameterWord($N[DST])), VMStructField{SS}(ReadParameterWord($N[SRC])))")
    while len(handler.instructions) >= 1 and parser.match_expression(handler.instructions[0], xchg_line, params):
        xchg_fields_pre.append((params.vars["DST"].value, params.vars["SRC"].value))
        parser.replace_instructions(handler, handler, 0, 1, [])
        params = handlers_parser.Params({})
    # Those are the changes that suppose to happen after the operations. They are not always at the end
    # (sometimes they are before flag updating for example, acutally, it is the only case of it that I saw).
    # So we will treat all the xchgs that not at the start, as one that at the ends
    # xchgs that happens after the operation. It seems to happen mostly on Strings operations (and push/pop?)
    # TODO: Handle it better... (Maybe just check for all cases? sometimes = Flags and sometimes = var_1)
    i = 1
    while i < len(handler.instructions):
        if parser.match_expression(handler.instructions[i], xchg_line, params):
            xchg_fields_post.append((params.vars["DST"].value, params.vars["SRC"].value))
            parser.replace_instructions(handler, handler, i, 1, [])
            params = handlers_parser.Params({})
        else:
            i += 1
    return (xchg_fields_pre, xchg_fields_post)