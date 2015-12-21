import common_keys


KEYS = [
    # We don't distinguish anymore between the keys
    common_keys.KeyInfo("KEY_1", 4),
    common_keys.KeyInfo("KEY_2", 4),
    common_keys.KeyInfo("KEY_3", 4),
    common_keys.KeyInfo("KEY_4", 4),
    common_keys.KeyInfo("KEY_5", 4),
    common_keys.KeyInfo("KEY_6", 4),

    # Not used
    common_keys.KeyInfo("UNKNOWN_WORD", 2, common_keys.check_if_unused),

    # For the new conditions (<= conditions)
    common_keys.KeyInfo("KEY_CHOOSE_BYTE", 1, common_keys.check_choose_byte),
    # Store the type of the operation, the only byte key left, no need to check it
    common_keys.KeyInfo("VALUE_BYTE", 1),
]

