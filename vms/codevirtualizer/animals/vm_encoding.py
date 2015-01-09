import handlers_parser
import struct


class Key(object):
    def __init__(self, bits):
        self.value = 0
        self.bits = bits

    def do_operation(self, state, decode):
        self.value = decode.decode(state, self.value) & ((1 << self.bits) - 1)

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value & ((1 << self.bits) - 1)

    def reset(self):
        self.value = 0


class DwordKey(Key):
    def __init__(self):
        Key.__init__(self, 32)


class WordKey(Key):
    def __init__(self):
        Key.__init__(self, 16)


class ByteKey(Key):
    def __init__(self):
        Key.__init__(self, 8)


class DecodingState(object):
    def __init__(self, keys, address, read_func):
        self.keys = keys
        self.address = address
        self._read = read_func

    def read_parameter(self, offset, size):
        return struct.unpack("<%s" % {1: "B", 2: "H", 4: "L"}[size], self._read(self.address + offset, size))[0]

    def get_key(self, name):
        return self.keys[name]

    def reset(self):
        for key in self.keys.itervalues():
            key.reset()

    def update_ip(self, x):
        if x & 0x80000000:
            self.address -= x & 0x7fffffff
        else:
            self.address += x


class VarsMapping(object):
    def __init__(self):
        self.map = {}

    def get_real_var(self, var):
        # For reghigh
        if var in self.map:
            return self.map[var]
        if var - 1 in self.map:
            return self.map[var - 1] + 1
        return var

    def xchg_vars(self, var1, var2):
        oldvar1 = self.map.get(var1, var1)
        oldvar2 = self.map.get(var2, var2)
        self.map[var1] = oldvar2
        self.map[var2] = oldvar1

    def reset(self):
        self.map = {}


class FISHDecodingState(DecodingState):
    def __init__(self, address, read_func):
        DecodingState.__init__(self, {
            "KEY_DECODE": DwordKey(),
            "KEY_COND": DwordKey(),
            "KEY_REGULAR_1": DwordKey(),
            "KEY_REGULAR_2": DwordKey(),
            "KEY_UNUSED": DwordKey(),
            "KEY_SPECIAL": DwordKey(),
            "VALUE_BYTE": ByteKey(),
            }, address, read_func)


class TIGERDecodingState(DecodingState):
    def __init__(self, address, read_func):
        DecodingState.__init__(self, {
            "KEY_DECODE": DwordKey(),
            "KEY_COND": DwordKey(),
            "VALUE_DWORD": DwordKey(),
            "VALUE_DWORD_HIGH": DwordKey(),
            "VALUE_WORD_1": WordKey(),
            "VALUE_WORD_2": WordKey(),
            "KEY_SPECIAL": DwordKey(),
            "KEY_DECODE_POST": DwordKey(),
            }, address, read_func)
        self.vars = VarsMapping()


def new_fish_state(address, read_func):
    return FISHDecodingState(address, read_func)


def new_tiger_state(address, read_func):
    return TIGERDecodingState(address, read_func)


class DecodingOperation(object):
    def decode(self, state):
        pass


class DecodingValueOperation(DecodingOperation):
    def get_size(self):
        pass

    def get_offset(self):
        pass


class Decode(object):
    OPERATIONS = {"+": lambda x, y: x + y,
                  "-": lambda x, y: x - y,
                  "^": lambda x, y: x ^ y,
                  "&": lambda x, y: x & y,
                  "|": lambda x, y: x | y}

    def decode(self, state, x):
        pass


class DecodeNumber(Decode):
    def __init__(self, op, value):
        self.op = op
        self.value = value

    def decode(self, state, x):
        return Decode.OPERATIONS[self.op](x, self.value)


class DecodeKey(Decode):
    def __init__(self, op, key):
        self.op = op
        self.key = key

    def decode(self, state, x):
        return Decode.OPERATIONS[self.op](x, state.get_key(self.key).value)


class UpdateKey(DecodingOperation):
    def __init__(self, key, op):
        self.key = key
        self.op = op

    def decode(self, state):
        state.get_key(self.key).do_operation(state, self.op)


class UpdateKeyCond(DecodingOperation):
    def __init__(self, op):
        self.op = op

    def decode(self, state):
        if state.get_key("KEY_COND").get_value() & 1:
            state.get_key("KEY_COND").do_operation(state, self.op)


class UpdateKeyKey(UpdateKey):
    def __init__(self, key1, key2, op):
        UpdateKey.__init__(self, key1, DecodeKey(op, key2))


class UpdateValue(DecodingValueOperation):
    def __init__(self, value, op, read):
        self.read = read
        self.op = op
        self.value = value
        self.ops = None

    def decode(self, state):
        key = state.get_key(self.value)
        key.do_operation(state, DecodeNumber(self.op, self.read.decode(state)))
        res = key.get_value()
        if self.ops is not None:
            for op in self.ops:
                res = op.decode(state, res)
            res &= ((1 << key.bits) - 1)
        return res

    def get_size(self):
        return self.read.get_size()

    def get_offset(self):
        return self.read.get_offset()

class SetValue(DecodingValueOperation):
    def __init__(self, value, read):
        self.read = read
        self.value = value
        self.ops = None

    def decode(self, state):
        key = state.get_key(self.value)
        key.set_value(self.read.decode(state))
        res = key.get_value()
        if self.ops is not None:
            for op in self.ops:
                res = op.decode(state, res)
            res &= ((1 << key.bits) - 1)
        return res

    def get_size(self):
        return self.read.get_size()

    def get_offset(self):
        return self.read.get_offset()


class DecodeParameter(DecodingValueOperation):
    class UpdateKeyDecode(object):
        def __init__(self, key, op):
            self.op = op
            self.key = key

    def __init__(self, offset, size, ops):
        self.offset = offset
        self.size = size
        self.ops = ops

    def decode(self, state):
        res = state.read_parameter(self.offset, self.size)
        for op in self.ops:
            if type(op) is DecodeParameter.UpdateKeyDecode:
                UpdateKey(op.key, DecodeNumber(op.op, res)).decode(state)
            elif type(op) is UpdateKey:
                op.decode(state)
            else:
                res = op.decode(state, res) & 0xffffffff
        return res

    def get_size(self):
        return self.size

    def get_offset(self):
        return self.offset

class DecodeQwordParameter(DecodingValueOperation):
    def __init__(self, offset, low_dword, high_dword):
        self.offset = offset
        self.low_dword = low_dword
        self.high_dword = high_dword

    def decode(self, state):
        # Note that decode may not return dword number do to recent changes
        # But since dword is the max read size, it will return dword number
        res = self.low_dword.decode(state)
        return res | (self.high_dword.decode(state) << 0x20)

    def get_size(self):
        return 8

    def get_offset(self):
        return self.offset


class DecodeHandler(DecodingOperation):
    def __init__(self, decodes):
        self.decodes = decodes

    def decode(self, state):
        params = {}
        for decode in self.decodes:
            if isinstance(decode, DecodingValueOperation):
                # We apply the size mask here, because UpdateValue must get the value as is.
                params[decode.get_offset()] = decode.decode(state) & ((1 << (decode.get_size() * 8)) - 1)
            else:
                decode.decode(state)
        return params


def simple_optimization(handler, instructions_container, index):
    olen = len(instructions_container.instructions)
    if index + 1 >= olen:
        return False
    handler._optimize_instructions(instructions_container.instructions[index:index+2], {})
    handler.clean_instructions()
    return olen != len(instructions_container.instructions)



def get_all_read_offsets(instructions, fields):
    parser = handlers_parser.HandlerParser.get_default_parser()
    parser.groups["READ_PARAMETER"] = ["ReadParameterByte", "ReadParameterWord", "ReadParameterDword"]

    res = []

    for inst in instructions:
        if isinstance(inst, handlers_parser.ConditionBlock):
            res.extend(get_all_read_offsets(inst.instructions, fields))
        for child in inst.get_all_children():
            params = handlers_parser.Params(fields)
            if parser.match_expression(child, "$G[READ_PARAMETER:READ_OP]($N[OFFSET])", params):
                offset = params.vars["OFFSET"].value
                size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4}[params.vars["READ_OP"].value]
                res.append((offset, size))
    return res


def get_reading_decoding_info(handler, fields, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()

    parser.dont_optimize = True

    parser.groups["READ_PARAMETER"] = ["ReadParameterByte", "ReadParameterWord", "ReadParameterDword", "ReadParameterQword"]
    parser.groups["FIELDS"] = ["VMStructFieldByte", "VMStructFieldWord", "VMStructFieldDword"]
    parser.groups["SIMPLE_MATH"] = ["+", "-", "^"]
    parser.groups["UPDATE_MATH"] = ["+", "-", "^", "&", "|"]


    def find_child(expr, query, params):
        for child in expr.get_children():
            res = find_child(child, query, params)
            if res is not None:
                return res
            if parser.match_expression(child, query, params):
                return child, expr
        return None


    decoding = []
    current_decoding = None
    offset = None
    size = None

    offsets = {}

    values = {}
    values_replace = {}

    do_inside = False

    def read_decode(i):
        inst = handler.instructions[i]
        if do_inside:
           inst = inst.instructions[0]
        params = handlers_parser.Params(fields)
        res = find_child(inst, "DecodeWithNumber($G[READ_PARAMETER:READ_OP]($N[OFFSET]), SimpleOperation(Operation($[OP]), $N[NUMBER]))", params)
        if res is not None:
            expr, parent = res
            offset = params.vars["OFFSET"].value
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
            dec = DecodeNumber(params.vars["OP"].value, params.vars["NUMBER"].value)
            parent.replace_child(expr, expr.parameters[0])
            return dec, offset, size, False
        res = find_child(inst, "DecodeWithKey($G[READ_PARAMETER:READ_OP]($N[OFFSET]), SimpleOperation(Operation($[OP]), VMStructFieldDword(?O[KEY*:KEY])))", params)
        if res is not None:
            expr, parent = res
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeKey(params.vars["OP"].value, params.real_field_name["KEY"])
            parent.replace_child(expr, expr.parameters[0])
            return dec, offset, size, False
        if do_inside:
           return None
        if parser.match_expression(inst, "UpdateKeyDecode(VMStructFieldDword(?O[KEY_DECODE]), SimpleOperation(Operation($[OP]), $G[READ_PARAMETER:READ_OP]($N[OFFSET])))", params):
            # It is in tiger. And we return the new read parameter, even it isn't going to be used, because it will be handled correclty anyway
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode("KEY_DECODE", params.vars["OP"].value)
            parser.replace_instructions(handler, handler, i, 1, [])
            return dec, offset, size, True
        nparams = params.copy()
        if i + 1 < len(handler.instructions) and \
                parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", nparams) and \
                parser.match_expression(handler.instructions[i+1], "UpdateKeyDecode(VMStructFieldDword(?O[KEY_DECODE]), SimpleOperation(Operation($[OP]), $V[VAR]))", nparams):
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[nparams.vars["READ_OP"].value]
            offset = nparams.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode("KEY_DECODE", nparams.vars["OP"].value)
            parser.replace_instructions(handler, handler, i+1, 1, [])
            return dec, offset, size, False
        nparams = params.copy()
        if i + 2 < len(handler.instructions) and \
                parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", nparams) and \
                parser.match_expression(handler.instructions[i+1], "UpdateValue($G[FIELDS:FIELD](?O[VALUE_*:VALUE]), SimpleOperation(Operation($[OP1]), $V[VAR]))", nparams) and \
                parser.match_expression(handler.instructions[i+2], "UpdateKeyDecode(VMStructFieldDword(?O[KEY_DECODE_POST]), SimpleOperation(Operation($[OP]), $V[VAR]))", nparams):
            # We are dealing with UpdateKeyDecode first because it is still correct
            # and we just simplify the expression (And we we handle UpdateValue next time)
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[nparams.vars["READ_OP"].value]
            if size == 8:
                assert nparams.vars["FIELD"].value == "VMStructFieldDword"
            else:
                assert size <= {"VMStructFieldByte": 1, "VMStructFieldWord": 2, "VMStructFieldDword": 4}[nparams.vars["FIELD"].value]
            offset = nparams.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode("KEY_DECODE_POST", nparams.vars["OP"].value)
            parser.replace_instructions(handler, handler, i+2, 1, [])
            return dec, offset, size, False
        return None

    def replace_value_decoding(i):
        inst = handler.instructions[i]
        if do_inside:
            inst = inst.instructions[0]
        for name, (value_holder, read_op) in values_replace.iteritems():
            nparams = params.copy()
            res = find_child(inst, str(value_holder), nparams)
            if res is not None:
                expr, parent = res
                nres = find_child(inst, "ValueDecode(%s, $[OP1T], $[OP2T])" % str(value_holder), nparams)
                ops = []
                if nres is not None:
                    expr, parent = nres
                    if type(nparams.vars["OP1T"]) is not handlers_parser.NoneExpression:
                        assert parser.match_expression(nparams.vars["OP1T"], "SimpleOperation(Operation($[OP1]), $N[NUMBER1])", nparams)
                        ops.append(DecodeNumber(nparams.vars["OP1"].value, nparams.vars["NUMBER1"].value))
                        if type(nparams.vars["OP2T"]) is not handlers_parser.NoneExpression:
                            assert parser.match_expression(nparams.vars["OP2T"], "SimpleOperation(Operation($[OP2]), $N[NUMBER2])", nparams)
                            ops.append(DecodeNumber(nparams.vars["OP2"].value, nparams.vars["NUMBER2"].value))
                if values[name].ops is not None:
                    assert len(ops) == len(values[name].ops)
                    for j in xrange(len(ops)):
                        assert (ops[j].op, ops[j].value) == (values[name].ops[j].op, values[name].ops[j].value)
                else:
                    values[name].ops = ops

                parent.replace_child(expr, read_op)

    i = 0
    while i < len(handler.instructions):
        inst = handler.instructions[i]
        params = handlers_parser.Params(fields)
        dec = None
        if parser.match_expression(inst, "UpdateKey(VMStructFieldDword(?O[KEY*:KEY]), SimpleOperation(Operation($[X]), $[Y]))", params):
            dec = UpdateKey(params.real_field_name["KEY"], DecodeNumber(params.vars["X"].value, params.vars["Y"]. value))
            parser.replace_instructions(handler, handler, i, 1, [])
            if current_decoding is not None:
                i -= 1
        elif parser.match_expression(inst, "UpdateKeyCond(SimpleOperation(Operation($[X]), $[Y]))", params):
            dec = UpdateKeyCond(DecodeNumber(params.vars["X"].value, params.vars["Y"].value))
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "UpdateKeySpecial(Operation($[X]))", params):
            dec = UpdateKeyKey("KEY_SPECIAL", "KEY_DECODE", params.vars["X"].value)
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "UpdateKeySpecialCond(Operation($[X]))", params):
            dec = UpdateKeyKey("KEY_DECODE_POST", "KEY_COND", params.vars["X"].value)
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        else:
            res = read_decode(i)
            if res is not None:
                dec, toffset, tsize, end = res
                if current_decoding is None:
                    current_decoding = []
                    offset = toffset
                    size = tsize
                    assert offset not in offsets
                    offsets[offset] = size
                else:
                    assert offset == toffset
                    assert size == tsize
                if end:
                    current_decoding.append(dec)
                    decoding.append(DecodeParameter(offset, size, current_decoding))
                    current_decoding = None
                    continue
            elif parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params) and \
                    len(params.vars["VAR"].instructions) == 1 and len(params.vars["VAR"].used_instructions) == 1:
                if not simple_optimization(handler, handler, i):
                    i += 1
                continue
            elif parser.match_expression(inst, "UpdateValue($G[FIELDS:FIELD](?O[VALUE_*:VALUE]), SimpleOperation(Operation($[OP]), $G[READ_PARAMETER:READ_OP]($N[OFFSET])))", params):
                if current_decoding is None:
                    current_decoding = []
                    offset = params.vars["OFFSET"].value
                    size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
                    assert size <= {"VMStructFieldByte": 1, "VMStructFieldWord": 2, "VMStructFieldDword": 4}[params.vars["FIELD"].value]
                    assert offset not in offsets
                    offsets[offset] = size
                value = params.real_field_name["VALUE"]
                assert value not in values
                if size == 8:
                    assert value == "VALUE_DWORD"
                    values[value] = UpdateValue(value, params.vars["OP"].value, DecodeParameter(offset, 4, current_decoding))
                    values_replace[value] = (parser.create_macro_result("$[FIELD](?O[VALUE])", params), parser.create_macro_result("($[READ_OP]($N[OFFSET]) & 0xFFFFFFFF)", params))
                    current_decoding = [values[value]]
                else:
                    values[value] = UpdateValue(value, params.vars["OP"].value, DecodeParameter(offset, size, current_decoding))
                    values_replace[value] = (parser.create_macro_result("$[FIELD](?O[VALUE])", params), parser.create_macro_result("$[READ_OP]($N[OFFSET])", params))
                    current_decoding = None
                    decoding.append(values[value])
                parser.replace_instructions(handler, handler, i, 1, []) #parser.create_macro_result("UpdateValue($[FIELD](?O[VALUE]), $[READ_OP]($N[OFFSET]))", params)])
                # i += 1
                continue
            elif parser.match_expression(inst, "VMStructFieldDword(?O[VALUE_DWORD_HIGH]) = (ReadParameterQword($N[OFFSET]) >> 0x20)", params):
                    toffset = params.vars["OFFSET"].value
                    tsize = 8
                    assert current_decoding is not None
                    assert type(current_decoding[0]) is UpdateValue and current_decoding[0].value == "VALUE_DWORD"
                    assert offset == toffset
                    assert size == tsize
                    value = "VALUE_DWORD_HIGH"
                    values[value] = SetValue(value, DecodeParameter(offset+4, 4, current_decoding[1:]))
                    values_replace[value] = (parser.create_macro_result("VMStructFieldDword(?O[VALUE_DWORD_HIGH])", params), parser.create_macro_result("(ReadParameterQword($N[OFFSET]) >> 0x20)", params))
                    decoding.append(DecodeQwordParameter(offset, values["VALUE_DWORD"], values["VALUE_DWORD_HIGH"]))
                    current_decoding = None
                    parser.replace_instructions(handler, handler, i, 1, [])
                    continue
            elif parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params) and \
                    len(params.vars["VAR"].instructions) == 1 and len(params.vars["VAR"].used_instructions) >= 2 and \
                    type(handler.instructions[i+1]) is handlers_parser.Macro and handler.instructions[i+1].name == "UpdateKey":
                # For UpdateKey,... UpdateKeyDecode
                # TODO: Check for UpdateKey,.. UpdateKeyDecode, because right now this flow may do troubles
                # Checking only for UpdateKey isn't enough
                tsize = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
                toffset = params.vars["OFFSET"].value
                if current_decoding is None:
                    current_decoding = []
                    offset = toffset
                    size = tsize
                    assert offset not in offsets
                    offsets[offset] = size
                else:
                    assert offset == toffset
                    assert size == tsize
                i += 1
                continue
            else:
                if current_decoding:
                    decoding.append(DecodeParameter(offset, size, current_decoding))
                    current_decoding = None
                replace_value_decoding(i)
                if not do_inside and isinstance(inst, handlers_parser.ConditionBlock) and len(inst.instructions) == 1:
                    do_inside = True
                else:
                    do_inside = False
                    i += 1
                continue

        if current_decoding is not None:
            current_decoding.append(dec)
        else:
            decoding.append(dec)

    if current_decoding:
        decoding.append(DecodeParameter(offset, size, current_decoding))

    offsets_decoding = {}
    for offset, size in get_all_read_offsets(handler.instructions, fields):
        if offset in offsets:
            if offsets[offset] != size:
                assert offset in offsets_decoding
                offsets_decoding[offset].size = max(size, offsets[offset])
        else:
            for o, s in offsets.iteritems():
                assert not (o < offset < o + s or offset < o < offset + size or
                            (offset < o and offset + size >= o + s) or
                            (o < offset and o + s >= offset + size))
            offsets[offset] = size
            decoding.append(DecodeParameter(offset, size, []))
            offsets_decoding[offset] = decoding[-1]

    return DecodeHandler(decoding)


