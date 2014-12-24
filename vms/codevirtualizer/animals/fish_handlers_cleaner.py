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
            parser.replace_instructions(handler, instructions_container.instructions[index], 0, 1, [parser.create_macro_result("$[VAR] = RandomFlags()", nparams)])
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

def fix_encoding_values(handler, fields):
    parser = handlers_parser.HandlerParser.get_default_parser()

    to_replace = []
    lines_to_replace = []
    def fix_func(handler, instructions_container, index, params):
        nparams = params.copy()
        parser.replace_macros_in_expression(handler, to_replace, instructions_container.instructions[index], params)
        parser.replace_instructions_templates(handler, lines_to_replace, instructions_container, index, params)
        if parser.match_instructions(instructions_container.instructions, index, ["$[X1] = EncodedValue($[X2], SimpleOperation(Operation($[OP1]), $[VAR1]), $[OP2T])"], 0, nparams)[0]:
            current_expression = nparams.vars["X1"]
            encoding_expression = handlers_parser.Str("$[X]")
            if type(nparams.vars["OP2T"]) is not handlers_parser.NoneExpression:
                assert parser.match_expression(nparams.vars["OP2T"], "SimpleOperation(Operation($[OP2]), $[VAR2])", nparams)
                if str(nparams.vars["OP2"]) == "+":
                    neg_op = handlers_parser.Sub
                elif str(nparams.vars["OP2"]) == "-":
                    neg_op = handlers_parser.Add
                elif str(nparams.vars["OP2"]) == "^":
                    neg_op = handlers_parser.Xor
                current_expression = neg_op(current_expression, nparams.vars["VAR2"])
            if str(nparams.vars["OP1"]) == "+":
                neg_op = handlers_parser.Sub
            elif str(nparams.vars["OP1"]) == "-":
                neg_op = handlers_parser.Add
            elif str(nparams.vars["OP1"]) == "^":
                neg_op = handlers_parser.Xor
            current_expression = neg_op(current_expression, nparams.vars["VAR1"])
            encoding_expression = handlers_parser.OPS[str(nparams.vars["OP1"])](encoding_expression, nparams.vars["VAR1"])
            if type(nparams.vars["OP2T"]) is not handlers_parser.NoneExpression:
                encoding_expression = handlers_parser.OPS[str(nparams.vars["OP2"])](encoding_expression, nparams.vars["VAR2"])
            encoding_expression = handlers_parser.SetValue(nparams.vars["X1"], encoding_expression)
            encoding_expression_result = handlers_parser.SetValue(nparams.vars["X1"], handlers_parser.Macro("EncodedValue", [handlers_parser.Str("$[X]")]))
            parser.replace_instructions(handler, instructions_container, index, 1, [parser.create_macro_result("$[X1] = EncodedValue($[X2])", nparams)])
            res = (str(current_expression), str(parser.create_macro_result("DecodedValue($[X1])", nparams)))
            res_lines = ([str(encoding_expression)], str(encoding_expression_result))
            if res not in to_replace:
                assert res_lines not in lines_to_replace
                to_replace.append(res)
                lines_to_replace.append(res_lines)
            else:
                assert res_lines in lines_to_replace
                assert type(nparams.vars["OP2T"]) is handlers_parser.NoneExpression and type(nparams.vars["VAR1"]) is handlers_parser.Immediate
            #return True # No need a second pass
        elif parser.match_instructions(instructions_container.instructions, index, ["$[X1] = EncodedValueByte($[X2], SimpleOperation(Operation($[OP1]), $[VAR1]))"], 0, nparams)[0]:
            current_expression = nparams.vars["X1"]
            if str(nparams.vars["OP1"]) == "+":
                neg_op = handlers_parser.Sub
            elif str(nparams.vars["OP1"]) == "-":
                neg_op = handlers_parser.Add
            elif str(nparams.vars["OP1"]) == "^":
                neg_op = handlers_parser.Xor
            current_expression = neg_op(current_expression, nparams.vars["VAR1"])
            res = (str(current_expression), str(parser.create_macro_result("DecodedValueByte($[X1])", nparams)))
            assert res not in to_replace
            to_replace.append(res)
            # BUG!! For specific case size decoding in 64 bit
            res = (str(current_expression).replace("VMStructFieldByte", "VMStructFieldQword"), str(parser.create_macro_result("DecodedValueByte($[X1])", nparams)))
            to_replace.append(res)
        return False
    parser.clean_handler(handler.handler, fields, handler.parameters, [fix_func], reverse=False)
