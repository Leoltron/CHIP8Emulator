# !/usr/bin/env python3
import random
from functools import wraps
from multiprocessing import Value

import font

from screen import CHIP8ScreenApp, SCREEN_HEIGHT, SCREEN_WIDTH
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
    delay_timer = TimerProcess(1 / 60, delay_timer_value)

    sound_timer_value = Value('i', 0)
    sound_timer = BeepTimerProcess(1 / 60, delay_timer_value)

    screen = [[False] * SCREEN_HEIGHT] * SCREEN_WIDTH

    def __init__(self, screen_app: CHIP8ScreenApp):
        self.screen_app = screen_app

    def load_program(self, program_bytes):
        self.memory[PROGRAM_START:] = program_bytes

    def execute(self):
        self.program_counter = 0x200
        while True:
            program_code = (self.memory[self.program_counter] << 8) | \
                           self.memory[self.program_counter + 1]
            self.execute_program(program_code)

    def execute_program(self, program_code, first_hex=None):
        if first_hex is None:
            first_hex = (program_code >> 12) & 0xf
        if not self.programs_by_first_digit[first_hex](self, program_code):
            raise ValueError(
                'Not found program matching ' + hex(program_code)[2:].upper())
        self.program_counter += 2

    def clear_screen(self):
        self.screen = [[False] * SCREEN_HEIGHT] * SCREEN_WIDTH

    def return_back(self):
        if self.stack_pointer < 0:
            raise IndexError
        self.program_counter = self.stack[self.stack_pointer] - 2
        self.stack_pointer -= 1

    programs_0 = {0x00E0: clear_screen, 0x00EE: return_back}

    def execute_program_0(self, program_code):
        if program_code in self.programs_0:
            self.programs_0[program_code](self)
            return True
        else:
            return False

    def jump(self, location):
        self.program_counter = location - 2

    def execute_program_1(self, program_code):
        self.jump(program_code & 0xFFF)
        return True

    def call(self, location):
        self.stack_pointer += 1
        self.stack[self.stack_pointer] = self.program_counter
        self.program_counter = location - 2

    def execute_program_2(self, program_code):
        self.call(program_code & 0xFFF)
        return True

    def skip_if_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] == comparing_value:
            self.program_counter += 2

    def execute_program_3(self, program_code):
        self.skip_if_eq((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    def skip_if_not_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] != comparing_value:
            self.program_counter += 2

    def execute_program_4(self, program_code):
        self.skip_if_not_eq((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    def skip_if_regs_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] == self.v_reg[reg_num_2]:
            self.program_counter += 2

    def execute_program_5(self, program_code):
        if program_code & 0xF != 0:
            return False
        self.skip_if_regs_eq((program_code & 0xF00) >> 8,
                             (program_code & 0xF0) >> 4)
        return True

    def set(self, reg_num, value):
        self.v_reg[reg_num] = value

    def execute_program_6(self, program_code):
        self.set((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    def increment(self, reg_num, value):
        self.v_reg[reg_num] += value

    def execute_program_7(self, program_code):
        self.increment((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    def set_reg(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_2]

    def set_reg_or(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] | self.v_reg[reg_num_2]

    def set_reg_and(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] & self.v_reg[reg_num_2]

    def set_reg_xor(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] ^ self.v_reg[reg_num_2]

    def sum_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] + self.v_reg[reg_num_2]
        self.v_reg[0xF] = result & (V_MAX + 1)
        self.v_reg[reg_num_1] = result & V_MAX

    def sub_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] - self.v_reg[reg_num_2]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    def rshift_reg(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 1
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] >> 1

    def subn_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_2] - self.v_reg[reg_num_1]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    def lshift_reg(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 0b10000000
        self.v_reg[reg_num_1] = (self.v_reg[reg_num_1] << 1) & V_MAX

    programs_8 = {0: set_reg, 1: set_reg_or, 2: set_reg_and, 3: set_reg_xor,
                  4: sum_regs, 5: sub_regs, 6: rshift_reg, 7: subn_regs,
                  0xE: lshift_reg}

    def execute_program_8(self, program_code):
        last_digit = program_code & 0xF
        if last_digit in self.programs_8:
            reg_num_1 = (program_code & 0xF00) >> 8
            reg_num_2 = (program_code & 0xF0) >> 4
            self.programs_8[last_digit](self, reg_num_1, reg_num_2)
            return True
        return False

    def skip_if_regs_not_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] != self.v_reg[reg_num_2]:
            self.program_counter += 2

    def execute_program_9(self, program_code):
        if program_code & 0xF != 0:
            return False
        self.skip_if_regs_not_eq((program_code & 0xF00) >> 8,
                                 (program_code & 0xF0) >> 4)
        return True

    def set_i(self, value):
        self.i_reg = value

    def execute_program_a(self, program_code):
        self.set_i(program_code & 0xFFF)
        return True

    def jump_to_v0_sum(self, value):
        self.program_counter = value + self.v_reg[0] -2

    def execute_program_b(self, program_code):
        self.jump_to_v0_sum(program_code & 0xFFF)
        return True

    def set_rand_and(self, reg_num, value):
        self.v_reg[reg_num] = random.randint(0, 255) & value

    def execute_program_c(self, program_code):
        self.set_rand_and((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

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

    def execute_program_d(self, program_code):
        self.draw_sprite((program_code & 0xf00) >> 8,
                         (program_code & 0xF0) >> 4,
                         program_code & 0xF)

    def skip_if_pressed(self, key):
        if self.screen_app.is_key_pressed(key):
            self.program_counter += 2

    def skip_if_not_pressed(self, key):
        if not self.screen_app.is_key_pressed(key):
            self.program_counter += 2

    programs_e = {0x9E: skip_if_pressed, 0xA1: skip_if_not_pressed}

    def execute_program_e(self, program_code):
        last_two_digits = program_code & 0xFF
        if last_two_digits in self.programs_e:
            self.programs_e[last_two_digits](self, (program_code & 0xF00) >> 8)
            return True
        return False

    def set_delay_timer_value_to_v(self, reg_num):
        with self.delay_timer_value.get_lock():
            self.v_reg[reg_num] = self.delay_timer_value

    def wait_and_set_pressed_key(self, reg_num):
        self.screen_app.pressed_event.clear()
        self.screen_app.pressed_event.wait()
        self.v_reg[reg_num] = self.screen_app.last_pressed_key

    def set_delay_timer(self, reg_num):
        with self.delay_timer_value.get_lock():
            self.delay_timer_value = self.v_reg[reg_num]

    def set_sound_timer(self, reg_num):
        with self.sound_timer_value.get_lock():
            self.sound_timer_value = self.v_reg[reg_num]

    def add_vx_to_i(self, reg_num):
        self.i_reg += self.v_reg[reg_num]

    def set_i_to_digit_sprite(self, reg_num):
        self.i_reg = self.v_reg[reg_num] * 5

    def store_in_i_as_bcd(self, reg_num):
        value = self.v_reg[reg_num]
        hundreds = value % 1000 / 100
        tens = value % 100 / 10
        ones = value % 10
        self.memory[self.i_reg] = hundreds
        self.memory[self.i_reg + 1] = tens
        self.memory[self.i_reg + 2] = ones

    def write_v_to_i(self, reg_end_num):
        for i in range(reg_end_num):
            self.memory[self.i_reg + i] = self.v_reg[i]

    def read_v_from_i(self, reg_end_num):
        for i in range(reg_end_num):
            self.v_reg[i] = self.memory[self.i_reg + i]

    programs_f = {0x07: set_delay_timer_value_to_v,
                  0x0A: wait_and_set_pressed_key,
                  0x15: set_delay_timer,
                  0x18: set_sound_timer,
                  0x1E: add_vx_to_i,
                  0x29: set_i_to_digit_sprite,
                  0x33: store_in_i_as_bcd,
                  0x55: write_v_to_i,
                  0x65: read_v_from_i}

    def execute_program_f(self, program_code):
        last_two_digits = program_code & 0xFF
        if last_two_digits in self.programs_f:
            self.programs_f[last_two_digits](self, (program_code & 0xF00) >> 8)
            return True
        return False

    programs_by_first_digit = [execute_program_0,
                               execute_program_1,
                               execute_program_2,
                               execute_program_3,
                               execute_program_4,
                               execute_program_5,
                               execute_program_6,
                               execute_program_7,
                               execute_program_8,
                               execute_program_9,
                               execute_program_a,
                               execute_program_b,
                               execute_program_c,
                               execute_program_d,
                               execute_program_e,
                               execute_program_f]
