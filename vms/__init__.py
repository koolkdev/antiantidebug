import vmtools
import codevirtualizer.animals.vm as animals_vm
import codevirtualizer.cisc.vm as cisc_vm

vmtools.VMS = {"CISC": vmtools.VMType(cisc_vm.VMFunctionJumper, cisc_vm.VMInfo, cisc_vm.VMFunction),
               "FISH": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.FISHVMInfo, animals_vm.VMFunction),
               "TIGER": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.TIGERVMInfo, animals_vm.TIGERVMFunction),
               "SHARK": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.SHARKVMInfo, animals_vm.VMFunction),
               "PUMA": vmtools.VMType(animals_vm.VMFunctionJumper, animals_vm.PUMAVMInfo, animals_vm.TIGERVMFunction)}