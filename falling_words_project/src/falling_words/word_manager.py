"""Loads graded word levels from words_config.json and serves random words."""
import json
import random
from pathlib import Path

from loguru import logger

from .profiles import Profile

DEFAULT_CONFIG = Path(__file__).with_name("words_config.json")
MAX_LEVELS = 14  # dropdown rows (40 px each) must fit in the 650 px window
THEME_META = {"grade": None, "rows": "mixed", "kind": "theme"}


class WordManager:
    """Holds the word levels. A missing or invalid config raises; there is no silent fallback.

    A profile's themes replace the shared themes, and its start_level replaces the default level.
    """

    def __init__(self, config_path: Path = DEFAULT_CONFIG, profile: Profile | None = None):
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.levels: dict[str, list[str]] = dict(data["levels"])
        self.meta: dict[str, dict] = dict(data.get("meta", {}))
        if profile and profile.themes:
            shared = {n for n, m in self.meta.items() if m.get("kind") == "theme"}
            self.levels = {n: w for n, w in self.levels.items() if n not in shared}
            self.meta = {n: m for n, m in self.meta.items() if n not in shared}
            for theme, words in profile.themes.items():
                self.levels[f"Theme: {theme}"] = list(words)
                self.meta[f"Theme: {theme}"] = dict(THEME_META)
        if len(self.levels) > MAX_LEVELS:
            raise ValueError(f"{len(self.levels)} levels is more than the {MAX_LEVELS} the menu can show")
        self.level_names = list(self.levels)
        self.current_level = ""
        self.set_level((profile.start_level if profile else None) or data["default_level"])
        logger.info("Loaded {} word levels from {}", len(self.levels), config_path)

    def set_level(self, level_name: str) -> None:
        if level_name not in self.levels:
            raise KeyError(f"Unknown word level {level_name!r}; choose from {self.level_names}")
        self.current_level = level_name

    def get_word(self) -> str:
        return random.choice(self.levels[self.current_level])

    def level_letters(self) -> set[str]:
        """Every letter used by the current level's words (the keys the player will need)."""
        return set("".join(self.levels[self.current_level]))

    def next_graded_level(self) -> str:
        """The level after the current one in menu order if both are row-graded, else "" (none)."""
        i = self.level_names.index(self.current_level)
        if i + 1 >= len(self.level_names):
            return ""
        pair = (self.current_level, self.level_names[i + 1])
        return pair[1] if all(self.meta.get(n, {}).get("grade") for n in pair) else ""
