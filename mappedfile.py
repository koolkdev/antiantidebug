import pefile
import instruction
import struct

class MappedFile(object):
    def __init__(self, mode=32):
        self.mode = mode

    def get_instruction(self, address):
        return instruction.Instruction(self.read(address, 32), address, self.mode)
        
    def get_reader(self, address):
        return instruction.InstructionReader(self, address)

    def read_format(self, address, fmt):
        return struct.unpack(fmt, self.read(address, struct.calcsize(fmt)))[0]
        
    def read_dword(self, address):
        return self.read_format(address, "<L")

    def read_pointer(self, address):
        if self.mode == 32:
            return self.read_format(address, "<L")
        else:
            return self.read_format(address, "<Q")

    def get_arch(self):
        return instruction.Arch(self.mode)
    
    def read_byte(self, address):
        return self.read_format(address, "<B")
        
    def read(self, address, length):
        raise NotImplementedError()

    def write(self, address, data):
        raise NotImplementedError()

class PEMappedFile(MappedFile):
    def __init__(self, pe):
        if pe.PE_TYPE == pefile.OPTIONAL_HEADER_MAGIC_PE_PLUS:
            MappedFile.__init__(self, 64)
        else:
            MappedFile.__init__(self, 32)
        self.pefile = pe

    def read(self, address, length):
        return self.pefile.get_data(address - self.pefile.OPTIONAL_HEADER.ImageBase, length)

    def write(self, address, data):
        return self.pefile.set_bytes_at_rva(address - self.pefile.OPTIONAL_HEADER.ImageBase, data)

class BytesMappedFile(MappedFile):
    def __init__(self, bytes, address=0, mode=32):
        MappedFile.__init__(self, mode)
        self.bytes = list(bytes)
        self.address = address

    def read(self, address, length):
        return "".join(self.bytes[address-self.address:address-self.address+length])

    def write(self, address, data):
        self.bytes[address-self.address:address-self.address+len(data)] = list(data)