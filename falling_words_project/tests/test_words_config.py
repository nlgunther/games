"""words_config.json is graded correctly by keyboard row and loads in the game.

Run from falling_words_project/:  uv run pytest
"""
import json
from pathlib import Path

import pytest
from build_words import rows_of  # tools/ is on pythonpath; single source of truth for row logic

from falling_words.word_manager import MAX_LEVELS, WordManager

CONFIG = Path(__file__).resolve().parents[1] / "src" / "falling_words" / "words_config.json"


@pytest.fixture(scope="module")
def cfg():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def graded(cfg):
    return {n: m for n, m in cfg["meta"].items() if m["grade"]}


def test_structure(cfg):
    assert set(cfg["levels"]) == set(cfg["meta"])
    assert cfg["default_level"] in cfg["levels"]
    assert len(cfg["levels"]) <= MAX_LEVELS


def test_every_word_is_lowercase_letters_without_duplicates(cfg):
    for name, words in cfg["levels"].items():
        assert all(w.isascii() and w.isalpha() and w.islower() for w in words), name
        assert len(words) == len(set(words)), name


def test_graded_levels_use_exactly_their_rows(cfg):
    for name, meta in graded(cfg).items():
        assert meta["grade"] == len(meta["rows"]), name
        for w in cfg["levels"][name]:
            assert rows_of(w) == meta["rows"], f"{name}: {w!r} uses {rows_of(w)}"


def test_home_hand_levels_use_only_their_keys(cfg):
    assert all(set(w) <= set("asdfg") for w in cfg["levels"]["1 Home: left"])
    assert all(set(w) <= set("hjkl") for w in cfg["levels"]["1 Home: right"])


def test_level_sizes(cfg):
    for name, meta in cfg["meta"].items():
        minimum = 10 if meta["kind"] == "theme" else 25
        assert len(cfg["levels"][name]) >= minimum, name


def test_grades_cover_one_two_and_three_rows(cfg):
    assert {m["grade"] for m in graded(cfg).values()} == {1, 2, 3}
    assert {m["rows"] for m in graded(cfg).values()} >= {"H", "T", "B", "HT", "HB", "TB", "HTB"}


def test_word_manager_loads_the_shipped_file():
    wm = WordManager()
    assert wm.current_level == "1 Home: left"
    assert wm.get_word() in wm.levels["1 Home: left"]


def test_word_manager_missing_config_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        WordManager(tmp_path / "nope.json")


def test_word_manager_unknown_level_fails_loudly():
    with pytest.raises(KeyError):
        WordManager().set_level("no such level")
