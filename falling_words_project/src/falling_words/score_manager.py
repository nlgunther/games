"""Per-level, per-difficulty high scores, saved as JSON in the user's home folder."""
import json
from pathlib import Path

from loguru import logger

# Not the package folder: that is read-only once the game is installed.
DEFAULT_SCORES_PATH = Path.home() / ".falling_words" / "highscores.json"


class ScoreManager:
    def __init__(self, filepath: Path = DEFAULT_SCORES_PATH):
        self.filepath = Path(filepath)
        self.scores = self.load_scores()

    def load_scores(self) -> dict:
        if not self.filepath.exists():
            return {}
        try:
            return json.loads(self.filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Failed to parse high scores JSON {}: {}", self.filepath, e)
            return {}

    def save_scores(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps(self.scores, indent=4), encoding="utf-8")

    def update_score(self, level_name: str, difficulty_name: str, accuracy: float, perfect_words: int) -> bool:
        """Record the score if it beats the best for this level and difficulty; True if it did.

        Example:
            update_score("1 Top row", "BEGINNER", 96.7, 12)   # True on a new record
        """
        key = f"{level_name}_{difficulty_name}"
        best = self.scores.get(key, {"accuracy": 0.0, "perfect_words": 0})
        is_record = (accuracy > best["accuracy"]
                     or (accuracy == best["accuracy"] and perfect_words > best["perfect_words"]))
        if is_record:
            self.scores[key] = {"accuracy": round(accuracy, 1), "perfect_words": perfect_words}
            self.save_scores()
            logger.info("NEW HIGH SCORE for [{}]: accuracy {:.1f}%, perfects {}", key, accuracy, perfect_words)
        return is_record
