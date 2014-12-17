#ifndef PE_CLEANER_H
#define PE_CLEANER_H

extern "C" {
#include <x86utils.h>
#include "deobfuscator.h"
}
#include <map>
#include <vector>
#include <string>

class Cleaner {
public:
	Cleaner(reader_f reader, int mode, void * opaque);
	instruction_info getInstructionAt(uint64_t * address);
	instruction_info getCleanInstructionAt(uint64_t * address);
	
	bool is_inc(instruction_info * opcode);
	bool is_dec(instruction_info * opcode, bool change = true);
	int cleanIncDec(uint64_t * address, instruction_info * result);
	int cleanIncDecSure(uint64_t * address, instruction_info * result);
	int mergeMemorySplit(uint64_t * address, instruction_info * result);
	int clearJunkAddSub(uint64_t * address, instruction_info * result);
	int clearNotIncDecNot(uint64_t * address, instruction_info * result);
	int clear0Minus(uint64_t * address, instruction_info * result);
	int clear0MinusThruReg(uint64_t * address, instruction_info * result);
	int clearMovConstant(uint64_t * address, instruction_info * result);
	int fixPushPop(uint64_t * address, instruction_info * result);
	int fixPushMovMovPop(uint64_t * address, instruction_info * result);
	int fixPushMovMovCalcPop(uint64_t * address, instruction_info * result);
	int fixPushPopAddSub(uint64_t * address, instruction_info * result);
	int fixPush(uint64_t * address, instruction_info * result);
	int fixPop(uint64_t * address, instruction_info * result);
	int fixXorXorXor(uint64_t * address, instruction_info * result);
	int fixPushMovPop(uint64_t * address, instruction_info * result);
	int fixXchgByteThruReg(uint64_t * address, instruction_info * result);
	int fixOperationThruReg(uint64_t * address, instruction_info * result);
	int fixOperationThruReg2(uint64_t * address, instruction_info * result);
	int fixOperationThruStack(uint64_t * address, instruction_info * result);
	int fixOperationThruStackByte(uint64_t * address, instruction_info * result);
	int fixOperationThruRegByte(uint64_t * address, instruction_info * result);
	int fixOperationConstantThruReg(uint64_t * address, instruction_info * result);
	int fixOperationConstantOnEsp(uint64_t * address, instruction_info * result);
	
	int fixPushMovMovPopUnusedRegs(uint64_t * address, instruction_info * result);
	int fixPushMovMovCalcPopUnusedRegs(uint64_t * address, instruction_info * result);
	int fixOperationConstantThruRegUnusedRegs(uint64_t * address, instruction_info * result);

	int fixLods(uint64_t * address, instruction_info * result);
	int fixMovzx(uint64_t * address, instruction_info * result);
	
	int fixOperationConstantThruRegOnStack(uint64_t * address, instruction_info * result);
	
	std::vector<ud_type_t> unused_regs;
	std::map<int, uint64_t> options;
	
private:
	std::map<uint64_t, std::pair<instruction_info, uint64_t>> cache;
	reader_f reader;
	int mode;
	void * opaque;

};

unsigned dynamicStringHash(char * str);

#endif