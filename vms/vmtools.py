import mappedfile
import sys

try:
    import progressbar
    PROGRESSBAR = True
except ImportError:
    PROGRESSBAR = False


class VMType(object):
    def __init__(self, jumper_cls, vm_info_cls, vm_func_cls):
        self.jumper_cls = jumper_cls
        self.vm_info_cls = vm_info_cls
        self.vm_func_cls = vm_func_cls

    def get_vm(self, file, address):
        return self.get_vm_from_jumper(file, self.jumper_cls(file, address))

    def get_vm_from_jumper(self, file, jumper):
        return self.vm_func_cls(file, self.vm_info_cls.get_vm_info(file, jumper.get_vm_address()), jumper)

    def get_vm_code(self, file, jumper):
        return self.get_vm_from_jumper(file, jumper).get_code()

    def get_compiled_vm_code(self, file, jumper):
        return self.get_vm_from_jumper(file, jumper).compile_code()

    # TODO: Add option to remove vm section
    def fix_vms(self, pe, code_section=0, vms_section=3, big_macro=True):
        code_section_start = pe.sections[code_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
        code_section_end = code_section_start + pe.sections[code_section].SizeOfRawData
        vms_section_start = pe.sections[vms_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
        vms_section_end = vms_section_start + pe.sections[vms_section].SizeOfRawData
        file = mappedfile.PEMappedFile(pe)
        self.decompile_all_vms(file, (code_section_start, code_section_end), (vms_section_start, vms_section_end), big_macro)

    def decompile_all_vms(self, file, code_section, vm_section, big_macro):
        address = code_section[0]
        if PROGRESSBAR:
            class Address(progressbar.Widget):
                def update(self, pbar):
                    return '0x%x' % (pbar.currval + code_section[0])
            widgets = ['Searching: ', Address(), ' ', progressbar.Percentage(), ' ', progressbar.Bar(),
               ' ', progressbar.ETA()]
            prog = progressbar.ProgressBar(maxval=code_section[1] - code_section[0], widgets=widgets, fd=sys.stdout).start()
        while address < code_section[1]:
            if file.read_byte(address) in (0xe9, 0xeb): # Jump
                if file.read_byte(address) == 0xe9:
                    jmp_address = file.read_dword(address + 1) + address + 5
                else:
                    jmp_address = file.read_byte(address + 1) + address + 2
                if vm_section[0] <= jmp_address <= vm_section[1]:
                    try:
                        self.jumper_cls(file, jmp_address)
                    except:
                        address += 1
                        continue
                    # Now it must be a vm
                    print "Found VM: 0x%08x" % address
                    self.decompile_vm(file, address, big_macro)
            address += 1
            if PROGRESSBAR:
                prog.update(address - code_section[0])
        if PROGRESSBAR:
            prog.finish()

    def decompile_vm(self, file, address, big_macro=True):
        if big_macro:
            macro_size = 0x12
        else:
            macro_size = 0x6
        if file.read_byte(address) == 0xe9:
            jmp_address = file.read_dword(address + 1) + address + 5
        elif file.read_byte(address) == 0xe8:
            jmp_address = file.read_byte(address + 1) + address + 2
        else:
            assert False
        vm = self.get_vm(file, jmp_address)
        code = vm.get_code()
        print code
        # Try to find the real end.
        # we can't find the real end if our function ends with ret or jump to anything else
        # and there isn't any jump during it
        end_address = 0
        for line in code.splitlines():
            line_parts = line.split(" ")
            if len(line_parts) == 2 and line_parts[0] in ("jmp", "ja", "jae", "jb", "jbe", "jz", "jg", "jge", "jl", "jle", "jnz", "jno", "jnp", "jns", "jo", "jp" ,"js") and \
                    (line_parts[1].startswith("?") or line_parts[1].startswith("0x")):
                j_address = int(line_parts[1].replace("?", ""), 16)
                if j_address > address and (end_address == 0 or j_address < end_address):
                    end_address = j_address

        # Last line must be jmp or ret
        assert line.startswith("jmp ") or line.startswith("ret")

        code_proc = None
        if end_address != 0:
            inst = file.get_instruction(end_address)
            # In 32 bit
            if file.mode == 32:
                while inst.opcode == "mov" and str(inst.operands[0]) == str(inst.operands[1]):
                    inst = file.get_instruction(inst.next)

            # In 64 bit
            if file.mode == 64:
                inst = file.get_instruction(inst.address)
                inst2 = file.get_instruction(inst.next)
                while inst.opcode == "push" and inst2.opcode == "pop" and str(inst.operands[0]) == str(inst2.operands[0]):
                    inst = file.get_instruction(inst2.next)
                    inst2 = file.get_instruction(inst.next)

            real_end_address = inst.address

            if real_end_address != end_address:
                to_replace = "0x%x" % end_address
                replace_with = "0x%x" % real_end_address
                code_proc = lambda x: x.replace(to_replace, replace_with)
                assert macro_size == real_end_address - end_address
                end_address = real_end_address

        code_address, compiled_code, relocations_info = vm.compile_code(address + macro_size, relocs=True, code_proc=code_proc)
        if end_address != 0:
            assert end_address - code_address > len(compiled_code)
            if end_address - code_address - macro_size != len(compiled_code) - 2:
                print "Warning: Code size is different %d" % (end_address - code_address - macro_size - (len(compiled_code) - 2))

        file.write(address, "\xeb" + chr(macro_size - 2))
        file.write(code_address, compiled_code)

VMS = {}
