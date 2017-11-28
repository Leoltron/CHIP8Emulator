# !/usr/bin/env python3
import unittest

from multiprocessing import Array, Event, Value

import font
from emulator import CHIP8Emulator, SCREEN_WIDTH, SCREEN_HEIGHT


class EmulatorTests(unittest.TestCase):
    def setUp(self):
        self.pixels_state = Array('b',
                                  [False] * (SCREEN_WIDTH * SCREEN_HEIGHT))
        self.key_press_event = Event()
        self.key_press_value = Value('i', 0)
        self.key_down_values = []
        for i in range(0x10):
            self.key_down_values.append(Value('b', False))

        self.emulator = CHIP8Emulator(self.pixels_state,
                                      self.key_press_event,
                                      self.key_press_value,
                                      self.key_down_values,
                                      False, False)

    def tearDown(self):
        self.emulator.delay_timer.terminate()

    def test_jump(self):
        e = self.emulator
        e.execute_program(0x1208)
        self.assertEqual(0x208, e.program_counter)

    def test_call(self):
        e = self.emulator
        e.program_counter = 0x500
        e.execute_program(0x28FF)
        self.assertEqual(e.stack[e.stack_pointer - 1], 0x500)
        self.assertEqual(e.program_counter, 0x8ff)

    def test_skip_if_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5F
        e.program_counter = 0x200
        e.execute_program(0x325F)
        self.assertEqual(e.program_counter, 0x204)

    def test_not_skip_if_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5d
        e.program_counter = 0x200
        e.execute_program(0x325F)
        self.assertEqual(e.program_counter, 0x202)

    def test_not_skip_if_not_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5F
        e.program_counter = 0x200
        e.execute_program(0x425F)
        self.assertEqual(e.program_counter, 0x202)

    def test_skip_if_not_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5d
        e.program_counter = 0x200
        e.execute_program(0x425F)
        self.assertEqual(e.program_counter, 0x204)

    def test_skip_if_regs_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5d
        e.v_reg[4] = 0x5d
        e.program_counter = 0x200
        e.execute_program(0x5240)
        self.assertEqual(e.program_counter, 0x204)

    def test_not_skip_if_regs_not_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5d
        e.v_reg[4] = 0x5e
        e.program_counter = 0x200
        e.execute_program(0x5240)
        self.assertEqual(e.program_counter, 0x202)

    def test_set_v(self):
        e = self.emulator
        e.execute_program(0x6508)
        self.assertEqual(e.v_reg[5], 8)

    def test_increment(self):
        e = self.emulator
        e.v_reg[7] = 0x61
        e.execute_program(0x7718)
        self.assertEqual(e.v_reg[7], 0x61 + 0x18)

    def test_increment_overflow(self):
        e = self.emulator
        e.v_reg[7] = 0xF1
        e.execute_program(0x7718)
        self.assertEqual(e.v_reg[7], 0x9)

    def test_set_reg(self):
        e = self.emulator
        e.v_reg[7] = 0xF1
        e.execute_program(0x8170)
        self.assertEqual(e.v_reg[1], 0xf1)

    def test_digits(self):
        e = self.emulator
        for i in range(16):
            e.set(0, i)
            e.set_i_to_digit_sprite(0)
            for dy in range(5):
                expected = font.FONT[i][dy]
                actual = e.memory[e.i_reg + dy]
                self.assertEqual(expected, actual,
                                 "Digit {:d}, line {:d}: {} != {}".format(
                                     i, dy,
                                     bin(expected)[2:].rjust(8, '0'),
                                     bin(actual)[2:].rjust(8, '0')))

    def test_set_reg_or(self):
        e = self.emulator
        e.v_reg[0] = 0b0101
        e.v_reg[1] = 0b0011
        e.execute_program(0x8011)
        self.assertEqual(e.v_reg[0], 0b0111)

    def test_set_reg_and(self):
        e = self.emulator
        e.v_reg[0] = 0b0101
        e.v_reg[1] = 0b0011
        e.execute_program(0x8012)
        self.assertEqual(e.v_reg[0], 0b0001)

    def test_set_reg_xor(self):
        e = self.emulator
        e.v_reg[0] = 0b0101
        e.v_reg[1] = 0b0011
        e.execute_program(0x8013)
        self.assertEqual(e.v_reg[0], 0b0110)

    def test_v_add(self):
        e = self.emulator
        e.set(0, 1)
        e.set(1, 3)
        e.execute_program(0x8014)
        self.assertEqual(4, e.v_reg[0])
        self.assertEqual(0, e.v_reg[0xf])

    def test_v_add_carry(self):
        e = self.emulator
        e.set(0, 0xF4)
        e.set(1, 0x10)
        e.execute_program(0x8014)
        self.assertEqual(4, e.v_reg[0])
        self.assertEqual(1, e.v_reg[0xf])

    def test_v_sub(self):
        e = self.emulator
        e.execute_program(0x6001)
        e.execute_program(0x6102)
        e.execute_program(0x8015)
        self.assertEqual(0xff, e.v_reg[0])
        self.assertEqual(0, e.v_reg[0xF])

    def test_v_sub_borrow(self):
        e = self.emulator
        e.v_reg[0xa] = 0x10
        e.v_reg[0xb] = 0x40
        e.execute_program(0x8ab5)
        self.assertEqual(0xd0, e.v_reg[0xa])
        self.assertEqual(0, e.v_reg[0xF])

    def test_v_sub_no_borrow(self):
        e = self.emulator
        e.v_reg[0xa] = 0x40
        e.v_reg[0xb] = 0x30
        e.execute_program(0x8AB5)
        self.assertEqual(0x10, e.v_reg[0xa])
        self.assertEqual(1, e.v_reg[0xF])

    def test_v_subn_no_borrow(self):
        e = self.emulator
        e.v_reg[0x0] = 0x1
        e.v_reg[0x1] = 0x2
        e.execute_program(0x8017)
        self.assertEqual(1, e.v_reg[0])
        self.assertEqual(1, e.v_reg[0xF])

    def test_rshift_no_carry(self):
        e = self.emulator
        e.v_reg[0xa] = 0x40
        e.execute_program(0x8AB6)
        self.assertEqual(e.v_reg[0xa], 0x20)
        self.assertEqual(e.v_reg[0xf], 0)

    def test_rshift_carry(self):
        e = self.emulator
        e.v_reg[0xa] = 0x41
        e.execute_program(0x8AB6)
        self.assertEqual(e.v_reg[0xa], 0x20)
        self.assertEqual(e.v_reg[0xf], 1)

    def test_v_subn_borrow(self):
        e = self.emulator
        e.v_reg[0x0] = 0x1
        e.v_reg[0x1] = 0x2
        e.execute_program(0x8107)
        self.assertEqual(0xff, e.v_reg[1])
        self.assertEqual(0, e.v_reg[0xF])

    def test_lshift(self):
        e = self.emulator
        e.v_reg[0xa] = 0x40
        e.execute_program(0x8ABE)
        self.assertEqual(e.v_reg[0xa], 0x80)
        self.assertEqual(e.v_reg[0xf], 0)

    def test_lshift_carry(self):
        e = self.emulator
        e.v_reg[0xa] = 0b10110011
        e.execute_program(0x8ABE)
        self.assertEqual(e.v_reg[0xa], 0b01100110)
        self.assertEqual(e.v_reg[0xf], 1)

    def test_skip_if_regs_not_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5d
        e.v_reg[4] = 0x5d
        e.program_counter = 0x200
        e.execute_program(0x9240)
        self.assertEqual(e.program_counter, 0x202)

    def test_not_skip_if_regs_eq(self):
        e = self.emulator
        e.v_reg[2] = 0x5d
        e.v_reg[4] = 0x5e
        e.program_counter = 0x200
        e.execute_program(0x9240)
        self.assertEqual(e.program_counter, 0x204)

    def test_set_i(self):
        e = self.emulator
        e.execute_program(0xA123)
        self.assertEqual(e.i_reg, 0x123)

    def test_jump_to_v0_sum(self):
        e = self.emulator
        e.v_reg[0] = 0x12
        e.execute_program(0xB123)
        self.assertEqual(e.program_counter, 0x135)

    def test_add_vx_to_i(self):
        e = self.emulator
        e.i_reg = 0x565
        e.v_reg[5] = 0x5
        e.execute_program(0xF51E)
        self.assertEqual(e.i_reg, 0x56A)

    def test_store_in_i_as_bcd(self):
        e = self.emulator
        e.v_reg[0xe] = 254
        e.i_reg = 0x250
        e.execute_program(0xFE33)
        self.assertEqual(e.memory[e.i_reg], 2)
        self.assertEqual(e.memory[e.i_reg + 1], 5)
        self.assertEqual(e.memory[e.i_reg + 2], 4)

    def test_write_v_to_i(self):
        e = self.emulator
        e.v_reg[0] = 8
        e.v_reg[1] = 99
        e.v_reg[2] = 3
        e.v_reg[3] = 5
        e.v_reg[4] = 123
        e.v_reg[5] = 88
        e.i_reg = 0x300
        e.execute_program(0xF555)
        self.assertEqual(e.memory[e.i_reg], 8)
        self.assertEqual(e.memory[e.i_reg + 1], 99)
        self.assertEqual(e.memory[e.i_reg + 2], 3)
        self.assertEqual(e.memory[e.i_reg + 3], 5)
        self.assertEqual(e.memory[e.i_reg + 4], 123)
        self.assertEqual(e.memory[e.i_reg + 5], 88)

    def test_read_v_from_i(self):
        e = self.emulator
        e.i_reg = 0x300
        e.memory[e.i_reg + 0] = 8
        e.memory[e.i_reg + 1] = 99
        e.memory[e.i_reg + 2] = 3
        e.memory[e.i_reg + 3] = 5
        e.memory[e.i_reg + 4] = 123
        e.memory[e.i_reg + 5] = 88
        e.execute_program(0xF565)
        self.assertEqual(e.v_reg[0], 8)
        self.assertEqual(e.v_reg[1], 99)
        self.assertEqual(e.v_reg[2], 3)
        self.assertEqual(e.v_reg[3], 5)
        self.assertEqual(e.v_reg[4], 123)
        self.assertEqual(e.v_reg[5], 88)
