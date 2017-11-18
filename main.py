# !/usr/bin/env python3
from emulator import CHIP8Emulator
from screen import CHIP8ScreenApp


def main():
    app = CHIP8ScreenApp()
    emulator = CHIP8Emulator(app)


if __name__ == '__main__':
    main()
