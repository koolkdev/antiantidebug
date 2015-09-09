import vmtools
import codevirtualizer.animals.vm as animals_vm
import codevirtualizer.cisc.vm as cisc_vm

vmtools.VMS = {"CISC": vmtools.VMType(cisc_vm.VMFunctionJumper, cisc_vm.VMInfo, cisc_vm.VMFunction),
               "FISH": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.FISHVMInfo, animals_vm.FISHVMFunction),
               "TIGER": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.TIGERVMInfo, animals_vm.TIGERVMFunction),
               "DOLPHIN": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.DOLPHINVMInfo, animals_vm.DOLPHINVMFunction),
               "SHARK": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.SHARKVMInfo, animals_vm.FISHVMFunction),
               "PUMA": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.PUMAVMInfo, animals_vm.TIGERVMFunction),
               "EAGLE": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.EAGLEVMInfo, animals_vm.FISHVMFunction)}