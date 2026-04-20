# CSC 102 Defuse the Bomb Project
# Phase Classes
# Team: Save Times Square

from threading import Thread
from time import sleep

# -----------------------
# Base Phase Thread
# -----------------------

class PhaseThread(Thread):
    def __init__(self, name, component=None, target=None):
        super().__init__(name=name, daemon=True)
        self._component = component
        self._target = target
        self._defused = False
        self._failed = False
        self._value = None
        self._running = False

# -----------------------
# Timer
# -----------------------

class Timer(PhaseThread):
    def __init__(self, component, initial_value, name="Timer"):
        super().__init__(name, component)
        self._value = initial_value
        self._paused = False
        self._interval = 1
        self._min = ""
        self._sec = ""

    def run(self):
        self._running = True
        while self._running:
            if not self._paused:
                self._update()
                if self._component:
                    self._component.print(str(self))
                sleep(self._interval)
                if self._value > 0:
                    self._value -= 1
                else:
                    self._running = False
            else:
                sleep(0.1)

    def _update(self):
        self._min = f"{self._value // 60}".zfill(2)
        self._sec = f"{self._value % 60}".zfill(2)

    def __str__(self):
        return f"{self._min}:{self._sec}"

# -----------------------
# Keypad
# -----------------------

class Keypad(PhaseThread):
    def __init__(self, component, target, name="Keypad"):
        super().__init__(name, component, target)
        self._value = ""

    def run(self):
        self._running = True
        while self._running:
            if self._component and self._component.pressed_keys:
                while self._component.pressed_keys:
                    try:
                        key = self._component.pressed_keys[0]
                    except:
                        key = ""
                    sleep(0.1)
                self._value += str(key)

                if self._value == self._target:
                    self._defused = True
                elif self._value != self._target[:len(self._value)]:
                    self._failed = True

            sleep(0.1)

    def __str__(self):
        return "DEFUSED" if self._defused else self._value

# -----------------------
# Toggles (Option A)
# -----------------------

class Toggles(PhaseThread):
    def __init__(self, component, target, name="Toggles"):
        super().__init__(name, component, target)
        self._sequence = []
        self._seen = set()
        self._prev = [False]*4

    def run(self):
        self._running = True
        while self._running:
            curr = []
            for pin in self._component:
                curr.append(pin.value if pin else False)

            for idx, (p, c) in enumerate(zip(self._prev, curr), start=1):
                if not p and c and idx not in self._seen:
                    self._sequence.append(idx)
                    self._seen.add(idx)

            self._prev = curr
            sleep(0.1)

    def check_correct(self):
        if self._sequence == self._target:
            self._defused = True
        else:
            self._failed = True

    def __str__(self):
        return "DEFUSED" if self._defused else f"Sequence: {self._sequence}"

# -----------------------
# Wires
# -----------------------

class Wires(PhaseThread):
    def __init__(self, component, target, name="Wires"):
        super().__init__(name, component, target)
        self._last_pulled = None
        self._prev = [True]*5

    def run(self):
        self._running = True
        while self._running:
            curr = []
            for pin in self._component:
                curr.append(pin.value if pin else True)

            for idx, (p, c) in enumerate(zip(self._prev, curr)):
                if p and not c:
                    self._last_pulled = idx

            self._prev = curr
            sleep(0.1)

    def check_correct(self):
        if self._last_pulled == self._target:
            self._defused = True
        else:
            self._failed = True

    def __str__(self):
        return "DEFUSED" if self._defused else f"Last pulled: {self._last_pulled}"

# -----------------------
# Button (Submit Only)
# -----------------------

class Button(PhaseThread):
    def __init__(self, component_state, component_rgb, timer, name="Button"):
        super().__init__(name, component_state, None)
        self._pressed = False
        self._submit = False
        self._rgb = component_rgb
        self._timer = timer

    def run(self):
        self._running = True
        for pin in self._rgb:
            if pin:
                pin.value = False

        while self._running:
            val = self._component.value if self._component else False

            if val:
                self._pressed = True
            else:
                if self._pressed:
                    self._submit = True
                    self._pressed = False

            sleep(0.1)

    def consume_submit(self):
        if self._submit:
            self._submit = False
            return True
        return False

    def __str__(self):
        return "Pressed" if self._pressed else "Released"
