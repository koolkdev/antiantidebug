import common_keys
import handlers_parser


def check_value_dword(expr, usages, fields, arch):
    for handler_usages in usages:
        for usage in handler_usages:
            if type(usage) is handlers_parser.Push or type(usage) is handlers_parser.PushWord:
                return True
    return False


def check_value_dword_high(expr, usages, fields, arch):
    if arch.mode == 32:
        return len(usages) == 0
    if len(usages) != 1:
        return False
    parser = handlers_parser.HandlerParser.get_default_parser()
    params = handlers_parser.Params(fields)
    for usage in usages[0]:
        if parser.match_expression(usage, "%s = (ReadParameterQword($N[OFFSET]) >> 0x20)" % expr, params):
            return True
    return False


KEYS = [
    # We don't distinguish anymore between the keys
    common_keys.KeyInfo("KEY_1", 4),
    common_keys.KeyInfo("KEY_2", 4),
    common_keys.KeyInfo("KEY_3", 4),
    common_keys.KeyInfo("KEY_4", 4),

    common_keys.KeyInfo("UNKNOWN_DWORD", 4, common_keys.check_if_unused),

    common_keys.KeyInfo("VALUE_DWORD", 4, check_value_dword),
    common_keys.KeyInfo("VALUE_DWORD_HIGH", 4, check_value_dword_high),

    # Not used
    common_keys.KeyInfo("UNKNOWN_WORD", 2, common_keys.check_if_unused),
    common_keys.KeyInfo("VALUE_WORD_1", 2),
    common_keys.KeyInfo("VALUE_WORD_2", 2),

    # For the new conditions (<= conditions)
    common_keys.KeyInfo("KEY_CHOOSE_BYTE", 1, common_keys.check_choose_byte),
]


