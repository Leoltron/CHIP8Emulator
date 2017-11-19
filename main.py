# !/usr/bin/env python3
import sys

from multiprocessing import SimpleQueue, Process

import emulator


def main():
    queue = SimpleQueue()
    app = CHIP8ScreenApp(queue)
    with open(' '.join(sys.argv[1:]), 'rb') as f:
        program = f.read()

    p = Process(target=emulator.run_emulator, args=(queue, app.pressed_event,
                                                    app.pressed_key,
                                                    app.pressed, program))
    p.start()
    app.run()


if __name__ == '__main__':
    from screen import CHIP8ScreenApp
    main()
