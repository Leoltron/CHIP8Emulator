# !/usr/bin/env python3
import sys

from PyQt5.QtWidgets import QApplication

import emulator
from screen import CHIP8QScreen


def main():
    app = QApplication(sys.argv[0:1])
    ex = CHIP8QScreen()

    args = sys.argv[1:]

    use_delay = True
    use_sound = True
    if "--no-delay" in args:
        args.remove("--no-delay")
        use_delay = False

    if "--no-sound" in args:
        args.remove("--no-sound")
        use_sound = False

    with open(' '.join(args), 'rb') as f:
        program = f.read()

    p = emulator.EmulatorProcess(ex.pixels_state,
                                 ex.pressed_event,
                                 ex.pressed_key,
                                 ex.pressed,
                                 use_delay,
                                 use_sound,
                                 program)
    p.start()
    app.exec_()
    p.terminate()
    p.join()


if __name__ == '__main__':
    main()
