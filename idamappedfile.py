# For usage with IDAPython
import mappedfile
import idc

class IDAMappedFile(mappedfile.MappedFile):
    def __init__(self):
        if idc.GetShortPrm(idc.INF_LFLAGS) & idc.LFLG_64BIT:
            mappedfile.MappedFile.__init__(self, 64)
        else:
            mappedfile.MappedFile.__init__(self, 32)

    def read(self, address, length):
        return "".join([chr(idc.Byte(address+i)) for i in xrange(length)])

    def write(self, address, data):
        for i in xrange(len(data)):
            idc.PatchByte(address + i, ord(data[i]))
