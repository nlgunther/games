"""New words must not start on top of words already falling, and speed jitter is a setting."""
import random
from dataclasses import replace

import pygame
import pytest

from falling_words.game import SPAWN_TRIES, WIDTH, WORD_GAP, WORD_HEIGHT, Game, Word
from falling_words.settings import load_settings
from falling_words.ui import WORD_COL_WIDTH, get_font


@pytest.fixture
def make_game(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr("falling_words.score_manager.DEFAULT_SCORES_PATH", tmp_path / "highscores.json")
    pygame.init()
    get_font.cache_clear()
    screen = pygame.display.set_mode((900, 650))

    def build(**settings):
        return Game(screen, settings=replace(load_settings(), **settings))

    yield build
    pygame.quit()
    get_font.cache_clear()


def box(word):
    return pygame.Rect(word.x, word.y, len(word.text) * WORD_COL_WIDTH, WORD_HEIGHT)


def assert_no_overlaps(words):
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            assert not box(a).colliderect(box(b)), f"{a.text} at {a.x},{a.y} overlaps {b.text} at {b.x},{b.y}"


@pytest.mark.parametrize("seed", range(30))
def test_rapid_spawns_never_start_on_top_of_each_other(make_game, seed):
    random.seed(seed)
    game = make_game()
    game.word_manager.set_level("3 All rows")
    game.words = []
    for _ in range(10):            # typing a word spawns the next one at once
        game.spawn_word()
    assert_no_overlaps(game.words)


def test_words_stay_inside_the_window_sideways(make_game):
    random.seed(1)
    game = make_game()
    game.word_manager.set_level("3 All rows")
    game.words = []
    for _ in range(10):
        game.spawn_word()
    assert all(w.x >= 10 and w.x + len(w.text) * WORD_COL_WIDTH <= WIDTH for w in game.words)


def test_a_crowded_top_starts_the_word_above_the_highest_one(make_game):
    game = make_game()
    word = "abcdefgh"
    game.words = [Word(x, y, word, 0) for y in (10, 100) for x in (0, 230, 460, 690)]   # covers the whole top band
    game.word_manager.get_word = lambda: "plain"
    game.spawn_word()
    new = game.words[-1]
    assert new.y <= 10 - WORD_HEIGHT - WORD_GAP
    assert not any(box(new).colliderect(box(other)) for other in game.words[:-1])   # the filler words overlap each other on purpose


def test_a_word_avoids_columns_where_a_faster_word_above_would_catch_it(make_game):
    random.seed(0)
    game = make_game()
    game.words = [Word(10, 10, "abcdefgh", 2.0)]               # fast, on the left: it would run over a slower word below it
    for _ in range(SPAWN_TRIES):
        x, _y = game._spawn_position(5 * WORD_COL_WIDTH, 1.0)
        assert x >= 10 + 8 * WORD_COL_WIDTH or x + 5 * WORD_COL_WIDTH <= 10   # never in that word's columns


def test_a_slower_word_above_is_no_reason_to_avoid_its_columns(make_game):
    random.seed(0)
    game = make_game()
    game.words = [Word(10, 10, "abcdefgh", 0.2)]               # slow: the new word falls behind it and never catches it
    xs = [game._spawn_position(5 * WORD_COL_WIDTH, 1.0)[0] for _ in range(300)]
    assert any(x < 10 + 8 * WORD_COL_WIDTH for x in xs)


def speeds(game, count=60, text="plain"):
    game.words = []
    game.word_manager.get_word = lambda: text
    out = []
    for _ in range(count):
        game.spawn_word()
        out.append(game.words[-1].speed)
        game.words = []
    return out


def test_no_jitter_by_default_so_equal_length_words_share_a_speed(make_game):
    assert len(set(speeds(make_game()))) == 1


def test_jitter_varies_speed_within_the_chosen_fraction(make_game):
    game = make_game(speed_jitter=0.1)
    base = game.current_speed * 3 / 5                          # a 5-letter word falls at 3/5 of the base speed
    values = speeds(game)
    assert len(set(values)) > 1
    assert all(base * 0.9 - 1e-9 <= v <= base * 1.1 + 1e-9 for v in values)


@pytest.mark.parametrize("bad", [-0.1, 1, 1.5, "0.1", True, None])
def test_bad_jitter_values_are_errors(tmp_path, bad):
    import json
    (tmp_path / "settings.json").write_text(json.dumps({"speed_jitter": bad}), encoding="utf-8")
    with pytest.raises(ValueError, match="speed_jitter"):
        load_settings(tmp_path)


@pytest.mark.parametrize("good", [0, 0.1, 0.5, 0.99])
def test_good_jitter_values_load(tmp_path, good):
    import json
    (tmp_path / "settings.json").write_text(json.dumps({"speed_jitter": good}), encoding="utf-8")
    assert load_settings(tmp_path).speed_jitter == good
