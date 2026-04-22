# CSC 102 Defuse the draft_bomb Project
# Main program
# Team: Save Times Square

from tkinter import *
import os, sys

from draft_bomb_configs import (
    RPi, COUNTDOWN, NUM_STRIKES, NUM_PHASES, boot_text,
    component_7seg, component_keypad, component_wires,
    component_button_state, component_button_RGB,
    component_toggles, toggles_target, wires_target, keypad_target
)

from draft_bomb_phases import Timer, Keypad, Wires, Button, Toggles

# -----------------------
# LCD GUI
# -----------------------

class Lcd(Frame):
    def __init__(self, window):
        super().__init__(window, bg="black")
        window.attributes("-fullscreen", True)
        self._timer = None
        self._button = None
        self.setupBoot()

    def setupBoot(self):
        self._lscroll = Label(self, bg="black", fg="white",
                              font=("Courier New", 14), text="", justify=LEFT)
        self._lscroll.grid(row=0, column=0, columnspan=3, sticky=W)
        self.pack(fill=BOTH, expand=True)

    def setup(self):
        self._ltimer = Label(self, bg="black", fg="#00ff00",
                             font=("Courier New", 18), text="Time left:")
        self._ltimer.grid(row=1, column=0, columnspan=3, sticky=W)

        self._lkeypad = Label(self, bg="black", fg="#00ff00",
                              font=("Courier New", 18), text="Keypad:")
        self._lkeypad.grid(row=2, column=0, columnspan=3, sticky=W)

        self._lwires = Label(self, bg="black", fg="#00ff00",
                             font=("Courier New", 18), text="Wires:")
        self._lwires.grid(row=3, column=0, columnspan=3, sticky=W)

        self._lbutton = Label(self, bg="black", fg="#00ff00",
                              font=("Courier New", 18), text="Button:")
        self._lbutton.grid(row=4, column=0, columnspan=3, sticky=W)

        self._ltoggles = Label(self, bg="black", fg="#00ff00",
                               font=("Courier New", 18), text="Toggles:")
        self._ltoggles.grid(row=5, column=0, columnspan=2, sticky=W)

        self._lstrikes = Label(self, bg="black", fg="#00ff00",
                               font=("Courier New", 18), text="Strikes left:")
        self._lstrikes.grid(row=5, column=2, sticky=W)

    def setTimer(self, timer):
        self._timer = timer

    def setButton(self, button):
        self._button = button

    def conclusion(self, success=False):
        for widget in self.winfo_children():
            widget.destroy()

        msg = "draft_bomb DEFUSED" if success else "BOOM"
        Label(self, text=msg, bg="black", fg="red",
              font=("Courier New", 40)).pack(pady=40)

        Button(self, text="Retry", bg="red", fg="white",
               font=("Courier New", 18),
               command=self.retry).pack(pady=20)

        Button(self, text="Quit", bg="red", fg="white",
               font=("Courier New", 18),
               command=self.quit).pack(pady=20)

    def retry(self):
        os.execv(sys.executable, ["python3"] + [sys.argv[0]])

    def quit(self):
        if RPi and self._timer and self._timer._component:
            self._timer._running = False
            self._timer._component.blink_rate = 0
            self._timer._component.fill(0)
        exit(0)

# -----------------------
# Bootup
# -----------------------

def bootup(n=0):
    # This takes the full boot_text and reveals it character by character
    if n <= len(boot_text):
        current_text = boot_text[:n]
        gui._lscroll.config(text=current_text)
        # Call this function again after 30ms for the next character
        window.after(30, lambda: bootup(n + 1))
    else:
        # Once text is done, show the rest of the UI
        gui.setup()
        if (RPi):
            setup_phases()
            check_phases()

# -----------------------
# Setup Phases
# -----------------------

def setup_phases():
    global timer, keypad, wires, button, toggles, current_phase

    timer = Timer(component_7seg, COUNTDOWN)
    gui.setTimer(timer)

    keypad = Keypad(component_keypad, keypad_target)
    wires = Wires(component_wires, wires_target)
    toggles = Toggles(component_toggles, toggles_target)
    button = Button(component_button_state, component_button_RGB, timer)
    gui.setButton(button)

    timer.start()
    keypad.start()
    wires.start()
    toggles.start()
    button.start()

    current_phase = 1

# -----------------------
# Strike + Timer Effects
# -----------------------

def apply_correct():
    timer._value = max(0, timer._value - 30)

def apply_incorrect():
    global strikes_left
    timer._value = max(0, timer._value - 60)
    timer._interval = 1.5
    strikes_left -= 1

# -----------------------
# Turn Off
# -----------------------

def turn_off():
    timer._running = False
    keypad._running = False
    wires._running = False
    toggles._running = False
    button._running = False

    if component_7seg:
        component_7seg.blink_rate = 0
        component_7seg.fill(0)
    for pin in component_button_RGB:
        pin.value = True

# -----------------------
# Check Phases
# -----------------------

def check_phases():
    global active_phases, current_phase, strikes_left

    if timer._running:
        gui._ltimer["text"] = f"Time left: {timer}"
    else:
        turn_off()
        gui.after(100, gui.conclusion, False)
        return

    gui._lkeypad["text"] = f"Keypad: {keypad}"
    gui._lwires["text"] = f"Wires: {wires}"
    gui._ltoggles["text"] = f"Toggles: {toggles}"
    gui._lbutton["text"] = f"Button: {button}"

    if button.consume_submit():
        if current_phase == 1:
            toggles.check_correct()
            if toggles._defused:
                apply_correct()
                toggles._running = False
                active_phases -= 1
                current_phase = 2
            elif toggles._failed:
                apply_incorrect()
                toggles._failed = False

        elif current_phase == 2:
            if keypad._defused:
                apply_correct()
                keypad._running = False
                active_phases -= 1
                current_phase = 3
            else:
                apply_incorrect()

        elif current_phase == 3:
            wires.check_correct()
            if wires._defused:
                apply_correct()
                wires._running = False
                active_phases -= 1
            elif wires._failed:
                apply_incorrect()
                wires._failed = False

    gui._lstrikes["text"] = f"Strikes left: {strikes_left}"

    if strikes_left <= 0:
        turn_off()
        gui.after(1000, gui.conclusion, False)
        return

    if active_phases == 0:
        turn_off()
        gui.after(100, gui.conclusion, True)
        return

    gui.after(100, check_phases)

# -----------------------
# MAIN
# -----------------------

window = Tk()
gui = Lcd(window)

strikes_left = NUM_STRIKES
active_phases = NUM_PHASES
current_phase = 1

gui.after(100, bootup)
window.mainloop()
