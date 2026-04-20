# CSC 102 Defuse the Bomb Project
# Configuration file
# Team: Save Times Square

from random import choice

DEBUG = False
RPi = False

SHOW_BUTTONS = False
COUNTDOWN = 600          # 10 minutes
NUM_STRIKES = 5
NUM_PHASES = 3           # Toggles → Keypad → Wires

# -----------------------
# Character + Story Setup
# -----------------------

CHARACTERS = ["conductor", "engineer", "student", "inspector"]

CHARACTER_INTROS = {
    "conductor": (
        "The Conductor: A former MTA engineer with a grudge. "
        "He wired the bomb into the New Year's Eve ball mechanism."
    ),
    "engineer": (
        "The Engineer: Marcus, a construction worker's son, pushed out of the system "
        "after years maintaining the city's infrastructure."
    ),
    "student": (
        "The Student: Carmen, an urban planner whose work was scrapped for a private airport deal. "
        "She never forgave the city."
    ),
    "inspector": (
        "The Inspector: Ray, a third‑generation New Yorker forced into early retirement "
        "by automated inspection drones."
    ),
}

# Toggle mapping
BOROUGH_TOGGLES = {
    "bronx": 1,
    "brooklyn": 2,
    "queens": 3,
    "staten island": 4,
}

# Borough order per character
CHARACTER_BOROUGH_ORDER = {
    "conductor": ["bronx", "brooklyn", "queens", "staten island"],
    "engineer": ["brooklyn", "bronx", "queens", "staten island"],
    "student": ["staten island", "brooklyn", "bronx", "queens"],
    "inspector": ["brooklyn", "bronx", "staten island", "queens"],
}

# Wire color mapping
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

# Choose character
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
    return "2027"

serial = genSerial()
toggles_target = genTogglesTarget()
wires_target = genWiresTarget()
keypad_target = genKeypadTarget()

# -----------------------
# Boot Text
# -----------------------

boot_text = (
    "*Welcome to New York City! It's New Year's Eve 2026, and you have 10 minutes to save Times Square.*\n\n"
    f"*Serial number: {serial}*\n\n"
    f"*Bomber profile: {CHARACTER_INTROS[character]}*\n\n"
    "*Phase 1: Flip the toggles in the order of where they lived.*\n"
    "*Phase 2: Enter the code everyone is chanting for the new year.*\n"
    "*Phase 3: Pull the wire whose color matches their final clue.*"
)

# -----------------------
# Hardware Setup (unchanged)
# -----------------------

if RPi:
    import board
    from adafruit_ht16k33.segments import Seg7x4
    from digitalio import DigitalInOut, Direction, Pull
    from adafruit_matrixkeypad import Matrix_Keypad

    # 7‑segment
    i2c = board.I2C()
    component_7seg = Seg7x4(i2c)
    component_7seg.brightness = 0.5

    # Keypad
    keypad_cols = [DigitalInOut(i) for i in (board.D10, board.D9, board.D11)]
    keypad_rows = [DigitalInOut(i) for i in (board.D5, board.D6, board.D13, board.D19)]
    keypad_keys = ((1,2,3),(4,5,6),(7,8,9),("*",0,"#"))
    component_keypad = Matrix_Keypad(keypad_rows, keypad_cols, keypad_keys)

    # Wires
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

    # Toggles
    component_toggles = [DigitalInOut(i) for i in (board.D12, board.D16, board.D20, board.D21)]
    for pin in component_toggles:
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

else:
    # Simulation placeholders
    component_7seg = None
    component_keypad = None
    component_wires = [None]*5
    component_button_state = None
    component_button_RGB = [None]*3
    component_toggles = [None]*4
