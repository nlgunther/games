"""Loads graded word levels from words_config.json and serves random words."""
import json
import random
from pathlib import Path

from loguru import logger

DEFAULT_CONFIG = Path(__file__).with_name("words_config.json")


class WordManager:
    """Holds the word levels. A missing or invalid config raises; there is no silent fallback."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG):
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.levels: dict[str, list[str]] = data["levels"]
        self.level_names = list(self.levels)
        self.current_level = ""
        self.set_level(data["default_level"])
        logger.info("Loaded {} word levels from {}", len(self.levels), config_path)

    def set_level(self, level_name: str) -> None:
        if level_name not in self.levels:
            raise KeyError(f"Unknown word level: {level_name!r}")
        self.current_level = level_name

    def get_word(self) -> str:
        return random.choice(self.levels[self.current_level])
