HANDLERS = {
    "INIT_HANDLER":
        [
            "VMStructFieldDword($KEY1) = 0x0",
            "VMStructFieldDword($KEY2) = 0x0",
            "VMStructFieldDword($KEY3) = 0x0",
            "VMStructFieldDword($KEY4) = 0x0",
            "VMStructFieldDword($KEY5) = 0x0",
            "VMStructFieldWord($UNKNOWN_WORD) = 0x0",
            "VMStructFieldByte($ACC_BYTE) = 0x0",
            "VMStructFieldDword($KEY6) = 0x0",
            "UpdateEipAndJump(ReadParameterWord(#NEXT_HANDLER), 0x2)"
        ]
}


"""
if ((VMStructFieldDword($KEY2$)) & 1))
    MathUpdate(!MATH_OP_1!, VMStructFieldDword($KEY2$)

"""
