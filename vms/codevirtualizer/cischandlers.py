HANDLERS = {

"ADDREALLOC":
"""
mov eax, dword [edi+{REALLOCOFFSET}]
add dword [esp], eax
""",

"ADDEDXREALLOC":
"""
mov eax, dword [edi+{REALLOCOFFSET}]
add edx, eax
""",

"POPUNKNOWN":
"""
pop dword [edi+{UKNOWNOFFSET}]
""",

"PUSHUNKNOWN":
"""
push dword [edi+{UKNOWNOFFSET}]
""",

"POP2UNKNOWN":
"""
mov eax, dword [esp+0x4]
mov dword [edi+{UKNOWNOFFSET}], eax
pop eax
add esp, 0x4
push eax
""",

"SETUNKNOWN":
"""
READ 1 1
mov byte [edi+{UNKNOWNOFFSET}], al
""",

"SETRETN":
"""
READ 1 1
mov byte [edi+{RETNOFFSET}], al
""",

"PUSHENCODE":
"""
push dword [edi+{ENCODEOFFSET}]
""",

"PUSHWITHENCODE":
"""
READ 4 1
add eax, dword [edi+{ENCODEOFFSET}]
push eax
""",

"JMP":
"""
READ 4 0
add esi, eax
mov ebx, 0x0
""",

"JMPIF":
"""
READ 4 0
cmp dword [edi+{IFJUMPOFFSET}], 0x0
jz {ANY}
add esi, eax
mov ebx, 0x0
mov eax, eax
""",

"JMPREGOFFSET":
"""
READ 1 1
add edi, {VMSTRUCTSIZE}
movzx eax, al
push dword [edi+eax*4]
sub edi, {VMSTRUCTSIZE}
ret
""",

"JMPREG":
"""
READ 1 1
movzx eax, al
jmp dword [edi+eax*4]
popad
ret
""",

"MOVEDX":
"""
READ 4 1
mov edx, eax
""",

"ADDEDXREG":
"""
READ 1 1
movzx eax, al
cmp eax, 0x7
jz {ANY}
mov eax, dword [edi+eax*4]
add edx, eax
""",

"ADDEDX":
"""
READ 4 1
add edx, eax
""",

"SUBEDX":
"""
READ 4 1
sub edx, eax
""",

"XOREDX":
"""
READ 4 1
xor edx, eax
""",

"MOVEDXESP":
"""
mov edx, esp
""",

"POPDWORDV":
"""
READ 4 1
pop dword [eax]
""",

"POPWORDV":
"""
READ 4 1
pop word [eax]
""",

"POPBYTEV":
"""
READ 4 1
pop dx
mov byte [eax], dl
""",

"POPBYTEREG2ND":
"""
READ 1 1
movzx eax, al
pop dx
mov byte [edi+eax*4+0x1], dl
""",

"POPDWORDREG":
"""
READ 1 1
movzx eax, al
pop dword [edi+eax*4]
""",

"POPBYTEREG":
"""
READ 1 1
movzx eax, al
pop dx
mov byte [edi+eax*4], dl
""",

"POPWORDREG":
"""
READ 1 1
movzx eax, al
pop word [edi+eax*4]
""",

"POPDWORDESPVV":
"""
pop eax
pop ecx
mov dword [eax], ecx
""",

"PUSHDWORDESPVV":
"""
pop eax
push dword [eax]
""",

"POPDWORDESP":
"""
pop esp
""",

"POPWORDESP":
"""
pop sp
""",

"POPEDX":
"""
pop edx
""",

"POPDWORDEDXV":
"""
pop dword [edx]
""",

"POPWORDEDXV":
"""
pop word [edx]
""",

"POPBYTEEDXV":
"""
pop ax
mov byte [edx], al
""",

"POPDWORDFSEDXV":
"""
pop dword fs:[edx]
""",

"POPWORDFSEDXV":
"""
pop ax
mov word fs:[edx], ax
""",

"popfd":
"""
pop dword [edi+0x1c]
""",

"PUSHDWORD":
"""
READ 4 1
push eax
""",

"PUSHWORD":
"""
READ 2 1
movzx eax, ax
push ax
""",

"PUSHBYTE":
"""
READ 1 1
movzx eax, al
push ax
""",

"PUSHDWORDV":
"""
READ 4 1
push dword [eax]
""",

"PUSHWORDV":
"""
READ 4 1
push word [eax]
""",

"PUSHBYTEV":
"""
READ 4 1
movzx ax, byte [eax]
push ax
""",

"PUSHREGREF":
"""
READ 1 1
movzx eax, al
lea eax, [edi+eax*4]
push eax
""",

"PUSHDWORDREG":
"""
READ 1 1
movzx eax, al
push dword [edi+eax*4]
""",

"PUSHWORDREGV":
"""
READ 1 1
movzx eax, al
mov eax, dword [edi+eax*4]
push word [eax]
""",

"PUSHBYTEREGV":
"""
READ 1 1
movzx eax, al
mov eax, dword [edi+eax*4]
movzx ax, byte [eax]
push ax
""",

"PUSHDWORDESP":
"""
push esp
""",

"PUSHEDX":
"""
push edx
""",

"PUSHDWORDEDXV":
"""
push dword [edx]
""",

"PUSHWORDEDXV":
"""
push word [edx]
""",

"PUSHBYTEEDXV":
"""
movzx ax, byte [edx]
push ax
""",

"POPBYTEFSEDXV":
"""
pop ax
mov byte fs:[edx], al
""",

"PUSHDWORDFSEDXV":
"""
push dword fs:[edx]
""",

"PUSHWORDFSEDXV":
"""
mov ax, word fs:[edx]
push ax
""",

"PUSHBYTEFSEDXV":
"""
movzx ax, byte fs:[edx]
push ax
""",

"PUSHWORDSP":
"""
push sp
""",

"NOP":
"""
mov eax, eax
""",

"MOVEAX53947":
"""
mov eax, 0x53947
""",

"STI":
"""
or dword [edi+0x1c], 0x200
""",

"STC":
"""
or dword [edi+0x1c], 0x1
""",

"CLC":
"""
and dword [edi+0x1c], 0xfffffffe
""",

"CLCBUG":
"""
and dword [edi+0x1c], 0xfe
""",

"CMC":
"""
mov eax, dword [edi+0x1c]
and eax, 0x1
or eax, eax
jz {ANY}
and dword [edi+0x1c], 0xfffffffe
mov ebx, ebx
""",

"CMCBUG":
"""
mov eax, dword [edi+0x1c]
and eax, 0x1
or eax, eax
jz {ANY}
and dword [edi+0x1c], 0xfe
mov ebx, ebx
""",

"STD":
"""
mov dword [edi+{DIRECTIONOFFSET}], 0x0
and dword [edi+0x1c], 0xfffffbff
""",

"CLD":
"""
mov dword [edi+{DIRECTIONOFFSET}], 0x1
or dword [edi+0x1c], 0x400
""",

#"STD": Old handlers
#"""
#and dword [edi+0x1c], 0xfffffbff
#""",
#
#"CLD":
#"""
#or dword [edi+0x1c], 0x400
#""",

"XCHGEDX":
"""
pop eax
push edx
mov edx, eax
""",

"SHLDWORD":
"""
pop ecx
shl dword [esp], cl
""",

"RESETKEY":
"""
mov ebx, 0x0
""",

"RETURN":
"""
mov ecx, dword [edi+{RETNOFFSET}]
mov edx, edi
or ecx, ecx
jz {ANY}
mov esi, esp
add esi, 0x24
mov edi, esi
add edi, ecx
std
mov ecx, 0xa
rep movsd
add esp, dword [edx+{RETNOFFSET}]
mov dword [edx+{RETNOFFSET}], 0x0
cmp dword [edx+{DIRECTIONOFFSET}], 0x0
jz {ANY}
or dword [esp+0x20], 0x400
mov dword [edx+{DIRECTIONOFFSET}], 0x0
mov dword [edx+{ANY}], 0x0
popad
popfd
ret
""",

##"RETURN": old handler
##"""
##mov ecx, [edi+{RETNOFFSET}]
##mov edx, edi
##or ecx, ecx
##jz {ANY}
##mov esi, esp
##add esi, 0x24
##mov edi, esi
##add edi, ecx
##std
##mov ecx, 0xa
##rep
##add esp, [edx+{RETNOFFSET}]
##mov dword [edx+{RETNOFFSET}], 0x0
##mov dword [edx+{ANY}], 0x0
##popad
##popfd
##ret
##"""
}

import re

def find_matches(handler, variables):
    matches = []
    match_without_variables = None
    for handler_name, code in HANDLERS.items():
        local_variables = variables.copy()
        lines = [x.strip() for x in code.splitlines() if x.strip()]
        if lines[0].split()[0] == "READ":
            if handler.read == None:
                continue
            if handler.read.size != int(lines[0].split()[1]):
                continue
            if handler.read.encrypted != bool(int(lines[0].split()[2])):
                continue
            lines = lines[1:]
        if len(handler.insts) != len(lines):
            continue
        match = True
        has_variables = False
        for i in xrange(len(lines)):
            if lines[i].find("{") == -1:
                if str(handler.insts[i]).strip() != lines[i]:
                    match = False
                    break
            else:
                has_variables = True
                linevars = re.findall("\{(\w+)\}", lines[i])
                regexline = "(.+)".join([re.escape(x) for x in re.split("\{(\w+)\}", lines[i])[::2]])
                regexmatch = re.match(regexline, str(handler.insts[i]).strip())
                if regexmatch == None:
                    match = False
                    break
                for i in xrange(len(linevars)):
                    if linevars[i] == "ANY":
                        continue
                    if local_variables.has_key(linevars[i]):
                        if regexmatch.groups()[i] != local_variables[linevars[i]]:
                            match = False
                            break
                    else:
                        local_variables[linevars[i]] = regexmatch.groups()[i]
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

MATH_HANDLERS = [
(["add", "sub", "and", "xor", "or", "bt", "btr", "bts", "btc"], 1, "",
"""
pop {STACKREG:1:EAX}
{OPERATIONSIZE:1} [esp], {REG:1:EAX}
"""),

(["dec", "inc"], 1, "",
"""
pop {STACKREG:1:EAX}
{OPERATIONSIZE:1} [esp]
"""),

(["neg", "not"], 1, "",
"""
{OPERATIONSIZE:1} [esp]
"""),

(["bswap"], 1, "",
"""
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:EAX}
push {STACKREG:1:EAX}
"""),

(["movzx", "movsx"], 2, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:ECX}, {REG:2:EAX}
push {STACKREG:1:ECX}
"""),

(["imul", "mul"], 1, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:ECX}
push {STACKREG:1:EDX}
push {STACKREG:1:EAX}
"""),

(["div", "idiv"], 1, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
pop {STACKREG:1:EDX}
{OPERATION} {REG:1:ECX}
push {STACKREG:1:EDX}
push {STACKREG:1:EAX}
"""),

(["div", "idiv"], 1, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:ECX}
push {STACKREG:1:EDX}
push {STACKREG:1:EAX}
"""),

(["imul"], 1, "TWO",
"""
pop {STACKREG:1:EAX}
pop {STACKREG:1:ECX}
{OPERATION} {REG:1:ECX}, {REG:1:EAX}
push {STACKREG:1:ECX}
"""),

# Kinda hack
(["div", "idiv", "mul", "imul"], 1, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:ECX}
movzx cx, ah
push {STACKREG:1:ECX}
movzx cx, al
push {STACKREG:1:ECX}
"""),

(["cmp", "test"], 1, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:EAX}, {REG:1:ECX}
"""),

(["cmp", "test"], 1, "",
"""
pop {STACKREG:1:ECX}
pop {STACKREG:1:EAX}
{OPERATION} {REG:1:ECX}, {REG:1:EAX}
"""),

(["cmp", "test"], 1, "",
"""
pop {STACKREG:1:EAX}
pop {STACKREG:1:ECX}
{OPERATION} {REG:1:EAX}, {REG:1:ECX}
"""),

(["cmp", "test"], 1, "",
"""
pop {STACKREG:1:EAX}
pop {STACKREG:1:ECX}
{OPERATION} {REG:1:ECX}, {REG:1:EAX}
"""),

(["shl", "shr", "sar", "rol", "ror"], 1, "",
"""
pop cx
{OPERATIONSIZE:1} [esp], cl
"""),

(["rcr", "rcl"], 1, "",
"""
push dword [edi+0x1c]
popfd
pop cx
{OPERATIONSIZE:1} [esp], cl
"""),

(["sbb", "adc"], 1, "",
"""
push dword [edi+0x1c]
popfd
pop {STACKREG:1:EAX}
{OPERATIONSIZE:1} [esp], {REG:1:EAX}
"""),

]

SIZES = {"dword": 4, "word": 2, "byte":1}
REGS = {"EAX": {"al":1, "ax":2, "eax":4}, "ECX": {"cl":1, "cx":2, "ecx":4}, "EDX": {"dl":1, "dx":2, "edx":4}}
def find_math_operation(handler):
    if str(handler.insts[-1]) == "pushfd":
        push_flags = True
        insts = handler.insts[:-1]
    else:
        push_flags = False
        insts = handler.insts
    for opcodes, sizes, ext, code in MATH_HANDLERS:
        lines = [x.strip() for x in code.splitlines() if x.strip()]
        if len(insts) != len(lines):
            continue
        left_sizes = [[1,2,4] for i in xrange(sizes)]
        operation = None
        match = True
        for i in xrange(len(lines)):
            if lines[i].find("{") == -1:
                if str(insts[i]).strip() != lines[i]:
                    match = False
                    break
            else:
                has_variables = True
                linevars = re.findall("\{([\w:]+)\}", lines[i])
                regexline = "(.+)".join([re.escape(x) for x in re.split("\{([\w:]+)\}", lines[i])[::2]])
                regexmatch = re.match(regexline, str(insts[i]).strip())
                if regexmatch == None:
                    match = False
                    break
                for i in xrange(len(linevars)):
                    linevar = linevars[i].split(":")
                    if linevar[0] in ("OPERATION", "OPERATIONSIZE"):
                        if linevar[0] == "OPERATIONSIZE":
                            res = regexmatch.groups()[i].split(" ")
                            if len(res) != 2:
                                match = False
                                break
                            operation = res[0]
                            size = res[1]
                            to_size = int(linevar[1])
                            if not SIZES.has_key(size):
                                match = False
                                break
                            if not left_sizes[to_size-1].count(SIZES[size]):
                                match = False
                                break
                            left_sizes[to_size-1] = [SIZES[size]]
                        else:
                            operation = regexmatch.groups()[i]
                        if operation not in opcodes:
                            match = False
                            break
                    elif linevar[0] in ("REG", "STACKREG"):
                        to_size = int(linevar[1])
                        linereg = linevar[2]
                        reg = regexmatch.groups()[i]
                        if not REGS[linereg].has_key(reg):
                            match = False
                            break
                        if linevar[0] == "STACKREG":
                            if REGS[linereg][reg] == 4:
                                cansizes = [4]
                            else:
                                cansizes = [2, 1]
                        else:
                            cansizes = [REGS[linereg][reg]]
                        new_sizes = []
                        for size in cansizes:
                            if left_sizes[to_size-1].count(size) > 0:
                                new_sizes.append(size)
                        if not new_sizes:
                            match = False
                            break
                        left_sizes[to_size-1] = new_sizes
                    else:
                        assert False
                if not match:
                    break
        if match:
            for size in left_sizes:
                assert len(size) == 1
            assert operation != None
            func = operation.upper() + ext
            func += "_".join([{1:"BYTE", 2:"WORD", 4:"DWORD"}[size[0]] for size in left_sizes])
            if push_flags:
                func += "F"
            return func
    return None
