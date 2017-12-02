# !/usr/bin/env python3
import sys
from multiprocessing import Array, Value, Event

from PyQt5.QtCore import Qt, QBasicTimer
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QWidget, QApplication

from emulator import SCREEN_HEIGHT, SCREEN_WIDTH

KEY_BINDINGS = {Qt.Key_1: 0x1, Qt.Key_2: 0x2, Qt.Key_3: 0x3, Qt.Key_4: 0xc,
                Qt.Key_Q: 0x4, Qt.Key_W: 0x5, Qt.Key_E: 0x6, Qt.Key_R: 0xd,
                Qt.Key_A: 0x7, Qt.Key_S: 0x8, Qt.Key_D: 0x9, Qt.Key_F: 0xe,
                Qt.Key_Z: 0xa, Qt.Key_X: 0x0, Qt.Key_C: 0xb, Qt.Key_V: 0xf, }


class CHIP8QScreen(QWidget):
    color_inactive = QColor(0, 0, 0)
    color_active = QColor(255, 255, 255)

    def __init__(self, pixel_side_size):
        super().__init__()

        self.pixel_side_size = pixel_side_size

        self.init_ui()

        self.timer_redraw = QBasicTimer()
        self.timer_redraw.start(1, self)

        self.pixels_state = Array('b',
                                  [False] * (SCREEN_WIDTH * SCREEN_HEIGHT))
        self.pressed_event = Event()
        self.pressed_key = Value('i', 0)

        self.close_event = Event()

        self.pressed = []
        for i in range(0x10):
            self.pressed.append(Value('b', False))

    def init_ui(self):
        self.setFixedSize(self.pixel_side_size * SCREEN_WIDTH,
                          self.pixel_side_size * SCREEN_HEIGHT)
        self.setWindowTitle('CHIP-8')
        self.show()

    def paintEvent(self, e=None):
        qp = QPainter()
        qp.begin(self)

        index = 0
        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                self.draw_pixel(qp,
                                x * self.pixel_side_size,
                                y * self.pixel_side_size,
                                self.pixels_state[index])
                index += 1
        qp.end()

    def keyPressEvent(self, e):
        if e.isAutoRepeat():
            return
        if e.key() in KEY_BINDINGS:
            key = KEY_BINDINGS[e.key()]
            self.pressed[key].value = True
            if not self.pressed_event.is_set():
                self.pressed_key.value = key
                self.pressed_event.set()

    def keyReleaseEvent(self, e):
        if e.isAutoRepeat():
            return
        if e.key() in KEY_BINDINGS:
            self.pressed[KEY_BINDINGS[e.key()]].value = False

    def draw_pixel(self, qp, x, y, state):
        color = self.color_active if state else self.color_inactive
        qp.setBrush(color)
        qp.setPen(color)
        qp.drawRect(x, y, self.pixel_side_size, self.pixel_side_size)

    def timerEvent(self, event):
        if self.close_event.is_set():
            QApplication.quit()
        if event.timerId() == self.timer_redraw.timerId():
            self.update()
        else:
            super().timerEvent(event)
