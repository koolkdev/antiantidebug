#ifndef __DEOBFUSCATOR_H__
#define __DEOBFUSCATOR_H__

#include <stdint.h>

typedef int (*reader_f)(void * opaque, uint64_t address, unsigned char * buffer, size_t size);

void * create_cleaner(reader_f reader, int mode, void * opaque); 
uint64_t clean_instruction(void * cleaner, uint64_t address, unsigned char * output, size_t * output_size);
void destroy_cleaner(void * cleaner);
void set_reg_unused(void * cleaner, int reg);
void set_option(void * cleaner, char * option, uint64_t value);

#endif