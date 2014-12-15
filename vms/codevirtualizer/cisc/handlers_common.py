from collections import namedtuple
import itertools
import re

HANDLERS = {

"STACK_PUSH_REGREF":
"""
lodsb
movzx {R:ax}, al
lea {R:ax}, [{R:di}+{R:ax}*{N}]
push {R:ax}
""",

"STACK_POP_DX":
"""
pop {R:dx}
""",

"PUSH_WORD_IMM":
"""
lodsw
movzx eax, ax
push ax
""",

"PUSH_DWORD_IMM":
"""
lodsd
push {R:ax}
""",

"STACK_ADD":
"""
pop {R:ax}
add {S} [{R:sp}], {R:ax}
""",

"STACK_SHL":
"""
pop {R:cx}
shl dword [{R:sp}], cl
""",

"STACK_PUSH_REG":
"""
lodsb
movzx {R:ax}, al
push {S} [{R:di}+{R:ax}*{N}]
""",

"STACK_PUSH_DX":
"""
push {R:dx}
""",

"STACK_PUSH_BYTE_MEMDX":
"""
movzx ax, byte [{R:dx}]
push ax
""",

"STACK_PUSH_WORD_MEMDX":
"""
push word [{R:dx}]
""",

"STACK_PUSH_BYTE_REG":
"""
lodsb
movzx {R:ax}, al
mov {R:ax}, {S} [{R:di}+{R:ax}*{N}]
movzx ax, byte [{R:ax}]
push ax
""",

"STACK_PUSH_WORD_REG":
"""
lodsb
movzx {R:ax}, al
mov {R:ax}, {S} [{R:di}+{R:ax}*{N}]
push word [{R:ax}]
""",

"STACK_PUSH_BYTE_MEMIMM":
"""
lods{SB}
movzx ax, byte [{R:ax}]
push ax
""",

"STACK_PUSH_WORD_MEMIMM":
"""
lods{SB}
push word [{R:ax}]
""",

"STACK_POP_BYTE_MEMDX":
"""
pop ax
mov byte [{R:dx}], al
""",

"STACK_POP_WORD_MEMDX":
"""
pop word [{R:dx}]
""",

"STACK_POP_BYTE_REGHIGH":
"""
lodsb
movzx {R:ax}, al
pop dx
mov byte [{R:di}+{R:ax}*{N}+0x1], dl
""",

"STACK_POP_BYTE_REG":
"""
lodsb
movzx {R:ax}, al
pop dx
mov byte [{R:di}+{R:ax}*{N}], dl
""",

"STACK_POP_WORD_REG":
"""
lodsb
movzx {R:ax}, al
pop word [{R:di}+{R:ax}*{N}]
""",

"STACK_POP_BYTE_MEMIMM":
"""
lods{SB}
pop dx
mov byte [{R:ax}], dl
""",

"STACK_POP_WORD_MEMIMM":
"""
lods{SB}
pop word [{R:ax}]
""",

"STACK_SUB":
"""
pop {R:ax}
sub {S} [{R:sp}], {R:ax}
""",

"MOV_EAX_EAX":
"""
mov eax, eax
""",

"STC":
"""
or dword [{R:di}+<FLAGS>], 0x1
""",

"CLC":
"""
and dword [{R:di}+<FLAGS>], 0xfffffffe
""",

"CLD":
"""
mov {S} [{R:di}+<DIRECTION_FLAG>], 0x0
and dword [{R:di}+<FLAGS>], 0xfffffbff
""",

"STD":
"""
mov {S} [{R:di}+<DIRECTION_FLAG>], 0x1
or dword [{R:di}+<FLAGS>], 0x400
""",

"STI":
"""
or dword [{R:di}+<FLAGS>], 0x200
""",

"SET_RETURN_POP_SIZE":
"""
lodsb
mov byte [{R:di}+<RETURN_POP_SIZE>], al
""",

"MOV_DX":
"""
lodsd
mov edx, eax
""",

"SUB_DX":
"""
lodsd
sub {R:dx}, {R:ax}
""",

"XOR_DX":
"""
lodsd
xor {R:dx}, {R:ax}
""",

"ADD_DX":
"""
lodsd
add {R:dx}, {R:ax}
""",

"XCHG_DX_MEMSP":
"""
pop {R:ax}
push {R:dx}
mov {R:dx}, {R:ax}
""",

"PUSHUNKNOWN":
"""
push {S} [{R:di}+<UNKNOWN>]
""",

"POPUNKNOWN":
"""
pop {S} [{R:di}+<UNKNOWN>]
""",

"POP2UNKNOWN":
"""
mov {R:ax}, {S} [{R:sp}+0x{N}]
mov {S} [{R:di}+<UNKNOWN>], {R:ax}
pop {R:ax}
add {R:sp}, 0x{N}
push {R:ax}
""",

"STACK_POP_DWORD_MEM":
"""
pop {R:ax}
pop {R:cx}
mov dword [{R:ax}], ecx
""",

"STACK_PUSH_MEM":
"""
pop {R:ax}
push {S} [{R:ax}]
""",

"STACK_MOV_DX_SP":
"""
mov {R:dx}, {R:sp}
""",

"PUSH_WORD_SP":
"""
push sp
""",

"POP_WORD_SP":
"""
pop sp
""",

"SET_CHECK_CX_REG":
"""
lodsb
mov byte [{R:di}+<CHECK_CX_REG>], al
""",

"PUSH_ENCODED":
"""
lods{SB}
add {R:ax}, {S} [{R:di}+<ENCODE>]
push {R:ax}
""",

"STACK_ADD_REALLOC":
"""
mov {R:ax}, {S} [{R:di}+<REALLOC>]
add {S} [{R:sp}], {R:ax}
""",

"ADD_DX_REALLOC":
"""
mov {R:ax}, {S} [{R:di}+<REALLOC>]
add {R:dx}, {R:ax}
""",

"STACK_XOR":
"""
pop {R:ax}
xor {S} [{R:sp}], {R:ax}
""",

"RESETKEY":
"""
mov ebx, 0x0
""",

"STACK_POPF":
"""
pop {S} [{R:di}+<FLAGS>]
""",

"HIGH_MAIN_HANDLER":
"""
lodsb
add {R:di}, <100_PTRS>
movzx eax, al
push {S} [{R:di}+{R:ax}*{N}]
sub {R:di}, <100_PTRS>
ret
"""
}

MATH_HANDLER = namedtuple("MATH_HANDLER", ["NAME", "VARS", "CODE"])

MATH_HANDLERS = [
MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["add", "sub", "xor", "and", "or"],
"SIZE": [1, 2, 4, 8]},
"""
pop {RS:ax:#SIZE#}
#OP# {S:#SIZE#} [{R:sp}], {R:ax:#SIZE#}
pushf{SB}
"""),

# Just a note: btc/btr/bts are not properly support dword and qword
MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["bt", "btc", "btr", "bts"],
"SIZE": [2, 4, 8]},
"""
pop {RS:ax:#SIZE#}
#OP# {S:#SIZE#} [{R:sp}], {R:ax:#SIZE#}
pushf{SB}
"""),

MATH_HANDLER(
"#OP#TWOF_#SIZE#",
{"OP": ["imul"],
"SIZE": [2, 4, 8]},
"""
pop {RS:ax:#SIZE#}
pop {RS:cx:#SIZE#}
#OP# {R:cx:#SIZE#}, {R:ax:#SIZE#}
push {RS:cx:#SIZE#}
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["adc", "sbb"],
"SIZE": [1, 2, 4, 8]},
"""
push {S} [{R:di}+<FLAGS>]
popf{SB}
pop {RS:ax:#SIZE#}
#OP# {S:#SIZE#} [{R:sp}], {R:ax:#SIZE#}
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["cmp", "test"],
"SIZE": [1, 2, 4, 8]},
"""
pop {RS:ax:#SIZE#}
pop {RS:cx:#SIZE#}
#OP# {R:cx:#SIZE#}, {R:ax:#SIZE#}
pushf{SB}
"""),

# In 32 bit...
MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["test"],
"SIZE": [1, 2, 4, 8]},
"""
pop {RS:ax:#SIZE#}
pop {RS:cx:#SIZE#}
#OP# {R:ax:#SIZE#}, {R:cx:#SIZE#}
pushf{SB}
"""),

MATH_HANDLER(
"#OP#_#SIZE1#_#SIZE2#",
{"OP": ["movzx", "movsx"],
"SIZE1": [2, 4, 8],
"SIZE2": [1, 2]},
"""
pop {RS:cx:#SIZE1#}
pop {RS:ax:#SIZE1#}
#OP# {R:cx:#SIZE1#}, {R:ax:#SIZE2#}
push {RS:cx:#SIZE1#}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["inc", "dec"],
"SIZE": [1, 2, 4, 8]},
"""
pop {RS:ax:#SIZE#}
#OP# {S:#SIZE#} [{R:sp}]
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["rcr", "rcl"],
"SIZE": [1, 2, 4, 8]},
"""
push {S} [{R:di}+<FLAGS>]
popf{SB}
pop cx
#OP# {S:#SIZE#} [{R:sp}], cl
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["rol", "ror", "sar", "shl", "shr"],
"SIZE": [1, 2, 4, 8]},
"""
pop cx
#OP# {S:#SIZE#} [{R:sp}], cl
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["mul", "imul"],
"SIZE": [2, 4, 8]},
"""
pop {RS:cx:#SIZE#}
pop {RS:ax:#SIZE#}
#OP# {R:cx:#SIZE#}
push {RS:dx:#SIZE#}
push {RS:ax:#SIZE#}
pushf{SB}
"""),

# In 32 bit..
MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["div"],
"SIZE": [2]},
"""
pop {RS:cx:#SIZE#}
pop {RS:ax:#SIZE#}
pop {RS:ax:#SIZE#}
#OP# {R:cx:#SIZE#}
push {RS:dx:#SIZE#}
push {RS:ax:#SIZE#}
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["div", "idiv"],
"SIZE": [2, 4, 8]},
"""
pop {RS:cx:#SIZE#}
pop {RS:ax:#SIZE#}
pop {RS:dx:#SIZE#}
#OP# {R:cx:#SIZE#}
push {RS:dx:#SIZE#}
push {RS:ax:#SIZE#}
pushf{SB}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["mul", "imul", "div", "idiv"],
"SIZE": [1]},
"""
pop cx
pop ax
#OP# cl
movzx cx, ah
push cx
movzx cx, al
push cx
pushf{SB}
"""),

MATH_HANDLER(
"#OP#_#SIZE#",
{"OP": ["bswap"],
"SIZE": [4, 8]},
"""
pop {RS:ax:#SIZE#}
#OP# {R:ax:#SIZE#}
push {RS:ax:#SIZE#}
"""),

MATH_HANDLER(
"#OP#F_#SIZE#",
{"OP": ["neg"],
"SIZE": [1, 2, 4, 8]},
"""
#OP# {S:#SIZE#} [{R:sp}]
pushf{SB}
"""),

MATH_HANDLER(
"#OP#_#SIZE#",
{"OP": ["not"],
"SIZE": [1, 2, 4, 8]},
"""
#OP# {S:#SIZE#} [{R:sp}]
"""),
]


def find_matches(mode, handlers, handler, variables):
    matches = []
    match_without_variables = None
    for handler_name, code in handlers.items():
        if handler_name.find("_OLD") != -1:
            handler_name = handler_name[:handler_name.find("_OLD")]
        local_variables = variables.copy()
        lines = [mode.translate(x.strip()) for x in code.splitlines() if x.strip()]
        if lines[0].startswith("lods"):
            if handler.read == None:
                continue
            if mode.translate("lods{SB:%d}" % handler.read.size) != lines[0]:
                continue
            if handler.read.size != 8 and not handler_name in ("JMP", "JMPIF") and not handler.read.encrypted:
                continue
            if handler_name in ("JMP", "JMPIF") and handler.read.encrypted:
                continue
            lines = lines[1:]
            if lines[0].startswith("nop"):
                if lines[1].startswith("cdqe"):
                    if not handler.read.extend_dword:
                        continue
                    lines = lines[2:]

        if len(handler.insts) != len(lines):
            continue
        match = True
        has_variables = False
        for i in xrange(len(lines)):
            if lines[i].find("<") == -1:
                if str(handler.insts[i]).strip() != lines[i]:
                    if not (lines[i] == "movzx eax, al" and str(handler.insts[i]).strip() == "movzx rax, al"):
                        match = False
                        break
            else:
                has_variables = True
                linevars = re.findall("<(\w+)>", lines[i])
                regexline = "(.+)".join([re.escape(x) for x in re.split("<(\w+)>", lines[i])[::2]])
                regexmatch = re.match(regexline, str(handler.insts[i]).strip())
                if regexmatch == None:
                    match = False
                    break
                try:
                    values = [int(x, 16) for x in regexmatch.groups()]
                except ValueError:
                    match = False
                    break
                for i in xrange(len(linevars)):
                    if linevars[i] == "ANY":
                        continue
                    if local_variables.has_key(linevars[i]):
                        if values[i] != local_variables[linevars[i]]:
                            match = False
                            break
                    else:
                        local_variables[linevars[i]] = values[i]
                if not match:
                    break
        if match:
            matches.append((handler_name, local_variables))
            if not has_variables:
                if match_without_variables:
                    raise Exception("Has multiple handlers with same info")
                match_without_variables = matches[-1]
    if match_without_variables:
        return [match_without_variables]
    return matches


def find_math_handler(mode, handler, variables):
    for handler_name, vars, code in MATH_HANDLERS:
        if len([x for x in code.splitlines() if x.strip()]) != len(handler.insts):
            continue
        for vars_values in itertools.product(*vars.values()):
            if mode.native_size() == 4 and 8 in vars_values:
                continue
            lines = []
            for line in code.splitlines():
                line = line.strip()
                if line:
                    line = line.replace("<FLAGS>", "0x%x" % variables["FLAGS"])
                    for i in xrange(len(vars)):
                        line = line.replace("#%s#" % vars.keys()[i], str(vars_values[i]))
                    lines.append(mode.translate(line))
            match = True
            for i in xrange(len(lines)):
                if lines[i].find("<") == -1:
                    if str(handler.insts[i]).strip() != lines[i]:
                        match = False
                        break
            if match:
                for i in xrange(len(vars)):
                    if vars_values[i] in [1, 2, 4, 8]:
                        handler_name = handler_name.replace("#%s#" % vars.keys()[i], mode.translate("{S:%d}" % vars_values[i]).upper())
                    else:
                        handler_name = handler_name.replace("#%s#" % vars.keys()[i], vars_values[i].upper())
                return handler_name