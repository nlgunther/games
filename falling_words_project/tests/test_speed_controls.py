"""Speed slider, ramp-up checkbox, and the high-score key they feed."""
import pygame
import pytest

from falling_words.game import SPEED_INCREASE_PER_WORD, Game
from falling_words.ui import Checkbox, Slider, get_font


@pytest.fixture
def pg(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setattr("falling_words.score_manager.DEFAULT_SCORES_PATH", tmp_path / "highscores.json")
    pygame.init()
    get_font.cache_clear()   # cached fonts die with pygame.quit(); never reuse them across tests
    yield pygame
    pygame.quit()
    get_font.cache_clear()


def mouse(pg, kind, x, y=0):
    return pg.event.Event(kind, pos=(x, y), button=1)


def test_slider_snaps_and_clamps():
    s = Slider(100, 50, 200, minimum=0.5, maximum=2.5, step=0.1, value=1.0)
    assert s.value_at(100) == 0.5
    assert s.value_at(300) == 2.5
    assert s.value_at(-50) == 0.5 and s.value_at(999) == 2.5
    assert s.value_at(200) == 1.5


def test_slider_rejects_out_of_range_start():
    with pytest.raises(ValueError):
        Slider(0, 0, 100, minimum=0.5, maximum=2.5, step=0.1, value=3.0)


def test_slider_reports_change_only_on_release(pg):
    s = Slider(100, 50, 200, minimum=0.5, maximum=2.5, step=0.1, value=1.0)
    assert not s.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 200, 50))
    assert not s.handle_event(mouse(pg, pg.MOUSEMOTION, 260, 50))
    assert s.value == 2.1
    assert s.handle_event(mouse(pg, pg.MOUSEBUTTONUP, 260, 50))


def test_slider_click_without_change_is_not_a_change(pg):
    s = Slider(100, 50, 200, minimum=0.5, maximum=2.5, step=0.1, value=1.5)
    s.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 200, 50))
    assert not s.handle_event(mouse(pg, pg.MOUSEBUTTONUP, 200, 50))


def test_slider_ignores_clicks_elsewhere(pg):
    s = Slider(100, 50, 200, minimum=0.5, maximum=2.5, step=0.1, value=1.0)
    s.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 200, 400))
    assert not s.dragging and s.value == 1.0


def test_checkbox_toggles_on_click(pg):
    box = Checkbox(10, 10, "Speed up as I go", checked=True)
    assert box.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 15, 20)) and not box.checked
    assert not box.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 500, 500))


def test_ramp_adds_speed_per_word_only_when_ticked(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.words_typed = 10
    assert game.speed_now() == pytest.approx(game.current_speed + 10 * SPEED_INCREASE_PER_WORD)
    game.ramp_box.checked = False
    assert game.speed_now() == game.current_speed


def test_score_key_separates_speed_and_ramp(pg):
    game = Game(pg.display.set_mode((900, 650)))
    assert game.score_key() == "speed 1.0 ramp"
    game.ramp_box.checked = False
    assert game.score_key() == "speed 1.0 fixed"


def test_top_row_buttons_do_not_overlap(pg):
    game = Game(pg.display.set_mode((900, 650)))
    rects = [game.dropdown.rect, game.fx_button.rect, game.exit_button.rect, game.reset_button.rect]
    for i, a in enumerate(rects):
        assert a.right <= 900
        for b in rects[i + 1:]:
            assert not a.colliderect(b)


def test_exit_button_click_is_detected(pg):
    game = Game(pg.display.set_mode((900, 650)))
    assert game.exit_button.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, *game.exit_button.rect.center))
    assert not game.exit_button.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 5, 600))
