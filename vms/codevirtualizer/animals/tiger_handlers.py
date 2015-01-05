from common_handlers import *

RESET_KEYS = HandlerMatch(match_funcs([lines_matcher(\
    [
        "VMStructFieldDword($O[KEY_DECODE]) = 0x0",
        "VMStructFieldDword($O[KEY_COND]) = 0x0",
        "VMStructFieldDword($O[UNK_DWORD_1]) = 0x0",
        "VMStructFieldDword($O[VALUE_DWORD]) = 0x0",
        "VMStructFieldDword($O[UNK_DWORD_2]) = 0x0",
        "VMStructFieldWord($O[VALUE_WORD_1]) = 0x0",
        "VMStructFieldWord($O[VALUE_WORD_2]) = 0x0",
        "VMStructFieldWord($O[UNK_WORD]) = 0x0",
        "VMStructFieldDword($O[KEY_SPECIAL]) = 0x0",
        "VMStructFieldDword($O[KEY_DECODE_POST]) = 0x0"
    ]), UPDATE_IP_AND_JUMP]),
    create_handler_reader_class("RESET_KEYS"))

HANDLERS = [RESET_KEYS] + COMMON_HANDLERS