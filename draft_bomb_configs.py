# CSC 102 Defuse the Bomb Project
# Configuration file
# Team: Save Times Square

from random import choice

DEBUG = False
RPi = True          # MUST be True on the Raspberry Pi
SHOW_BUTTONS = False

COUNTDOWN = 300     # 5 minutes
NUM_STRIKES = 5
NUM_PHASES = 3      # Phase 1: Toggles, Phase 2: Keypad, Phase 3: Wires

# -----------------------
# Character + Story Setup
# -----------------------

CHARACTERS = ["conductor", "engineer", "student", "inspector"]

CHARACTER_INTROS = {
    "conductor": ("The Conductor:\n Born near Yankee Stadium,\n moved to Kings county, worked for the MTA near JFK,\n then exiled to The Island south of manhattan\n"),
    "engineer": ("The Engineer:\n Grew up near Coney Island,\n worked on the gird near the zoo big zoo,\n then at Citi Field,\n finally pushed out to The Island borough.\n"),
    "student": (
        "The Student: Raised on Hylan Blvd,\n worked in  Canarsie\n transferred to near the Botanical Garden,\n then betrayed at the train junction in jamicia.\n"),
    "inspector": (
        "The Inspector:\n inspected tracks on The oldest Bridge,\n worked near 162nd street\n bounced to the famous ferry\n then ended in new york citys small small airport\n"),
}

BOROUGH_TOGGLES = {
    "bronx": 1,
    "brooklyn": 2,
    "queens": 3,
    "staten island": 4,
}

CHARACTER_BOROUGH_ORDER = {
    "conductor": ["bronx", "brooklyn", "queens", "staten island"],
    "engineer": ["brooklyn", "bronx", "queens", "staten island"],
    "student": ["staten island", "brooklyn", "bronx", "queens"],
    "inspector": ["brooklyn", "bronx", "staten island", "queens"],
}

WIRE_COLORS = {
    0: "red",     # Conductor
    1: "blue",    # Engineer
    2: "orange",  # Student
    3: "yellow",  # Inspector
    4: "black",   # decoy
}

CHARACTER_WIRE_INDEX = {
    "conductor": 0,
    "engineer": 1,
    "student": 2,
    "inspector": 3,
}

character = choice(CHARACTERS)

# -----------------------
# Target Generators
# -----------------------

def genSerial():
    return "B026DES"

def genTogglesTarget():
    order = CHARACTER_BOROUGH_ORDER[character]
    return [BOROUGH_TOGGLES[b] for b in order]

def genWiresTarget():
    return CHARACTER_WIRE_INDEX[character]

def genKeypadTarget():
    # The year they are counting down to
    return "2027"

serial = genSerial()
toggles_target = genTogglesTarget()
wires_target = genWiresTarget()
keypad_target = genKeypadTarget()

boot_text = (
    "*Welcome to New York City! It's New Year's Eve 2026,"
    "you have 5 minutes to save Times Square.*\n\n"
    f"*Serial number: {serial}*\n\n"
    f"*Bomber profile: {CHARACTER_INTROS[character]}*\n\n"
    "*Phase 1: Flip the toggles in the order of where they lived"
    "(Bronx, Brooklyn, Queens, Staten Island).\n"
    "Phase 2: Enter the code everyone is chanting for the new year.\n"
    "Phase 3: Pull the wire whose color matches their final clue in Times Square.*"
)

# -----------------------
# Hardware Setup
# -----------------------

if RPi:
    import board
    from adafruit_ht16k33.segments import Seg7x4
    from digitalio import DigitalInOut, Direction, Pull
    from adafruit_matrixkeypad import Matrix_Keypad

    # 7‑segment display
    i2c = board.I2C()
    component_7seg = Seg7x4(i2c)
    component_7seg.brightness = 0.5

    # Keypad
    keypad_cols = [DigitalInOut(i) for i in (board.D10, board.D9, board.D11)]
    keypad_rows = [DigitalInOut(i) for i in (board.D5, board.D6, board.D13, board.D19)]
    keypad_keys = ((1, 2, 3), (4, 5, 6), (7, 8, 9), ("*", 0, "#"))
    component_keypad = Matrix_Keypad(keypad_rows, keypad_cols, keypad_keys)

    # Wires (5 jumper wires)
    component_wires = [DigitalInOut(i) for i in (board.D14, board.D15, board.D18, board.D23, board.D24)]
    for pin in component_wires:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

    # Button
    component_button_state = DigitalInOut(board.D4)
    component_button_state.direction = Direction.INPUT
    component_button_state.pull = Pull.DOWN

    component_button_RGB = [DigitalInOut(i) for i in (board.D17, board.D27, board.D22)]
    for pin in component_button_RGB:
        pin.direction = Direction.OUTPUT
        pin.value = True

    # Toggles (4 switches)
    component_toggles = [DigitalInOut(i) for i in (board.D12, board.D16, board.D20, board.D21)]
    for pin in component_toggles:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

else:
    component_7seg = None
    component_keypad = None
    component_wires = []
    component_button_state = None
    component_button_RGB = []
    component_toggles = []
