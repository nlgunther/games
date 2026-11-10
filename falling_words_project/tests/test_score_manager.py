"""ScoreManager records only improvements and persists them."""
from falling_words.score_manager import ScoreManager


def test_new_record_is_saved_and_reloaded(tmp_path):
    path = tmp_path / "scores.json"
    assert ScoreManager(path).update_score("1 Top row", "BEGINNER", 90.0, 5)
    assert ScoreManager(path).scores["1 Top row_BEGINNER"] == {"accuracy": 90.0, "perfect_words": 5}


def test_worse_score_is_not_a_record(tmp_path):
    sm = ScoreManager(tmp_path / "scores.json")
    sm.update_score("L", "EXPERT", 90.0, 5)
    assert not sm.update_score("L", "EXPERT", 80.0, 9)


def test_tie_on_accuracy_broken_by_perfect_words(tmp_path):
    sm = ScoreManager(tmp_path / "scores.json")
    sm.update_score("L", "EXPERT", 90.0, 5)
    assert sm.update_score("L", "EXPERT", 90.0, 6)
    assert not sm.update_score("L", "EXPERT", 90.0, 6)
