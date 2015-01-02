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

    def reset(self):
        self.value = 0


class DwordKey(Key):
    def __init__(self):
        Key.__init__(self, 32)


class AccByte(Key):
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


def new_fish_state(address, read_func):
    return DecodingState({
        "KEY1": DwordKey(),
        "KEY2": DwordKey(),
        "KEY3": DwordKey(),
        "KEY4": DwordKey(),
        "KEY5": DwordKey(),
        "KEY6": DwordKey(),
        "ACC_BYTE": AccByte(),
        }, address, read_func)


class DecodingOperation(object):
    def decode(self, state):
        pass


class DecodingValueOperation(DecodingOperation):
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
        if state.get_key("KEY2").get_value() & 1:
            state.get_key("KEY2").do_operation(state, self.op)


class UpdateKeySpecial(UpdateKey):
    def __init__(self, op):
        UpdateKey.__init__(self, "KEY6", DecodeKey(op, "KEY1"))


class UpdateAccByte(DecodingValueOperation):
    def __init__(self, op, read):
        self.read = read
        self.op = op

    def decode(self, state):
        state.get_key("ACC_BYTE").do_operation(state, DecodeNumber(self.op, self.read.decode(state)))
        return state.get_key("ACC_BYTE").get_value()

    def get_offset(self):
        return self.read.get_offset()


class DecodeParameter(DecodingValueOperation):
    class UpdateKeyDecode(object):
        def __init__(self, op):
            self.op = op

    def __init__(self, offset, size, ops):
        self.offset = offset
        self.size = size
        self.ops = ops

    def decode(self, state):
        res = state.read_parameter(self.offset, self.size)
        for op in self.ops:
            if type(op) is DecodeParameter.UpdateKeyDecode:
                UpdateKey("KEY1", DecodeNumber(op.op, res)).decode(state)
            elif type(op) is UpdateKey:
                op.decode(state)
            else:
                res = op.decode(state, res) & 0xffffffff
        return res & ((1 << (self.size * 8)) - 1)

    def get_offset(self):
        return self.offset


class DecodeHandler(DecodingOperation):
    def __init__(self, decodes):
        self.decodes = decodes

    def decode(self, state):
        params = {}
        for decode in self.decodes:
            if isinstance(decode, DecodingValueOperation):
                params[decode.get_offset()] = decode.decode(state)
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

    parser.groups["READ_PARAMETER"] = ["ReadParameterByte", "ReadParameterWord", "ReadParameterDword"]
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

    acc_byte = None

    def read_decode(i):
        inst = handler.instructions[i]
        if arch.native_size() == 8 and isinstance(inst, handlers_parser.ConditionBlock) and len(inst.instructions) == 1 and " << 0x20) | " in str(inst.instructions[0]):
            # Hack for inside condition decoding in 64bit
            inst = inst.instructions[0]
        params = handlers_parser.Params(fields)
        res = find_child(inst, "DecodeWithNumber($G[READ_PARAMETER:READ_OP]($N[OFFSET]), SimpleOperation(Operation($[OP]), $N[NUMBER]))", params)
        if res is not None:
            expr, parent = res
            offset = params.vars["OFFSET"].value
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4}[params.vars["READ_OP"].value]
            dec = DecodeNumber(params.vars["OP"].value, params.vars["NUMBER"].value)
            parent.replace_child(expr, expr.parameters[0])
            return dec, offset, size
        res = find_child(inst, "DecodeWithKey($G[READ_PARAMETER:READ_OP]($N[OFFSET]), SimpleOperation(Operation($[OP]), VMStructFieldDword(?O[KEY*:KEY])))", params)
        if res is not None:
            expr, parent = res
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeKey(params.vars["OP"].value, params.real_field_name["KEY"])
            parent.replace_child(expr, expr.parameters[0])
            return dec, offset, size
        if i + 1 < len(handler.instructions) and \
                parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params) and \
                parser.match_expression(handler.instructions[i+1], "UpdateKeyDecode(SimpleOperation(Operation($[OP]), $V[VAR]))", params):
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode(params.vars["OP"].value)
            parser.replace_instructions(handler, handler, i+1, 1, [])
            return dec, offset, size
        return None

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
            dec = UpdateKeySpecial(params.vars["X"].value)
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        else:
            res = read_decode(i)
            if res is not None:
                dec, toffset, tsize = res
                if current_decoding is None:
                    current_decoding = []
                    offset = toffset
                    size = tsize
                    assert offset not in offsets
                    offsets[offset] = size
                else:
                    assert offset == toffset
                    assert size == tsize
            elif parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params) and \
                    len(params.vars["VAR"].instructions) == 1 and len(params.vars["VAR"].used_instructions) == 1:
                if not simple_optimization(handler, handler, i):
                    i += 1
                continue
            elif parser.match_expression(inst, "UpdateAccByte(SimpleOperation(Operation($[OP]), ReadParameterByte($N[OFFSET])))", params):
                if current_decoding is None:
                    current_decoding = []
                    offset = params.vars["OFFSET"].value
                    size = 1
                    assert offset not in offsets
                    offsets[offset] = size
                assert acc_byte is None
                acc_byte = UpdateAccByte(params.vars["OP"].value, DecodeParameter(offset, size, current_decoding))
                current_decoding = None
                decoding.append(acc_byte)
                parser.replace_instructions(handler, handler, i, 1, [parser.create_macro_result("UpdateAccByte(ReadParameterByte($N[OFFSET]))", params)])
                i += 1
                continue
            elif parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params) and \
                    len(params.vars["VAR"].instructions) == 1 and len(params.vars["VAR"].used_instructions) == 2:
                # For UpdateKey,... UpdateKeyDecode
                # TODO: Check for UpdateKey,.. UpdateKeyDecode, because right now this flow may do troubles
                tsize = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4}[params.vars["READ_OP"].value]
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


