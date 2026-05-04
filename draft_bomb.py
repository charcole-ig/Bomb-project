# CSC 102 Defuse the draft_bomb Project
# Main program
# Team: Save Times Square
#    Ourteam is awesome

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
from lcd_gui import Lcd

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

    # ── Timer + strikes HUD ─────────────────────────────────────────────
    if timer._running:
        # Update circular timer ring
        gui.updateTimer(timer._value, COUNTDOWN)
    else:
        turn_off()
        gui.after(500, gui.conclusion, False)
        return

    # Update strikes bar
    gui.updateStrikes(strikes_left)

    # Update phase status text from __str__ of each phase
    gui.updateToggles(str(toggles))
    gui.updateKeypad(str(keypad))
    gui.updateWires(str(wires))

    # Phase dots: mark active phase
    if current_phase == 1:
        gui.setPhaseActive(0)
    elif current_phase == 2:
        gui.setPhaseActive(1)
    elif current_phase == 3:
        gui.setPhaseActive(2)

    # ── Handle submit button ────────────────────────────────────────────
    if button.consume_submit():
        if current_phase == 1:
            toggles.check_correct()
            if toggles._defused:
                apply_correct()
                toggles._running = False
                active_phases -= 1
                gui.setPhaseComplete(0)
                current_phase = 2
                keypad.reset()
            elif toggles._failed:
                apply_incorrect()
                toggles.reset()
                keypad.reset()
                toggles._failed = False

        elif current_phase == 2:
            # Player pressed submit — now evaluate the code
            if keypad._value == keypad._target:
                keypad._defused = True
                apply_correct()
                keypad._running = False
                active_phases -= 1
                current_phase = 3
                button._submit = False
            else:
                apply_incorrect()
                keypad.reset()


        elif current_phase == 3:
            wires.check_correct()
            if wires._defused:
                apply_correct()
                wires._running = False
                active_phases -= 1
                gui.setPhaseComplete(2)
            elif wires._failed:
                apply_incorrect()
                wires.reset()

    # ── End conditions ──────────────────────────────────────────────────
    if strikes_left <= 0:
        turn_off()
        gui.after(1000, gui.conclusion, False)
        return

    if active_phases == 0:
        turn_off()
        gui.after(300, gui.conclusion, True)
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
