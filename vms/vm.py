import instruction

class VMInfo(object):
    cache = {}
    def __init__(self, file, vm_address):
        pass

    @classmethod
    def get_vm_info(cls, file, address):
        if cls.cache.has_key((file, address)):
            if cls.cache[(file, address)] is None:
                raise Exception("Invalid VM")
            return cls.cache[(file, address)]

        try:
            res = cls(file, address)
        except:
            cls.cache[(file, address)] = None
            raise

        cls.cache[(file, address)] = res
        return res

class VMFunctionJumper(object):
    def __init__(self, file, address):
        pass

    def get_vm_address(self):
        pass

class VMFunction(object):
    def __init__(self, file, vm_info, jumper):
        pass

    def get_code(self):
        return ""

    def compile_code(self, address=None, relocs=False, code_proc=None):
        code = self.get_code()
        if address is None:
            address = self.code_address
        if code_proc is not None:
            code = "\n".join([code_proc(line) for line in code.splitlines()])
        compiled_code = instruction.Assembler(self.mode).assemble(code, address, relocs)
        if not compiled_code:
            raise Exception("Failed to compile code")
        if relocs:
            return address, compiled_code[0], compiled_code[1]
        return address, compiled_code
