# !/usr/bin/env python3
from multiprocessing import Value

import font
import re
from timers import TimerProcess, BeepTimerProcess

PROGRAM_START = 0x200
V_MAX = 0xFF


class CHIP8Emulator:
    memory = bytearray(4096)

    for i in range(16):
        memory[5 * i:5 * (i + 1)] = font.FONT[i]

    v_reg = [0] * 16
    i_reg = 0
    program_counter = 0
    stack_pointer = 0
    stack = [0] * 16

    delay_timer_value = Value('i', 0)
    delay_timer = TimerProcess(delay_timer_value)

    sound_timer_value = Value('i', 0)
    sound_timer = BeepTimerProcess(delay_timer_value)

    screen = [[False] * 32] * 4

    def load_program(self, program_bytes):
        self.memory[PROGRAM_START:] = program_bytes

    programs = dict()

    def program(self, pattern):
        regex = re.compile(pattern)

        def wrap(f):
            self.programs[regex] = f
            return f

        return wrap

    def execute(self, program):
        for regex, program_func in self.programs:
            match = regex.fullmatch(program)
            if match:
                program(*[int(i, base=16) for i in match.groups()])

    @program(r"00E0")
    def clear_screen(self):
        self.screen = [[False] * 32] * 4

    @program(r"00EE")
    def return_back(self):
        if self.stack_pointer < 0:
            raise IndexError
        self.program_counter = self.stack[self.stack_pointer]
        self.stack_pointer -= 1

    @program(r"1([0-9A-F]{3})")
    def jump(self, location):
        self.program_counter = location

    @program(r"2([0-9A-F]{3})")
    def call(self, location):
        self.stack_pointer += 1
        self.stack[self.stack_pointer] = self.program_counter
        self.program_counter = location

    @program(r"3([0-9A-F])([0-9A-F]{2})")
    def skip_if_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] == comparing_value:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(r"4([0-9A-F])([0-9A-F]{2})")
    def skip_if_not_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] != comparing_value:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(r"5([0-9A-F])([0-9A-F])0")
    def skip_if_regs_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] == self.v_reg[reg_num_2]:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(r"6([0-9A-F])([0-9A-F]{2})")
    def set(self, reg_num, value):
        self.v_reg[reg_num] = value

    @program(r"7([0-9A-F])([0-9A-F]{2})")
    def increment(self, reg_num, value):
        self.v_reg[reg_num] += value

    @program(r"8([0-9A-F])([0-9A-F])0")
    def set_reg(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_2]

    @program(r"8([0-9A-F])([0-9A-F])1")
    def set_reg_or(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] | self.v_reg[reg_num_2]

    @program(r"8([0-9A-F])([0-9A-F])2")
    def set_reg_and(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] & self.v_reg[reg_num_2]

    @program(r"8([0-9A-F])([0-9A-F])3")
    def set_reg_xor(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] ^ self.v_reg[reg_num_2]

    @program(r"8([0-9A-F])([0-9A-F])4")
    def sum_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] + self.v_reg[reg_num_2]
        self.v_reg[0xF] = result & (V_MAX + 1)
        self.v_reg[reg_num_1] = result & V_MAX

    @program(r"8([0-9A-F])([0-9A-F])5")
    def sub_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] - self.v_reg[reg_num_2]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    @program(r"8([0-9A-F])([0-9A-F])6")
    def rshift_reg(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 1
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] >> 1

    @program(r"8([0-9A-F])([0-9A-F])7")
    def subn_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_2] - self.v_reg[reg_num_1]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    @program(r"8([0-9A-F])([0-9A-F])E")
    def subn_regs(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 0x100
        self.v_reg[reg_num_1] = (self.v_reg[reg_num_1] << 1) & V_MAX

    @program(r"9([0-9A-F])([0-9A-F])0")
    def skip_if_regs_not_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] != self.v_reg[reg_num_2]:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(r"1([0-9A-F]{3})")
    def set_i(self, value):
        self.i_reg = value
