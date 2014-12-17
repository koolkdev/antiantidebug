from libc.stdlib cimport malloc, free

cdef extern from "Python.h":
    object PyString_FromStringAndSize(char *s, Py_ssize_t len)
    object PyString_FromString(char *s)
    
cdef extern from "string.h":
    void *memcpy(void *s1, void *s2, int n)

cdef extern from "stdint.h":
    ctypedef signed char 	int8_t
    ctypedef unsigned char 	uint8_t
    ctypedef signed int 	int16_t
    ctypedef unsigned int 	uint16_t
    ctypedef signed long int 	int32_t
    ctypedef unsigned long int 	uint32_t
    ctypedef signed long long int 	int64_t
    ctypedef unsigned long long int 	uint64_t

cdef extern from "deobfuscator.h":    
    void * create_cleaner(void * reader, int mode, void * opaque)
    uint64_t clean_instruction(void * cleaner, uint64_t address, unsigned char * output, size_t * output_size)
    void destroy_cleaner(void * cleaner)
    void set_reg_unused(void * cleaner, int reg)
    void set_option(void * cleaner, char * option, uint64_t value)
    
cdef extern from "udis86.h":    
    cdef enum ud_type:
        UD_NONE
        UD_R_AL
        UD_R_CL
        UD_R_DL
        UD_R_BL
        UD_R_AH
        UD_R_CH
        UD_R_DH
        UD_R_BH
        UD_R_SPL
        UD_R_BPL
        UD_R_SIL
        UD_R_DIL
        UD_R_R8B
        UD_R_R9B
        UD_R_R10B
        UD_R_R11B
        UD_R_R12B
        UD_R_R13B
        UD_R_R14B
        UD_R_R15B
        UD_R_AX
        UD_R_CX
        UD_R_DX
        UD_R_BX
        UD_R_SP
        UD_R_BP
        UD_R_SI
        UD_R_DI
        UD_R_R8W
        UD_R_R9W
        UD_R_R10W
        UD_R_R11W
        UD_R_R12W
        UD_R_R13W
        UD_R_R14W
        UD_R_R15W
        UD_R_EAX
        UD_R_ECX
        UD_R_EDX
        UD_R_EBX
        UD_R_ESP
        UD_R_EBP
        UD_R_ESI
        UD_R_EDI
        UD_R_R8D
        UD_R_R9D
        UD_R_R10D
        UD_R_R11D
        UD_R_R12D
        UD_R_R13D
        UD_R_R14D
        UD_R_R15D
        UD_R_RAX
        UD_R_RCX
        UD_R_RDX
        UD_R_RBX
        UD_R_RSP
        UD_R_RBP
        UD_R_RSI
        UD_R_RDI
        UD_R_R8
        UD_R_R9
        UD_R_R10
        UD_R_R11
        UD_R_R12
        UD_R_R13
        UD_R_R14
        UD_R_R15
        UD_R_ES
        UD_R_CS
        UD_R_SS
        UD_R_DS
        UD_R_FS
        UD_R_GS
        UD_R_CR0
        UD_R_CR1
        UD_R_CR2
        UD_R_CR3
        UD_R_CR4
        UD_R_CR5
        UD_R_CR6
        UD_R_CR7
        UD_R_CR8
        UD_R_CR9
        UD_R_CR10
        UD_R_CR11
        UD_R_CR12
        UD_R_CR13
        UD_R_CR14
        UD_R_CR15
        UD_R_DR0
        UD_R_DR1
        UD_R_DR2
        UD_R_DR3
        UD_R_DR4
        UD_R_DR5
        UD_R_DR6
        UD_R_DR7
        UD_R_DR8
        UD_R_DR9
        UD_R_DR10
        UD_R_DR11
        UD_R_DR12
        UD_R_DR13
        UD_R_DR14
        UD_R_DR15
        UD_R_MM0
        UD_R_MM1
        UD_R_MM2
        UD_R_MM3
        UD_R_MM4
        UD_R_MM5
        UD_R_MM6
        UD_R_MM7
        UD_R_ST0
        UD_R_ST1
        UD_R_ST2
        UD_R_ST3
        UD_R_ST4
        UD_R_ST5
        UD_R_ST6
        UD_R_ST7
        UD_R_XMM0
        UD_R_XMM1
        UD_R_XMM2
        UD_R_XMM3
        UD_R_XMM4
        UD_R_XMM5
        UD_R_XMM6
        UD_R_XMM7
        UD_R_XMM8
        UD_R_XMM9
        UD_R_XMM10
        UD_R_XMM11
        UD_R_XMM12
        UD_R_XMM13
        UD_R_XMM14
        UD_R_XMM15
        UD_R_RIP
        UD_OP_REG
        UD_OP_MEM
        UD_OP_PTR
        UD_OP_IMM
        UD_OP_JIMM
        UD_OP_CONST
        
REGISTERS = {    
    "AL": UD_R_AL,
    "CL": UD_R_CL,
    "DL": UD_R_DL,
    "BL": UD_R_BL,
    "AH": UD_R_AH,
    "CH": UD_R_CH,
    "DH": UD_R_DH,
    "BH": UD_R_BH,
    "SPL": UD_R_SPL,
    "BPL": UD_R_BPL,
    "SIL": UD_R_SIL,
    "DIL": UD_R_DIL,
    "R8B": UD_R_R8B,
    "R9B": UD_R_R9B,
    "R10B": UD_R_R10B,
    "R11B": UD_R_R11B,
    "R12B": UD_R_R12B,
    "R13B": UD_R_R13B,
    "R14B": UD_R_R14B,
    "R15B": UD_R_R15B,
    "AX": UD_R_AX,
    "CX": UD_R_CX,
    "DX": UD_R_DX,
    "BX": UD_R_BX,
    "SP": UD_R_SP,
    "BP": UD_R_BP,
    "SI": UD_R_SI,
    "DI": UD_R_DI,
    "R8W": UD_R_R8W,
    "R9W": UD_R_R9W,
    "R10W": UD_R_R10W,
    "R11W": UD_R_R11W,
    "R12W": UD_R_R12W,
    "R13W": UD_R_R13W,
    "R14W": UD_R_R14W,
    "R15W": UD_R_R15W,
    "EAX": UD_R_EAX,
    "ECX": UD_R_ECX,
    "EDX": UD_R_EDX,
    "EBX": UD_R_EBX,
    "ESP": UD_R_ESP,
    "EBP": UD_R_EBP,
    "ESI": UD_R_ESI,
    "EDI": UD_R_EDI,
    "R8D": UD_R_R8D,
    "R9D": UD_R_R9D,
    "R10D": UD_R_R10D,
    "R11D": UD_R_R11D,
    "R12D": UD_R_R12D,
    "R13D": UD_R_R13D,
    "R14D": UD_R_R14D,
    "R15D": UD_R_R15D,
    "RAX": UD_R_RAX,
    "RCX": UD_R_RCX,
    "RDX": UD_R_RDX,
    "RBX": UD_R_RBX,
    "RSP": UD_R_RSP,
    "RBP": UD_R_RBP,
    "RSI": UD_R_RSI,
    "RDI": UD_R_RDI,
    "R8": UD_R_R8,
    "R9": UD_R_R9,
    "R10": UD_R_R10,
    "R11": UD_R_R11,
    "R12": UD_R_R12,
    "R13": UD_R_R13,
    "R14": UD_R_R14,
    "R15": UD_R_R15,
    "ES": UD_R_ES,
    "CS": UD_R_CS,
    "SS": UD_R_SS,
    "DS": UD_R_DS,
    "FS": UD_R_FS,
    "GS": UD_R_GS,
    "CR0": UD_R_CR0,
    "CR1": UD_R_CR1,
    "CR2": UD_R_CR2,
    "CR3": UD_R_CR3,
    "CR4": UD_R_CR4,
    "CR5": UD_R_CR5,
    "CR6": UD_R_CR6,
    "CR7": UD_R_CR7,
    "CR8": UD_R_CR8,
    "CR9": UD_R_CR9,
    "CR10": UD_R_CR10,
    "CR11": UD_R_CR11,
    "CR12": UD_R_CR12,
    "CR13": UD_R_CR13,
    "CR14": UD_R_CR14,
    "CR15": UD_R_CR15,
    "DR0": UD_R_DR0,
    "DR1": UD_R_DR1,
    "DR2": UD_R_DR2,
    "DR3": UD_R_DR3,
    "DR4": UD_R_DR4,
    "DR5": UD_R_DR5,
    "DR6": UD_R_DR6,
    "DR7": UD_R_DR7,
    "DR8": UD_R_DR8,
    "DR9": UD_R_DR9,
    "DR10": UD_R_DR10,
    "DR11": UD_R_DR11,
    "DR12": UD_R_DR12,
    "DR13": UD_R_DR13,
    "DR14": UD_R_DR14,
    "DR15": UD_R_DR15,
    "MM0": UD_R_MM0,
    "MM1": UD_R_MM1,
    "MM2": UD_R_MM2,
    "MM3": UD_R_MM3,
    "MM4": UD_R_MM4,
    "MM5": UD_R_MM5,
    "MM6": UD_R_MM6,
    "MM7": UD_R_MM7,
    "ST0": UD_R_ST0,
    "ST1": UD_R_ST1,
    "ST2": UD_R_ST2,
    "ST3": UD_R_ST3,
    "ST4": UD_R_ST4,
    "ST5": UD_R_ST5,
    "ST6": UD_R_ST6,
    "ST7": UD_R_ST7,
    "XMM0": UD_R_XMM0,
    "XMM1": UD_R_XMM1,
    "XMM2": UD_R_XMM2,
    "XMM3": UD_R_XMM3,
    "XMM4": UD_R_XMM4,
    "XMM5": UD_R_XMM5,
    "XMM6": UD_R_XMM6,
    "XMM7": UD_R_XMM7,
    "XMM8": UD_R_XMM8,
    "XMM9": UD_R_XMM9,
    "XMM10": UD_R_XMM10,
    "XMM11": UD_R_XMM11,
    "XMM12": UD_R_XMM12,
    "XMM13": UD_R_XMM13,
    "XMM14": UD_R_XMM14,
    "XMM15": UD_R_XMM15,
    "RIP": UD_R_RIP,
}

cdef class Cleaner:
    cdef void * cleaner
    cdef object mode
    cdef object read_func
    
    def __cinit__(self):
        self.cleaner = NULL
        
    def __init__(self, read, mode):
        self.read_func = read
        self.mode = mode
        self.cleaner = create_cleaner(<void *>self._read, mode, <void *>self)
        if self.cleaner is NULL:
            raise MemoryError()
    
    cpdef int _read(self, uint64_t address, unsigned char * buffer, size_t size):
        #print hex(address)
        try:            
            data = self.read_func(address, size)
        except:
            return 0
        if len(data) < size:
            size = len(data)
        memcpy(buffer, <void *><char *>data, size)
        return size
    
    def set_reg_unused(self, reg):
        if reg.upper() in REGISTERS:
            set_reg_unused(self.cleaner, REGISTERS[reg.upper()])
        else:
            raise ValueError("Invalid register %s" % reg)

    def set_option(self, option, value):
        set_option(self.cleaner, option, value)
        
    def get_clean_instruction(self, address):
        cdef unsigned char buffer[20]
        cdef size_t output_size = sizeof(buffer)
        next_address = clean_instruction(self.cleaner, address, buffer, &output_size)
        if next_address == 0:
            return None, ""
        return (next_address, PyString_FromStringAndSize(<char *>buffer, output_size))
        
    def __dealloc__(self):
        if self.cleaner is not NULL:
            destroy_cleaner(self.cleaner)
            