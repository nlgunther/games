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
    game.ramp_box.checked = True
    assert game.speed_now() == pytest.approx(game.current_speed + 10 * SPEED_INCREASE_PER_WORD)
    game.ramp_box.checked = False
    assert game.speed_now() == game.current_speed


def test_score_key_separates_speed_and_ramp(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.ramp_box.checked = True
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


def test_finger_codes_box_turns_pictures_off_without_toggling(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.sprite_manager.enabled = True
    game.codes_box.checked = True
    game.apply_finger_codes()
    assert not game.sprite_manager.enabled and game.fx_button.text.endswith("OFF")
    game.apply_finger_codes()                      # already off: must stay off, not flip on
    assert not game.sprite_manager.enabled


def test_unticking_codes_box_leaves_pictures_alone(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.codes_box.checked = True
    game.apply_finger_codes()
    game.codes_box.checked = False
    game.apply_finger_codes()
    assert not game.sprite_manager.enabled


def test_fx_button_still_works_alone(pg):
    game = Game(pg.display.set_mode((900, 650)))
    before = game.sprite_manager.enabled
    game.sprite_manager.toggle()
    assert game.sprite_manager.enabled != before


def test_words_fit_the_window_in_both_draw_modes(pg):
    from falling_words.ui import WORD_COL_WIDTH
    game = Game(pg.display.set_mode((900, 650)))
    game.word_manager.set_level("3 All rows")
    for _ in range(300):
        game.spawn_word()
    assert all(w.x + len(w.text) * WORD_COL_WIDTH <= 900 for w in game.words)


def test_game_waits_at_the_guide_so_options_can_be_set(pg):
    game = Game(pg.display.set_mode((900, 650)))
    assert game.intro_open
    y_before = [w.y for w in game.words]
    game.update()
    assert [w.y for w in game.words] == y_before          # paused behind the guide
    game.reset_game()                                      # e.g. after moving the slider
    assert game.intro_open
    game.dismiss_intro()
    assert not game.intro_open


def test_guide_card_leaves_the_options_and_start_button_uncovered(pg):
    from falling_words.game import INTRO_CARD
    from falling_words.ui import KEYBOARD_WIDTH
    game = Game(pg.display.set_mode((900, 650)))
    top_row = [game.dropdown.rect, game.fx_button.rect, game.exit_button.rect, game.reset_button.rect]
    assert all(r.bottom <= INTRO_CARD.top for r in top_row)               # buttons above the card
    keyboard_right = INTRO_CARD.left + 25 + KEYBOARD_WIDTH
    track = pg.Rect(game.speed_slider.left, game.speed_slider.y - 11, game.speed_slider.width, 22)
    controls = [track, game.ramp_box.hit_rect, game.codes_box.hit_rect, game.start_button.rect]
    assert all(keyboard_right < r.left for r in controls)                  # keyboard picture stays left of them
    assert all(INTRO_CARD.contains(r) for r in controls)
    for i, a in enumerate(controls):
        assert not any(a.colliderect(b) for b in controls[i + 1:])


def test_options_are_drawn_over_the_guide(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.speed_slider.value = 1.5
    game.draw()
    knob_x = game.speed_slider.left + round((1.5 - 0.5) / 2.0 * game.speed_slider.width)
    ring = (knob_x, game.speed_slider.y - 9)                                  # the knob's white rim
    assert tuple(game.screen.get_at(ring))[:3] == (255, 255, 255)           # slider knob visible on the card
    start = game.start_button.rect
    assert tuple(game.screen.get_at((start.left + 5, start.centery)))[:3] != (20, 20, 45)   # START, not card color


def test_start_button_click_is_detected_only_on_the_button(pg):
    game = Game(pg.display.set_mode((900, 650)))
    assert game.start_button.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, *game.start_button.rect.center))
    assert not game.start_button.handle_event(mouse(pg, pg.MOUSEBUTTONDOWN, 100, 300))


def click(pg, game, widget_or_pos):
    """Left-click on a widget's centre (or a point), as the main loop would route it. True means EXIT."""
    x, y = widget_or_pos if isinstance(widget_or_pos, tuple) else widget_or_pos.rect.center
    return game.handle_mouse(mouse(pg, pg.MOUSEBUTTONDOWN, x, y))


def test_start_screen_shows_choices_and_play_screen_only_the_essentials(pg):
    game = Game(pg.display.set_mode((900, 650)))
    assert game.top_widgets() == [game.fx_button, game.exit_button, game.dropdown]
    game.dismiss_intro()
    assert game.top_widgets() == [game.options_button, game.exit_button, game.reset_button]


def test_play_screen_buttons_do_not_overlap(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.dismiss_intro()
    rects = [w.rect for w in game.top_widgets()]
    for i, a in enumerate(rects):
        assert a.right <= 900
        assert not any(a.colliderect(b) for b in rects[i + 1:])


def test_exit_works_on_both_screens(pg):
    game = Game(pg.display.set_mode((900, 650)))
    assert click(pg, game, game.exit_button)
    game.dismiss_intro()
    assert click(pg, game, game.exit_button)


def test_hidden_controls_cannot_be_clicked(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.words_typed = 5
    assert not click(pg, game, game.reset_button)          # RESET is not on the start screen
    assert not click(pg, game, game.options_button)
    assert game.words_typed == 5 and game.intro_open
    game.dismiss_intro()
    game.sprite_manager.enabled = True
    click(pg, game, game.fx_button)                         # FX is not on the play screen
    click(pg, game, game.dropdown)
    click(pg, game, game.codes_box.rect.center)
    assert game.sprite_manager.enabled and not game.dropdown.is_open and not game.codes_box.checked
    assert game.words_typed == 5


def test_options_button_returns_to_the_start_screen_without_losing_the_game(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.dismiss_intro()
    game.words_typed = 7
    click(pg, game, game.options_button)
    assert game.intro_open and game.words_typed == 7


def test_reset_starts_over_but_waits_on_the_start_screen(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.dismiss_intro()
    game.words_typed, game.score = 7, 9
    click(pg, game, game.reset_button)
    assert (game.words_typed, game.score) == (0, 0)
    assert game.intro_open                       # the new game has not started
    y_after_reset = [w.y for w in game.words]
    game.update()
    assert [w.y for w in game.words] == y_after_reset   # paused: words do not fall until START
    assert game.top_widgets() == [game.fx_button, game.exit_button, game.dropdown]


def test_reset_works_from_the_result_screen_too(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.dismiss_intro()
    game._finish(won=True)
    click(pg, game, game.reset_button)
    assert not game.victory and game.intro_open


def test_options_pauses_and_start_resumes_the_same_game(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.dismiss_intro()
    game.words_typed, game.score = 7, 9
    click(pg, game, game.options_button)
    assert game.intro_open
    click(pg, game, game.start_button)
    assert not game.intro_open and (game.words_typed, game.score) == (7, 9)


def test_start_screen_controls_work(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.words_typed = 5
    click(pg, game, game.codes_box.rect.center)             # finger codes on: slower, restarts, pictures off
    assert game.codes_box.checked and game.words_typed == 0 and not game.sprite_manager.enabled
    game.sprite_manager.enabled = True
    click(pg, game, game.fx_button)                         # FX is its own switch
    assert not game.sprite_manager.enabled
    slider = game.speed_slider
    game.words_typed = 5
    x = slider.left + slider.width                          # drag to the far right: 2.5
    game.handle_mouse(mouse(pg, pg.MOUSEBUTTONDOWN, slider.left + 10, slider.y))
    game.handle_mouse(mouse(pg, pg.MOUSEMOTION, x, slider.y))
    game.handle_mouse(mouse(pg, pg.MOUSEBUTTONUP, x, slider.y))
    assert slider.value == 2.5 and game.words_typed == 0
    click(pg, game, game.start_button)
    assert not game.intro_open


def test_level_menu_works_on_the_start_screen(pg):
    game = Game(pg.display.set_mode((900, 650)))
    click(pg, game, game.dropdown)
    assert game.dropdown.is_open
    click(pg, game, game.dropdown.open_rects[2].center)
    assert game.word_manager.current_level == game.word_manager.level_names[2]
    assert game.intro_open and not game.dropdown.is_open


def test_play_screen_does_not_draw_the_start_screen_controls(pg):
    game = Game(pg.display.set_mode((900, 650)))
    game.speed_slider.value = 1.5
    game.dismiss_intro()
    game.draw()
    knob_x = game.speed_slider.left + round((1.5 - 0.5) / 2.0 * game.speed_slider.width)
    assert tuple(game.screen.get_at((knob_x, game.speed_slider.y - 9)))[:3] != (255, 255, 255)
    assert tuple(game.screen.get_at(game.dropdown.rect.center))[:3] != game.dropdown.color
