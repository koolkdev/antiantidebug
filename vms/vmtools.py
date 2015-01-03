import codevirtualizer.animals.vm as animals_vm
import codevirtualizer.cisc.vm as cisc_vm
import mappedfile

try:
    import progressbar
    PROGRESSBAR = True
except ImportError:
    PROGRESSBAR = False


class VMType(object):
    def __init__(self, jumper_cls, vm_func_cls):
        self.jumper_cls = jumper_cls
        self.vm_func_cls = vm_func_cls

    def get_vm(self, file, address):
        jumper = self.jumper_cls(file, address)
        return self.vm_func_cls(file, jumper)


    def get_vm_code(self, file, jumper):
        return self.vm_func_cls(file, jumper).get_code()

    def get_compiled_vm_code(self, file, jumper):
        return self.vm_func_cls(file, jumper).compile_code()

    def fix_vms(self, pe, code_section=0, vms_section=3, macro_size=0x12):
        code_section_start = pe.sections[code_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
        code_section_end = code_section_start + pe.sections[code_section].SizeOfRawData
        vms_section_start = pe.sections[vms_section].VirtualAddress + pe.OPTIONAL_HEADER.ImageBase
        vms_section_end = vms_section_start + pe.sections[vms_section].SizeOfRawData
        file = mappedfile.PEMappedFile(pe)
        self.decompile_all_vms(file, (code_section_start, code_section_end), (vms_section_start, vms_section_end), macro_size)

    def decompile_all_vms(self, file, code_section, vm_section, macro_size=0x12):
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
                    self.decompile_vm(file, address, macro_size)
            address += 1
            if PROGRESSBAR:
                prog.update(address - code_section[0])
        if PROGRESSBAR:
            prog.finish()

    def decompile_vm(self, file, address, macro_size=0x12):
        if file.read_byte(address) == 0xe9:
            jmp_address = file.read_dword(address + 1) + address + 5
        elif file.read_byte(address) == 0xe8:
            jmp_address = file.read_byte(address + 1) + address + 2
        else:
            assert False
        vm = self.get_vm(file, jmp_address)
        code = vm.get_code()
        print code
        last_line = code.splitlines()[-1]
        assert last_line.startswith("jmp ")
        end_address = int(last_line.split()[1].replace("?", ""), 16)
        code_address, compiled_code, relocations_info = vm.compile_code(address + macro_size, relocs=True)

        assert end_address - code_address > len(compiled_code)
        if end_address - code_address - macro_size != len(compiled_code) - 2:
            print "Warning: Code size is different %d" % (end_address - code_address - macro_size - (len(compiled_code) - 2))
        file.write(address, "\xeb" + chr(macro_size - 2))
        file.write(code_address, compiled_code)


VMS = {"CISC": VMType(cisc_vm.VMFunctionJumper, cisc_vm.VMFunction),
       "FISH": VMType(animals_vm.VMFunctionJumper, animals_vm.VMFunction)}
