HANDLERS = {

"PUSH_BYTE_IMM":
"""
lodsb
movzx ax, al
push ax
""",

"PUSH_QWORD_IMM":
"""
lodsq
push rax
""",

"PUSH_DWORD_MEMDX":
"""
mov eax, dword [rdx]
push rax
""",

"PUSH_QWORD_MEMDX":
"""
push qword [rdx]
""",

"POP_BYTE_MEMGSDX":
"""
pop ax
mov byte gs:[rdx], al
""",

"POP_WORD_MEMGSDX":
"""
pop ax
mov word gs:[rdx], ax
""",

"POP_DWORD_MEMGSDX":
"""
pop rax
mov dword gs:[rdx], eax
""",

"POP_QWORD_MEMGSDX":
"""
pop rax
mov qword gs:[rdx], rax
""",

"PUSH_BYTE_MEMGSDX":
"""
movzx ax, byte gs:[rdx]
push ax
""",

"PUSH_WORD_MEMGSDX":
"""
mov ax, word gs:[rdx]
push ax
""",

"PUSH_DWORD_MEMGSDX":
"""
mov eax, dword gs:[rdx]
push rax
""",

"PUSH_QWORD_MEMGSDX":
"""
mov rax, qword gs:[rdx]
push rax
""",

"PUSH_DWORD_MEMIMM":
"""
lodsq
mov eax, dword [rax]
push rax
""",

"PUSH_QWORD_MEMIMM":
"""
lodsq
push qword [rax]
""",

"POP_DWORD_MEMDX":
"""
pop rax
mov dword [rdx], eax
""",

"POP_QWORD_MEMDX":
"""
pop qword [rdx]
""",

"POP_DWORD_REG":
"""
lodsb
movzx rax, al
pop rcx
mov dword [rdi+rax*8], ecx
""",

"POP_QWORD_REG":
"""
lodsb
movzx rax, al
pop qword [rdi+rax*8]
""",

"POP_DWORD_MEMIMM":
"""
lodsq
pop rcx
mov dword [rax], ecx
""",

"POP_QWORD_MEMIMM":
"""
lodsq
pop qword [rax]
""",

"STACK_ZERO_HIGH_DWORD":
"""
mov dword [rsp+0x4], 0x0
""",

"CLI":
"""
and dword [{R:di}+<FLAGS>], 0xfffffdff
""",

"PUSHENCODE":
"""
push qword [rdi+<ENCODE2>]
""",

"PUSH_QWORD_SP":
"""
push rsp
""",

"POP_QWORD_SP":
"""
pop rsp
""",

"PUSH_BYTE_SP":
"""
movzx ax, spl
push ax
""",

"POP_BYTE_SP":
"""
pop ax
mov spl, al
""",

"JMP":
"""
lodsd
nop
cdqe
add rsi, rax
mov ebx, 0x0
""",

"JMPIF":
"""
lodsd
nop
cdqe
cmp dword [rdi+<CHECK_RESULT>], 0x0
jz <ANY>
add rsi, rax
mov ebx, 0x0
mov eax, eax
""",

"ADDDXREG":
"""
lodsb
movzx eax, al
cmp eax, 0x7
jnz <ANY>
mov rax, rsp
add rdx, rax
""",

"CMC": # Bug
"""
mov eax, dword [rdi+<FLAGS>]
and eax, 0x1
test eax, eax
jz <ANY>
and dword [rdi+<FLAGS>], 0xfe
mov eax, eax
""",

"CHECK_FLAGS":
"""
lodsd
and al, 0x7f
push rbx
mov ebx, eax
mov dword [rdi+<CHECK_RESULT>], 0x1
mov dword [rdi+<CHECK_COUNTER>], 0x0
xor edx, edx
mov eax, ebx
and eax, 0x200
mov ecx, dword [rdi+<FLAGS>]
and ecx, 0x1
shr ecx, 0x0
test eax, eax
jz <ANY>
mov eax, ebx
and eax, 0x100
shr eax, 0x8
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x800
test eax, eax
jz <ANY>
mov ecx, dword [rdi+<FLAGS>]
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
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x2000000
test eax, eax
jz <ANY>
mov ecx, dword [rdi+<DIRECTION>]
mov eax, ebx
and eax, 0x1000000
shr eax, 0x18
xor eax, ecx
not eax
and eax, 0x1
or edx, eax
shl edx, 0x1
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x2000
test eax, eax
jz <ANY>
mov ecx, dword [rdi+<FLAGS>]
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
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x8000
test eax, eax
jz <ANY>
mov ecx, dword [rdi+<FLAGS>]
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
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x20000
test eax, eax
jz <ANY>
mov ecx, dword [rdi+<FLAGS>]
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
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x80000
test eax, eax
jz <ANY>
mov ecx, dword [rdi+<FLAGS>]
and ecx, 0x80
shr ecx, 0x7
mov eax, dword [rdi+<FLAGS>]
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
inc dword [rdi+<CHECK_COUNTER>]
mov eax, ebx
and eax, 0x200000
test eax, eax
jz <ANY>
mov rax, qword [rdi+<CHECK_CX_REG>]
mov eax, dword [rdi+rax*8]
and eax, 0xffff
cmp eax, 0x0
jnz <ANY>
mov edx, 0x1
mov eax, ebx
and eax, 0x800000
test eax, eax
jz <ANY>
mov rax, qword [rdi+<CHECK_CX_REG>]
mov eax, dword [rdi+rax*8]
cmp eax, 0x0
jnz <ANY>
mov edx, 0x1
mov ecx, dword [rdi+<CHECK_COUNTER>]
mov eax, 0x1
shl eax, cl
dec eax
and ebx, 0x10
cmp ebx, 0x0
jnz <ANY>
mov dword [rdi+<CHECK_RESULT>], edx
pop rbx
""",

"RETURN":
"""
mov ecx, dword [rdi+<RETURN_POP_SIZE>]
mov rdx, rdi
test ecx, ecx
jz <ANY>
mov rsi, rsp
add rsi, 0x80
mov rdi, rsi
add rdi, rcx
std
mov ecx, 0x11
rep movsq
add rsp, qword [rdx+<RETURN_POP_SIZE>]
mov qword [rdx+<RETURN_POP_SIZE>], 0x0
cmp qword [rdx+<DIRECTION>], 0x0
jz <ANY>
or dword [rsp+0x78], 0x400
mov qword [rdx+<DIRECTION>], 0x0
mov qword [rdx+<ANY>], 0x0
pop rax
pop rbx
pop rcx
pop rdx
pop rsi
pop rdi
pop rbp
pop r8
pop r9
pop r10
pop r11
pop r12
pop r13
pop r14
pop r15
popfq
ret
""",

"PUSH_DX_PLUS_UNKNOWN2":
"""
lodsq
add rax, qword [rdi+<ANY>]
push rax
""",

"CLC": # Bug
"""
and dword [{R:di}+<FLAGS>], 0xfe
""",

}