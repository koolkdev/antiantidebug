from winappdbg import *
import threading
import time
import pefile
import instruction

class AsyncOperation(object):
    def __init__(self):
        self.request_event = threading.Event()
        self.response_event = threading.Event()

    def request(self, obj = None):
        self.request_obj = obj
        self.request_event.set()
        self.response_event.wait(0xffffffff)
        self.response_event.clear()
        return self.response_obj
    
    def wait(self):
        self.request_event.wait(0xffffffff)
        self.request_event.clear()
        return self.request_obj
        
    def response(self, obj = None):
        self.response_obj = obj
        self.response_event.set()

class MyEventHandler(EventHandler):
    def __init__(self, debugger):
        self.debugger = debugger
        EventHandler.__init__(self)
        
    def create_process(self, event):
        self.debugger.create_process_event = event
        event.debug.stalk_at(event.get_pid(), event.get_start_address())
   
    # Create thread events go here.
    #def create_thread( self, event ):

    def single_step(self, event):
        # Show the user where we're running.
        #thread = event.get_thread()
        #pc     = thread.get_pc()
        #code   = thread.disassemble( pc, 0x10 ) [0]
        #bits   = event.get_process().get_bits()
        #print "%s: %s" % ( HexDump.address(code[0], bits), code[2].lower() )
        self.debugger.breakpoint_tunnel.request(event)
        
    breakpoint = single_step

class Debugger(object):
    def __init__(self):
        self.hwbps = []
        self.hooks = {}
    
    def start(self, filepath):
        self.filepath = filepath
        self.breakpoint_tunnel = AsyncOperation()
        t = threading.Thread(target=self.thread_task, args=())
        # TODO: make it stoppable
        t.setDaemon(True)
        t.start()
        res = self.breakpoint_tunnel.wait()
        while self.debug.lastEvent.get_thread().get_pc() != self.create_process_event.get_start_address():
            res = self.go()
        return res

    def thread_task(self):
        self.debug = Debug(MyEventHandler(self))
        self.process = self.debug.execl(self.filepath)
        self.mode = self.process.get_bits()
        try:
            self.debug.loop()
        finally:
            self.debug.stop()

    def go(self, address = None, use_hardware = False):
        if address:
            if use_hardware:
                self.debug.define_hardware_breakpoint(
                        self.thread.get_tid(), address,
                        self.debug.BP_BREAK_ON_EXECUTION,
                        self.debug.BP_WATCH_BYTE,
                        True
                        )
                self.debug.enable_one_shot_hardware_breakpoint(self.thread.get_tid(), address)
                self.hwbps.append(address)
            else:
                self.debug.stalk_at(self.process.get_pid(), address)
        self.breakpoint_tunnel.response()
        event = self.breakpoint_tunnel.wait()

        try:
            if event.breakpoint.get_address() in self.hwbps:
                event.debug.erase_hardware_breakpoint(event.get_tid(), event.breakpoint.get_address())
                self.hwbps.remove(event.breakpoint.get_address())
        except:
            pass
        return self.get_instruction()

    def get_instruction(self, address = None):
        if address == None:
            address = self.thread.get_pc()
        return instruction.Instruction(self.process.read(address, 32), address, self.mode, False)

    def step(self):
        # The direct api is slow
        self.debug._BreakpointContainer__start_tracing(self.debug.lastEvent.get_thread())
        res = self.go()
        self.debug._BreakpointContainer__stop_tracing(self.debug.lastEvent.get_thread())
        return res
    
    def stepover(self):
        #TODO: handle jmps/rets better
        inst = self.get_instruction()
        if inst.opcode.startswith("j") or inst.opcode.startswith("ret"):
            return self.step()
        return self.go(self.thread.get_pc() + self.get_instruction().size)

    def pc(self):
        inst = self.step()
        while inst.opcode != "call":
            inst = self.step()
        return inst

    #def hook(self, library, function, pre = None, post = None):
    #    self.hooks[library + "!" + function] = 
    #def unhook(self, library, function):        
    

    def dump(self, to_file=None):
        base = self.create_process_event.get_module_base()
        pe = pefile.PE(data=self.process.read(base, 0x1000))
        pe.OPTIONAL_HEADER.AddressOfEntryPoint = self.thread.get_pc() - base
        sections = ""
        pos = 0x1000
        for section in pe.sections:
            data = self.process.read(base + section.VirtualAddress, section.Misc).rstrip('\0')
            data += '\0' * ((-len(data)) % 0x200)
            sections += data
            section.PointerToRawData = pos
            section.SizeOfRawData = len(data)
            pos += len(data)
        file_data = list(pe.__data__)
        for structure in pe.__structures__:
            struct_data = list(structure.__pack__())
            offset = structure.get_file_offset()
            file_data[offset:offset+len(struct_data)] = struct_data
        new_file_data = ''.join( [ chr(ord(c)) for c in file_data] ) + sections
        if to_file is not None:
            open(to_file, "wb").write(new_file_data)
        return new_file_data
        # TODO: fix checksum

    def __getattr__(self, name):
        if name == "thread":
            return self.debug.lastEvent.get_thread()
        elif name.startswith("handle_"):
            def set_attribute(value):
                if value:
                    setattr(self.debug.get_event_handler(), name[len("handle_"):], self.debug.get_event_handler().breakpoint)
                else:
                    try:
                        delattr(self.debug.get_event_handler(), name[len("handle_"):])
                    except AttributeError:
                        pass
                
            return set_attribute
        raise AttributeError

    def run(self):
        while True:
            inst = self.step()
            print "0x%08X: %s" % (inst.address, str(inst))

    def runover(self):
        while True:
            inst = self.stepover()
            print "0x%08X: %s" % (inst.address, str(inst))

        
