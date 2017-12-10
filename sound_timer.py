# !/usr/bin/env python3

from kivy.core.audio import SoundLoader

from timer import TimerProcess

sound = SoundLoader.load('beep.wav')
if sound:
    sound.loop = True
else:
    print("Unexpected kivy error during beeps loading, beeps won't work.")


def stop_beeping():
    if sound:
        sound.stop()


def start_beeping():
    if sound:
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
