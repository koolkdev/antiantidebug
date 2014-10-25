import struct

def hide_IsDebuggerPresent(debugger):
    debugger.process.write_char(debugger.process.get_peb_address()+2, 0)

def hide_ZwSetInformationThread(debugger):
    api_ptr = debugger.process.resolve_label("ntdll!ZwSetInformationThread")
    if debugger.process.read_char(api_ptr) != 0xB8:
        # It is already patched or something
        print "Warning, didn't patch ZwSetInformationThread"
        return
    code_page = debugger.process.malloc(0x1000)
    patch = "837C240811".decode("hex") # cmp dword [esp+8], 11
    patch += "7503".decode("hex") # jnz $+5
    patch += "C21000".decode("hex") # retn 10
    patch += debugger.process.read(api_ptr, 5) # mov eax, ...
    patch += "E9".decode("hex") + struct.pack("<L", (api_ptr - code_page - len(patch)) % (1<<32))

    api_patch = "E9".decode("hex") + struct.pack("<L", (code_page - api_ptr - 5) % (1<<32))
    
    debugger.process.write(code_page, patch)
    debugger.process.write(api_ptr, api_patch)

def hide_CheckRemoteDebuggerPresent(debugger):
    debugger.process.write(debugger.process.resolve_label("kernel32!CheckRemoteDebuggerPresent"), "B800000000C20800".decode("hex")) # mov eax,0; retn 8
