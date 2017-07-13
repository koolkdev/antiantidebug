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

def clean_get_speical_push_value_reg(handlers):
    # If VAR_VALUE is set before those if, it will be used as one of the potential values
    # But it shouldn't be that way
    # We need to remove it as soon as possible, because if we don't do it we will have junk register that will fuck up the first cleaners
    parser = handlers_parser.HandlerParser.get_default_parser()
    params = handlers_parser.Params({})

    lines = [
        "If(($V[VAR_TYPE] == $N[N1]))",
        "    $V[VAR_VALUE] = *(WORD*)(ebp + $N[O1])",
        "If(($V[VAR_TYPE] == $N[N2]))",
        "    $V[VAR_VALUE] = *(WORD*)(ebp + $N[O2])",
        "If(($V[VAR_TYPE] == $N[N3]))",
        "    $V[VAR_VALUE] = *(DWORD*)(ebp + $N[O3])",
    ]

    for handler in handlers.itervalues():
        for i in xrange(len(handler.handler.instructions)-3):
            if parser.match_instructions(handler.handler.instructions, i, lines, 0, params)[0]:
                assert len(params.vars["VAR_VALUE"].used_instructions) == 1
                use_inst = params.vars["VAR_VALUE"].used_instructions[0]
                assert params.vars["VAR_VALUE"].equals(use_inst.rvalue)
                if len(use_inst.rvalue.instructions) > 3:
                    for j in xrange(len(use_inst.rvalue.instructions) - 3):
                        # Unlink between those two registers
                        use_inst.rvalue.instructions[0].lvalue.used_instructions.remove(use_inst)
                        if len(use_inst.rvalue.instructions[0].lvalue.used_instructions) == 0:
                            # This was the only use. it is junk, remove it
                            handler.handler.make_unvisible(use_inst.rvalue.instructions[0])
                        use_inst.rvalue.instructions.remove(use_inst.rvalue.instructions[0])
                    handler.handler.optimize_instructions()
                    handler.handler.clean_instructions()
                break

def fix_handler_calls(handlers):
    parser = handlers_parser.HandlerParser.get_default_parser()
    handler_index_by_address = {handler.address: index for index, handler in handlers.iteritems()}
    for handler in handlers.itervalues():
        for i in xrange(len(handler.handler.instructions)):
            inst = handler.handler.instructions[i]
            if isinstance(inst, handlers_parser.Call):
                assert inst.address.value in handler_index_by_address
                handler_call = handlers_parser.Macro("CallHandler", [handlers_parser.Immediate(handler_index_by_address[inst.address.value]), handlers_parser.Macro("Parameters", inst.parameters)])
                parser.replace_instructions(handler.handler, handler.handler, i, 1, [handler_call])
