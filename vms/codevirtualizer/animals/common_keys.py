import handlers_parser
import common_handlers
import vm_encoding


class KeyInfo(object):
    def __init__(self, name, size, check=None):
        self.name = name
        self.size = size
        self.check = check


def create_state(keys, address, read_func, cls=vm_encoding.DecodingState):
    return cls({key.name: {1: vm_encoding.ByteKey(), 2: vm_encoding.WordKey(), 4: vm_encoding.DwordKey()}[key.size] for key in keys},
        address, read_func)


def find_keys(keys, handlers, fields, arch):
    # Let's find reset key first
    handler_match = common_handlers.create_lazy_reset_key_handler([({1: "Byte", 2: "Word", 4: "Dword"}[key.size], key.name) for key in keys])

    parser = handlers_parser.HandlerParser.get_default_parser()
    reset_key_handler = None
    i = 0
    for handler in handlers:
        handler_info = common_handlers.match_handlers(parser, handler.handler, fields, [handler_match], arch)
        i +=1
        if handler_info is not None:
            handler.info = handler_info
            assert reset_key_handler is None
            reset_key_handler = handler
    assert reset_key_handler is not None

    used_offsets = []
    possible_values = {}

    for key in keys:
        if key.name in fields:
            used_offsets.append(fields[key.name])
            possible_values[key.name] = [fields[key.name]]
        else:
            possible_values[key.name] = []

    usages = {}
    expr = {}

    for i in xrange(len(keys)):
        key_size = {"VMStructFieldByte": 1,
                   "VMStructFieldWord": 2,
                   "VMStructFieldDword": 4}[reset_key_handler.handler.instructions[i].lvalue.name]
        key_offset = reset_key_handler.handler.instructions[i].lvalue.parameters[0].value
        if key_offset not in used_offsets:
            for key in keys:
                if key.name not in fields and key.size == key_size:
                    possible_values[key.name].append(key_offset)

            usages[key_offset] = []
            expr[key_offset] = str(reset_key_handler.handler.instructions[i].lvalue)
            # Find all usages. TODO: Optimize it (Only one run on all handlers)
            for handler in handlers:
                if handler == reset_key_handler:
                    continue
                handler_usages = []
                def find_usages(handler, instructions_container, index, params):
                    if parser.find_child(instructions_container.instructions[index], str(reset_key_handler.handler.instructions[i].lvalue), params) is not None:
                        handler_usages.append(instructions_container.instructions[index])
                    return False
                parser.clean_handler(handler.handler, fields, [find_usages])
                if handler_usages:
                    usages[key_offset].append(handler_usages)

    for key in keys:
        if len(possible_values[key.name]) > 1 and key.check is not None:
            found = False
            for value in possible_values[key.name]:
                if key.check(expr[value], usages[value], fields, arch):
                    found = True
                    for key_name, possible_values_list in possible_values.iteritems():
                        if key_name != key.name and value in possible_values_list:
                            possible_values_list.remove(value)
                    possible_values[key.name] = [value]
                    break
            if not found:
                print "Error: didn't find key '%s'" % key.name
                assert False

    for key in keys:
        assert len(possible_values[key.name]) > 0
        if len(possible_values[key.name]) == 1 and key.name not in fields:
            fields[key.name] = possible_values[key.name][0]

    # Now fill the rest...
    handler_info = common_handlers.match_handlers(parser, reset_key_handler.handler, fields, [common_handlers.create_reset_key_handler([({1: "Byte", 2: "Word", 4: "Dword"}[key.size], key.name) for key in keys])], arch)
    assert handler_info is not None
    reset_key_handler.info = handler_info


def check_choose_byte(expr, usages, fields, arch):
    parser = handlers_parser.HandlerParser.get_default_parser()
    params = handlers_parser.Params(fields)
    for handler_usages in usages:
        for usage in handler_usages:
            return parser.match_expression(usage, "If((%s > $N[NUMBER]))" % expr, params)


def check_if_unused(expr, usages, fields, arch):
    return len(usages) == 0

