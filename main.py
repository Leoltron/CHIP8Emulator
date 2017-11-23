# !/usr/bin/env python3
import sys

from multiprocessing import SimpleQueue

import gc

from PyQt5.QtWidgets import QApplication

import emulator
from qscreen import CHIP8QScreen


def main():

    app = QApplication(sys.argv[0:1])
    ex = CHIP8QScreen()

    with open(' '.join(sys.argv[1:]), 'rb') as f:
        program = f.read()

    p = emulator.EmulatorProcess(ex.pixels_state, ex.pressed_event,
                                 ex.pressed_key,
                                 ex.pressed, program)
    p.start()
    app.exec_()
    p.terminate()
    p.join()

if __name__ == '__main__':
    main()
