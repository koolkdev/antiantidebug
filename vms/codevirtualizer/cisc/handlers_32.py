HANDLERS = {

"PUSH_BYTE_IMM":
"""
lodsb
movzx eax, al
push ax
""",

"PUSH_DWORD_MEMDX":
"""
push dword [edx]
""",

"POP_BYTE_MEMFSDX":
"""
pop ax
mov byte fs:[edx], al
""",

"POP_WORD_MEMFSDX":
"""
pop ax
mov word fs:[edx], ax
""",

"POP_DWORD_MEMFSDX":
"""
pop dword fs:[edx]
""",

"PUSH_BYTE_MEMFSDX":
"""
movzx ax, byte fs:[edx]
push ax
""",

"PUSH_WORD_MEMFSDX":
"""
mov ax, word fs:[edx]
push ax
""",

"PUSH_DWORD_MEMFSDX":
"""
push dword fs:[edx]
""",

"PUSH_DWORD_MEMIMM":
"""
lodsd
push dword [eax]
""",

"POP_DWORD_MEMDX":
"""
pop dword [edx]
""",

"POP_DWORD_REG":
"""
lodsb
movzx eax, al
pop dword [edi+eax*4]
""",

"POP_DWORD_MEMIMM":
"""
lodsd
pop dword [eax]
""",

"CLI":
"""
mov eax, 0x53947
""",

"PUSHENCODE":
"""
push dword [edi+<ENCODE>]
""",

"PUSH_DWORD_SP":
"""
push esp
""",

"POP_DWORD_SP":
"""
pop esp
""",

"JMP":
"""
add esi, eax
mov ebx, 0x0
""",

"JMPIF":
"""
lodsd
cmp dword [edi+<JMPIF>], 0x0
jz <ANY>
add esi, eax
mov ebx, 0x0
mov eax, eax
""",

"ADDDXREG":
"""
lodsb
movzx eax, al
cmp eax, 0x7
jz <ANY>
mov eax, dword [edi+eax*4]
add edx, eax
""",

"CMC":
"""
mov eax, dword [edi+<FLAGS>]
and eax, 0x1
or eax, eax
jz <ANY>
and dword [edi+<FLAGS>], 0xfffffffe
mov ebx, ebx
""",

"CHECK_FLAGS":
"""
lodsd
and al, 0x7f
push ebx
mov ebx, eax
mov dword [edi+<CHECK_RESULT>], 0x1
mov dword [edi+<CHECK_COUNTER>], 0x0
xor edx, edx
mov eax, ebx
and eax, 0x200
mov ecx, dword [edi+<FLAGS>]
and ecx, 0x1
shr ecx, 0x0
or eax, eax
jz <ANY>
mov eax, ebx
and eax, 0x100
shr eax, 0x8
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x800
or eax, eax
jz <ANY>
mov ecx, dword [edi+<FLAGS>]
and ecx, 0x40
shr ecx, 0x6
mov eax, ebx
and eax, 0x400
shr eax, 0xa
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x2000000
or eax, eax
jz <ANY>
mov ecx, dword [edi+<DIRECTION>]
mov eax, ebx
and eax, 0x1000000
shr eax, 0x18
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x2000
or eax, eax
jz <ANY>
mov ecx, dword [edi+<FLAGS>]
and ecx, 0x80
shr ecx, 0x7
mov eax, ebx
and eax, 0x1000
shr eax, 0xc
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x8000
or eax, eax
jz <ANY>
mov ecx, dword [edi+<FLAGS>]
and ecx, 0x800
shr ecx, 0xb
mov eax, ebx
and eax, 0x4000
shr eax, 0xe
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x20000
or eax, eax
jz <ANY>
mov ecx, dword [edi+<FLAGS>]
and ecx, 0x4
shr ecx, 0x2
mov eax, ebx
and eax, 0x10000
shr eax, 0x10
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x80000
or eax, eax
jz <ANY>
mov ecx, dword [edi+<FLAGS>]
and ecx, 0x80
shr ecx, 0x7
mov eax, dword [edi+<FLAGS>]
and eax, 0x800
shr eax, 0xb
xor ecx, eax
mov eax, ebx
and eax, 0x40000
shr eax, 0x12
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [edi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x200000
or eax, eax
jz <ANY>
mov eax, dword [edi+<CHECK_CX_REG>]
mov eax, dword [edi+eax*4]
and eax, 0xffff
or eax, eax
jnz <ANY>
mov edx, 0x1
mov eax, ebx
and eax, 0x800000
or eax, eax
jz <ANY>
mov eax, dword [edi+<CHECK_CX_REG>]
mov eax, dword [edi+eax*4]
or eax, eax
jnz <ANY>
mov edx, 0x1
mov ecx, dword [edi+<CHECK_COUNTER>]
mov eax, 0x1
shl eax, cl
dec eax
and ebx, 0x10
or ebx, ebx
jnz <ANY>
mov dword [edi+<CHECK_RESULT>], edx
pop ebx
""",

"RETURN":
"""
mov ecx, dword [edi+<RETURN_POP_SIZE>]
mov edx, edi
or ecx, ecx
jz <ANY>
mov esi, esp
add esi, 0x24
mov edi, esi
add edi, ecx
std
mov ecx, 0xa
rep movsd
add esp, dword [edx+<RETURN_POP_SIZE>]
mov dword [edx+<RETURN_POP_SIZE>], 0x0
cmp dword [edx+<DIRECTION>], 0x0
jz <ANY>
or dword [esp+0x20], 0x400
mov dword [edx+<DIRECTION>], 0x0
mov dword [edx+<ANY>], 0x0
popad
popfd
ret
""",

}