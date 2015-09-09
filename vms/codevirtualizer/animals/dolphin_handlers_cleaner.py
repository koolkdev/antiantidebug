import handlers_parser

def clean_junk_check(handlers, fields, arch):
   cleaner = handlers_parser.HandlerParser.get_parser(r"handlers\dolphin_clean.txt", arch.mode)
   for handler in handlers:
        cleaner.clean_handler(handler.handler, fields)


def clean_junk_flag(handlers, fields, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()

    #lines = ["If((ReadParameterByte($N[PARAM1]) != 0x0))",
    #        "    VMStructFieldDword(ReadParameterWord($N[PARAM2])) = Flags($[X])"]

    lines = ["If((*(BYTE*)(*({SU}*)({R:bp} + $N[PARAMETERS_OFFSET]) + $N[PARAM1]) != 0x0))",
             "    *({SU}*)(*(WORD*)(*({SU}*)({R:bp} + $N[PARAMETERS_OFFSET]) + $N[PARAM2]) + {R:bp}) = Flags($[X])"]

    def fix_func(handler, instructions_container, index, params):
        nparams = params.copy()
        if parser.match_instructions(instructions_container.instructions, index, [arch.translate(line) for line in lines], 0, nparams)[0]:
            params.update_global(nparams)
            inst = instructions_container.instructions[index].instructions[0]
            def replace_child_flags(expr):
                for child in expr.get_children():
                    if isinstance(child, handlers_parser.FlagsOf):
                        handler.make_unvisible(inst)
                        expr.replace_child(child, parser.create_macro_result("RandomFlags()", nparams))
                        handler.make_visible(inst)
                        return True
                    if replace_child_flags(child):
                        return True
                return False
            assert replace_child_flags(inst)
            return True
        return False

    for handler in handlers:
        parser.clean_handler(handler.handler, fields, [fix_func])

def fix_encoding_values(handler, fields, arch):
    # TODO: Do it for real... Verify everything
    cleaner = handlers_parser.HandlerParser.get_parser(r"handlers\dolphin_encoding_clean.txt", arch.mode)
    cleaner.clean_handler(handler, fields)