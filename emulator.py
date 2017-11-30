# !/usr/bin/env python3
import random
from multiprocessing import Value, Process

import time

import font
import timer

SCREEN_WIDTH = 64
SCREEN_HEIGHT = 32

PROGRAM_START = 0x200
V_MAX = 0xFF
I_MAX = 0xFFFF


class EmulatorProcess(Process):
    def terminate(self):
        self.emulator.on_terminate()
        super().terminate()

    def __init__(self, pixels_state, key_press_event, key_press_value,
                 key_down_values, close_event,
                 use_delay=True, use_sound=True, program=None, *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.emulator = CHIP8Emulator(pixels_state,
                                      key_press_event,
                                      key_press_value,
                                      key_down_values,
                                      close_event,
                                      use_delay,
                                      use_sound)
        self.use_sound = use_sound
        self.program = program

    def join(self, timeout=None):
        self.emulator.delay_timer.stopped.set()
        self.emulator.delay_timer.join(timeout)

        if self.use_sound:
            self.emulator.sound_timer.stopped.set()
            self.emulator.sound_timer.join(timeout)

        super().join(timeout)

    def run(self):
        self.emulator.load_program(self.program)
        self.emulator.execute()


def hex_and_dec(value):
    return hex(value) + ' (' + str(value) + ')'


# noinspection SpellCheckingInspection
class CHIP8Emulator:
    def __init__(self, pixels_state, key_press_event, key_press_value,
                 key_down_values, close_event, use_delay=True, use_sound=True):
        self.memory = bytearray(4096)

        self.use_delay = use_delay
        self.use_sound = use_sound
        self.close_event = close_event

        for i in range(16):
            self.memory[5 * i:5 * (i + 1)] = font.FONT[i]

        self.v_reg = [0] * 16
        self.i_reg = 0
        self.program_counter = 0
        self.stack_pointer = 0
        self.stack = [0] * 16

        self.delay_timer_value = Value('i', 0)
        self.delay_timer = timer.TimerProcess(1 / 60, self.delay_timer_value)
        self.delay_timer.start()

        self.sound_timer_value = Value('i', 0)
        if use_sound:
            import sound_timer
            self.sound_timer = sound_timer.BeepTimerProcess(1 / 60,
                                                            self.sound_timer_value)
            self.sound_timer.start()

        self.pixels_state = pixels_state
        self.key_press_event = key_press_event
        self.key_press_value = key_press_value
        self.key_down_values = key_down_values

        self.screen = list()
        for i in range(SCREEN_WIDTH):
            column = list()
            for n in range(SCREEN_WIDTH):
                column.append(False)
            self.screen.append(column)

    def load_program(self, program_bytes):
        self.memory[
        PROGRAM_START:PROGRAM_START + len(program_bytes)] = program_bytes

    def execute(self):
        self.program_counter = PROGRAM_START
        while True:
            program_code = (self.memory[self.program_counter] << 8) | \
                           self.memory[self.program_counter + 1]
            try:
                self.execute_program(program_code)
            except OpCodeNotFoundError:
                print(
                    "Error at memory position {0} "
                    "({1} bytes from program start): ".format(
                        hex_and_dec(self.program_counter),
                        hex_and_dec(self.program_counter - PROGRAM_START)),
                    end='')
                readable_code = hex(program_code)[2:].zfill(4).upper()
                print('Not found program matching ' + readable_code)
                self.close_event.set()
                return
            if self.use_delay:
                time.sleep(0.001)

    def execute_program(self, program_code, first_hex=None):
        if first_hex is None:
            first_hex = (program_code >> 12) & 0xf

        if not self.programs_by_first_digit[first_hex](self, program_code):
            raise OpCodeNotFoundError(
                'Not found program matching ' + hex(program_code)[2:].upper())
        self.program_counter += 2

    # 00E0
    def clear_screen(self):
        for x in range(SCREEN_WIDTH):
            for y in range(SCREEN_HEIGHT):
                if self.screen[x][y]:
                    self._switch_pixel(x, y)

    def _switch_pixel(self, x, y):
        while x < 0:
            x += SCREEN_WIDTH
        while x >= SCREEN_WIDTH:
            x -= SCREEN_WIDTH
        while y < 0:
            y += SCREEN_HEIGHT
        while y >= SCREEN_HEIGHT:
            y -= SCREEN_HEIGHT

        old_val = self.screen[x][y]
        self.pixels_state[x + SCREEN_WIDTH * y] = \
            self.screen[x][y] = not old_val
        return old_val

    # 00EE
    def return_back(self):
        self.stack_pointer -= 1
        self.program_counter = self.stack[self.stack_pointer]

    programs_0 = {0x00E0: clear_screen, 0x00EE: return_back}

    def execute_program_0(self, program_code):
        if program_code in self.programs_0:
            self.programs_0[program_code](self)
            return True
        return False

    # 1nnn
    def jump(self, location):
        self.program_counter = location - 2

    def execute_program_1(self, program_code):
        self.jump(program_code & 0xFFF)
        return True

    # 2nnn
    def call(self, location):
        self.stack[self.stack_pointer] = self.program_counter
        self.stack_pointer += 1
        self.program_counter = location - 2

    def execute_program_2(self, program_code):
        self.call(program_code & 0xFFF)
        return True

    # 3xkk
    def skip_if_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] == comparing_value:
            self.program_counter += 2

    def execute_program_3(self, program_code):
        self.skip_if_eq((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    # 4xkk
    def skip_if_not_eq(self, reg_num, comparing_value):
        if self.v_reg[reg_num] != comparing_value:
            self.program_counter += 2

    def execute_program_4(self, program_code):
        self.skip_if_not_eq((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    # 5xy0
    def skip_if_regs_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] == self.v_reg[reg_num_2]:
            self.program_counter += 2

    def execute_program_5(self, program_code):
        if program_code & 0xF != 0:
            return False
        self.skip_if_regs_eq((program_code & 0xF00) >> 8,
                             (program_code & 0x0F0) >> 4)
        return True

    # 6xkk
    def set(self, reg_num, value):
        self.v_reg[reg_num] = value

    def execute_program_6(self, program_code):
        self.set((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    # 7xkk
    def increment(self, reg_num, value):
        self.v_reg[reg_num] = (self.v_reg[reg_num] + value) & V_MAX

    def execute_program_7(self, program_code):
        self.increment((program_code & 0xF00) >> 8, program_code & 0xFF)
        return True

    # 8xy0
    def set_reg(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_2]

    # 8xy1
    def set_reg_or(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] | self.v_reg[reg_num_2]

    # 8xy2
    def set_reg_and(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] & self.v_reg[reg_num_2]

    # 8xy3
    def set_reg_xor(self, reg_num_1, reg_num_2):
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] ^ self.v_reg[reg_num_2]

    # 8xy4
    def sum_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] + self.v_reg[reg_num_2]
        self.v_reg[0xF] = int(result & (V_MAX + 1) > 0)
        self.v_reg[reg_num_1] = result & V_MAX

    # 8xy5
    def sub_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_1] - self.v_reg[reg_num_2]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    # 8xy6
    def rshift_reg(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = self.v_reg[reg_num_1] & 1
        self.v_reg[reg_num_1] = self.v_reg[reg_num_1] >> 1

    # 8xy7
    def subn_regs(self, reg_num_1, reg_num_2):
        result = self.v_reg[reg_num_2] - self.v_reg[reg_num_1]
        self.v_reg[0xF] = int(result >= 0)
        if result < 0:
            result += V_MAX + 1
        self.v_reg[reg_num_1] = result

    # 8xyE
    def lshift_reg(self, reg_num_1, reg_num_2):
        self.v_reg[0xF] = int((self.v_reg[reg_num_1] & 0b10000000) != 0)
        self.v_reg[reg_num_1] = (self.v_reg[reg_num_1] << 1) & V_MAX

    programs_8 = {0: set_reg, 1: set_reg_or, 2: set_reg_and, 3: set_reg_xor,
                  4: sum_regs, 5: sub_regs, 6: rshift_reg, 7: subn_regs,
                  0xE: lshift_reg}

    def execute_program_8(self, program_code):
        last_digit = program_code & 0xF
        if last_digit in self.programs_8:
            reg_num_1 = (program_code & 0xF00) >> 8
            reg_num_2 = (program_code & 0x0F0) >> 4
            self.programs_8[last_digit](self, reg_num_1, reg_num_2)
            return True
        return False

    # 9xy0
    def skip_if_regs_not_eq(self, reg_num_1, reg_num_2):
        if self.v_reg[reg_num_1] != self.v_reg[reg_num_2]:
            self.program_counter += 2

    def execute_program_9(self, program_code):
        if program_code & 0xF != 0:
            return False
        self.skip_if_regs_not_eq((program_code & 0xF00) >> 8,
                                 (program_code & 0x0F0) >> 4)
        return True

    # Annn
    def set_i(self, value):
        self.i_reg = value

    def execute_program_a(self, program_code):
        self.set_i(program_code & 0xFFF)
        return True

    # Bnnn
    def jump_to_v0_sum(self, value):
        self.program_counter = value + self.v_reg[0] - 2

    def execute_program_b(self, program_code):
        self.jump_to_v0_sum(program_code & 0xFFF)
        return True

    # Cxkk
    def set_rand_and(self, reg_num, value):
        self.v_reg[reg_num] = random.randint(0, 255) & value

    def execute_program_c(self, program_code):
        self.set_rand_and((program_code & 0xF00) >> 8,
                          program_code & 0x0FF)
        return True

    # Dxyn
    def draw_sprite(self, vx, vy, sprite_height):
        x = self.v_reg[vx]
        y = self.v_reg[vy]
        collision = False
        for i in range(sprite_height):
            line = self.memory[self.i_reg + i]
            dx = 7
            while dx >= 0:
                if line & 1:
                    collision = self._switch_pixel(x + dx, y + i) or collision
                line = line >> 1
                dx -= 1
        self.v_reg[0xf] = int(collision)

    def execute_program_d(self, program_code):
        self.draw_sprite((program_code & 0xF00) >> 8,
                         (program_code & 0x0F0) >> 4,
                         program_code & 0x00F)
        return True

    # Ex9E
    def skip_if_pressed(self, reg_num):
        key = self.v_reg[reg_num]
        if self.key_down_values[key].value:
            self.program_counter += 2

    # ExA1
    def skip_if_not_pressed(self, reg_num):
        key = self.v_reg[reg_num]
        if not self.key_down_values[key].value:
            self.program_counter += 2

    programs_e = {0x9E: skip_if_pressed, 0xA1: skip_if_not_pressed}

    def execute_program_e(self, program_code):
        last_two_digits = program_code & 0xFF
        if last_two_digits in self.programs_e:
            self.programs_e[last_two_digits](self, (program_code & 0xF00) >> 8)
            return True
        return False

    # Fx07
    def set_delay_timer_value_to_v(self, reg_num):
        with self.delay_timer_value.get_lock():
            self.v_reg[reg_num] = self.delay_timer_value.value & V_MAX

    # Fx0A
    def wait_and_set_pressed_key(self, reg_num):
        self.key_press_event.clear()
        self.key_press_event.wait()
        self.v_reg[reg_num] = self.key_press_value.value & V_MAX

    # Fx15
    def set_delay_timer(self, reg_num):
        with self.delay_timer_value.get_lock():
            self.delay_timer_value.value = self.v_reg[reg_num]

    # Fx18
    def set_sound_timer(self, reg_num):
        if self.v_reg[reg_num] != 1:
            with self.sound_timer_value.get_lock():
                self.sound_timer_value.value = self.v_reg[reg_num]

    # Fx1E
    def add_vx_to_i(self, reg_num):
        new_i = self.i_reg + self.v_reg[reg_num]
        self.i_reg = new_i & I_MAX
        self.v_reg[0xf] = int((new_i & (I_MAX + 1)) > 0)

    # Fx29
    def set_i_to_digit_sprite(self, reg_num):
        self.i_reg = self.v_reg[reg_num] * 5

    # Fx33
    def store_in_i_as_bcd(self, reg_num):
        value = self.v_reg[reg_num]
        hundreds = value % 1000 // 100
        tens = value % 100 // 10
        ones = value % 10
        self.memory[self.i_reg] = hundreds
        self.memory[self.i_reg + 1] = tens
        self.memory[self.i_reg + 2] = ones

    # Fx55
    def write_v_to_i(self, reg_end_num):
        for i in range(reg_end_num + 1):
            self.memory[self.i_reg + i] = self.v_reg[i]

    # Fx65
    def read_v_from_i(self, reg_end_num):
        for i in range(reg_end_num + 1):
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

    def on_terminate(self):
        self.delay_timer.terminate()
        if self.use_sound:
            self.sound_timer.terminate()


class OpCodeNotFoundError(Exception):
    pass
