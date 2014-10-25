class uint32(object):
    def __init__(self, x):
        self.x = x % (1<<32)
        
    @staticmethod
    def __wrap__(f):
        def n(*args):
            new_args = [args[0].x]
            for arg in args[1:]:
                if type(arg) in (int, long):
                    new_args.append(arg % (1<<32))
                elif isinstance(arg, uint32):
                    new_args.append(arg.x)
                else:
                    new_args.append(arg)
            res = f(*new_args)
            if type(res) is long:
                return uint32(res)
            return res
        
        return n

    def __int__(self):
        return int(self.x)

    def __long__(self):
        return self.x
        

for func in dir(long):
    if func not in ["__class__", "__doc__", "__getattribute__", "__getnewargs__", "__new__", "__init__", "__setattr__", "__int__", "__long__"]:
        setattr(uint32, func, uint32.__wrap__(getattr(long, func)))
