import common_keys
import handlers_parser


def check_cond(expr, usages, fields, arch):
    for handler_usages in usages:
        for usage in handler_usages:
            if isinstance(usage, handlers_parser.If):
                return True
    return False

KEYS = [
    common_keys.KeyInfo("KEY_ENCODE", 4),
    common_keys.KeyInfo("KEY_COND", 4, check_cond),
    common_keys.KeyInfo("KEY_UNUSED", 4, common_keys.check_if_unused),
]

