import instruction


class CompressedVMJumper(object):
    def __init__(self, file, address):
        reader = file.get_reader(address)
        call = reader.get_cond(lambda x: x.opcode == "call").operands[0].value
        jumper = CompressedVMJumperFunction.get_compressed_vm_jumper(file, call)

        if jumper is None:
            raise Exception("Not a jumper to compressed function")

        self.address = jumper.get_vm_address(address)

    def get_vm_address(self):
        return self.address


class CompressedVMJumperFunction(object):
    cache = {}

    def __init__(self, file, address):
        mode = file.get_arch()
        if file.mode == 64:
            # TODO: Add support for 64bit
            raise Exception("64bit compressed VMs not supported")

        reader = file.get_reader(address)
        # pushf
        reader.get_cond(lambda x: x.opcode == mode.translate("pushf{SB}"))
        # push esi
        reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg(mode.reg_native("si")))
        # call $+5
        list_address = reader.get_cond(lambda x: x.opcode == "call" and x.operands[0].value == x.address + 5).operands[0].value
        # pop esi
        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(mode.reg_native("si")))
        # TODO: Verify this
        # sub esi, 0x23
        list_address -= reader.get_cond(lambda x: x.opcode == "sub" and x.operands[1].is_immediate(list_address - address + 7 * mode.native_size())).operands[1].value
        # sub esi, 0x20
        list_size = reader.get_cond(lambda x: x.opcode == "sub" and x.operands[1].is_immediate() and (x.operands[1].value % (mode.native_size() * 2)) == 0).operands[1].value / (mode.native_size() * 2)
        list_address -= list_size * (mode.native_size() * 2)
        # push eax
        reader.get_cond(lambda x: x.opcode == "push" and x.operands[0].is_reg(mode.reg_native("pop")))
        # mov eax, esi
        reader.get_cond(lambda x: x.opcode == "mov" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_reg(mode.reg_native("si")))
        # sub eax, 0x1b000
        base_address = list_address - reader.get_cond(lambda x: x.opcode == "sub" and x.operands[0].is_reg(mode.reg_native("ax")) and x.operands[1].is_immediate()).operands[1].value
        # mov dword [esi+0x4], eax
        reader.get_cond(lambda x: str(x) == mode.translate("mov {S} [{R:si}+0x{N:0x1}], {R:ax}"))
        # pop eax
        reader.get_cond(lambda x: x.opcode == "pop" and x.operands[0].is_reg(mode.reg_native("ax")))
        # cmp dword [esi], 0x0
        reader.get_cond(lambda x: str(x) == mode.translate("cmp {S} [{R:si}], 0x0"))
        # jz ...
        find_vm_in_list_address = reader.get_cond(lambda x: x.opcode == "jz").operands[0].value

        if file.read_pointer(list_address) == 1:
            # TODO: Maybe run the unpacking code if can (if dynamic)?
            raise Exception("Can't uncompress VMs, dump it uncompressed first")
        assert file.read_pointer(list_address) == 0

        list_address += mode.native_size() * 7

        self.vms_mapping = {}
        for i in xrange(list_size):
            call_address = file.read_pointer(list_address + i * mode.native_size() * 2) + base_address
            vm_address = file.read_pointer(list_address + i * mode.native_size() * 2 + mode.native_size()) + base_address
            self.vms_mapping[call_address] = vm_address

    def get_vms_mapping(self):
        return self.vms_mapping

    def get_vm_address(self, address):
        # There will be an exception if this address is not valid
        return self.vms_mapping[address]

    @classmethod
    def get_compressed_vm_jumper(cls, file, address):
        if cls.cache.has_key((file, address)):
            return cls.cache[(file, address)]

        try:
            res = cls(file, address)
        except instruction.ReaderException:
            res = None

        cls.cache[(file, address)] = res
        return res
