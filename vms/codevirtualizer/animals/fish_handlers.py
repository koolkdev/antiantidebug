HANDLERS = {
    "VM_INIT":
        [
            "VMStructFieldDword($O[KEY1]) = 0x0",
            "VMStructFieldDword($O[KEY2]) = 0x0",
            "VMStructFieldDword($O[KEY3]) = 0x0",
            "VMStructFieldDword($O[KEY4]) = 0x0",
            "VMStructFieldDword($O[KEY5]) = 0x0",
            "VMStructFieldWord($O[UNKNOWN_WORD]) = 0x0",
            "VMStructFieldByte($O[ACC_BYTE]) = 0x0",
            "VMStructFieldDword($O[KEY6]) = 0x0",
            "UpdateEip(0x2)",
            "JumpToHandler(ReadParameterWord($P[NEXT_HANDLER], $[X1]))"
        ]
}


"""
if ((VMStructFieldDword($KEY2$)) & 1))
    MathUpdate(!MATH_OP_1!, VMStructFieldDword($KEY2$)

"""
