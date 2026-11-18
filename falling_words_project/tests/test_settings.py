"""game_settings.json / settings.json, and the speed factor they feed while finger codes are shown."""
import json
import shutil
from dataclasses import fields, replace
from pathlib import Path

import pygame
import pytest

from falling_words.game import SPEED_INCREASE_PER_WORD, Game
from falling_words.settings import DEFAULT_SETTINGS_PATH, OVERRIDE_NAME, _RULES, Settings, load_settings, override_dir_for
from falling_words.ui import get_font


PROJECT_DIR = Path(__file__).resolve().parent.parent


def settings_with(**changes) -> Settings:
    """The packaged settings with some values forced, so tests never depend on what the file currently holds."""
    return replace(load_settings(), **changes)


def write_override(directory, **data):
    (directory / OVERRIDE_NAME).write_text(json.dumps(data), encoding="utf-8")


def test_packaged_defaults_load_whatever_value_the_file_holds():
    shipped = json.loads(DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8"))["finger_codes_speed_factor"]
    assert load_settings().finger_codes_speed_factor == shipped > 0


def test_settings_fields_defaults_file_and_rules_stay_in_step():
    names = {f.name for f in fields(Settings)}
    assert set(json.loads(DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8"))) == names
    assert set(_RULES) == names


def test_override_file_replaces_the_default(tmp_path):
    write_override(tmp_path, finger_codes_speed_factor=0.25)
    assert load_settings(tmp_path).finger_codes_speed_factor == 0.25


def test_missing_override_file_or_folder_uses_defaults(tmp_path):
    defaults = load_settings(None)
    assert load_settings(tmp_path) == defaults
    assert load_settings(tmp_path / "nowhere") == defaults


def test_unknown_key_is_an_error_that_names_the_allowed_ones(tmp_path):
    write_override(tmp_path, finger_code_speed_factor=0.5)   # typo: "code"
    with pytest.raises(ValueError, match="unknown settings.*allowed:.*finger_codes_speed_factor.*ramp_up_by_default"):
        load_settings(tmp_path)


@pytest.mark.parametrize("bad", [0, -1, "0.5", None, True, [0.5]])
def test_bad_values_are_errors(tmp_path, bad):
    write_override(tmp_path, finger_codes_speed_factor=bad)
    with pytest.raises(ValueError, match="finger_codes_speed_factor"):
        load_settings(tmp_path)


def test_invalid_json_error_names_the_file(tmp_path):
    (tmp_path / OVERRIDE_NAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="settings.json.*not valid JSON"):
        load_settings(tmp_path)


def test_non_object_json_is_an_error(tmp_path):
    (tmp_path / OVERRIDE_NAME).write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a JSON object"):
        load_settings(tmp_path)


@pytest.fixture
def game(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr("falling_words.score_manager.DEFAULT_SCORES_PATH", tmp_path / "highscores.json")
    pygame.init()
    get_font.cache_clear()
    # an explicit factor, so these tests do not depend on the value currently in game_settings.json
    yield Game(pygame.display.set_mode((900, 650)), settings=settings_with(finger_codes_speed_factor=0.5))
    pygame.quit()
    get_font.cache_clear()


def test_speed_is_halved_with_finger_codes(game):
    game.ramp_box.checked = False
    assert game.speed_now() == pytest.approx(game.current_speed)
    game.codes_box.checked = True
    assert game.speed_now() == pytest.approx(game.current_speed / 2)


def test_halving_applies_to_the_ramp_too(game):
    game.words_typed = 10
    game.ramp_box.checked = True
    game.codes_box.checked = True
    assert game.speed_now() == pytest.approx((game.current_speed + 10 * SPEED_INCREASE_PER_WORD) / 2)


def test_factor_comes_from_the_settings_passed_in(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr("falling_words.score_manager.DEFAULT_SCORES_PATH", tmp_path / "highscores.json")
    pygame.init()
    get_font.cache_clear()
    g = Game(pygame.display.set_mode((900, 650)), settings=settings_with(finger_codes_speed_factor=0.25))
    g.ramp_box.checked, g.codes_box.checked = False, True
    assert g.speed_now() == pytest.approx(g.current_speed * 0.25)
    pygame.quit()
    get_font.cache_clear()


def test_toggling_finger_codes_restarts_the_game(game):
    game.words_typed = 5
    game.codes_box.checked = True
    game.apply_finger_codes()
    assert game.words_typed == 0


def test_scores_with_finger_codes_are_kept_apart(game):
    game.ramp_box.checked = True
    assert game.score_key() == "speed 1.0 ramp"
    game.codes_box.checked = True
    assert game.score_key() == "speed 1.0 ramp codes"


def test_speed_up_is_off_by_default():
    assert load_settings().ramp_up_by_default is False


@pytest.mark.parametrize("bad", [1, 0, "true", None, [True]])
def test_ramp_default_must_be_true_or_false(tmp_path, bad):
    write_override(tmp_path, ramp_up_by_default=bad)
    with pytest.raises(ValueError, match="ramp_up_by_default.*true or false"):
        load_settings(tmp_path)


def test_override_can_turn_the_speed_up_default_on(tmp_path):
    write_override(tmp_path, ramp_up_by_default=True)
    assert load_settings(tmp_path).ramp_up_by_default is True


def _game_with(monkeypatch, tmp_path, **changes):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr("falling_words.score_manager.DEFAULT_SCORES_PATH", tmp_path / "highscores.json")
    pygame.init()
    get_font.cache_clear()
    return Game(pygame.display.set_mode((900, 650)), settings=settings_with(**changes))


@pytest.mark.parametrize("default", [True, False])
def test_the_checkbox_starts_as_the_setting_says(monkeypatch, tmp_path, default):
    game = _game_with(monkeypatch, tmp_path, ramp_up_by_default=default)
    assert game.ramp_box.checked is default
    pygame.quit()
    get_font.cache_clear()


def test_override_lives_next_to_the_profiles_folder(tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    assert override_dir_for(profiles) == tmp_path.resolve()
    write_override(tmp_path, ramp_up_by_default=True)           # beside profiles/, not inside it
    assert load_settings(override_dir_for(profiles)).ramp_up_by_default is True
    (profiles / OVERRIDE_NAME).write_text(json.dumps({"ramp_up_by_default": False}), encoding="utf-8")
    assert load_settings(override_dir_for(profiles)).ramp_up_by_default is True   # the one inside profiles/ is ignored


def test_example_file_is_complete_and_valid(tmp_path):
    example = PROJECT_DIR / "settings.example.json"
    assert set(json.loads(example.read_text(encoding="utf-8"))) == {f.name for f in fields(Settings)}
    shutil.copy(example, tmp_path / OVERRIDE_NAME)
    load_settings(tmp_path)                                    # raises if the template is invalid
