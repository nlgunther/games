import json
import os
from loguru import logger

class ScoreManager:
    def __init__(self, filename="highscores.json"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(base_dir, filename)
        self.scores = self.load_scores()

    def load_scores(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse high scores JSON: {e}")
        return {}

    def save_scores(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.scores, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving high scores: {e}")

    def update_score(self, level_name, difficulty_name, accuracy, perfect_words):
        key = f"{level_name}_{difficulty_name}"
        current_best = self.scores.get(key, {"accuracy": 0.0, "perfect_words": 0})
        is_new_record = False
        
        if (accuracy > current_best["accuracy"]) or \
           (accuracy == current_best["accuracy"] and perfect_words > current_best["perfect_words"]):
            self.scores[key] = {
                "accuracy": round(accuracy, 1),
                "perfect_words": perfect_words
            }
            self.save_scores()
            is_new_record = True
            logger.info(f"🏆 NEW HIGH SCORE for [{key}]: Accuracy {accuracy:.1f}%, Perfects: {perfect_words}")
            
        return is_new_record
