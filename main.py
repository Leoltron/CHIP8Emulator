# !/usr/bin/env python3
import sys

import os
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

    file_path = ' '.join(args)
    if len(args) == 0:
        print("Usage: " + sys.argv[0] + " <program_path> "
                                        "[--no-sound] [--no-delay]")
        return
    elif not os.path.isfile(file_path):
        print("File " + file_path + " not found")
        return
    with open(file_path, 'rb') as f:
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
