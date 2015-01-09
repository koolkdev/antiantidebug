import handlers_parser

def get_vars_xchg(handler, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()
    xchg_fields_pre = []
    xchg_fields_post = []
    params = handlers_parser.Params({})
    xchg_line = arch.translate("XchgStructFields(VMStructField{SS}(ReadParameterWord($P[DST])), VMStructField{SS}(ReadParameterWord($P[SRC])))")
    while len(handler.instructions) >= 1 and \
            parser.match_instructions(handler.instructions, 0, [xchg_line], 0, params)[0]:
        xchg_fields_pre.append((params.parameters["DST"], params.parameters["SRC"]))
        parser.replace_instructions(handler, handler, 0, 1, [])
        params = handlers_parser.Params({})
    while len(handler.instructions) >= 3 and \
            parser.match_instructions(handler.instructions, len(handler.instructions) - 3,
                                    [
                                        xchg_line,
                                        "UpdateEip($N[X])",
                                        "JumpToHandler(ReadParameterWord($N[Y]))",
                                    ], 0, params)[0]:
        xchg_fields_post.append((params.parameters["DST"], params.parameters["SRC"]))
        parser.replace_instructions(handler, handler, len(handler.instructions) - 3, 1, [])
        params = handlers_parser.Params({})
    return (xchg_fields_pre, xchg_fields_post)