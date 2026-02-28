import json
import random
import os
from loguru import logger

class WordManager:
    def __init__(self, config_filename="words_config.json"):
        self.levels = {}
        self.level_names = []
        self.current_level = ""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, config_filename)
        self.load_config(self.config_path)

    def load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            self.levels = data.get("levels", {})
            self.level_names = list(self.levels.keys())
            self.set_level(data.get("default_level", ""))
            logger.info(f"Successfully loaded word configuration from {config_path}")
        except FileNotFoundError:
            logger.error(f"Config file {config_path} not found.")
            self.levels = {"default": ["error", "missing", "json"]}
            self.level_names = ["default"]
            self.set_level("default")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_path}: {e}")
            self.levels = {"default": ["json", "format", "error"]}
            self.level_names = ["default"]
            self.set_level("default")

    def set_level(self, level_name):
        if level_name in self.levels:
            self.current_level = level_name
        else:
            logger.warning(f"Level '{level_name}' not found.")

    def cycle_level(self):
        if not self.level_names:
            return "default"
        current_idx = self.level_names.index(self.current_level)
        next_idx = (current_idx + 1) % len(self.level_names)
        self.set_level(self.level_names[next_idx])
        return self.current_level

    def get_word(self):
        if not self.levels or not self.current_level:
            return "error"
        return random.choice(self.levels[self.current_level])
