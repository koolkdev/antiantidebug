#include <cstddef>

extern "C" {
#include "deobfuscator.h"
}

#include "Cleaner.h"
#include <stdexcept>

extern "C" {
void * create_cleaner(reader_f reader, int mode, void * opaque) {
	return (void *)new Cleaner(reader, mode, opaque);
}
uint64_t clean_instruction(void * cleaner, uint64_t address, unsigned char * output, size_t * output_size) {
	try {
		uint64_t naddress = address;
		instruction_info opcode = ((Cleaner *)cleaner)->getCleanInstructionAt(&naddress, true);
		((Cleaner *)cleaner)->cleanIncDecSure(&naddress, &opcode); // fix inc and dec before returning the result
		if (instruction_assemble(&opcode, output, output_size, address)) {
			throw std::runtime_error("FATAL: Failed to assemble instruction\n");
		}
		return naddress;
	} catch(std::exception &e) {
		fprintf(stderr, "%s\n", e.what());
		return 0;
	}
}
void destroy_cleaner(void * cleaner) {
	delete (Cleaner *)cleaner;
}
void set_reg_unused(void * cleaner, int reg) {
	((Cleaner *)cleaner)->unused_regs.push_back((ud_type_t)reg);
}
void set_option(void * cleaner, char * option, uint64_t value) {
	((Cleaner *)cleaner)->options[dynamicStringHash(option)] = value;
}
}
