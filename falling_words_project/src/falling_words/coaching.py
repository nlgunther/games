"""Typing coaching: which finger types which key, and the messages shown to the player.

Everything here is pure (no pygame), so it is easy to test. `name` is the player's display
name, or "" when playing without a profile.

Example:
    intro_card("Adam", set("asdfg")).title
    # -> "Adam - now we're going to work on the home row."
"""
from dataclasses import dataclass

# QWERTY keys, left to right. Punctuation keys are only drawn on the keyboard picture.
KEY_ROWS = ("qwertyuiop", "asdfghjkl;", "zxcvbnm,./")
ROW_NAMES = ("top", "home", "bottom")
ROWS = {name: "".join(c for c in keys if c.isalpha()) for name, keys in zip(ROW_NAMES, KEY_ROWS)}
ROW_ORDER = ("home", "top", "bottom")   # the order rows are named in messages

# Each finger covers one or two columns; the index fingers cover two (r/t, f/g, v/b and y/u, h/j, n/m).
_LEFT = (("pinky", "qaz"), ("ring", "wsx"), ("middle", "edc"), ("index", "rfv"), ("index", "tgb"))
_RIGHT = (("index", "yhn"), ("index", "ujm"), ("middle", "ik,"), ("ring", "ol."), ("pinky", "p;/"))
FINGER_OF = ({k: ("left", f) for f, keys in _LEFT for k in keys}
             | {k: ("right", f) for f, keys in _RIGHT for k in keys})

HOME_LEFT, HOME_RIGHT = "asdf", "jkl;"
NEXT_LEVEL_ACCURACY = 80   # a win at or above this suggests moving on
STREAK_STEP = 5            # cheer every this many perfect words in a row
_CHEERS = ("{n} perfect words in a row!", "{n} in a row - keep that rhythm!", "{n} perfect - no mistakes!")


@dataclass(frozen=True)
class IntroCard:
    title: str
    lines: tuple[str, ...]
    keys: frozenset[str]   # keys to highlight on the keyboard picture


def display_name(profile_name: str) -> str:
    """'adam' -> 'Adam', 'mary-ann' -> 'Mary Ann'."""
    return profile_name.replace("-", " ").replace("_", " ").title()


def _keys_text(keys) -> str:
    return " ".join(k.upper() for k in keys)


def _rows_phrase(rows: list[str]) -> str:
    if len(rows) == 3:
        return "all three rows"
    return "the " + " and ".join(rows) + (" rows" if len(rows) > 1 else " row")


def intro_card(name: str, letters) -> IntroCard:
    """Finger-placement guidance for a level that uses `letters`.

    Example:
        intro_card("", set("qwerty")).title   # "Now we're going to work on the top row."
    """
    letters = set(letters)
    rows = [r for r in ROW_ORDER if letters & set(ROWS[r])]
    work = f"now we're going to work on {_rows_phrase(rows)}."
    title = f"{name} - {work}" if name else work.capitalize()
    lines = [f"Rest your left fingers on {_keys_text(HOME_LEFT)} and your right fingers on "
             f"{_keys_text(HOME_RIGHT)}. Your index fingers also reach G and H."]
    for row, verb in (("top", "up"), ("bottom", "down")):
        used = [k for k in ROWS[row] if k in letters]
        if used:
            lines.append(f"Reach {verb} for the {row} row ({_keys_text(used)}), then come back to the home row.")
    hands = {FINGER_OF[k][0] for k in letters}
    if len(hands) == 1:
        idle = "right" if hands == {"left"} else "left"
        lines.append(f"Only your {hands.pop()} hand is busy here; keep your {idle} fingers resting on the home row.")
    # The resting keys are always shown (including ";"), since the fingers start there.
    return IntroCard(title, tuple(lines), frozenset(letters) | set(HOME_LEFT) | set(HOME_RIGHT))


def suggested_level(won: bool, accuracy: float, next_level: str) -> str:
    """The level to suggest after a game, or "" for none (needs a win with good accuracy)."""
    return next_level if won and accuracy >= NEXT_LEVEL_ACCURACY else ""


def result_lines(name: str, won: bool, accuracy: float, perfect_words: int, suggested: str) -> list[str]:
    """Three lines for the end screen: a verdict, the perfect-word count, and what to press next."""
    if won:
        verdict = ("Excellent accuracy. You are ready to move on." if accuracy >= 95 else
                   "Solid work. Accuracy is the goal; speed follows." if accuracy >= NEXT_LEVEL_ACCURACY else
                   "You finished it! Next time, slow down a little and aim for fewer misses.")
    else:
        verdict = ("So close. Words piled up; steady typing beats fast typing." if accuracy >= 50 else
                   "That one was tough. Slow down and get each word right; speed comes later.")
    perfect = (f"{perfect_words} perfect words (no backspace, no mistakes)." if perfect_words
               else "Try for a perfect word: no backspace, no mistakes.")
    action = f"Next up: {suggested}. Press Enter to go there." if suggested else "Press Enter to play this level again."
    return [f"{name}: {verdict}" if name else verdict, perfect, action]


def streak_cheers(name: str, streak: int) -> list[str]:
    """A cheer when `streak` perfect words in a row hits a multiple of STREAK_STEP, else an empty list."""
    if streak == 0 or streak % STREAK_STEP:
        return []
    text = _CHEERS[(streak // STREAK_STEP - 1) % len(_CHEERS)].format(n=streak)
    return [f"{name}: {text}" if name else text]
