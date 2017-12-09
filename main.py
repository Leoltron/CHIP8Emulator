# !/usr/bin/env python3
import importlib.util
import sys
from argparse import ArgumentParser

import os
from PyQt5.QtWidgets import QApplication

import emulator
from screen import CHIP8QScreen

PIXEL_DEFAULT_SIDE_SIZE = 15


def main():
    kivy_installed = is_kivy_installed()
    parsed_args = parse_args()

    use_delay = not parsed_args.no_delay
    use_sound = not parsed_args.no_sound
    if not kivy_installed and use_sound:
        print("Warning: kivy not found, switching to no-sound mode")
        use_sound = False

    pixel_side_size = parsed_args.pixel_size
    if pixel_side_size <= 0:
        print("Pixel size must be positive, got {:d}"
              .format(pixel_side_size))
        return

    if not os.path.isfile(parsed_args.program_path):
        print('Program file "{}" not found.'.format(parsed_args.program_path))
        return

    bg_music = None
    bg_music_path = parsed_args.background_music

    sys.argv = sys.argv[:1]

    with open(parsed_args.program_path, 'rb') as f:
        program = f.read()

    if bg_music_path is not None:
        if not kivy_installed:
            print("kivy not found, cannot play bg music.")
            return
        if not os.path.isfile(bg_music_path):
            print('File "{}" not found.'.format(bg_music_path))
            return
        from kivy.core.audio import SoundLoader
        bg_music = SoundLoader.load(bg_music_path)
        if bg_music:
            bg_music.loop = True
            bg_music.play()
        else:
            print("Unexpected error during music loading.")
            print("Background music has been disabled.")

    app = QApplication(sys.argv[0:1])
    ex = CHIP8QScreen(pixel_side_size)
    p = emulator.EmulatorProcess(ex.pixels_state,
                                 ex.pressed_event,
                                 ex.pressed_key,
                                 ex.pressed,
                                 ex.close_event,
                                 use_delay,
                                 use_sound,
                                 program)
    try:
        p.start()
        app.exec_()
    finally:
        p.terminate()
        if bg_music:
            bg_music.stop()


def parse_args():
    parser = ArgumentParser(description="Launch a CHIP-8 emulator")

    parser.add_argument("program_path", type=str,
                        help="Path to the CHIP-8 program file")

    parser.add_argument("-d", "--no-delay",
                        action="store_true",
                        help="Disable delay between opcodes execution")
    parser.add_argument("-s", "--no-sound",
                        action="store_true",
                        help="Disable beeps sound (starts a bit faster)")
    parser.add_argument("-p", "--pixel-size",
                        type=int, default=PIXEL_DEFAULT_SIDE_SIZE,
                        help="Define a screen pixel size (must be positive)")
    parser.add_argument("-b", "--background-music", type=str, default=None,
                        help="Path to a sound file"
                             " that will play in background")
    return parser.parse_args()


def is_kivy_installed():
    spam_spec = importlib.util.find_spec("kivy")
    return spam_spec is not None


if __name__ == '__main__':
    main()
