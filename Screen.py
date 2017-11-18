# !/usr/bin/env python3
from multiprocessing import Event

PIXEL_SIDE_SIZE = 15
SCREEN_WIDTH = 64
SCREEN_HEIGHT = 32

from kivy.config import Config

Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'width', str(PIXEL_SIDE_SIZE * SCREEN_WIDTH))
Config.set('graphics', 'height', str(PIXEL_SIDE_SIZE * SCREEN_HEIGHT))

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle


class Pixel(Widget):
    active_color_rgb = [1, 1, 1]
    inactive_color_rgb = [0, 0, 0]
    side_size = PIXEL_SIDE_SIZE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active = False
        self.update_color()

    def update_color(self):
        self.color = self.active_color_rgb if self.active else self.inactive_color_rgb
        with self.canvas:
            Color(rgb=self.color)
            Rectangle(size=self.size, pos=self.pos)

    def set_active(self, new_val=True):
        old_val = self.active
        self.active = new_val
        if old_val ^ new_val:
            self.update_color()

    def switch_active(self):
        print("Switching x:{:d} y:{:d} ({})".format(self.x, self.y,
                                                    str(self.size)))
        self.active = not self.active
        self.update_color()
        return self.active


class CHIP8Screen(Widget):
    pass


KEY_BINDINGS = {'1': 0x1, '2': 0x2, '3': 0x3, '4': 0xf,
                'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xe,
                'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xd,
                'z': 0xa, 'x': 0x0, 'c': 0xb, 'v': 0xc, }


class CHIP8ScreenApp(App):
    pixels = [[None] * SCREEN_HEIGHT] * SCREEN_WIDTH

    screen = None
    pressed = [False] * 0x10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.pressed_event = Event()
        self.last_pressed_key = 0

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self._keyboard.bind(on_key_up=self._on_keyboard_up)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard.unbind(on_key_up=self._on_keyboard_up)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, key_code, text, modifiers):
        key_name = key_code[1]
        if key_name in KEY_BINDINGS:
            key = KEY_BINDINGS[key_name]
            self.pressed[key] = True
            self._on_key_pressed(key)
        return True

    def _on_keyboard_up(self, keyboard, key_code):
        key_name = key_code[1]
        if key_name in KEY_BINDINGS:
            self.pressed[KEY_BINDINGS[key_name]] = False
        return True

    def build(self):
        self.screen = screen = CHIP8Screen()
        self.pixels = []
        for x in range(SCREEN_WIDTH):
            self.pixels.append([None] * SCREEN_HEIGHT)

        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                pixel = Pixel(pos=(x * PIXEL_SIDE_SIZE, y * PIXEL_SIDE_SIZE))
                self.pixels[x][y] = pixel
                screen.add_widget(pixel, index=y * SCREEN_WIDTH + x)
        return screen

    def switch_pixel(self, x, y):
        return self.pixels[x][y].switch_active()

    def is_key_pressed(self, key):
        return self.pressed[key]

    def _on_key_pressed(self, key):
        if not self.pressed_event.is_set():
            self.last_pressed_key = key
            self.pressed_event.set()


if __name__ == '__main__':
    CHIP8ScreenApp().run()
