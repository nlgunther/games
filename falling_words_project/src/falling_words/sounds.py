"""Sound effects via winsound (Windows only). Silent no-op on other systems.

Example:
    play("correct")   # beeps on Windows, does nothing elsewhere
"""
try:
    import winsound
except ImportError:  # not Windows
    winsound = None

ENABLED = winsound is not None

# name -> (frequency Hz, duration ms)
BEEPS = {
    "correct": (880, 150),
    "incorrect": (220, 200),
    "victory": (784, 3000),
    "game_over_good": (523, 3000),
    "game_over_bad": (196, 1000),
}


def play(name: str) -> None:
    """Play a named beep. An unknown name raises KeyError, so typos fail loudly."""
    frequency, duration_ms = BEEPS[name]
    if ENABLED:
        winsound.Beep(frequency, duration_ms)
