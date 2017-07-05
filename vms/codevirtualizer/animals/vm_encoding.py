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


class TIGERDecodingStateOld(DecodingState):
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


class DOLPHINDecodingState(DecodingState):
    def __init__(self, address, read_func):
        DecodingState.__init__(self, {
            "KEY_DECODE": DwordKey(),
            "KEY_COND": DwordKey(),
            "KEY_UNUSED": DwordKey(),
            }, address, read_func)
        self.params = {}


class TIGERDecodingState(DecodingState):
    def __init__(self, keys, address, read_func):
        DecodingState.__init__(self, keys, address, read_func)
        self.vars = VarsMapping()


def new_fish_state(address, read_func):
    return FISHDecodingState(address, read_func)


def new_tiger_state(address, read_func):
    return TIGERDecodingStateOld(address, read_func)


def new_dolphin_state(address, read_func):
    return DOLPHINDecodingState(address, read_func)


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


class DecodeIf(Decode):
    def __init__(self, key, cond, op):
        self.key = key
        self.cond = cond
        self.op = op

    def decode(self, state, x):
        if self.cond(state.get_key(self.key).value):
            return self.op.decode(state, x)
        else:
            return x


class DecodeKey(Decode):
    def __init__(self, op, key):
        self.op = op
        self.key = key

    def decode(self, state, x):
        return Decode.OPERATIONS[self.op](x, state.get_key(self.key).value)


# New more generic design
class Operation(object):
    def decode(self, state):
        pass


class ValueOperation(object):
    def decode(self, state):
        pass


class UpdateOperation(object):
    def decode(self, state):
        pass


class DecodeOperation(ValueOperation):
    OPERATIONS = {"+": lambda x, y: x + y,
                  "-": lambda x, y: x - y,
                  "^": lambda x, y: x ^ y,
                  "&": lambda x, y: x & y,
                  "|": lambda x, y: x | y}

    def __init__(self, op, lvalue, rvalue):
        self.op = op
        self.lvalue = lvalue
        assert isinstance(self.lvalue, ValueOperation)
        self.rvalue = rvalue
        assert isinstance(self.rvalue, ValueOperation)

    def decode(self, state):
        return self.OPERATIONS[self.op](self.lvalue.decode(state), self.rvalue.decode(state))


class GetKey(ValueOperation):
    def __init__(self, key):
        self.key = key

    def decode(self, state):
        return state.get_key(self.key).value


class Number(ValueOperation):
    def __init__(self, value):
        self.value = value

    def decode(self, state):
        return self.value


class SetKey(UpdateOperation):
    def __init__(self, key, value):
        self.key = key
        self.value = value
        isinstance(self.value, ValueOperation)

    def decode(self, state):
        return state.get_key(self.key).set_value(self.value.decode(state))


class UpdateKey(DecodingOperation):
    def __init__(self, key, op):
        self.key = key
        self.op = op

    def decode(self, state):
        state.get_key(self.key).do_operation(state, self.op)


class UpdateKeyCond(DecodingOperation):
    def __init__(self, key, bit, op1=None, op2=None):
        self.key = key
        self.bit = bit
        self.op1 = op1
        self.op2 = op2

    def decode(self, state):
        if state.get_key(self.key).get_value() & self.bit:
            if self.op1 is not None:
                self.op1.decode(state)
            if self.op2 is not None:
                self.op2.decode(state)


class XchgKeys(DecodingOperation):
    def __init__(self, key1, key2):
        self.key1 = key1
        self.key2 = key2

    def decode(self, state):
        key1 = state.get_key(self.key1).get_value()
        state.get_key(self.key1).set_value(state.get_key(self.key2).get_value())
        state.get_key(self.key2).set_value(key1)


class UpdateKeyEx(DecodingOperation):
    def __init__(self, key1, op1, key2, op2):
        self.key1 = key1
        self.op1 = op1
        self.key2 = key2
        self.op2 = op2

    def decode(self, state):
        # key1 op1= op2(key2)
        value = state.get_key(self.key2).get_value()
        if self.op2 is not None:
            value = self.op2.decode(state, value)
        state.get_key(self.key1).do_operation(state, DecodeNumber(self.op1, value))


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
            elif type(op) is UpdateKey or isinstance(op, UpdateOperation):
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


class ResetKeys(DecodingOperation):
    def __init__(self):
        pass

    def decode(self, state):
        state.reset()


def simple_optimization(handler, instructions_container, index):
    olen = len(instructions_container.instructions)
    if index + 1 >= olen:
        return False
    to_optimize = 2
    # This can be safely be skipped
    if isinstance(instructions_container.instructions[index+1], handlers_parser.Macro) and instructions_container.instructions[index+1].name == "UpdateEip":
        to_optimize += 1
    handler._optimize_instructions(instructions_container.instructions[index:index+to_optimize], {})
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
    if arch.mode == 32:
        native_field = "VMStructFieldDword"
    else:
        native_field = "VMStructFieldQword"


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
    current_xchg_var = None
    current_xchg_middle = False
    current_xchg_key1 = None
    current_xchg_key2 = None

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
        if find_child(inst, "%s(?O[JUNK])" % native_field, params) is None: # HACK FOR FISH ENCODED VALUE, TODO IT BETTER
            # TODO: Handle this properly. We need to create a proper macro for it, and not to confuse it with the fish var encoding
            res = find_child(inst, "($G[READ_PARAMETER:READ_OP]($N[OFFSET]) $G[SIMPLE_MATH:OP] $N[NUMBER])", params)
            if res is not None:
                expr, parent = res
                size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
                offset = params.vars["OFFSET"].value
                dec = DecodeNumber(params.vars["OP"].value, params.vars["NUMBER"].value)
                parent.replace_child(expr, expr.lvalue)
                return dec, offset, size, False
        res = find_child(inst, "DecodeIfLess($G[READ_PARAMETER:READ_OP]($N[OFFSET]), VMStructFieldByte(?O[KEY_*:KEY]), $N[NUMBER], SimpleOperation(Operation($[OP]), $N[NUMBER2]))", params)
        if res is not None:
            # KEY_CHOOSE_BYTE, For tiger
            expr, parent = res
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeIf(params.real_field_name["KEY"], lambda x: x > params.vars["NUMBER"].value, DecodeNumber(params.vars["OP"].value, params.vars["NUMBER2"].value))
            parent.replace_child(expr, expr.parameters[0])
            return dec, offset, size, False
        if parser.match_expression(inst, "UpdateKeyDecode(VMStructFieldDword(?O[KEY*:KEY]), SimpleOperation(Operation($[OP]), $G[READ_PARAMETER:READ_OP]($N[OFFSET])))", params):
            # It is in tiger. And we return the new read parameter, even it isn't going to be used, because it will be handled correclty anyway
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode(params.real_field_name["KEY"], params.vars["OP"].value)
            parser.replace_instructions(handler, handler, i, 1, [])
            return dec, offset, size, True
        if parser.match_expression(inst, "VMStructFieldDword(?O[KEY*:KEY]) $G[UPDATE_MATH:OP]= $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params):
            # Same as UpdateKeyDecode
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[params.vars["READ_OP"].value]
            offset = params.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode(params.real_field_name["KEY"], params.vars["OP"].value)
            parser.replace_instructions(handler, handler, i, 1, [])
            return dec, offset, size, True
        nparams = params.copy()
        if i + 1 < len(handler.instructions) and \
                parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", nparams) and \
                parser.match_expression(handler.instructions[i+1], "UpdateKeyDecode($G[FIELDS:KEY_FIELD](?O[KEY*:KEY]), SimpleOperation(Operation($[OP]), $V[VAR]))", nparams):
            # TODO: Check that key size is right
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[nparams.vars["READ_OP"].value]
            offset = nparams.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode(nparams.real_field_name["KEY"], nparams.vars["OP"].value)
            parser.replace_instructions(handler, handler, i+1, 1, [])
            return dec, offset, size, False
        nparams = params.copy()
        if i + 2 < len(handler.instructions) and \
                parser.match_expression(inst, "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", nparams) and \
                parser.match_expression(handler.instructions[i+1], "UpdateValue($G[FIELDS:FIELD](?O[VALUE_*:VALUE]), SimpleOperation(Operation($[OP1]), $V[VAR]))", nparams) and \
                parser.match_expression(handler.instructions[i+2], "UpdateKeyDecode(VMStructFieldDword(?O[KEY*:KEY]), SimpleOperation(Operation($[OP]), $V[VAR]))", nparams):
            # The key is KEY_DECODE_POST
            # We are dealing with UpdateKeyDecode first because it is still correct
            # and we just simplify the expression (And we we handle UpdateValue next time)
            size = {"ReadParameterByte": 1, "ReadParameterWord": 2, "ReadParameterDword": 4, "ReadParameterQword": 8}[nparams.vars["READ_OP"].value]
            if size == 8:
                assert nparams.vars["FIELD"].value == "VMStructFieldDword"
            else:
                assert size <= {"VMStructFieldByte": 1, "VMStructFieldWord": 2, "VMStructFieldDword": 4}[nparams.vars["FIELD"].value]
            offset = nparams.vars["OFFSET"].value
            dec = DecodeParameter.UpdateKeyDecode(params.real_field_name["KEY"], nparams.vars["OP"].value)
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
        if parser.match_expression(inst, "UpdateKey($G[FIELDS:KEY_FIELD](?O[KEY*:KEY]), SimpleOperation(Operation($[X]), $[Y]))", params):
            # TODO: Check that key size is fit
            dec = UpdateKey(params.real_field_name["KEY"], DecodeNumber(params.vars["X"].value, params.vars["Y"]. value))
            parser.replace_instructions(handler, handler, i, 1, [])
            # If it is right after the reading of the parameter, we haven't create the current decoding yet
            if current_decoding is not None or (i > 0 and parser.match_expression(handler.instructions[i-1], "$V[VAR] = $G[READ_PARAMETER:READ_OP]($N[OFFSET])", params.copy())):
                i -= 1
        elif parser.match_expression(inst, "UpdateKeyCond(VMStructFieldDword(?O[KEY*:KEY]), $N[BIT], $[OPT1], $[OPT2])", params):
            if type(params.vars["OPT1"]) is not handlers_parser.NoneExpression:
                assert parser.match_expression(params.vars["OPT1"], "UpdateKey(VMStructFieldDword(?O[KEY_*:KEY1]), SimpleOperation(Operation($[OP1]), $[NUM1]))", params)
                op1 = UpdateKey(params.real_field_name["KEY1"], DecodeNumber(params.vars["OP1"].value, params.vars["NUM1"].value))
            else:
                op1 = None
            if type(params.vars["OPT2"]) is not handlers_parser.NoneExpression:
                assert parser.match_expression(params.vars["OPT2"], "UpdateKey(VMStructFieldDword(?O[KEY_*:KEY2]), SimpleOperation(Operation($[OP2]), $[NUM2]))", params)
                op2 = UpdateKey(params.real_field_name["KEY2"], DecodeNumber(params.vars["OP2"].value, params.vars["NUM2"].value))
            else:
                op2 = None
            dec = UpdateKeyCond(params.real_field_name["KEY"], params.vars["BIT"].value, op1, op2)
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "UpdateKeyComplex(VMStructFieldDword(?O[KEY_*:KEY1]), Operation($[OP1]), VMStructFieldDword(?O[KEY_*:KEY2]), $[OPT])", params):
            if type(params.vars["OPT"]) is not handlers_parser.NoneExpression:
                assert parser.match_expression(params.vars["OPT"], "SimpleOperation(Operation($[OP2]), $[NUM])", params)
                op2 = DecodeNumber(params.vars["OP2"].value, params.vars["NUM"].value)
            else:
                op2 = None
            dec = UpdateKeyEx(params.real_field_name["KEY1"], params.vars["OP1"].value, params.real_field_name["KEY2"], op2)
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "UpdateKeyComplex2(VMStructFieldDword(?O[KEY_*:KEY1]), Operation($[OP3]), $[OPT1], SimpleOperation(Operation($[OP2]), VMStructFieldDword(?O[KEY_*:KEY2])))", params):
            value = GetKey(params.real_field_name["KEY1"])
            if type(params.vars["OPT1"]) is not handlers_parser.NoneExpression:
                assert parser.match_expression(params.vars["OPT1"], "SimpleOperation(Operation($[OP1]), $[NUM])", params)
                value = DecodeOperation(params.vars["OP1"].value, value, Number(params.vars["NUM"].value))
            dec = SetKey(params.real_field_name["KEY1"], DecodeOperation(params.vars["OP3"].value, GetKey(params.real_field_name["KEY1"]), DecodeOperation(params.vars["OP2"].value, value, GetKey(params.real_field_name["KEY2"]))))
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "XchgKeys(VMStructFieldDword(?O[KEY_*:KEY1]), VMStructFieldDword(?O[KEY_*:KEY2]))", params):
            dec = XchgKeys(params.real_field_name["KEY1"], params.real_field_name["KEY2"])
            assert current_decoding is None
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "ResetKeys()", params):
            assert current_decoding is None
            dec = ResetKeys()
            i += 1
        elif parser.match_expression(inst, "XchgKeys1($V[VAR], VMStructFieldDword(?O[KEY_*:KEY]))", params):
            # TODO: Can one of the keys change during xchg? because there may be other key updates between the xchg
            # TODO: add checks to verify it
            assert len(params.vars["VAR"].instructions) == 0 and len(params.vars["VAR"].used_instructions) == 1
            assert current_decoding is None
            assert current_xchg_var is None
            current_xchg_var = params.vars["VAR"].used_instructions[0]
            current_xchg_key1 = params.real_field_name["KEY"]
            parser.replace_instructions(handler, handler, i, 1, [])
            continue
        elif parser.match_expression(inst, "XchgKeys2(VMStructFieldDword(?O[KEY_*:KEY1]), VMStructFieldDword(?O[KEY_*:KEY2]))", params):
            assert current_decoding is None
            assert current_xchg_var is not None
            assert current_xchg_key1 == params.real_field_name["KEY1"]
            current_xchg_key2 = params.real_field_name["KEY2"]
            current_xchg_middle = True
            dec = XchgKeys(params.real_field_name["KEY1"], params.real_field_name["KEY2"])
            parser.replace_instructions(handler, handler, i, 1, [])
        elif parser.match_expression(inst, "XchgKeys3($V[VAR], VMStructFieldDword(?O[KEY_*:KEY]))", params):
            assert current_xchg_var == inst
            assert current_xchg_middle
            assert current_decoding is None
            assert current_xchg_key2 == params.real_field_name["KEY"]
            current_xchg_var = None
            current_xchg_middle = False
            parser.replace_instructions(handler, handler, i, 1, [])
            continue
        else:
            res = read_decode(i)
            if res is not None:
                dec, toffset, tsize, end = res
                if current_decoding is not None:
                    if offset == toffset:
                        assert size == tsize
                    else:
                        # The parameter was just for update key decode, so there should be at least one
                        assert any([x for x in current_decoding if type(x) is DecodeParameter.UpdateKeyDecode])
                        decoding.append(DecodeParameter(offset, size, current_decoding))
                        current_decoding = None
                if current_decoding is None:
                    current_decoding = []
                    offset = toffset
                    size = tsize
                    assert offset not in offsets
                    offsets[offset] = size
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
                    # We need to skip UpdateEip
                    if not (isinstance(inst, handlers_parser.Macro) and inst.name == "UpdateEip"):
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

    assert current_xchg_var is None
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


