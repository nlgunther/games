"""Per-player profiles: validation, word themes, start level, difficulty and separate high scores."""
import json
from pathlib import Path

import pytest

from falling_words.game import Game, parse_args
from falling_words.profiles import MIN_THEME_WORDS, Profile, load_profile
from falling_words.score_manager import DEFAULT_SCORES_PATH, scores_path
from falling_words.word_manager import MAX_LEVELS, WordManager

REPO_PROFILES = Path(__file__).resolve().parents[1] / "profiles"
WORDS = ["alpha", "bravo", "cobra", "delta", "eagle", "fable", "gamma", "hotel", "india", "jolly"]


def write_profile(tmp_path, name="kid", **data):
    (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_valid_profile_loads(tmp_path):
    write_profile(tmp_path, themes={"Pets": WORDS}, difficulty="EXPERT", start_level="1 Top row")
    p = load_profile("kid", tmp_path)
    assert (p.name, p.difficulty, p.start_level, p.themes) == ("kid", "EXPERT", "1 Top row", {"Pets": WORDS})


def test_empty_profile_uses_defaults(tmp_path):
    write_profile(tmp_path)
    assert load_profile("kid", tmp_path) == Profile(name="kid")


def test_missing_profile_names_the_available_ones(tmp_path):
    write_profile(tmp_path, name="adam")
    with pytest.raises(FileNotFoundError, match="adam"):
        load_profile("nobody", tmp_path)


@pytest.mark.parametrize("name", ["../secret", "Adam", "a b", ""])
def test_unsafe_profile_names_are_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        load_profile(name, tmp_path)


@pytest.mark.parametrize("bad", [
    {"colour": "red"},                                   # typo'd key
    {"difficulty": "IMPOSSIBLE"},
    {"themes": {"T": WORDS[: MIN_THEME_WORDS - 1]}},     # too few words
    {"themes": {"T": WORDS[:-1] + [WORDS[0]]}},          # duplicate
    {"themes": {"T": WORDS[:-1] + ["Upper"]}},           # not lowercase
    {"themes": {"T": WORDS[:-1] + ["waytoolongword"]}},  # runs off screen
])
def test_invalid_profiles_fail_loudly(tmp_path, bad):
    write_profile(tmp_path, **bad)
    with pytest.raises(ValueError):
        load_profile("kid", tmp_path)


def test_shipped_example_profile_is_valid():
    assert load_profile("example", REPO_PROFILES).themes


def test_profile_themes_replace_shared_themes():
    wm = WordManager(profile=Profile(name="kid", themes={"Pets": WORDS}))
    assert "Theme: Pets" in wm.levels
    assert not {"Theme: Roblox", "Theme: Lua", "Theme: German"} & set(wm.levels)
    assert "1 Home: left" in wm.levels  # graded levels stay


def test_without_profile_shared_themes_remain():
    assert "Theme: Roblox" in WordManager().levels


def test_profile_start_level_is_used_and_unknown_one_fails():
    assert WordManager(profile=Profile(name="kid", start_level="1 Top row")).current_level == "1 Top row"
    with pytest.raises(KeyError):
        WordManager(profile=Profile(name="kid", start_level="Nope"))


def test_too_many_levels_fails():
    themes = {f"T{i}": WORDS for i in range(MAX_LEVELS)}
    with pytest.raises(ValueError):
        WordManager(profile=Profile(name="kid", themes=themes))


def test_each_profile_gets_its_own_score_file():
    assert scores_path() == DEFAULT_SCORES_PATH
    assert scores_path("adam") != scores_path("david")
    assert scores_path("adam").parent.name == "adam"


def test_game_starts_at_profile_difficulty(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr("falling_words.score_manager.DEFAULT_SCORES_PATH", tmp_path / "highscores.json")
    import pygame
    pygame.init()
    game = Game(pygame.display.set_mode((900, 650)), Profile(name="kid", difficulty="EXPERT"))
    assert game.difficulties[game.difficulty_index] == "EXPERT"
    pygame.quit()


def test_command_line_profile_option():
    assert parse_args(["--profile", "adam"]).profile == "adam"
    assert parse_args([]).profile is None
