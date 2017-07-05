#ifdef __GNUC__
	#define __STDC_LIMIT_MACROS
#endif

#include "Cleaner.h"
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#include <stdexcept>

extern "C" {
	#include <x86utils.h>
};

class StringHash 
{ 
unsigned m_val;

#ifdef __GNUC__
	#define FORCE_INLINE __attribute__((always_inline))
#else
	#define FORCE_INLINE __forceinline
#endif

template<size_t N> FORCE_INLINE unsigned _Hash(const char (&str)[N])
{ 
	typedef const char (&truncated_str)[N-4]; 
	return str[N-1] + 65599*(str[N-2] + 65599*(str[N-3] + 65599 * (str[N-4] + 65599*_Hash((truncated_str)str)))); 
} 
FORCE_INLINE unsigned _Hash(const char (&str)[4])
{
	typedef const char (&truncated_str)[3]; 
	return str[3] + 65599 * _Hash((truncated_str)str); 
} 
FORCE_INLINE unsigned _Hash(const char (&str)[3])
{ 
	typedef const char (&truncated_str)[2]; 
	return str[2] + 65599 * _Hash((truncated_str)str); 
} 
FORCE_INLINE unsigned _Hash(const char (&str)[2]) { return str[1] + 65599 * str[0]; }
FORCE_INLINE unsigned _Hash(const char (&str)[1]) { return str[0]; }

public: 
template <size_t N> FORCE_INLINE StringHash(const char (&str)[N]) { m_val = _Hash(str); }
	operator unsigned() { return m_val; } 
}; 

unsigned dynamicStringHash(char * str) {
	unsigned res = 0;
	do {
		res *= 65599;
		res += *str;
	} while (*(str++));

	return res;
}

struct Flags {
	int CF;
	int PF;
	int ZF;
	int SF;
	int OF;
};

#define JA UD_Ija
#define JAE UD_Ijae
#define JB UD_Ijb
#define JBE UD_Ijbe
#define JZ UD_Ijz
#define JG UD_Ijg
#define JGE UD_Ijge
#define JL UD_Ijl
#define JLE UD_Ijle
#define JNZ UD_Ijnz
#define JNO UD_Ijno
#define JNP UD_Ijnp
#define JNS UD_Ijns
#define JO UD_Ijo
#define JP UD_Ijp
#define JS UD_Ijs

#define INC UD_Iinc
#define DEC UD_Idec
#define ADD UD_Iadd
#define SUB UD_Isub
#define SHR UD_Ishr
#define SHL UD_Ishl
#define NOT UD_Inot
#define OR UD_Ior
#define AND UD_Iand
#define XOR UD_Ixor
#define NEG UD_Ineg
#define NOT UD_Inot

#define MOV UD_Imov
#define PUSH UD_Ipush
#define POP UD_Ipop
#define XCHG UD_Ixchg
#define MOVZX UD_Imovzx
#define LODSB UD_Ilodsb
#define LODSW UD_Ilodsw
#define LODSD UD_Ilodsd
#define LODSQ UD_Ilodsq

#define CALL UD_Icall
#define JMP UD_Ijmp

#define GET_OPCODE(instruction) ((instruction).opcode)
#define SET_OPCODE(instruction, _opcode) ((instruction).opcode = (_opcode))
#define GET_OPERAND(instruction, operand) ((instruction).operands[operand])

#define REMOVE_OPERAND(instruction, operand) (memset(&GET_OPERAND(instruction, operand), 0, sizeof(operand_info)))
#define COPY_OPERAND(dst_instruction, dst_operand, src_instruction, src_operand) (memcpy(&GET_OPERAND(dst_instruction, dst_operand), &GET_OPERAND(src_instruction, src_operand), sizeof(operand_info)))

#define GET_OPERAND_SIZE(instruction, operand) ((instruction).operands[operand].size >> 3)
#define GET_OPERAND_TYPE(instruction, operand) ((instruction).operands[operand].type)
#define SET_OPERAND_TYPE(instruction, operand, _type) ((instruction).operands[operand].type = (_type))

#define IS_REG_SP(reg) ((reg) == UD_R_RSP || (reg) == UD_R_ESP || (reg) == UD_R_SP || (reg) == UD_R_SPL)

#define NATIVE_SIZE(mode) ((mode) >> 3)
#define NATIVE_SP(mode) (((mode) == 32) ? UD_R_ESP : UD_R_RSP)

#define IS_OPERAND(instruction, operand) (GET_OPERAND_TYPE(instruction, operand) != OP_NONE)
#define IS_OPERAND_REG(instruction, operand) ((GET_OPERAND_TYPE(instruction, operand) & 0xF0) == OP_REG)
#define IS_OPERAND_IMM(instruction, operand) ((GET_OPERAND_TYPE(instruction, operand) & 0xF0) == OP_IMM)
#define IS_OPERAND_JIMM(instruction, operand) ((GET_OPERAND_TYPE(instruction, operand) & 0xF0) == OP_JIMM)
#define IS_OPERAND_MEM(instruction, operand) ((GET_OPERAND_TYPE(instruction, operand) & 0xF0) == OP_MEM)
#define IS_OPERAND_MEM_SP(instruction, operand, mode) (IS_OPERAND_MEM(instruction, operand) && GET_OPERAND(instruction, operand).base == NATIVE_SP(mode))
#define IS_OPERAND_SP_RELATED(instruction, operand, mode) (IS_OPERAND_SP(instruction, operand) || IS_OPERAND_MEM_SP(instruction, operand, mode))

#define IS_OPERAND_SP(instruction, operand) IS_REG_SP(GET_OPERAND(instruction, operand).reg)

#define IS_SAME_OPERANDS(instruction1, operand1, instruction2, operand2) (is_same_operands(&GET_OPERAND(instruction1, operand1), &GET_OPERAND(instruction2, operand2)))
#define IS_SAME_OPERANDS2(instruction1, operand1, operand) (is_same_operands(&GET_OPERAND(instruction1, operand1), &operand))

int is_same_operands(operand_info * op1, operand_info * op2) {
	if (op1->type != op2->type) {
		return false;
	}
	switch (op1->type & 0xF0) 
	{
	case OP_IMM:
		return op1->value == op2->value;
	case OP_REG:
		return op1->reg == op2->reg;
	case OP_MEM:
		return op1->base == op2->base && op1->index == op2->index && op1->scale == op2->scale && op1->offset == op2->offset;
	default:
		return false;
	}
}

int is_operand_mem_is(instruction_info * instruction, int operand, ud_type base, ud_type index = UD_NONE, int scale = 0, uint64_t offset = 0) {
	if (!IS_OPERAND_MEM(*instruction, operand)) return false;
	operand_info * op = &GET_OPERAND(*instruction, operand);
	return op->base == base && op->index == index && op->scale == scale && op->offset == offset;
}

template <class T>
T operation(T num, ud_mnemonic_code inst, __int64 realvalue)
{
	T value = realvalue;
	switch (inst) {
	case INC: return num + 1;
	case DEC: return num - 1;
	case ADD: return num + value;
	case SUB: return num - value;
	case SHR: return num >> value;
	case SHL: return num << value;
	case NOT: return ~num;
	case OR: return num | value;
	case AND: return num & value;
	case XOR: return num ^ value;
	case NEG: return -num;
	default: throw "error";
	}
}

template <class T>
unsigned __int64 toUnsigned64(T num) {
	return ((((unsigned __int64)1) << (8 * sizeof(num))) - 1) & ((unsigned __int64)num);
}
template <class T>
T operation(T num, ud_mnemonic_code inst, __int64 realvalue, Flags * flags)
{
	T value = realvalue;
	T res = 0;
	switch (inst) {
	case INC: 
		res = num + 1;
		flags->CF = -1;
		if (res < num) { flags->OF = 1; }
		else { flags->OF = 0; }
		break;
	case DEC:
		res = num - 1;
		flags->CF = -1;
		if (res > num) { flags->OF = 1; }
		else { flags->OF = 0; }
		break;
	case ADD: 
		res = num + value;
		if (toUnsigned64(res) < toUnsigned64(num)) {
			flags->CF = 1;
		} else {
			flags->CF = 0;
		}

		if ((value < 0 && num < 0 && res > 0) || (value > 0 && num > 0 && res < 0)) { flags->OF = 1; }
		else { flags->OF = 0; }
		break;
	case SUB:
		res = num - value;
		if (toUnsigned64(num) < toUnsigned64(value)) {
			flags->CF = 1;
		} else {
			flags->CF = 0;
		}
		if ((value > 0 && num < 0 && res > 0) || (value < 0 && num > 0 && res < 0)) { flags->OF = 1; }
		else { flags->OF = 0; }
		break;
	case SHR: 
		res = toUnsigned64(num) >> value;
		flags->CF = -1;
		flags->OF = -1;
		break;
	case SHL: 
		res = toUnsigned64(num) << value;
		flags->CF = -1;
		flags->OF = -1;
		break;
	case NOT: 
		res = ~num;
		flags->CF = -1;
		flags->OF = -1;
		flags->PF = -1;
		flags->SF = -1;
		flags->ZF = -1;
		return res;
	case OR: 
		res = num | value;
		flags->CF = 0;
		flags->OF = 0;
		break;
	case AND: 
		res = num & value;
		flags->CF = 0;
		flags->OF = 0;
		break;
	case XOR: 
		res = num ^ value;
		flags->CF = 0;
		flags->OF = 0;
		break;
	case NEG: 
		res = -num;
		flags->CF = num != 0;
		if (res < 0 && num < 0) { flags->OF = 1; }
		else { flags->OF = 0; }
		break;
	default: throw "error";
	}
	if (res < 0) {
		flags->SF = 1;
	} else {
		flags->SF = 0;
	}
	if (res == 0) {
		flags->ZF = 1;
	} else {
		flags->ZF = 0;
	}
	unsigned __int64 tres = res & 0xFF;
	int i = 0;
	while (tres != 0) {
		i += tres & 1;
		tres = tres >> 1;
	}
	if (i % 2 == 0) {
		flags->PF = 1;
	} else {
		flags->PF = 0;
	}
	return res;
}

bool is_jump_taken(ud_mnemonic_code inst, Flags * flags) {
	
	switch (inst) {
	case JA:
		if (flags->CF == -1 || flags->ZF == -1) throw "error";
		return flags->CF == 0 && flags->ZF == 0;
	case JAE:
		if (flags->CF == -1) throw "error";
		return flags->CF == 0;
	case JB:
		if (flags->CF == -1) throw "error";
		return flags->CF == 1;
	case JBE:
		if (flags->CF == -1 || flags->ZF == -1) throw "error";
		return flags->CF == 1 || flags->ZF == 1;
	case JZ:
		if (flags->ZF == -1) throw "error";
		return flags->ZF == 1;
	case JG:
		if (flags->OF == -1 || flags->ZF == -1 || flags->SF == -1) throw "error";
		return flags->ZF == 0 && (flags->SF == flags->OF);
	case JGE:
		if (flags->OF == -1 || flags->SF == -1) throw "error";
		return flags->SF == flags->OF;
	case JL:
		if (flags->OF == -1 || flags->SF == -1) throw "error";
		return flags->SF != flags->OF;
	case JLE:
		if (flags->OF == -1 || flags->ZF == -1 || flags->SF == -1) throw "error";
		return flags->ZF == 1 || (flags->SF != flags->OF);
	case JNZ:
		if (flags->ZF == -1) throw "error";
		return flags->ZF == 0;
	case JNO:
		if (flags->OF == -1) throw "error";
		return flags->OF == 0;
	case JNP:
		if (flags->PF == -1) throw "error";
		return flags->PF == 0;
	case JNS:
		if (flags->SF == -1) throw "error";
		return flags->SF == 0;
	case JO:
		if (flags->OF == -1) throw "error";
		return flags->OF == 1;
	case JP:
		if (flags->PF == -1) throw "error";
		return flags->PF == 1;
	case JS:
		if (flags->SF == -1) throw "error";
		return flags->SF == 1;
	default: throw "error";

	}
}
bool is_math_op(ud_mnemonic_code inst) {
	switch (inst) {
	case INC: 
	case DEC: 
	case ADD: 
	case SUB: 
	case SHR: 
	case SHL: 
	case NOT: 
	case OR: 
	case AND: 
	case XOR: 
	case NEG: return true;
	default: return false;
	}
}
bool is_cond_jump(ud_mnemonic_code inst) {
	switch (inst) {
	case JA:
	case JAE:
	case JB:
	case JBE:
	case JZ:
	case JG:
	case JGE:
	case JL:
	case JLE:
	case JNZ:
	case JNO:
	case JNP:
	case JNS:
	case JO:
	case JP:
	case JS: return true;
	}
	return false;
}

#undef OP_NONE
#define OP_NONE NONE

signed long long get_immediate_value(instruction_info * instruction, int operand) {
	switch (GET_OPERAND_SIZE(*instruction, operand)){
	case 1:	return (signed char)instruction->operands[operand].value;
	case 2:	return (signed short)instruction->operands[operand].value;
	case 4:	return (signed long)instruction->operands[operand].value;
	case 8:	return (signed long long)instruction->operands[operand].value;
	}
	return 0;
}

int get_register_group(int reg) {
	if (reg >= UD_R_RAX && reg <= UD_R_R15)
		return reg - UD_R_RAX;
	if (reg >= UD_R_EAX && reg <= UD_R_R15D)
		return reg - UD_R_EAX;
	if (reg >= UD_R_AX && reg <= UD_R_R15W)
		return reg - UD_R_AX;
	if (reg >= UD_R_AH && reg <= UD_R_R15B)
		return reg - UD_R_AH;
	if (reg >= UD_R_AL && reg <= UD_R_BL)
		return reg - UD_R_AL;
	return -1;
}

bool is_releated_reg(instruction_info * instruction1, int operand1, instruction_info * instruction2, int operand2) {
	if (!IS_OPERAND_REG(*instruction1, operand1) || !IS_OPERAND_REG(*instruction2, operand2)) {
		return false;
	}
	ud_type reg1 = instruction1->operands[operand1].reg;
	ud_type reg2 = instruction2->operands[operand2].reg;
	if (reg1 == reg2) {
		return true;
	}
	int group1 = get_register_group(reg1);
	if (group1 == -1)
		return false;
	int group2 = get_register_group(reg2);
	return group1 == group2;
}

bool is_releated_reg(instruction_info * instruction, int operand, ud_type reg) {
	if (!IS_OPERAND_REG(*instruction, operand)) {
		return false;
	}
	ud_type reg1 = instruction->operands[operand].reg;
	ud_type reg2 = reg;
	if (reg1 == reg2) {
		return true;
	}
	int group1 = get_register_group(reg1);
	if (group1 == -1)
		return false;
	int group2 = get_register_group(reg2);
	return group1 == group2;
}

bool is_unused_reg(Cleaner * cleaner, instruction_info * instruction, int operand) {
	if (!IS_OPERAND_REG(*instruction, operand)) return false;
	for (int i = 0 ; i < cleaner->unused_regs.size(); ++i) {
		if (is_releated_reg(instruction, operand, cleaner->unused_regs[i])) {
			return true;
		}
	}
	return false;
}

bool Cleaner::is_inc(instruction_info * instruction) {
	return (instruction->opcode == INC || (cleanIncDec(NULL, instruction) && instruction->opcode == INC));
}
bool Cleaner::is_dec(instruction_info * instruction, bool change) {
	if (change) {
		return (instruction->opcode == DEC || (cleanIncDec(NULL, instruction) && instruction->opcode == DEC));
	} else {
		instruction_info temp = *instruction;
		return (temp.opcode == DEC || (cleanIncDec(NULL, &temp) && temp.opcode == DEC));
	}
}

int Cleaner::cleanIncDec(uint64_t * address, instruction_info * result) {
	if ((GET_OPCODE(*result) == ADD && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == 1) ||
		(GET_OPCODE(*result) == SUB && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == -1)) {
			SET_OPCODE(*result, INC);
			REMOVE_OPERAND(*result, 1);
			return true;
	}
	if ((GET_OPCODE(*result) == ADD && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == -1) || 
		(GET_OPCODE(*result) == SUB && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == 1)) {
			SET_OPCODE(*result, DEC);
			REMOVE_OPERAND(*result, 1);
			return true;
	}
	/*if (GET_OPCODE(*result) == ADD && (result->operands[1] & 0xF0) == OPH_CONSTANT && get_immediate_value(result, 1) == 1) {
		// @@@@@@@@@@@@@@@@@
		int current_address = *address;
		instruction_info next = getCleanInstructionAt(address);
		if (GET_OPCODE(next) == XCHG || GET_OPCODE(next) == NOT) {
			*address = current_address;
			GET_OPCODE(*result) = INC;
			result->operands[1] = OP_NONE;
			return true;
		}
	}*/
	return false;
}
int Cleaner::cleanIncDecSure(uint64_t * address, instruction_info * result) {
	if (options[StringHash("fix_inc_dec")]) {
		if (GET_OPERAND_SIZE(*result, 0) < 4) return false;
		if ((GET_OPCODE(*result) == ADD && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == 1) ||
			(GET_OPCODE(*result) == SUB && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == -1)) {
				SET_OPCODE(*result, INC);
				REMOVE_OPERAND(*result, 1);
				return true;
		}
		if ((GET_OPCODE(*result) == ADD && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == -1) || 
			(GET_OPCODE(*result) == SUB && IS_OPERAND_IMM(*result, 1) && get_immediate_value(result, 1) == 1)) {
				SET_OPCODE(*result, DEC);
				REMOVE_OPERAND(*result, 1);
				return true;
		}
	}
	return false;
}
// Obfuscators: ADD, XOR, MOV
/*
//TODO: What about when XOR/ADD ..., [R64]?
// in 64 bit: only [RXN+Y]
// in 64 bit: only ADD or XOR
RN - Register Ntaive
INPUT:
ADD/XOR ..., [RXN+RYN*X+Y]
/
ADD/XOR [RXN+RYN*X+Y], ...
OUTPUT:
PUSH RAN
// in 32:
MOV RAN, RYN
SHL RAN, log2(X)
// 
MOV/ADD RAN, X
ADD RAN, RAN
XOR/ADD ..., [RA64]
/
XOR/ADD [RA64], ...
POP RA64
*/
int Cleaner::mergeMemorySplit(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0)) return false;
	ud_type used_reg = GET_OPERAND(*result, 0).reg;
	if (NATIVE_SIZE(this->mode) != GET_OPERAND_SIZE(*result, 0) || used_reg == NATIVE_SP(this->mode)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != MOV || !IS_OPERAND_REG(next, 0) || GET_OPERAND(next, 0).reg != used_reg) return false;
	ud_type base = UD_NONE;
	ud_type index = UD_NONE;
	int scale = 0;
	uint64_t offset = 0;

	if (this->mode == 32) {
		if (IS_OPERAND_REG(next, 1) && GET_OPERAND(next, 1).reg != used_reg && GET_OPERAND(next, 1).reg != NATIVE_SP(this->mode)) {
			index = GET_OPERAND(next, 1).reg;
			next = getCleanInstructionAt(address);
			if (GET_OPCODE(next) == SHL) {
				if (!IS_OPERAND_REG(next ,0) || GET_OPERAND_TYPE(next, 1) != OP_IMM_8 || GET_OPERAND(next, 0).reg != used_reg) return false;
				switch (get_immediate_value(&next, 1)) {
				case 1:
				case 2:
				case 3:
					scale = 1 << get_immediate_value(&next, 1);
					break;
				default:
					return false;
				}
				next = getCleanInstructionAt(address);
			} else {
				scale = 0;
			}
			if (GET_OPCODE(next) != ADD || !IS_OPERAND_REG(next, 0) || GET_OPERAND(next, 0).reg != used_reg) return false;
		}
	}
	if (GET_OPERAND_TYPE(next, 1) != OP_IMM_32 && (this->mode != 64 || GET_OPERAND_TYPE(next, 1) != OP_IMM_64 || (get_immediate_value(&next, 1) >> 32))) return false;
	offset = get_immediate_value(&next, 1);
	if (this->mode == 32) offset &= 0xffffffff;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != ADD || !IS_OPERAND_REG(next, 0) || !IS_OPERAND_REG(next, 1) || GET_OPERAND(next, 0).reg != used_reg || GET_OPERAND(next, 1).reg == used_reg || GET_OPERAND(next, 1).reg == NATIVE_SP(this->mode)) return false;
	base = GET_OPERAND(next, 1).reg;

	int address_op = 0, other_op = 1; 
	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) == ADD || GET_OPCODE(main) == XOR || (GET_OPCODE(main) == MOV && this->mode == 32)) {
		if (IS_OPERAND_MEM(main, 1) && (GET_OPERAND(main, 1).base == used_reg || GET_OPERAND(main, 1).index == used_reg) && (GET_OPERAND(main, 0).base == UD_NONE || GET_OPERAND(main, 0).index == UD_NONE) && GET_OPERAND(main, 0).offset == 0) {
			address_op = 1;
			other_op = 0;
		} else if (IS_OPERAND_MEM(main, 0) && (GET_OPERAND(main, 0).base == used_reg || GET_OPERAND(main, 0).index == used_reg) && (GET_OPERAND(main, 0).base == UD_NONE || GET_OPERAND(main, 0).index == UD_NONE) && GET_OPERAND(main, 0).offset == 0) {
		} else {
			return false;
		}
	} else {
		return false;
	}

	if (!IS_OPERAND_IMM(main, other_op) && !(IS_OPERAND_REG(main, other_op) && !IS_OPERAND_SP(main, other_op))) { return false; }
	
	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_OPERAND_REG(next, 0) || GET_OPERAND(next, 0).reg != used_reg) return false;

	*result = main;
	GET_OPERAND(*result, address_op).base = base;
	GET_OPERAND(*result, address_op).index = index;
	GET_OPERAND(*result, address_op).scale = scale; 
	GET_OPERAND(*result, address_op).offset = offset;

	return true;
}

// Obfuscators: ADD, SUB
// INPUT:
// ADD X, Y
// OUTPUT:
// ADD/SUB X, RANDOM
// ADD X, Y
// SUB/ADD X, RANDOM
int Cleaner::clearJunkAddSub(uint64_t * address, instruction_info * result) {
	if (!((GET_OPCODE(*result) == ADD || GET_OPCODE(*result) == SUB))) return false;
	if (!(IS_OPERAND_REG(*result, 0) || IS_OPERAND_MEM(*result, 0))) return false;
	if (!IS_OPERAND_IMM(*result, 1)) return false;
	
	instruction_info main = getCleanInstructionAt(address);
	if (!((GET_OPCODE(main) == ADD || GET_OPCODE(main) == SUB) && IS_SAME_OPERANDS(main, 0, *result, 0))) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (!((GET_OPCODE(next) == ADD || GET_OPCODE(next) == SUB) && GET_OPCODE(next) != GET_OPCODE(*result) && IS_SAME_OPERANDS(next, 0, *result, 0) && IS_SAME_OPERANDS(next, 1, *result, 1))) return false;

	*result = main;
	return true;	
}

// Obfuscators: NEG
// INPUT:
// NEG X
// OUTPUT:
// NOT X
// INC X
// ----
// DEC X
// NOT X

int Cleaner::clearNotIncDecNot(uint64_t * address, instruction_info * result) {
	if (!((GET_OPCODE(*result) == NOT || is_dec(result, false)) && !IS_OPERAND_SP(*result, 0))) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (!(((is_inc(&next) && GET_OPCODE(*result) == NOT) || (GET_OPCODE(next) == NOT && is_dec(result))) && IS_SAME_OPERANDS(*result, 0, next, 0))) return false;
	
	SET_OPCODE(*result, NEG);

	return true;
}

// Obfuscators: NEG
// INPUT:
// NEG R64
// OUTPUT:
// PUSH 0
// SUB [RSP], R64
// POP R64

// INPUT:
// NEG R16
// OUPUT:
// PUSH RA16
// MOV WORD [RSP], 0
// SUB [RSP], R16
// POP R16

// // TODO: Bug? in the case of SP it will probably  use the previous case
// INPUT:
// NEG RSP/SP
// OUTPUT:
// PUSH -8/-2
// SUB [RSP], RSP/SP
// POP RSP/SP

// INPUT:
// NEG R8
// OUTPUT:
// PUSH 0 (64/16)
// SUB BYTE [RSP], R8
// MOV R8, [RSP]
// ADD ESP, 8
int Cleaner::clear0Minus(uint64_t * address, instruction_info * result) {
	if (!(GET_OPCODE(*result) == PUSH && (IS_OPERAND_IMM(*result, 0) || (IS_OPERAND_REG(*result, 0) && !IS_OPERAND_SP(*result, 0) && this->mode == 64)))) return false;
	int size = GET_OPERAND_SIZE(*result, 0);
	int real_size = size;
	if (size == 2) {
		if (this->mode == 64) {
			if (IS_OPERAND_IMM(*result, 0)) return false;
			instruction_info next = getCleanInstructionAt(address);
			if (!(GET_OPCODE(next) == MOV && IS_OPERAND_MEM_SP(next, 0, this->mode) && GET_OPERAND(next, 0).index == UD_NONE && GET_OPERAND(next, 0).offset == 0 && GET_OPERAND_SIZE(next, 0) == size && IS_OPERAND_IMM(next, 1) && get_immediate_value(&next, 1) == 0)) return false;
		}
	} else if (size == (this->mode >> 3)) {
		if (!IS_OPERAND_IMM(*result, 0)) return false;
	} else {
		// Should not happen anyway
		return false;
	}
	int is_esp = 0;
	__int64 imm_val = get_immediate_value(result, 0);
	if (imm_val) {
		if (imm_val != -size) return false;
		is_esp = 1;
	}
	
	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != SUB || !IS_OPERAND_MEM_SP(main, 0, this->mode) || GET_OPERAND(main, 0).index != UD_NONE && GET_OPERAND(main, 0).offset != 0 || !IS_OPERAND_REG(main, 1)) return false;

	if (IS_OPERAND_SP(main, 1)) {
		if (!is_esp) return false;
	} else if (is_esp) {
		return false;
	}

	if (GET_OPERAND_SIZE(main, 0) == 1) {
		if (is_esp) return false;
		real_size = 1;
	} else if (GET_OPERAND_SIZE(main, 0) != size) {
		return false;
	}

	instruction_info next = getCleanInstructionAt(address);
	if(!IS_SAME_OPERANDS(main, 1, next, 0)) return false;
	if (real_size == 1) {
		if (GET_OPCODE(next) != MOV || !IS_SAME_OPERANDS(main, 0, next, 1)) return false;
		next = getCleanInstructionAt(address);
		if (GET_OPCODE(next) != ADD || GET_OPERAND(next, 0).reg != NATIVE_SP(this->mode) || get_immediate_value(&next, 1) != size) return false;
	} else {
		if (GET_OPCODE(next) != POP) return false;
	}
	*result = main;
	SET_OPCODE(*result, NEG);
	REMOVE_OPERAND(*result, 1);
	COPY_OPERAND(*result, 0, main, 1);
	return true;
}

// Obfuscators: NEG
// INPUT:
// NEG [32/16]
// OUTPUT:
// PUSH R32/R16
// MOV R32/R16, 0
// SUB R32/R16, [32/16]
// MOV/XCHG [32/16], R32/R16
// POP R32/R16
int Cleaner::clear0MinusThruReg(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != MOV || !IS_SAME_OPERANDS(next, 0, *result, 0) || !IS_OPERAND_IMM(next, 1) || get_immediate_value(&next, 1) != 0) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != SUB || !IS_SAME_OPERANDS(main, 0, *result, 0) || !((IS_OPERAND_REG(main, 1) && !IS_OPERAND_SP(main, 1)) || (IS_OPERAND_MEM(main, 1) && !IS_OPERAND_MEM_SP(main, 1, this->mode)))) return false;

	next = getCleanInstructionAt(address);
	if ((GET_OPCODE(next) == MOV || GET_OPCODE(next) == XCHG) && IS_SAME_OPERANDS(next, 0, main, 1) && IS_SAME_OPERANDS(next, 1, main, 0));
	else if (GET_OPCODE(next) == XCHG && IS_SAME_OPERANDS(next, 1, main, 1) && IS_SAME_OPERANDS(next, 0, main, 0));
	else return false;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	*result = main;
	GET_OPCODE(*result) = NEG;
	REMOVE_OPERAND(*result, 1);
	COPY_OPERAND(*result, 0, main, 1);

	return true;
}

// Also for part of the case:
// [PUSH R64]
// PUSH IMM
// POP R64
// MATH R64/R32/R16/R8, . ....
// // Someimtes the last math is going to be on R32 event if it is qword (read down about case 4) TODO: I am not completly understading this right now
// MOV .... R64/R32/R16/R8
// [POP R64]

// Obfuscators: MOV
int Cleaner::clearMovConstant(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != MOV || IS_OPERAND_SP(*result, 0) || !IS_OPERAND_IMM(*result, 1)) return false;
	if (this->mode == 64 && IS_OPERAND_MEM_SP(*result, 0, this->mode)) return false;
	int size = GET_OPERAND_SIZE(*result, 0);
	operand_info real_operand = GET_OPERAND(*result, 0);
	bool fix_size = false;
	bool fix_operand = false;
	bool check_for_mov = false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (this->mode == 64) {
		// An check for the case: (in 32 bit the real size is also the size of the push and the pop (16/32)
		// [PUSH R64]
		// PUSH IMM
		// POP R64
		// MATH R32/R16/R8, .. 
		// MOV A32/A16/A8, R32/R16/R8
		// [POP R64]
		if (is_math_op(GET_OPCODE(next)) && (!IS_OPERAND(next, 1) || IS_OPERAND_IMM(next, 1))) {
			if (!IS_SAME_OPERANDS(next, 0, *result, 0)) {
				if (!is_releated_reg(result, 0, &next, 0) || size != 8) return false;
				size = GET_OPERAND_SIZE(next, 0);
				if (GET_OPERAND(*result, 0).value > (1LL << size << 3)) return false;
				real_operand = GET_OPERAND(next, 0);
				fix_size = true;
				fix_operand = true;
				check_for_mov = true;
			}
		}
	}

	// TODO: Maybe in some cases, if the number is small, it will be only one byte?
	//int size = GET_OPERAND_SIZE(*result, 1);
	uint64_t last_address = *address;
	uint64_t last_last_address = 0;

	Flags flags;
	
	uint64_t v64;
	uint32_t v32;
	uint16_t v16;
	uint8_t v8;

	uint64_t lv64;
	uint32_t lv32;
	uint16_t lv16;
	uint8_t lv8;

	switch (size) {
	case 1: v8 = get_immediate_value(result, 1); break;
	case 2: v16 = get_immediate_value(result, 1); break;
	case 4: v32 = get_immediate_value(result, 1); break;
	case 8: v64 = get_immediate_value(result, 1); break;
	}

	last_address = *address;
	instruction_info first = next;
	instruction_info last;
	last.opcode = UD_Iinvalid;
	int instructions = 0;
	// I am not checking that there are up to 6 operations..
	while ((is_math_op(GET_OPCODE(next)) && IS_SAME_OPERANDS2(next, 0, real_operand) && (!IS_OPERAND(next, 1) || IS_OPERAND_IMM(next, 1))) || (is_cond_jump(GET_OPCODE(next)) && instructions > 0 && IS_OPERAND_JIMM(next, 0))) {
		if (is_cond_jump(GET_OPCODE(next))) {
			if (is_jump_taken(GET_OPCODE(next), &flags)) {
				*address = get_immediate_value(&next, 0);
			}
			last_address = *address;
			next = getCleanInstructionAt(address);
		} else {
			last = next;
			switch (size) {
			case 1: v8 = operation<int8_t>(v8, GET_OPCODE(next), get_immediate_value(&next, 1), &flags); break;
			case 2: v16 = operation<int16_t>(v16, GET_OPCODE(next), get_immediate_value(&next, 1), &flags); break;
			case 4: v32 = operation<int32_t>(v32, GET_OPCODE(next), get_immediate_value(&next, 1), &flags); break;
			case 8: v64 = operation<int64_t>(v64, GET_OPCODE(next), get_immediate_value(&next, 1), &flags); break;
			}
			last_address = *address;

			if (GET_OPCODE(last) == ADD || GET_OPCODE(last) == SUB || GET_OPCODE(last) == XOR || (size < 4 && GET_OPCODE(last) == NEG)) {
				// There are some cases in the vm init that there is mov ebx, 0x. shr ebx, 2
				// So we don't want to clean the last operation
				// So we will find the instruction that can be the last
				last_last_address = last_address;
				switch (size) {
				case 1: lv8 = v8; break;
				case 2: lv16 = v16; break;
				case 4: lv32 = v32; break;
				case 8: lv64 = v64; break;
				}
			}

			next = getCleanInstructionAt(address);
		}
		instructions += 1;
	}

	if (size == 4 && check_for_mov && instructions == 1) { 
		// It can be two cases: Or that it is a dword, or a qword (case 4 below)
		// We are going to determine it by checking the next instruction
		if (GET_OPCODE(next) != MOV || IS_OPERAND_SP_RELATED(next, 0, this->mode)) return false;
		if (IS_SAME_OPERANDS(next, 1, *result, 0)) {
			// So it is like the first mov, qword
			size = 8;
			v64 = v32;
			// no need to fix reg and size, the result is 32 bit anyway
			fix_operand = false;
			fix_size = false;
		} else if (!IS_SAME_OPERANDS(next, 1, last, 0)) return false; // It must be the dword registry otherwise
		check_for_mov = false; // We checked for it, no need any more

check_op:
		// In some cases, if it ends with:
		// NOT X
		// SUB X, 1
		// It will turn into neg. So accept neg if size < 4 (It is not probable that it will happen with 32 bit)
		if ((GET_OPCODE(last) != ADD && GET_OPCODE(last) != SUB && GET_OPCODE(last) != XOR && !(size < 4 && GET_OPCODE(last) == NEG)) || (instructions == 0)) return false;
		*address = last_address;
	} else if (size == 8) {
		// The completion have to happen thru another reg if our wanted result is bigger than 32bit.
		// There are three cases:
		// 1. Our target number is under 32 bit, so not completion thru reg is needed, but in this case xor will be used
		// 2. We will push another reg to the stack and do the operation thru its
		// 3. We will choose an unused reg and do the operation thru it
		// 4. Our target number is under 32 bit, and we are in the PUSH IMM/POP R64 flow (see at the start of this function), In this case the last operation will be with the R32 register
		// [PUSH R64]
		// MOV R64, COMPLETION
		// OPERATION [...], R64
		// [POP R64]
		fix_size = (int64_t)v64 > INT32_MAX || (int64_t)v64 < INT32_MIN;

		if ((GET_OPCODE(next) == XOR || GET_OPCODE(next) == ADD || GET_OPCODE(next) == SUB) && is_releated_reg(&next, 0, result, 0) && GET_OPERAND_SIZE(next, 0) == 4 && IS_OPERAND_IMM(next, 1)) { // case 4
			size = 4; // the immedaite is actually 32bits
			v32 = v64;
			v32 = operation<int32_t>(v32, GET_OPCODE(next), get_immediate_value(&next, 1), &flags);
			fix_size = true;
			uint64_t taddress = *address;
			next = getCleanInstructionAt(&taddress); // Just get the mov for checking it
			check_for_mov = true;;
		}
		else if ((GET_OPCODE(next) == PUSH || GET_OPCODE(next) == MOV) && IS_OPERAND_REG(next, 0) && GET_OPERAND_SIZE(next, 0) == size && !is_releated_reg(&next, 0, result, 0)) { // case 2 and 3 // TODO: what if result, 0 is not reg?
			instruction_info mov = next;
			if (GET_OPCODE(next) == PUSH) { // case 2
				mov = getCleanInstructionAt(address);
			} else { // case 3
				if (!is_unused_reg(this, &next, 0)) goto check_op;
			}
			if (GET_OPCODE(mov) != MOV || !IS_SAME_OPERANDS(next, 0, mov, 0) || !IS_OPERAND_IMM(mov, 1)) goto check_op;

			instruction_info op = getCleanInstructionAt(address);
			if (!(GET_OPCODE(op) == ADD || GET_OPCODE(op) == SUB || GET_OPCODE(op) == XOR) || !IS_SAME_OPERANDS(op, 0, *result, 0) || !IS_SAME_OPERANDS(op, 1, next, 0)) goto check_op;

			v64 = operation<int64_t>(v64, GET_OPCODE(op), get_immediate_value(&mov, 1), &flags); 
			
			fix_size = (int64_t)v64 > INT32_MAX || (int64_t)v64 < INT32_MIN;

			if (GET_OPCODE(next) == PUSH) { // case 2
				instruction_info pop = getCleanInstructionAt(address);
				if (GET_OPCODE(pop) != POP || !IS_SAME_OPERANDS(next, 0, pop, 0)) return false;
			}
		} else { // case 1 OR case 3  that we already fixed (because the number in mov was immedidate 32). that is why we allow ADD and OR
			goto check_op;	
		}

	} else {
		// TODO: Same for case 1/3 in 64 bit flow?
		if (instructions == 0 || last_last_address == 0) return false;
		// revert to the last good instruction
		last_address = last_last_address;
		switch (size) {
		case 1: v8 = lv8; break;
		case 2: v16 = lv16; break;
		case 4: v32 = lv32; break;
		case 8: v64 = lv64; break;
		}
		*address = last_address;
	}

	if (check_for_mov) {
		 // last should include the correct register
		if (GET_OPCODE(next) != MOV || IS_OPERAND_SP_RELATED(next, 0, this->mode) || !IS_SAME_OPERANDS(last, 0, next, 1)) return false;
	}

	if (fix_operand) {
		GET_OPERAND(*result, 0) = real_operand;
	}
	if (fix_size) {
		GET_OPERAND(*result, 1).size = size << 3;
		switch (size) {
		case 1: GET_OPERAND(*result, 1).type = OP_IMM_8; break;
		case 2: GET_OPERAND(*result, 1).type = OP_IMM_16; break;
		case 4: GET_OPERAND(*result, 1).type = OP_IMM_32; break; 
		case 8: GET_OPERAND(*result, 1).type = OP_IMM_64; break;
		}
	}

	switch (size) {
	case 1: GET_OPERAND(*result, 1).value = v8; break;
	case 2: GET_OPERAND(*result, 1).value = v16; break;
	case 4: GET_OPERAND(*result, 1).value = v32; break;
	case 8: GET_OPERAND(*result, 1).value = v64; break;
	}

	return true;
}

// Obfuscators: MOV
// INPUT:
// MOV X, Y
// OUTPUT:
// PUSH X
// POP Y
int Cleaner::fixPushPop(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || GET_OPERAND_SIZE(*result, 0) != GET_OPERAND_SIZE(next, 0) || (IS_OPERAND_MEM(*result, 0) && IS_OPERAND_MEM(next, 1))) return false;
	
	COPY_OPERAND(*result, 1, *result, 0);
	COPY_OPERAND(*result, 0, next, 0);
	SET_OPCODE(*result, MOV);

	return true;
}

// Obfuscators: MOV
 // INPUT:
// MOV X, Y
// OUTOUT:
// [PUSH R64]
// MOV R64/R32/R16/R8, X // TODO: Bug? missed R32 if there isn't unsed reg?
// MOV Y, R64/R32/R16/R8
// [POP R64]
int Cleaner::fixPushMovMovPop(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0) || GET_OPERAND_SIZE(*result, 0) != NATIVE_SIZE(this->mode)) return false;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != MOV || !is_releated_reg(&first, 0, result, 0) || IS_OPERAND_SP_RELATED(first, 1, this->mode)) return false;
	
	instruction_info second = getCleanInstructionAt(address);
	if (GET_OPCODE(second) != MOV || !IS_SAME_OPERANDS(second, 1, first, 0) || IS_OPERAND_SP_RELATED(second, 0, this->mode)) return false;

	if (IS_OPERAND_MEM(first, 1) && IS_OPERAND_REG(second, 0)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	*result = first;
	COPY_OPERAND(*result, 0, second, 0);
	/**********/

	return true;
}

// Obfuscators: MOV
// INPUT:
// MOV X, Y
// OUTPUT:
// MOV R64/R32/R16/R8, Y
// MOV X, R64/R32/R16/R8
// [ADD/SUB/XOR R64, RANDOM] * 3
int Cleaner::fixPushMovMovPopUnusedRegs(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != MOV || !is_unused_reg(this, result, 0) || IS_OPERAND_SP(*result, 1) || (this->mode == 32 && IS_OPERAND_MEM_SP(*result, 1, this->mode))) return false;
	
	instruction_info second = getCleanInstructionAt(address);
	if (GET_OPCODE(second) != MOV || !IS_SAME_OPERANDS(second, 1, *result, 0) || IS_OPERAND_SP_RELATED(second, 0, this->mode)) return false;

	uint64_t last_address = *address;
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) == POP && is_releated_reg(&next, 0, result, 0)) return false;
	
	if (!is_releated_reg(&second, 0, result, 0)) {
		// In some RARE cases, if this obfuscator happens twice like that:
		// MOV R15, IMM =>
		// MOV R11, IMM 
		// MOV R15, R11 
		// and than to:
		// MOV R15, IMM
		// MOV R11, R15
		// MOV R15, R11
		// Our deobfuscator will try to convert the second and third line first, so we will get:
		// MOV R15, IMM
		// MOV R15, R15
		// And if there will be operations on R15 after that they will be thrown away. And the output won't be correct. So we are checking for this case right now.
		// TODO: Think if there are such problems in more cases (or just try many deobfuscations)
		// TODO: Keep in state which regs are in usage right now (Will be problemtic in caching)

		// I am not checking that there are up to 3 operations
		while ((GET_OPCODE(next) == ADD || GET_OPCODE(next) == SUB || GET_OPCODE(next) == XOR) && IS_SAME_OPERANDS(next, 0, *result, 0) && (IS_OPERAND_REG(next, 1) || IS_OPERAND_IMM(next, 1))) {
			last_address = *address;
			next = getCleanInstructionAt(address);
		}
	}

	*address = last_address;

	COPY_OPERAND(*result, 0, second, 0);
	/**********/

	return true;
}

// Obfuscators: MOV
// PUSH R32
// MOV R32/R16/R8, #RANDOM
// MOV [...], #RANDOM(...)ORIGINAL
// ADD/SUB/XOR [...], R32/R16/R8
// POP R32
int Cleaner::fixPushMovMovCalcPop(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0) || GET_OPERAND_SIZE(*result, 0) != NATIVE_SIZE(this->mode)) return false;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != MOV || !is_releated_reg(&first, 0, result, 0) || !IS_OPERAND_IMM(first, 1)) return false;
	
	instruction_info calc = getCleanInstructionAt(address);
	if (GET_OPCODE(calc) != MOV || !IS_OPERAND_IMM(calc, 1) || IS_OPERAND_SP_RELATED(calc, 0, this->mode)) return false;

	instruction_info second = getCleanInstructionAt(address);
	if (!((GET_OPCODE(second) != ADD || GET_OPCODE(second) != SUB || GET_OPCODE(second) != XOR) && IS_SAME_OPERANDS(second, 0, calc, 0) && IS_SAME_OPERANDS(second, 1, first, 0))) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	*result = first;
	COPY_OPERAND(*result, 0, second, 0);
	
	switch (GET_OPERAND_SIZE(calc, 0)) {
	case 1: GET_OPERAND(*result, 1).value = operation<uint8_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(&first, 1)); break;
	case 2: GET_OPERAND(*result, 1).value = operation<uint16_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(&first, 1)); break;
	case 4: GET_OPERAND(*result, 1).value = operation<uint32_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(&first, 1)); break;
	case 8: GET_OPERAND(*result, 1).value = operation<uint64_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(&first, 1)); break;
	}
	
	if (GET_OPERAND_SIZE(*result, 0) == 8 && ((int64_t)GET_OPERAND(*result, 1).value > INT32_MAX || (int64_t)GET_OPERAND(*result, 1).value < INT32_MIN)) {
		GET_OPERAND(*result, 1).size = GET_OPERAND(*result, 0).size;
		GET_OPERAND(*result, 1).type = OP_IMM_64;
	}
	
	/**********/
	return true;
}

// Obfuscators: MOV
// INPUT:
// MOV X, IMM
// OUTPUT:
// MOV R64/R32/R16/R8, RANDOM
// MOV X, RANDOM^IMM
// ADD/SUB/XOR X, R64/R32/R16/R8
// ADD/SUB/XOR R64, RANDOM * 3
int Cleaner::fixPushMovMovCalcPopUnusedRegs(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != MOV || !is_unused_reg(this, result, 0) || !IS_OPERAND_IMM(*result, 1)) return false;
	
	instruction_info calc = getCleanInstructionAt(address);
	if (GET_OPCODE(calc) != MOV || !IS_OPERAND_IMM(calc, 1) || IS_OPERAND_SP_RELATED(calc, 0, this->mode)) return false;
	
	instruction_info second = getCleanInstructionAt(address);
	if (!((GET_OPCODE(second) != ADD || GET_OPCODE(second) != SUB || GET_OPCODE(second) != XOR) && IS_SAME_OPERANDS(second, 0, calc, 0) && IS_SAME_OPERANDS(second, 1, *result, 0))) return false;

	uint64_t last_address = *address;
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) == POP && is_releated_reg(&next, 0, result, 0)) return false;
	
	// I am not checking that there are up to 3 operations
	while ((GET_OPCODE(next) == ADD || GET_OPCODE(next) == SUB || GET_OPCODE(next) == XOR) && IS_SAME_OPERANDS(next, 0, *result, 0) && (IS_OPERAND_REG(next, 1) || IS_OPERAND_IMM(next, 1))) {
		last_address = *address;
		next = getCleanInstructionAt(address);
	}

	*address = last_address;
	
	COPY_OPERAND(*result, 0, second, 0);
	
	switch (GET_OPERAND_SIZE(calc, 0)) {
	case 1: GET_OPERAND(*result, 1).value = operation<uint8_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(result, 1)); break;
	case 2: GET_OPERAND(*result, 1).value = operation<uint16_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(result, 1)); break;
	case 4: GET_OPERAND(*result, 1).value = operation<uint32_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(result, 1)); break;
	case 8: GET_OPERAND(*result, 1).value = operation<uint64_t>(get_immediate_value(&calc, 1), GET_OPCODE(second), get_immediate_value(result, 1)); break;
	}
	
	if (GET_OPERAND_SIZE(*result, 0) == 8 && ((int64_t)GET_OPERAND(*result, 1).value > INT32_MAX || (int64_t)GET_OPERAND(*result, 1).value < INT32_MIN)) {
		GET_OPERAND(*result, 1).size = GET_OPERAND(*result, 0).size;
		GET_OPERAND(*result, 1).type = OP_IMM_64;
	}
	/**********/

	return true;
}

// Obfuscators: MOV
// INPUT:
// MOV X, Y (16/32/64)
// OUTPUT:
// PUSH Y (if 32=>64)
// ADD/SUB/XOR [RSP], #RANDOM
// POP X (if R32=>R64)
// SUB/ADD/XOR X, #RANDOM
int Cleaner::fixPushPopAddSub(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || IS_OPERAND_SP_RELATED(*result, 0, this->mode) || IS_OPERAND_IMM(*result, 0)) return false;

	instruction_info before = getCleanInstructionAt(address);
	if (!((GET_OPCODE(before) == ADD || GET_OPCODE(before) == SUB || GET_OPCODE(before) == XOR) && is_operand_mem_is(&before, 0, NATIVE_SP(this->mode)) && IS_OPERAND_IMM(before, 1))) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || IS_OPERAND_SP_RELATED(next, 0, this->mode) || GET_OPERAND_SIZE(*result, 0) != GET_OPERAND_SIZE(next, 0) || (IS_OPERAND_MEM(*result, 0) && IS_OPERAND_MEM(next, 0))) return false;

	instruction_info after = getCleanInstructionAt(address);
	if (!(((GET_OPCODE(after) == ADD && GET_OPCODE(before) == SUB) || (GET_OPCODE(after) == SUB && GET_OPCODE(before) == ADD) || (GET_OPCODE(after) == XOR && GET_OPCODE(before) == XOR)) && GET_OPERAND_SIZE(before, 0) == GET_OPERAND_SIZE(after, 0) && IS_SAME_OPERANDS(before, 1, after, 1))) return false;
	
	bool fix_64reg = false;
	if (GET_OPERAND_SIZE(before, 0) != GET_OPERAND_SIZE(*result, 0)) {
		if (this->mode != 64 || GET_OPERAND_SIZE(before, 0) != 4 || GET_OPERAND_SIZE(*result, 0) != 8 || !IS_OPERAND_REG(*result, 0) || !IS_OPERAND_REG(next, 0)) return false;
		fix_64reg = true;
	}

	COPY_OPERAND(*result, 1, *result, 0);
	COPY_OPERAND(*result, 0, next, 0);
	GET_OPCODE(*result) = MOV;

	if (fix_64reg) {
		// change to 32bit reg version
		GET_OPERAND(*result, 0).reg = (ud_type_t)(GET_OPERAND(*result, 0).reg - (UD_R_RAX - UD_R_EAX));
		GET_OPERAND(*result, 1).reg = (ud_type_t)(GET_OPERAND(*result, 1).reg - (UD_R_RAX - UD_R_EAX));
		GET_OPERAND(*result, 0).size = 32;
		GET_OPERAND(*result, 1).size = 32;
	}

	return true;
}

// SUB ESP, 4/2 / PUSH RA32/RA16 / PUSH #RANDOM
// MOV [ESP], R32/R16
// if R32/R16 is ESP/SP:
// ADD [ESP], 4/2

// SUB RSP, 8/2 / PUSH #RANDOM (if push random only R64 not esp)
// MOV [RSP], R64/R16
// if R64/R16 is RSP/SP:
//  ADD [RSP], 8/2

// PUSH RA64
// MOV RB32, RANDOM / MOV RA64, RA64
// MOV QWORD [RSP], IMM
int Cleaner::fixPush(uint64_t * address, instruction_info * result) {
	int size;
	bool allow_constant = options[StringHash("fixPush_allowConstants")];
	bool allow_reg = true;
	bool fix_imm_size = false;
	if (GET_OPCODE(*result) == SUB) {
		if (GET_OPERAND(*result, 0).reg != NATIVE_SP(this->mode) || !IS_OPERAND_IMM(*result, 1)) return false;		
		size = get_immediate_value(result, 1);
		if (size != 2 && size != NATIVE_SIZE(this->mode)) return false;
	} else if(GET_OPCODE(*result) == PUSH) {
		if (!IS_OPERAND_IMM(*result, 0) && !IS_OPERAND_REG(*result, 0)) return false;
		size = GET_OPERAND_SIZE(*result, 0);
		if (size == 2 && this->mode == 64) return false;
	} else {
		return false;
	}

	if (GET_OPCODE(*result) == PUSH && IS_OPERAND_REG(*result, 0) && this->mode == 64) {
		allow_reg = false;
		allow_constant = true;
		fix_imm_size = true;
		if (IS_OPERAND_SP(*result, 0)) return false;
		instruction_info next = getCleanInstructionAt(address);
		if (GET_OPCODE(next) != MOV) return false;
		if (!(IS_SAME_OPERANDS(*result, 0, next, 0) && IS_SAME_OPERANDS(next, 0, next, 1))) {
			if (!is_unused_reg(this, &next, 0) || GET_OPERAND_SIZE(next, 0) != 4 || !IS_OPERAND_IMM(next ,1)) return false;
		}
	}

	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != MOV || !is_operand_mem_is(&main, 0, NATIVE_SP(this->mode)) || !((IS_OPERAND_REG(main, 1) && allow_reg) || (IS_OPERAND_IMM(main, 1) && allow_constant)) || GET_OPERAND_SIZE(main, 0) != size) return false;
	
	if (IS_OPERAND_SP(main, 1)) {
		instruction_info next = getCleanInstructionAt(address);
		if (GET_OPCODE(next) != ADD || !IS_SAME_OPERANDS(next, 0, main, 0) || !IS_OPERAND_IMM(next, 1)) return false;
	}
	
	REMOVE_OPERAND(*result, 1);
	COPY_OPERAND(*result, 0, main, 1);
	SET_OPCODE(*result, PUSH);

	if (fix_imm_size) {
		GET_OPERAND(*result, 0).size = 64;
	}

	return true;
}

// MOV R32/R16, [esp]
// if R isn't esp/sp:
// ADD ESP, 4/2
int Cleaner::fixPop(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != MOV || !is_operand_mem_is(result, 1, NATIVE_SP(this->mode)) || !IS_OPERAND_REG(*result, 0)) return false;
	int size = GET_OPERAND_SIZE(*result, 0);
	if (size != 2 && size != NATIVE_SIZE(this->mode)) return false;
	
	if (!IS_OPERAND_SP(*result, 0)) {
		instruction_info next = getCleanInstructionAt(address);
		if (GET_OPCODE(next) != ADD || GET_OPERAND(next, 0).reg != NATIVE_SP(this->mode) || !IS_OPERAND_IMM(next, 1) || get_immediate_value(&next, 1) != size) return false;
	}
	
	REMOVE_OPERAND(*result, 1);
	SET_OPCODE(*result, POP);

	return true;
}

// Obfuscators: XCHG
// XCHG X/Y
// =>
// XOR X, Y
// XOR Y, X
// XOR X, Y
int Cleaner::fixXorXorXor(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != XOR || IS_OPERAND_SP(*result, 0) || IS_OPERAND_IMM(*result, 1) || IS_OPERAND_SP(*result, 1)) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != XOR || !IS_SAME_OPERANDS(next, 0, *result, 1) || !IS_SAME_OPERANDS(next, 1, *result, 0)) return false;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != XOR || !IS_SAME_OPERANDS(next, 0, *result, 0) || !IS_SAME_OPERANDS(next, 1, *result, 1)) return false;

	SET_OPCODE(*result, XCHG);
	return true;
}

// Obfuscators: XCHG
// XCHG R32/R16, [esp+X]
// =>
// PUSH R32/R16
// PUSH [esp+X+4/2]
// POP R32/R16
// POP [esp+X]

// PUSH R32/R16
// PUSH [esp+X+4/2]
// POP R32/R16
// POP [esp+X]
int Cleaner::fixPushMovPop(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || IS_OPERAND_SP(*result, 0) || IS_OPERAND_IMM(*result, 0)) return false;
	
	// TODO: Is it needed? because it shouldn't happen
	bool is_esp = IS_OPERAND_MEM_SP(*result, 0, this->mode);
	
	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != MOV || IS_OPERAND_SP(main, 1) || IS_OPERAND_IMM(main, 1)) return false;

	if (IS_OPERAND_MEM_SP(main, 1, this->mode)) {
		GET_OPERAND(main, 1).offset -= GET_OPERAND_SIZE(*result, 0);
	}
	if (is_esp) {
		GET_OPERAND(main, 0).offset -= GET_OPERAND_SIZE(*result, 0);
	} 
	if (!IS_SAME_OPERANDS(*result, 0, main, 0)) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(main, 1, next, 0)) return false;

	COPY_OPERAND(*result, 1, next, 0);
	SET_OPCODE(*result, XCHG);

	return true;
}

// Obfuscators: XCHG
// XCHG a, b
// =>
// PUSH R32/R16
// MOV R8, b (MOV R8, [esp+X+2/4]...)
// MOV b, a (MOV a, [esp+X+2/4] / MOV [esp+X+2/4], b)
// MOV a, R8 (MOV [esp+X+2/4], R8)
// POP R32/R16
int Cleaner::fixXchgByteThruReg(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0)) return false;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != MOV || !is_releated_reg(&first, 0, result, 0) || IS_OPERAND_IMM(first, 1) || GET_OPERAND_SIZE(first, 0) != 1) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != MOV || !IS_SAME_OPERANDS(main, 0, first, 1) || IS_OPERAND_IMM(main, 1)) return false;

	instruction_info third = getCleanInstructionAt(address);
	if (GET_OPCODE(third)!= MOV || !IS_SAME_OPERANDS(first, 0, third, 1) || !IS_SAME_OPERANDS(main, 1, third, 0)) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	if (IS_OPERAND_MEM_SP(main, 1, this->mode)) {
		GET_OPERAND(main, 1).offset -= GET_OPERAND_SIZE(*result, 0);		
	}
	if (IS_OPERAND_MEM_SP(main, 0, this->mode)) {
		GET_OPERAND(main, 0).offset -= GET_OPERAND_SIZE(*result, 0);
	} 

	*result = main;
	SET_OPCODE(*result, XCHG);

	return true;
}

// XCHG [...], R32/R16/R8
// OPERATION R32/R16/R8
// XCHG [...], R32/R16/R8
int Cleaner::fixOperationThruReg(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != XCHG || !IS_OPERAND_REG(*result, 1) || IS_OPERAND_SP(*result, 0) || (this->mode == 64 && GET_OPERAND_SIZE(*result, 1) == 4)) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != NEG && GET_OPCODE(main) != NOT && !is_inc(&main) && !is_dec(&main)) return false;
	if (!IS_SAME_OPERANDS(main, 0, *result, 1)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != XCHG || !((IS_SAME_OPERANDS(next, 0, *result, 0) && IS_SAME_OPERANDS(next, 1, *result, 1)) || (IS_SAME_OPERANDS(next, 0, *result, 1) && IS_SAME_OPERANDS(next, 1, *result, 0)))) return false;

	SET_OPCODE(*result, GET_OPCODE(main));
	REMOVE_OPERAND(*result, 1);

	return true;
}
int Cleaner::fixOperationThruReg2(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != XCHG || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0) || (this->mode == 64 && GET_OPERAND_SIZE(*result, 0) == 4)) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != NEG && GET_OPCODE(main) != NOT && !is_inc(&main) && !is_dec(&main)) return false;
	if (!IS_SAME_OPERANDS(main, 0, *result, 0)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != XCHG || !((IS_SAME_OPERANDS(next, 0, *result, 0) && IS_SAME_OPERANDS(next, 1, *result, 1)) || (IS_SAME_OPERANDS(next, 0, *result, 1) && IS_SAME_OPERANDS(next, 1, *result, 0)))) return false;

	SET_OPCODE(*result, GET_OPCODE(main));
	COPY_OPERAND(*result, 0, *result, 1);
	REMOVE_OPERAND(*result, 1);

	return true;
}

// This handler is to fix a rare deobfuscation bug, when there are the same xchg twice nested, for example:
//
// xchg ebp, eax
// xchg ebp, eax
// not ebp
// xchg ebp, eax
// sub eax, 0xffffffff
// xchg ebp, eax
//
// Since we devirtualize depth first, we will get rid of the second xchg/xchg first, so we will stay with:
// xchg ebp, eax
// xchg ebp, eax
// neg ebp
//
// It is ok to get ride of it

// XCHG [...], R32/R16/R8
// XCHG [...], R32/R16/R8
int Cleaner::fixOperationXchgXchg(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != XCHG || !IS_OPERAND_REG(*result, 1) || IS_OPERAND_SP(*result, 0) || (this->mode == 64 && GET_OPERAND_SIZE(*result, 1) == 4)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != XCHG || !((IS_SAME_OPERANDS(next, 0, *result, 0) && IS_SAME_OPERANDS(next, 1, *result, 1)) || (IS_SAME_OPERANDS(next, 0, *result, 1) && IS_SAME_OPERANDS(next, 1, *result, 0)))) return false;

	// So let's just ignore it and return the next opcode, which shouls be our "main"
	*result = getCleanInstructionAt(address);

	return true;
}

// PUSH [...]
// OPERATION [esp]
// POP [...]
int Cleaner::fixOperationThruStack(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || IS_OPERAND_IMM(*result, 0)) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (IS_OPERAND(main, 1) && !is_inc(&main) && !is_dec(&main)) return false;
	if (GET_OPCODE(main) == PUSH || GET_OPCODE(main) == POP) return false; // TODO: is needed?
	if (GET_OPERAND_SIZE(main, 0) != GET_OPERAND_SIZE(*result, 0) || !is_operand_mem_is(&main, 0, NATIVE_SP(this->mode))) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	SET_OPCODE(*result, GET_OPCODE(main));

	return true;
}

// PUSH R32/R16
// OPERATION BYTE [esp]/[esp+1]
// POP R32/R16
int Cleaner::fixOperationThruStackByte(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0)) return false;
	int reg = GET_OPERAND(*result, 0).reg;
	int new_reg = get_register_group(reg) + UD_R_AL + ((get_register_group(reg) < 4) ? 0 : 4);

	instruction_info main = getCleanInstructionAt(address);
	if ((IS_OPERAND(main, 1) && !is_inc(&main) && !is_dec(&main)) || GET_OPERAND_SIZE(main, 0) != 1 || !IS_OPERAND_MEM(main, 0)) return false;
	if (GET_OPCODE(main) == PUSH || GET_OPCODE(main) == POP) return false; // TODO: is needed?
	if (is_operand_mem_is(&main, 0, NATIVE_SP(this->mode))) {
	} else if (is_operand_mem_is(&main, 0, NATIVE_SP(this->mode), UD_NONE, 0, 1)) {
		if (get_register_group(reg) >= 4) return false;
		new_reg += 4;
	} else {
		return false;
	}

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	SET_OPCODE(*result, GET_OPCODE(main));
	GET_OPERAND(*result, 0).reg = (ud_type)new_reg;
	GET_OPERAND(*result, 0).size = 8;

	return true;
}

// TODO: in 64 mode it seems to also accept mem. It seesm like a bug, to check.
// PUSH RA32/RA16
// MOV RA8, R8
// OPERATION RA8
// MOV R8, RA8
// POP RA32/RA16
int Cleaner::fixOperationThruRegByte(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0)) return false;
	int reg = GET_OPERAND(*result, 0).reg;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != MOV || GET_OPERAND_SIZE(first, 0) != 1 || !is_releated_reg(&first, 0, result, 0) || !IS_OPERAND_REG(first, 1)) return false;

	instruction_info main = getCleanInstructionAt(address);
	if ((IS_OPERAND(main, 1) && !is_inc(&main) && !is_dec(&main)) || !IS_SAME_OPERANDS(main, 0, first, 0)) return false;
	if (GET_OPCODE(main) == PUSH || GET_OPCODE(main) == POP) return false; // TODO: is needed?
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != MOV || !IS_SAME_OPERANDS(next, 0, first, 1) || !IS_SAME_OPERANDS(next, 1, first, 0)) return false;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	*result = main;
	COPY_OPERAND(*result, 0, first, 1); 

	return true;
}

// PUSH R32/R16
// MOV R32/R16/R8, CONSTANT
// OPERATION a, R32/R16/R8
// POP R32/R16

// PUSH R32/R16
// MOV R32/R16/R8, CONSTANT
// OPERATION [esp+X+2/4], R32/R16/R8
// POP R32/R16

// INPUT:
// OPERATION [RSP+X], R64/R16
// OUTPUT:
// PUSH RA64/RA16
// MOV RA64/RA16, R64/R16
// OPERATION [RSP+X+8/2], RA64/RA16
// POP RA64/RA16
int Cleaner::fixOperationConstantThruReg(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0)) return false;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != MOV || !is_releated_reg(&first, 0, result, 0) || GET_OPERAND_SIZE(first, 0) > GET_OPERAND_SIZE(*result, 0) || !(IS_OPERAND_IMM(first, 1) || 
		(this->mode == 64 && IS_OPERAND_REG(first, 1) && !IS_OPERAND_SP(first, 1) && !is_releated_reg(&first, 0, &first, 1) && GET_OPERAND_SIZE(first, 0) == GET_OPERAND_SIZE(*result, 0)))) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (!IS_OPERAND(main, 1)|| IS_OPERAND_SP(main, 0) || !IS_SAME_OPERANDS(main, 1, first, 0)) return false;
	bool is_esp = IS_OPERAND_MEM_SP(main, 0, this->mode);

	// If it uses reg, it must be stack operation
	if (IS_OPERAND_REG(first, 1) && !is_esp) return false;

	// x64 limitation
	bool fix_size = false;
	if (IS_OPERAND_IMM(first, 1) && GET_OPERAND_SIZE(first, 1) == 8 && GET_OPCODE(main) != MOV) {
		int64_t val = get_immediate_value(&first, 1);
		if (val >= INT32_MIN && val <= INT32_MAX) {
			// It can be 32bit number
			fix_size = true;
		} else return false;
	}

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	int size = GET_OPERAND_SIZE(*result, 0);
	*result = main;
	COPY_OPERAND(*result, 1, first, 1); 
	if (is_esp) {
		GET_OPERAND(*result, 0).offset -= size;
	}

	if (fix_size) {
		GET_OPERAND(*result, 1).size = 32;
		GET_OPERAND(*result, 1).type = OP_IMM_32;
	}
	/**********/

	return true;
}


int Cleaner::fixOperationConstantThruRegUnusedRegs(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != MOV || !is_unused_reg(this, result, 0) || !IS_OPERAND_IMM(*result, 1)) return false;
	
	instruction_info main = getCleanInstructionAt(address);
	if (!IS_OPERAND(main, 1) || IS_OPERAND_SP_RELATED(main, 0, this->mode) || !IS_SAME_OPERANDS(main, 1, *result, 0)) return false;
	
	bool fix_size = false;
	// x64 limitation
	if (GET_OPERAND_SIZE(*result, 1) == 8 && GET_OPCODE(main) != MOV) {
		int64_t val = get_immediate_value(result, 1);
		if (val >= INT32_MIN && val <= INT32_MAX) {
			// It can be 32bit number
			fix_size = true;
		} else return false;
	}

	uint64_t last_address = *address;
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) == POP && is_releated_reg(&next, 0, result, 0)) return false;
	
	while ((GET_OPCODE(next) == ADD || GET_OPCODE(next) == SUB || GET_OPCODE(next) == XOR) && is_releated_reg(&next, 0, result, 0)) {
		last_address = *address;
		next = getCleanInstructionAt(address);
	}

	*address = last_address;
	
	COPY_OPERAND(main, 1, *result, 1);
	*result = main;

	if (fix_size) {
		GET_OPERAND(*result, 1).size = 32;
		GET_OPERAND(*result, 1).type = OP_IMM_32;
	}
	/**********/

	return true;
}

// OPERATION ESP/SP, CONSTANT
// =>
// PUSH REG32/REG16
// MOV REG32/REG16, ESP/SP
// ADD REG32/REG16, 4/2
// OPERATION REG32/REG16, CONSTANT
// XCHG REG32/REG16, [ESP]
// POP ESP/SP
int Cleaner::fixOperationConstantOnEsp(uint64_t * address, instruction_info * result) {
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0)) return false;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != MOV || !IS_SAME_OPERANDS(first, 0, *result, 0) || !IS_OPERAND_SP(first, 1)) return false;

	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != ADD || !IS_SAME_OPERANDS(next, 0, *result, 0) || !IS_OPERAND_IMM(next, 1) || get_immediate_value(&next, 1) != GET_OPERAND_SIZE(*result, 0)) return false;
	
	instruction_info main = getCleanInstructionAt(address);
	if (!IS_OPERAND(main, 1) || !IS_SAME_OPERANDS(main, 0, *result, 0) || !IS_OPERAND_IMM(main, 1)) return false;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != XCHG) return false;
	if (IS_SAME_OPERANDS(next, 0, *result, 0) && is_operand_mem_is(&next, 1, NATIVE_SP(this->mode)));
	else if (IS_SAME_OPERANDS(next, 1, *result, 0) && is_operand_mem_is(&next, 0, NATIVE_SP(this->mode)));
	else return false;

	instruction_info last = getCleanInstructionAt(address);
	if (GET_OPCODE(last) != POP || !IS_SAME_OPERANDS(last, 0, first, 1)) return false;

	*result = main;
	COPY_OPERAND(*result, 0, last, 0); 

	return true;
}

// PUSH R32
// PUSH R'32
// MOV R32, CONSTANT
// MOV R'32, ESP
// OPERATION [R'32+X+8], R32/R16/R8
// POP R'32
// POP R32
int Cleaner::fixOperationConstantThruRegOnStack(uint64_t * address, instruction_info * result) {
	if (!options[StringHash("fixDoubleStackOperation")]) return false;
	return false; 
	/*
	if (GET_OPCODE(*result) != PUSH || result->operands[0] != OP_REG || IS_OPERAND_IS(result, 0, ESP) || result->operands_info[0].reg.reg < REG_EAX) return false;

	instruction_info first = getCleanInstructionAt(address);
	if (GET_OPCODE(first) != PUSH || first.operands[0] != OP_REG || IS_OPERAND_IS(result, 0, ESP) || GET_OPERAND(first, 0).reg < REG_EAX || GET_OPERAND(first, 0).reg == result->operands_info[0].reg.reg) return false;

	instruction_info second = getCleanInstructionAt(address);
	if (GET_OPCODE(second) != MOV || !IS_SAME_OPERANDS(second, 0, *result, 0) || !IS_OPERAND_IS(&second, 1, CONSTANTS)) return false;

	instruction_info third = getCleanInstructionAt(address);
	if (third.instruction != MOV || !IS_SAME_OPERANDS(third, 0, first, 0) || !IS_OPERAND_IS(&third, 1, ESP)) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (main.operands[1] == OP_NONE || !IS_SAME_OPERANDS(main, 1, second, 0) || (main.operands[0] & 0xF0) != OPH_ADDRESS || main.operands_info[0].address.main_reg != GET_OPERAND(first, 0).reg) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, first, 0)) return false;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	*result = main;
	COPY_OPERAND(*result, 1, second, 1); 
	result->operands_info[0].address.main_reg = REG_ESP;
	result->operands_info[0].address.constant -= 8;

	return true;*/
}

// LODSB/LODSW/LODSD/LODSQ
// =>
// MOV AL/AX/EAX/RAX, [RSI]
// ADD RSI, 1/2/4/8
int Cleaner::fixLods(uint64_t * address, instruction_info * result) {
	if (!options[StringHash("fixLods")]) return false;
	if (this->mode != 64) return false;
	if (GET_OPCODE(*result) != MOV || !IS_OPERAND_REG(*result, 0) || !IS_OPERAND_MEM(*result, 1) || GET_OPERAND(*result, 1).offset != 0 || \
		get_register_group(GET_OPERAND(*result, 0).reg) != get_register_group(UD_R_RAX) || \
		!((get_register_group(GET_OPERAND(*result, 1).base) == get_register_group(UD_R_RSI) && GET_OPERAND(*result, 1).index == UD_NONE) || \
		(get_register_group(GET_OPERAND(*result, 1).index) == get_register_group(UD_R_RSI) && GET_OPERAND(*result, 1).base == UD_NONE))) return false;

	int size = GET_OPERAND_SIZE(*result, 0);
	instruction_info next = getCleanInstructionAt(address);
	if (!((size == 1 && is_inc(&next)) || (GET_OPCODE(next) == ADD && IS_OPERAND_REG(next, 0) && IS_OPERAND_IMM(next, 1) && get_register_group(GET_OPERAND(next, 0).reg) == get_register_group(UD_R_RSI) && get_immediate_value(&next, 1) == size))) return false;
	
	REMOVE_OPERAND(*result, 0);
	REMOVE_OPERAND(*result, 1);
	switch (size) {
	case 1: SET_OPCODE(*result, LODSB); return true;
	case 2: SET_OPCODE(*result, LODSW); return true;
	case 4: SET_OPCODE(*result, LODSD); return true;
	case 8: SET_OPCODE(*result, LODSQ); return true;
	default: return false;
	}
}

// MOVZX RA64/RA32, RB8
// =>
// PUSH RA64
// MOV qword [RSP], 0
// MOV byte [RSP], RB8
// POP RA64

// MOVZX RA16, RB8
// =>
// PUSH RA16
// MOV byte [RSP+1], 0
// MOV byte [RSP], RB8
// POP RA16
int Cleaner::fixMovzx(uint64_t * address, instruction_info * result) {
	if (this->mode != 64) return false;
	if (GET_OPCODE(*result) != PUSH || !IS_OPERAND_REG(*result, 0) || IS_OPERAND_SP(*result, 0)) return false;
	int size = GET_OPERAND_SIZE(*result, 0);
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != MOV || !IS_OPERAND_MEM_SP(next, 0, this->mode) || !IS_OPERAND_IMM(next, 1) || get_immediate_value(&next, 1) != 0) return false;
	if (size == 2) {
		if (GET_OPERAND_SIZE(next, 0) != 1 || !is_operand_mem_is(&next, 0, NATIVE_SP(this->mode), UD_NONE, 0, 1)) return false;
	} else if (size == 8) {
		if (GET_OPERAND_SIZE(next, 0) != 8 || !is_operand_mem_is(&next, 0, NATIVE_SP(this->mode))) return false;
	} else return false;
	
	instruction_info main = getCleanInstructionAt(address);
	if (GET_OPCODE(main) != MOV || !is_operand_mem_is(&main, 0, NATIVE_SP(this->mode)) || !IS_OPERAND_REG(main, 1) || GET_OPERAND_SIZE(main, 1) != 1) return false;
	
	instruction_info last = getCleanInstructionAt(address);
	if (GET_OPCODE(last) != POP || !IS_SAME_OPERANDS(last, 0, *result, 0)) return false;

	// We can't distinguish between MOVZX RA32, RB16 to MOVZX RA64, RB16 (they behave and implmented here the same). So we will assumme R64.
	SET_OPCODE(*result, MOVZX);
	COPY_OPERAND(*result, 1, main, 1);

	return true;
}  

typedef int(Cleaner::*cleaner_func)(uint64_t *, instruction_info *);

cleaner_func cleaners[] = {//&Cleaner::cleanIncDec,
						   &Cleaner::mergeMemorySplit,
						   &Cleaner::clearJunkAddSub,
						   &Cleaner::clearNotIncDecNot,
						   &Cleaner::clear0Minus,
						   &Cleaner::clear0MinusThruReg,
						   &Cleaner::clearMovConstant,
						   &Cleaner::fixPushPop,
						   &Cleaner::fixPushMovMovPop,
						   &Cleaner::fixPushMovMovCalcPop,
						   &Cleaner::fixPush,
						   &Cleaner::fixPop,
						   &Cleaner::fixXorXorXor,
						   &Cleaner::fixPushMovPop,
						   &Cleaner::fixXchgByteThruReg,
						   &Cleaner::fixOperationThruReg,
						   &Cleaner::fixOperationThruReg2,
						   &Cleaner::fixOperationThruStack,
						   &Cleaner::fixOperationThruStackByte,
						   &Cleaner::fixOperationThruRegByte,
						   &Cleaner::fixOperationConstantThruReg,
						   &Cleaner::fixOperationConstantOnEsp,

						   // It needs to be after operation thru stack
						   &Cleaner::fixPushPopAddSub,

						   &Cleaner::fixOperationXchgXchg,
						   
						   &Cleaner::fixLods,
						   &Cleaner::fixMovzx,
						   
						   &Cleaner::fixPushMovMovPopUnusedRegs,
						   &Cleaner::fixPushMovMovCalcPopUnusedRegs,
						   &Cleaner::fixOperationConstantThruRegUnusedRegs};

						   //&Cleaner::fixOperationConstantThruRegOnStack};

instruction_info Cleaner::getInstructionAt(uint64_t * address) {
	instruction_info result;
	instruction_init(&result, this->mode);
	unsigned char buffer[20] = {0};
	int buffer_size = reader(opaque, *address, buffer, sizeof(buffer));
	if (!buffer_size) {
		throw std::runtime_error("Failed to read data");
	}
	if (instruction_disassemble(&result, buffer, buffer_size, *address)) {
		throw std::runtime_error("Failed to dissassemble");
	}
	*address += result.size;
	return result;
}
 #define CALL_MEMBER_FN(object,ptrToMember)  ((object).*(ptrToMember))

instruction_info Cleaner::getCleanInstructionAt(uint64_t * address, bool top) {
	if (cache.find(*address) != cache.end()) {
		instruction_info res = cache[*address].first;
		*address = cache[*address].second;
		return res;
	}
	if (*address == options[StringHash("end_address")]) {
		instruction_info bad_instruction;
		instruction_init(&bad_instruction, this->mode);
		return bad_instruction;
	}
	uint64_t original_address = *address;
	bool changed = true;
	instruction_info result = getInstructionAt(address);
	if ((options[StringHash("ignore_jumps")] || (options[StringHash("ignore_nontop_jumps")] && !top)) && GET_OPCODE(result) == JMP && IS_OPERAND_JIMM(result, 0)) {
		*address = get_immediate_value(&result, 0);
		if (*address == options[StringHash("end_address")]) {
			return result;
		}
		return getCleanInstructionAt(address);
	} else if (options[StringHash("ignore_calls")] && GET_OPCODE(result) == CALL && IS_OPERAND_JIMM(result, 0)) {
		uint64_t new_address = get_immediate_value(&result, 0);
		GET_OPERAND(result, 0).value = *address;
		GET_OPERAND(result, 0).type = (this->mode == 64) ? OP_IMM_64 : OP_IMM_32;
		SET_OPCODE(result, PUSH);
		*address = new_address;
	} 
	while (changed) {
		changed = false;
		if (is_math_op(GET_OPCODE(result)) || GET_OPCODE(result) == PUSH || GET_OPCODE(result) == POP || GET_OPCODE(result) == MOV || GET_OPCODE(result) == XCHG) {
			for (int i = 0; i < sizeof(cleaners) / sizeof(cleaner_func); ++i) {
				uint64_t current_address = *address;
				if (CALL_MEMBER_FN(*this, cleaners[i])(&current_address, &result)) {
					*address = current_address;
					changed = true;
					break;
				}
			}
		}
	}

	cache[original_address] = std::pair<instruction_info, uint64_t>(result, *address);
	return result;
}


Cleaner::Cleaner(reader_f reader, int mode, void * opaque) : reader(reader), mode(mode), opaque(opaque) {	
	options[StringHash("fixDoubleStackOperation")] = false;
	options[StringHash("fixPush_allowConstants")] = false;
	options[StringHash("fixLods")] = false;

	options[StringHash("ignore_jumps")] = true;
	options[StringHash("ignore_nontop_jumps")] = false;
	options[StringHash("ignore_calls")] = false;
	options[StringHash("fix_inc_dec")] = true;
	
	options[StringHash("end_address")] = 0;
}

/*
// pusha
// operation reg, reg/imm
// jc ..
// popa
int Cleaner::cleanPushaPopa(uint64_t * address, instruction_info * result) {
	if (!options[StringHash("cleanPushaPopa")]) return false;
	if (GET_OPCODE(*result) != PUSHAD) return false;

	int start_address = *address;
	int max_address = start_address;

	instruction_info op = getCleanInstructionAt(address);
	while (op.instruction != POPAD) {
		if (op.instruction >= JA && op.instruction <= JS) {
			// this is dummy conditional jump
			if (
		}
	}
	if (GET_OPCODE(first) != PUSH || first.operands[0] != OP_REG || IS_OPERAND_IS(result, 0, ESP) || GET_OPERAND(first, 0).reg < REG_EAX || GET_OPERAND(first, 0).reg == result->operands_info[0].reg.reg) return false;

	instruction_info second = getCleanInstructionAt(address);
	if (GET_OPCODE(second) != MOV || !IS_SAME_OPERANDS(second, 0, *result, 0) || !IS_OPERAND_IS(&second, 1, CONSTANTS)) return false;

	instruction_info third = getCleanInstructionAt(address);
	if (third.instruction != MOV || !IS_SAME_OPERANDS(third, 0, first, 0) || !IS_OPERAND_IS(&third, 1, ESP)) return false;

	instruction_info main = getCleanInstructionAt(address);
	if (main.operands[1] == OP_NONE || !IS_SAME_OPERANDS(main, 1, second, 0) || (main.operands[0] & 0xF0) != OPH_ADDRESS || main.operands_info[0].address.main_reg != GET_OPERAND(first, 0).reg) return false;
	
	instruction_info next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, first, 0)) return false;

	next = getCleanInstructionAt(address);
	if (GET_OPCODE(next) != POP || !IS_SAME_OPERANDS(next, 0, *result, 0)) return false;

	*result = main;
	COPY_OPERAND(*result, 1, second, 1); 
	result->operands_info[0].address.main_reg = REG_ESP;
	result->operands_info[0].address.constant -= 8;

	return true;
}

0x01338278*/