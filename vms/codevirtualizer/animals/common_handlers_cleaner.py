import handlers_parser

#
# Push($[X]),
# UpdateEip($[Y])
# Return(0)
# =>
# UpdateEip($[Y])
# Return(0)
#
def fix_push_ret(handler):
    parser = handlers_parser.HandlerParser.get_default_parser()
    params = handlers_parser.Params({})

    # handlers_final_tiger will take care of the case UpdateEip Push Return
    lines = ["Push($[X])",
             "UpdateEip($[Y])",
             "Return(0)"]
    if len(handler.instructions) >= 3:
        if parser.match_instructions(handler.instructions, len(handler.instructions) - 3, lines, 0, params)[0]:
            parser.replace_instructions(handler, handler, len(handler.instructions) - 3, 3, [parser.create_macro_result("UpdateEip($[Y])", params), parser.create_macro_result("Jump($[X])", params)])

def fix_jump_to_field(handler, fields, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()
    params = handlers_parser.Params(fields)
    if parser.match_instructions(handler.instructions, len(handler.instructions) - 1, [arch.translate("Jump(VMStructField{SS}($O[NEXT_HANDLER]))")], 0, params)[0]:
        fields.update(params.fields)
        for i in xrange(len(handler.instructions)-1):
            if parser.match_instructions(handler.instructions, i, [arch.translate("VMStructField{SS}(?O[NEXT_HANDLER]) = HandlerIndex(ReadParameterWord($N[PARAM]))")], 0, params)[0]:
                parser.replace_instructions(handler, handler, len(handler.instructions) - 1, 1, [parser.create_macro_result("JumpToHandlerByIndex(ReadParameterWord($N[PARAM]))", params)])
                parser.replace_instructions(handler, handler, i, 1, [])
                return
        assert False