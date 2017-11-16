# !/usr/bin/env python3

from multiprocessing import Process, Value, Event

from kivy.core.audio import SoundLoader

sound = SoundLoader.load('beep.wav')


class TimerProcess(Process):
    paused = Event()
    stopped = Event()

    def __init__(self, interval, timer_value: Value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval = interval
        self.timer_value = timer_value
        self.paused.set()

    def cancel(self):
        self.stopped.set()
        self.paused.set()

    def _update_state(self):
        with self.timer_value.get_lock():
            if self.timer_value.value == 0:
                self.pause()
            else:
                self.resume()

    def run(self):
        while True:
            self.paused.wait(self.interval)
            if not self.paused.is_set():
                with self.timer_value.get_lock():
                    if self.timer_value.value > 0:
                        self.timer_value.value -= 1
            elif self.stopped.is_set():
                break
            self._update_state()

    def pause(self):
        self.paused.set()

    def resume(self):
        self.paused.clear()


def stop_beeping():
    if sound:
        sound.stop()


def start_beeping():
    if sound:
        sound.loop = True
        sound.play()


class BeepTimerProcess(TimerProcess):
    def pause(self):
        if not self.paused.is_set():
            stop_beeping()
        super().pause()

    def resume(self):
        if self.paused.is_set():
            start_beeping()
        super().resume()
