"""Per-player profiles: extra word themes, starting level and difficulty, and their own high scores.

A profile is profiles/<name>.json, found relative to the folder the game is started from.
Every key is optional; unknown keys are an error so typos never pass silently.

Example:
    {"start_level": "1 Top row", "difficulty": "BEGINNER",
     "themes": {"Roblox": ["avatar", "server", ...], "Discord": ["channel", "emoji", ...]}}

Run it with:  uv run falling-words --profile adam
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PROFILES_DIR = Path("profiles")
NAME_PATTERN = re.compile(r"[a-z0-9_-]+")   # also keeps the name safe to use as a folder name
MAX_WORD_LENGTH = 8     # longer words run off the right edge of the 900 px window
MIN_THEME_WORDS = 10    # a 30-point game needs variety, or words repeat constantly

# Starting speed per difficulty; a profile picks one by name.
DIFFICULTY_SETTINGS = {"BEGINNER": 1.0, "STANDARD": 1.5, "EXPERT": 2.0}

_ALLOWED_KEYS = {"start_level", "difficulty", "themes"}


@dataclass(frozen=True)
class Profile:
    name: str
    start_level: str | None = None
    difficulty: str = "BEGINNER"
    themes: dict[str, list[str]] = field(default_factory=dict)


def _check_theme(theme: str, words: list) -> None:
    if len(words) < MIN_THEME_WORDS:
        raise ValueError(f"Theme {theme!r} needs at least {MIN_THEME_WORDS} words, has {len(words)}")
    if len(words) != len(set(words)):
        raise ValueError(f"Theme {theme!r} has duplicate words")
    for w in words:
        if not (isinstance(w, str) and w.isascii() and w.isalpha() and w.islower() and len(w) <= MAX_WORD_LENGTH):
            raise ValueError(f"Theme {theme!r}: {w!r} must be lowercase letters, at most {MAX_WORD_LENGTH} long")


def load_profile(name: str, directory: Path = DEFAULT_PROFILES_DIR) -> Profile:
    """Load profiles/<name>.json. A missing or invalid profile raises; it never falls back silently.

    Example:
        load_profile("adam")   # Profile(name='adam', start_level='1 Top row', ...)
    """
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Profile name {name!r} must be lowercase letters, digits, '_' or '-'")
    path = Path(directory) / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in Path(directory).glob("*.json")) if Path(directory).is_dir() else []
        raise FileNotFoundError(f"No profile {name!r} at {path.resolve()}; available: {available or 'none'}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if unknown := set(data) - _ALLOWED_KEYS:
        raise ValueError(f"{path.name}: unknown keys {sorted(unknown)}; allowed: {sorted(_ALLOWED_KEYS)}")
    difficulty = data.get("difficulty", "BEGINNER")
    if difficulty not in DIFFICULTY_SETTINGS:
        raise ValueError(f"{path.name}: difficulty {difficulty!r} must be one of {list(DIFFICULTY_SETTINGS)}")
    themes = data.get("themes", {})
    for theme, words in themes.items():
        _check_theme(theme, words)
    return Profile(name=name, start_level=data.get("start_level"), difficulty=difficulty, themes=themes)
