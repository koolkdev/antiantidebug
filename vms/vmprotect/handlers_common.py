from collections import namedtuple
import itertools
import re

HANDLER = namedtuple("HANDLER", ["NAME", "VARS", "CODE"])

HANDLERS = [
HANDLER(
"STACK_POP_#SIZE#_REG",
{"SIZE": [1, 2, 4, 8]},
"""
READ_PARAM 1
mov {R:dx:#S_SIZE#}, @STACK_LOAD(#S_SIZE#)@
BALANCE_STACK
mov {S:#SIZE#} [{R:ax}+{R:di}], {R:dx:#SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_REG",
{"SIZE": [1, 2]},
"""
READ_PARAM 1
mov {R:ax:#SIZE#}, {S:#SIZE#} [{R:ax}+{R:di}]
BALANCE_STACK
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_REG",
{"SIZE": [4, 8]},
"""
READ_PARAM 1
mov {R:dx:#SIZE#}, {S:#SIZE#} [{R:ax}+{R:di}]
BALANCE_STACK
mov @STACK_STORE(#SIZE#)@, {R:dx:#SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_IMM",
{"SIZE": [1, 2, 4, 8]},
"""
READ_PARAM #SIZE#
BALANCE_STACK
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_POPMEMSP",
{"SIZE": [1, 2, 4, 8]},
"""
mov {R:dx}, @STACK_LOAD(@SIZE_NATIVE@)@
BALANCE_STACK
mov {R:ax:#SIZE#}, {S:#SIZE#} [{R:dx}]
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_POPMEMSP",
{"SIZE": [1, 2, 4, 8]},
"""
mov {R:ax}, @STACK_LOAD(@SIZE_NATIVE@)@
BALANCE_STACK
mov {R:ax:#SIZE#}, {S:#SIZE#} [{R:ax}]
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_POPMEM#SEG#SP",
{"SIZE": [1, 2, 4, 8],
 "SEG": ["ss", "fs"]},
"""
mov {R:ax}, @STACK_LOAD(@SIZE_NATIVE@)@
BALANCE_STACK
mov {R:ax:#SIZE#}, {S:#SIZE#} #SEG#:[{R:ax}]
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_POPMEM#SEG#SP",
{"SIZE": [1, 2, 4, 8],
 "SEG": ["ss", "fs"]},
"""
mov {R:dx}, @STACK_LOAD(@SIZE_NATIVE@)@
BALANCE_STACK
mov {R:ax:#SIZE#}, {S:#SIZE#} #SEG#:[{R:dx}]
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
"""),

HANDLER(
"STACK_POP_#SIZE#_POPMEMSP",
{"SIZE": [1, 2, 4, 8]},
"""
mov {R:ax}, @STACK_LOAD(@SIZE_NATIVE@)@
mov {R:dx:#SIZE#}, @STACK_LOAD(#SIZE#)@
BALANCE_STACK
mov {S:#SIZE#} [{R:ax}], {R:dx:#SIZE#}
"""),

HANDLER(
"STACK_POP_#SIZE#_POPMEM#SEG#SP",
{"SIZE": [1, 2, 4, 8],
 "SEG": ["ss", "fs"]},
"""
mov {R:ax}, @STACK_LOAD(@SIZE_NATIVE@)@
mov {R:dx:#SIZE#}, @STACK_LOAD(#SIZE#)@
BALANCE_STACK
mov {S:#SIZE#} #SEG#:[{R:ax}], {R:dx:#SIZE#}
"""),

HANDLER(
"STACK_PUSH_#SIZE#_SP",
{"SIZE": [2, 4, 8]},
"""
mov {R:ax}, {R:bp}
BALANCE_STACK
mov @STACK_STORE(#SIZE#)@, {R:ax:#SIZE#}
"""),

HANDLER(
"STACK_POP_#SIZE#_SP",
{"SIZE": [2, 4, 8]},
"""
mov {R:bp:#SIZE#}, @STACK_OP(#SIZE#)@
"""),

HANDLER(
"STACK_ADD_#SIZE#",
{"SIZE": [1, 2, 4, 8]},
"""
mov {R:ax:#SIZE#}, @STACK_LOAD(#SIZE#)@
BALANCE_STACK
add @STACK_OP(#SIZE#)@, {R:ax:#SIZE#}
pushf{SB}
pop @STACK_STORE({N})@
"""),

HANDLER(
"STACK_#OP#_#SIZE#",
{"SIZE": [1, 2, 4, 8],
 "OP": ["shl", "shr"]},
"""
mov {R:ax:#SIZE#}, @STACK_LOAD(#SIZE#)@
mov cl, @STACK_LOAD(1)@
BALANCE_STACK
#OP# {R:ax:#SIZE#}, cl
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
pushf{SB}
pop @STACK_STORE({N})@
"""),

HANDLER(
"STACK_#OP#_#SIZE#",
{"SIZE": [1, 2, 4, 8],
 "OP": ["rcr", "rcl"]},
"""
mov {R:ax:#SIZE#}, @STACK_LOAD(#SIZE#)@
mov cx, @STACK_LOAD(2)@
BALANCE_STACK
shr ch, 0x1
#OP# {R:ax:#SIZE#}, cl
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
pushf{SB}
pop @STACK_STORE({N})@
"""),

HANDLER(
"STACK_#OP#_#SIZE#",
{"SIZE": [1, 2, 4, 8],
 "OP": ["imul"]},
"""
mov {R:dx:#SIZE#}, @STACK_LOAD(#SIZE#)@
mov {R:ax:#SIZE#}, @STACK_LOAD(#SIZE#)@
BALANCE_STACK
#OP# {R:dx:#SIZE#}
mov @STACK_STORE_R1(#S_SIZE#)@, {R:dx:#S_SIZE#}
mov @STACK_STORE_R2(#S_SIZE#)@, {R:ax:#S_SIZE#}
pushf{SB}
pop @STACK_STORE({N})@
"""),

HANDLER(
"STACK_AND_NOT_#SIZE#",
{"SIZE": [1,4,8]},
"""
mov {R:ax:#S_SIZE#}, @STACK_LOAD(#S_SIZE#)@
mov {R:dx:#S_SIZE#}, @STACK_LOAD(#S_SIZE#)@
BALANCE_STACK
not {R:ax:#SIZE#}
not {R:dx:#SIZE#}
BALANCE_STACK
and {R:ax:#SIZE#}, {R:dx:#SIZE#}
mov @STACK_STORE(#S_SIZE#)@, {R:ax:#S_SIZE#}
pushf{SB}
pop @STACK_STORE({N})@
"""),

HANDLER(
"STACK_AND_NOT_WORD",
{},
"""
not @STACK_OP(4)@
mov {R:ax:2}, @STACK_LOAD(2)@
BALANCE_STACK
and @STACK_OP(2)@, {R:ax:2}
pushf{SB}
pop @STACK_STORE({N})@
"""),

]


def match_handler(mode, handlers, handler):
    for handler_name, vars, code in handlers:
        #if len([x for x in code.splitlines() if x.strip()]) != len(handler.insts):
        #    continue
        for vars_values in itertools.product(*vars.values()):
            if mode.native_size() == 4 and 8 in vars_values:
                continue
            lines = []
            for line in code.splitlines():
                line = line.strip()
                if line:
                    for i in xrange(len(vars)):
                        line = line.replace("#%s#" % vars.keys()[i], str(vars_values[i]))
                        if vars_values[i] == 1:
                            # Minimum stack size
                            line = line.replace("#S_%s#" % vars.keys()[i], "2")
                        else:
                            line = line.replace("#S_%s#" % vars.keys()[i], str(vars_values[i]))
                    line = line.replace("@SIZE_NATIVE@", str(mode.mode>>3))
                    lines.append(mode.translate(line))
            match = True
            stack_pos = 0
            j = 0
            for i in xrange(len(lines)):
                line = lines[i]
                if i == 0:
                    if line.startswith("READ_PARAM "):
                        if handler.read is not None:
                            size = int(line.split(" ")[1])
                            if handler.read.size == size and handler.read.extend_size == 0:
                                continue
                            if handler.read.extend_size == size:
                                continue
                        match = False
                        break
                    else:
                        if handler.read is not None:
                            match = False
                            break
                if len(handler.insts) <= j:
                    match = False
                    break
                hinst = handler.insts[j]
                if line == "BALANCE_STACK":
                    if hinst.opcode in ("add", "sub") and hinst.operands[0].is_reg(mode.reg_native("bp")) and hinst.operands[1].is_immediate():
                        if hinst.opcode == "add":
                            stack_pos -= hinst.operands[1].value
                        else:
                            stack_pos += hinst.operands[1].value
                        j += 1
                        continue
                    else:
                        # If no balance needed
                        continue
                res = re.findall(r"@([A-Z0-9_]+)\(([0-9]+)\)@", line)
                assert len(res) <= 1
                if len(res) == 1:
                    op, param = res[0]
                    size = int(param)
                    if op == "STACK_LOAD":
                        if stack_pos == 0:
                            to_replace = "{S:%d} [{R:bp}]" % size
                        else:
                            to_replace = "{S:%d} [{R:bp}+0x%x]" % (size, stack_pos)
                        if size == 1:
                            stack_pos += 2
                        else:
                            stack_pos += size
                    elif op == "STACK_OP":
                        if stack_pos == 0:
                            to_replace = "{S:%d} [{R:bp}]" % size
                        else:
                            to_replace = "{S:%d} [{R:bp}+0x%x]" % (size, stack_pos)
                    elif op == "STACK_STORE":
                        if size == 1:
                            stack_pos -= 2
                        else:
                            stack_pos -= size
                        if stack_pos == 0:
                            to_replace = "{S:%d} [{R:bp}]" % size
                        else:
                            to_replace = "{S:%d} [{R:bp}+0x%x]" % (size, stack_pos)
                    elif op == "STACK_STORE_R1":
                        ts = size
                        if ts == 1:
                            ts = 2
                        stack_pos -= ts
                        if stack_pos - ts == 0:
                            to_replace = "{S:%d} [{R:bp}]" % size
                        else:
                            to_replace = "{S:%d} [{R:bp}+0x%x]" % (size, stack_pos - ts)
                    elif op == "STACK_STORE_R2":
                        ts = size
                        if ts == 1:
                            ts = 2
                        stack_pos -= ts
                        if stack_pos + ts == 0:
                            to_replace = "{S:%d} [{R:bp}]" % size
                        else:
                            to_replace = "{S:%d} [{R:bp}+0x%x]" % (size, stack_pos + ts)
                    else:
                        assert False
                    line = line.replace("@%s(%s)@" % (op, param), mode.translate(to_replace))
                if str(hinst).strip() != line:
                    match = False
                    break
                j += 1
            if j != len(handler.insts) or stack_pos != 0:
                match = False

            if match:
                for i in xrange(len(vars)):
                    if vars_values[i] in [1, 2, 4, 8]:
                        handler_name = handler_name.replace("#%s#" % vars.keys()[i], mode.translate("{S:%d}" % vars_values[i]).upper())
                    else:
                        handler_name = handler_name.replace("#%s#" % vars.keys()[i], vars_values[i].upper())
                handler_name = handler_name.replace("@SIZE_NATIVE@", mode.translate("{S:%d}" % (mode.mode >> 3)).upper())
                return handler_name
    return None
