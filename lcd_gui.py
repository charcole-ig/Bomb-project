import os
import sys
import math
import time
import threading
from tkinter import *

try:
    import RPi.GPIO as GPIO
    RPi = True
except ImportError:
    RPi = False

# ─── Palette ──────────────────────────────────────────────────────────────────
BG          = "#0a0a0a"
PANEL       = "#0f0f0f"
BORDER      = "#1e1e1e"
ACCENT_RED  = "#cc1111"
ACCENT_DIM  = "#661111"
TEXT_PRI    = "#e8e8e8"
TEXT_SEC    = "#888888"
TEXT_WARN   = "#ff9900"
TEXT_GREEN  = "#22cc44"
TEXT_RED    = "#ff2222"
TIMER_CRIT  = "#ff2222"   # < 60 s
TIMER_WARN  = "#ff9900"   # < 120 s
TIMER_OK    = "#e8e8e8"   # normal

FONT_MONO   = "Courier New"
FONT_TITLE  = "Courier New"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _label(parent, text, fg=TEXT_PRI, bg=BG, size=13, weight="normal", **kw):
    return Label(parent, text=text, fg=fg, bg=bg,
                 font=(FONT_MONO, size, weight), **kw)


def _sep(parent, color=BORDER, padx=0, pady=(6, 6)):
    f = Frame(parent, bg=color, height=1)
    f.pack(fill=X, padx=padx, pady=pady)
    return f


# ─── Scanline canvas overlay ──────────────────────────────────────────────────
class Scanlines(Canvas):
    """Subtle CRT scanline effect drawn over the whole window."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg="", highlightthickness=0, **kw)
        self.configure(bg=BG)
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        for y in range(0, h, 4):
            self.create_line(0, y, w, y, fill="#000000", stipple="gray25")


# ─── Blinking dot indicator ───────────────────────────────────────────────────
class BlinkDot(Canvas):
    def __init__(self, parent, color=ACCENT_RED, size=10, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=BG, highlightthickness=0, **kw)
        self._color = color
        self._size  = size
        self._on    = True
        self._dot   = self.create_oval(1, 1, size-1, size-1, fill=color, outline="")
        self._tick()

    def _tick(self):
        self._on = not self._on
        self.itemconfig(self._dot, fill=self._color if self._on else BG)
        self.after(600, self._tick)


# ─── Section panel ────────────────────────────────────────────────────────────
class SectionPanel(Frame):
    """A bordered panel with a header label and a content area."""
    def __init__(self, parent, title, status_var=None, **kw):
        super().__init__(parent, bg=PANEL, bd=0, highlightthickness=1,
                         highlightbackground=BORDER, **kw)

        header = Frame(self, bg=BORDER)
        header.pack(fill=X)

        # left accent bar
        Frame(header, bg=ACCENT_RED, width=3).pack(side=LEFT, fill=Y)

        _label(header, f"  {title}", fg=TEXT_SEC, bg=BORDER,
               size=10, weight="normal").pack(side=LEFT, pady=6)

        if status_var:
            self._status_lbl = Label(header, textvariable=status_var,
                                     fg=TEXT_GREEN, bg=BORDER,
                                     font=(FONT_MONO, 10))
            self._status_lbl.pack(side=RIGHT, padx=10)

        self.body = Frame(self, bg=PANEL)
        self.body.pack(fill=BOTH, expand=True, padx=12, pady=10)


# ─── Timer ring (canvas arc) ──────────────────────────────────────────────────
class TimerRing(Canvas):
    """Circular arc countdown ring with large digital time in center."""
    RADIUS = 70
    SIZE   = 170

    def __init__(self, parent, **kw):
        s = self.SIZE
        super().__init__(parent, width=s, height=s, bg=BG,
                         highlightthickness=0, **kw)
        cx = cy = s // 2
        r  = self.RADIUS

        # background ring
        self.create_oval(cx-r, cy-r, cx+r, cy+r,
                         outline=BORDER, width=8)
        # arc (progress)
        self._arc = self.create_arc(cx-r, cy-r, cx+r, cy+r,
                                    start=90, extent=359.9,
                                    outline=TEXT_WARN, width=8,
                                    style=ARC)
        # time text
        self._time_txt = self.create_text(cx, cy - 10,
                                          text="05:00",
                                          fill=TEXT_PRI,
                                          font=(FONT_MONO, 26, "bold"))
        # label
        self.create_text(cx, cy + 22,
                         text="TIME LEFT",
                         fill=TEXT_SEC,
                         font=(FONT_MONO, 9))

        self._total   = 300   # seconds, updated from timer
        self._current = 300

    def update(self, seconds_left, total_seconds=None):
        if total_seconds:
            self._total = total_seconds
        self._current = max(0, seconds_left)

        fraction = self._current / self._total if self._total else 0
        extent   = fraction * 359.9

        if self._current <= 60:
            color = TIMER_CRIT
        elif self._current <= 120:
            color = TIMER_WARN
        else:
            color = TIMER_OK

        self.itemconfig(self._arc, extent=extent, outline=color)
        self.itemconfig(self._time_txt,
                        text=f"{self._current//60:02d}:{self._current%60:02d}",
                        fill=color)


# ─── Main LCD class ───────────────────────────────────────────────────────────
class Lcd(Frame):
    def __init__(self, window):
        super().__init__(window, bg=BG)
        self._window  = window
        self._timer   = None
        self._button  = None

        window.attributes("-fullscreen", True)
        window.configure(bg=BG)
        window.title("NYC BOMB DEFUSAL — CLASSIFIED")

        self._phase_vars   = []   # StringVar per phase
        self._timer_ring   = None
        self._strikes_var  = StringVar(value="")
        self._keypad_var   = StringVar(value="")
        self._wires_var    = StringVar(value="")
        self._toggles_var  = StringVar(value="")
        self._timer_var    = StringVar(value="05:00")

        self.setupBoot()

    # ── Boot scroll ───────────────────────────────────────────────────────────
    def setupBoot(self):
        self._lscroll = Label(self, bg=BG, fg=TEXT_GREEN,
                              font=(FONT_MONO, 13),
                              text="", justify=LEFT, anchor=W)
        self._lscroll.pack(fill=BOTH, expand=True, padx=20, pady=20)
        self.pack(fill=BOTH, expand=True)

    # ── Main HUD ──────────────────────────────────────────────────────────────
    def setup(self):
        # clear boot screen
        for w in self.winfo_children():
            w.destroy()

        # ── Top bar ───────────────────────────────────────────────────────────
        topbar = Frame(self, bg=ACCENT_DIM, height=2)
        topbar.pack(fill=X)

        header = Frame(self, bg=BG)
        header.pack(fill=X, padx=16, pady=(10, 4))

        # left: logo / title
        left_hdr = Frame(header, bg=BG)
        left_hdr.pack(side=LEFT)
        Label(left_hdr, text="⬡ NYC BOMB DEFUSAL", bg=BG, fg=ACCENT_RED,
              font=(FONT_MONO, 15, "bold")).pack(anchor=W)
        Label(left_hdr, text="CLASSIFIED — AUTHORIZED PERSONNEL ONLY",
              bg=BG, fg=TEXT_SEC, font=(FONT_MONO, 9)).pack(anchor=W)

        # right: live blink + strikes
        right_hdr = Frame(header, bg=BG)
        right_hdr.pack(side=RIGHT, padx=8)
        blink_row = Frame(right_hdr, bg=BG)
        blink_row.pack(anchor=E)
        BlinkDot(blink_row, color=ACCENT_RED).pack(side=LEFT, padx=(0, 6))
        Label(blink_row, text="LIVE", bg=BG, fg=ACCENT_RED,
              font=(FONT_MONO, 10, "bold")).pack(side=LEFT)

        self._strikes_lbl = Label(right_hdr, textvariable=self._strikes_var,
                                  bg=BG, fg=TEXT_WARN,
                                  font=(FONT_MONO, 13, "bold"))
        self._strikes_lbl.pack(anchor=E, pady=(4, 0))

        Frame(self, bg=BORDER, height=1).pack(fill=X)

        # ── Main body ─────────────────────────────────────────────────────────
        body = Frame(self, bg=BG)
        body.pack(fill=BOTH, expand=True, padx=16, pady=10)

        # left column
        left_col = Frame(body, bg=BG)
        left_col.pack(side=LEFT, fill=BOTH, expand=True)

        # right column (timer ring)
        right_col = Frame(body, bg=BG)
        right_col.pack(side=RIGHT, fill=Y, padx=(16, 0))

        self._timer_ring = TimerRing(right_col)
        self._timer_ring.pack(pady=(0, 16))

        # phase indicator dots
        phase_row = Frame(right_col, bg=BG)
        phase_row.pack()
        Label(phase_row, text="PHASES", bg=BG, fg=TEXT_SEC,
              font=(FONT_MONO, 9)).pack()
        self._phase_dots = []
        dots_row = Frame(right_col, bg=BG)
        dots_row.pack(pady=6)
        for i in range(3):
            c = Canvas(dots_row, width=14, height=14, bg=BG,
                       highlightthickness=0)
            c.pack(side=LEFT, padx=4)
            dot = c.create_oval(2, 2, 12, 12, fill=BORDER, outline="")
            self._phase_dots.append((c, dot))

        # ── Sections ──────────────────────────────────────────────────────────
        # Toggles
        tog_panel = SectionPanel(left_col, "PHASE 1 — BOROUGH TOGGLES",
                                 status_var=self._toggles_var)
        tog_panel.pack(fill=X, pady=(0, 8))
        self._ltoggle_body = tog_panel.body

        # Keypad
        kp_panel = SectionPanel(left_col, "PHASE 2 — KEYPAD CODE",
                                status_var=self._keypad_var)
        kp_panel.pack(fill=X, pady=(0, 8))
        self._lkeypad_body = kp_panel.body

        # Wires
        wire_panel = SectionPanel(left_col, "PHASE 3 — WIRE SELECTION",
                                  status_var=self._wires_var)
        wire_panel.pack(fill=X, pady=(0, 8))
        self._lwires_body = wire_panel.body

        # ── Default content labels (updated by game logic) ────────────────────
        self._ltimer = Label(self._ltoggle_body, textvariable=self._toggles_var,
                             bg=PANEL, fg=TEXT_PRI, font=(FONT_MONO, 13))

        self._lkeypad = Label(self._lkeypad_body, textvariable=self._keypad_var,
                              bg=PANEL, fg=TEXT_PRI, font=(FONT_MONO, 13))
        self._lkeypad.pack(anchor=W)

        self._lwires = Label(self._lwires_body, textvariable=self._wires_var,
                             bg=PANEL, fg=TEXT_PRI, font=(FONT_MONO, 13))
        self._lwires.pack(anchor=W)

        # bottom status bar
        Frame(self, bg=BORDER, height=1).pack(fill=X)
        statusbar = Frame(self, bg="#0a0000", height=28)
        statusbar.pack(fill=X)
        Label(statusbar, text="  NYPD BOMB SQUAD  |  TIMES SQUARE  |  DEC 31 2026  |  23:55:00",
              bg="#0a0000", fg=ACCENT_DIM,
              font=(FONT_MONO, 9)).pack(side=LEFT, pady=6)

        self._status_right = Label(statusbar, text="DEVICE ACTIVE  ●",
                                   bg="#0a0000", fg=ACCENT_RED,
                                   font=(FONT_MONO, 9))
        self._status_right.pack(side=RIGHT, padx=12, pady=6)

    # ── Public setters ────────────────────────────────────────────────────────
    def setTimer(self, timer):
        self._timer = timer

    def setButton(self, button):
        self._button = button

    def updateTimer(self, seconds_left, total_seconds=None):
        """Call this every second from your timer component."""
        if self._timer_ring:
            self._timer_ring.update(seconds_left, total_seconds)

    def updateStrikes(self, strikes_left):
        icons = "▮" * strikes_left + "▯" * (3 - strikes_left)
        self._strikes_var.set(f"STRIKES  {icons}")

    def updateKeypad(self, text):
        self._keypad_var.set(text)

    def updateWires(self, text):
        self._wires_var.set(text)

    def updateToggles(self, text):
        self._toggles_var.set(text)

    def setPhaseComplete(self, phase_index):
        """Mark phase dot as complete (0-indexed)."""
        if phase_index < len(self._phase_dots):
            c, dot = self._phase_dots[phase_index]
            c.itemconfig(dot, fill=TEXT_GREEN)

    def setPhaseActive(self, phase_index):
        """Highlight active phase dot."""
        if phase_index < len(self._phase_dots):
            c, dot = self._phase_dots[phase_index]
            c.itemconfig(dot, fill=TEXT_WARN)

    # ── Conclusion ────────────────────────────────────────────────────────────
    def conclusion(self, success=False):
        for w in self.winfo_children():
            w.destroy()

        outer = Frame(self, bg=BG)
        outer.pack(fill=BOTH, expand=True)

        # full-height dramatic accent bar
        Frame(outer, bg=ACCENT_RED if not success else TEXT_GREEN,
              width=4).pack(side=LEFT, fill=Y)

        content = Frame(outer, bg=BG)
        content.pack(fill=BOTH, expand=True, padx=40)

        # spacer
        Frame(content, bg=BG, height=60).pack()

        if success:
            Label(content, text="BOMB DEFUSED", bg=BG, fg=TEXT_GREEN,
                  font=(FONT_MONO, 48, "bold")).pack()
            Label(content, text="NEW YORK CITY IS SAVED",
                  bg=BG, fg=TEXT_GREEN,
                  font=(FONT_MONO, 20)).pack(pady=(8, 0))
            Label(content, text="Outstanding work, Agent. Times Square lives to ring in the New Year.",
                  bg=BG, fg=TEXT_SEC,
                  font=(FONT_MONO, 12),
                  wraplength=600, justify=CENTER).pack(pady=(20, 0))
        else:
            Label(content, text="DETONATION", bg=BG, fg=ACCENT_RED,
                  font=(FONT_MONO, 56, "bold")).pack()
            Label(content, text="NEW YORK CITY HAS FALLEN",
                  bg=BG, fg=ACCENT_RED,
                  font=(FONT_MONO, 20)).pack(pady=(8, 0))
            Label(content, text="The Conductor's device detonated at midnight. 100,000 lives lost.",
                  bg=BG, fg=TEXT_SEC,
                  font=(FONT_MONO, 12),
                  wraplength=600, justify=CENTER).pack(pady=(20, 0))

        Frame(content, bg=BORDER, height=1).pack(fill=X, pady=30)

        btn_row = Frame(content, bg=BG)
        btn_row.pack()

        Button(btn_row, text="[ RETRY MISSION ]",
               bg=BG, fg=TEXT_WARN,
               font=(FONT_MONO, 14),
               relief=FLAT, bd=0,
               activebackground=BG,
               activeforeground=ACCENT_RED,
               cursor="hand2",
               command=self.retry).pack(side=LEFT, padx=20)

        Button(btn_row, text="[ ABORT ]",
               bg=BG, fg=TEXT_SEC,
               font=(FONT_MONO, 14),
               relief=FLAT, bd=0,
               activebackground=BG,
               activeforeground=ACCENT_RED,
               cursor="hand2",
               command=self._quit).pack(side=LEFT, padx=20)

    def retry(self):
        os.execv(sys.executable, ["python3"] + [sys.argv[0]])

    def _quit(self):
        if RPi and self._timer and self._timer._component:
            self._timer._running = False
            self._timer._component.blink_rate = 0
            self._timer._component.fill(0)
        exit(0)
