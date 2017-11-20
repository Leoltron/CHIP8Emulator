# !/usr/bin/env python3
import unittest

import font
from emulator import CHIP8Emulator


class EmulatorTests(unittest.TestCase):
    def setUp(self):
        self.emulator = CHIP8Emulator(None, None, None, None)

    def tearDown(self):
        self.emulator.sound_timer.terminate()
        self.emulator.delay_timer.terminate()

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

    def test_v_add(self):
        e = self.emulator
        e.set(0, 1)
        e.set(1, 2)
        e.sum_regs(0, 1)
        self.assertEqual(3, e.v_reg[0])

    def test_v_sub(self):
        e = self.emulator
        e.execute_program(0x6001)
        e.execute_program(0x6102)
        e.execute_program(0x8015)
        self.assertEqual(0xff, e.v_reg[0])
        self.assertEqual(0, e.v_reg[0xF])

    def test_v_subn(self):
        e = self.emulator
        e.execute_program(0x6001)
        e.execute_program(0x6102)
        e.execute_program(0x8017)
        self.assertEqual(1, e.v_reg[0])
        self.assertEqual(1, e.v_reg[0xF])
