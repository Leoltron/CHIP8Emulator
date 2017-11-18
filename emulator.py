# !/usr/bin/env python3
import random
from multiprocessing import Value

import font
import re

from screen import CHIP8ScreenApp, SCREEN_HEIGHT, SCREEN_WIDTH
from timers import TimerProcess, BeepTimerProcess

PROGRAM_START = 0x200
V_MAX = 0xFF


def program(programs, pattern):
    regex = re.compile(pattern)

    def wrap(f):
        programs[regex] = f
        return f

    return wrap


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
    delay_timer = TimerProcess(1 / 60, delay_timer_value)

    sound_timer_value = Value('i', 0)
    sound_timer = BeepTimerProcess(1 / 60, delay_timer_value)

    screen = [[False] * SCREEN_HEIGHT] * SCREEN_WIDTH

    def __init__(self, screen_app: CHIP8ScreenApp):
        self.screen_app = screen_app

    def load_program(self, program_bytes):
        self.memory[PROGRAM_START:] = program_bytes

    programs = dict()

    def execute(self, program_code_str: str):
        for regex, program_func in self.programs:
            match = regex.fullmatch(program_code_str)
            if match:
                program_func(self, *[int(i, base=16) for i in match.groups()])
                return
        raise ValueError("No program matching " + program_code_str + " found")

    @program(programs, r"00E0")
    def clear_screen(self):
        self.screen = [[False] * SCREEN_HEIGHT] * SCREEN_WIDTH

    @program(programs, r"00EE")
    def return_back(self):
        if self.stack_pointer < 0:
            raise IndexError
        self.program_counter = self.stack[self.stack_pointer]
        self.stack_pointer -= 1

    @program(programs, r"1([0-9A-F]{3})")
    def jump(self, location):
        self.program_counter = location

    @program(programs, r"2([0-9A-F]{3})")
    def call(self, location):
        self.stack_pointer += 1
        self.stack[self.stack_pointer] = self.program_counter
        self.program_counter = location

    @program(programs, r"3([0-9A-F])([0-9A-F]{2})")
    def skip_if_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] == comparing_value:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(programs, r"4([0-9A-F])([0-9A-F]{2})")
    def skip_if_not_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] != comparing_value:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(programs, r"5([0-9A-F])([0-9A-F])0")
    def skip_if_regs_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] == self.v_reg[reg_num_2]:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(programs, r"6([0-9A-F])([0-9A-F]{2})")
    def set(self, reg_num, value):
        self.v_reg[reg_num] = value

    @program(programs, r"7([0-9A-F])([0-9A-F]{2})")
    def increment(self, reg_num, value):
        self.v_reg[reg_num] += value

    @program(programs, r"8([0-9A-F])([0-9A-F])0")
    def set_reg(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_2]

    @program(programs, r"8([0-9A-F])([0-9A-F])1")
    def set_reg_or(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] | self.v_reg[reg_num_2]

    @program(programs, r"8([0-9A-F])([0-9A-F])2")
    def set_reg_and(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] & self.v_reg[reg_num_2]

    @program(programs, r"8([0-9A-F])([0-9A-F])3")
    def set_reg_xor(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] ^ self.v_reg[reg_num_2]

    @program(programs, r"8([0-9A-F])([0-9A-F])4")
    def sum_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] + self.v_reg[reg_num_2]
        self.v_reg[0xF] = result & (V_MAX + 1)
        self.v_reg[reg_num_1] = result & V_MAX

    @program(programs, r"8([0-9A-F])([0-9A-F])5")
    def sub_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] - self.v_reg[reg_num_2]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    @program(programs, r"8([0-9A-F])([0-9A-F])6")
    def rshift_reg(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 1
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] >> 1

    @program(programs, r"8([0-9A-F])([0-9A-F])7")
    def subn_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_2] - self.v_reg[reg_num_1]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    @program(programs, r"8([0-9A-F])([0-9A-F])E")
    def subn_regs(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 0x100
        self.v_reg[reg_num_1] = (self.v_reg[reg_num_1] << 1) & V_MAX

    @program(programs, r"9([0-9A-F])([0-9A-F])0")
    def skip_if_regs_not_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] != self.v_reg[reg_num_2]:
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(programs, r"A([0-9A-F]{3})")
    def set_i(self, value):
        self.i_reg = value

    @program(programs, r"B([0-9A-F]{3})")
    def jump_to_v0_sum(self, value):
        self.program_counter = value + self.v_reg[0]

    @program(programs, r"C([0-9A-F])([0-9A-F]{2})")
    def set_rand_and(self, reg_num, value):
        self.v_reg[reg_num] = random.randint(0, 255) & value

    @program(programs, r"D([0-9A-F])([0-9A-F])([0-9A-F])")
    def draw_sprite(self, vx, vy, sprite_height):
        x = self.v_reg[vx]
        y = self.v_reg[vy]
        collision = False
        for i in range(sprite_height):
            line = self.memory[self.i_reg + i]
            dx = 0
            while line > 0:
                if line & 0b10000000:
                    collision = collision or self.screen_app.switch_pixel(
                        x + dx, y - i)
                line = (line << 1) & 0xff
                dx += 1
        self.v_reg[0xf] = int(collision)

    @program(programs, r"E([0-9A-F])9E")
    def skip_if_pressed(self, key):
        if self.screen_app.is_key_pressed(key):
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(programs, r"E([0-9A-F])A1")
    def skip_if_not_pressed(self, key):
        if not self.screen_app.is_key_pressed(key):
            self.program_counter += 2
        else:
            self.program_counter += 1

    @program(programs, r"F([0-9A-F])07")
    def set_delay_timer_value(self, reg_num):
        with self.delay_timer_value.get_lock():
            self.v_reg[reg_num] = self.delay_timer_value

    @program(programs, r"F([0-9A-F])0A")
    def wait_and_set_pressed_key(self, reg_num):
        self.screen_app.pressed_event.clear()
        self.screen_app.pressed_event.wait()
        self.v_reg[reg_num] = self.screen_app.last_pressed_key

    @program(programs, r"F([0-9A-F])15")
    def set_delay_timer(self, reg_num):
        with self.delay_timer_value.get_lock():
            self.delay_timer_value = self.v_reg[reg_num]

    @program(programs, r"F([0-9A-F])18")
    def set_sound_timer(self, reg_num):
        with self.sound_timer_value.get_lock():
            self.sound_timer_value = self.v_reg[reg_num]

    @program(programs, r"F([0-9A-F])1E")
    def add_vx_to_i(self, reg_num):
        self.i_reg += self.v_reg[reg_num]

    @program(programs, r"F([0-9A-F])29")
    def set_i_to_digit_sprite(self, reg_num):
        self.i_reg = self.v_reg[reg_num] * 5

    @program(programs, r"F([0-9A-F])33")
    def store_in_i_as_bcd(self, reg_num):
        value = self.v_reg[reg_num]
        hundreds = value % 1000 / 100
        tens = value % 100 / 10
        ones = value % 10
        self.memory[self.i_reg] = hundreds
        self.memory[self.i_reg + 1] = tens
        self.memory[self.i_reg + 2] = ones

    @program(programs, r"F([0-9A-F])55")
    def write_v_to_i(self, reg_end_num):
        for i in range(reg_end_num):
            self.memory[self.i_reg + i] = self.v_reg[i]

    @program(programs, r"F([0-9A-F])65")
    def read_v_from_i(self, reg_end_num):
        for i in range(reg_end_num):
            self.v_reg[i] = self.memory[self.i_reg + i]
