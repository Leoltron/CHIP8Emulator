# !/usr/bin/env python3

from multiprocessing import Process, Value, Event


class TimerProcess(Process):
    paused = Event()
    stopped = Event()

    def __init__(self, interval, timer_value: Value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval = interval
        self.timer_value = timer_value
        if timer_value.value > 0:
            self.pause()
        self._update_state()

    def cancel(self):
        self.stopped.set()
        self.pause()

    def _update_state(self):
        with self.timer_value.get_lock():
            if self.timer_value.value == 0:
                self.pause()
            else:
                self.resume()

    def run(self):
        while True:
            self.stopped.wait(self.interval)
            if not self.paused.is_set():
                with self.timer_value.get_lock():
                    if self.timer_value.value > 0:
                        self.timer_value.value -= 1
            elif self.stopped.is_set():
                return
            self._update_state()

    def pause(self):
        self.paused.set()

    def resume(self):
        self.paused.clear()


# class BeepTimerProcess(TimerProcess):
#     def pause(self):
#         if not self.paused.is_set():
#             stop_beeping()
#         super().pause()
#
#     def resume(self):
#         if self.paused.is_set():
#             start_beeping()
#             time.sleep(0.1)
#         super().resume()

