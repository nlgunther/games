"""A player's face picture replaces the dinosaur among the floating background sprites."""
import pygame
import pytest

from falling_words.profiles import load_profile
from falling_words.sprite_manager import FACE_SIZE, SpriteManager, circular_crop, load_face
from falling_words.ui import get_font
from test_profiles import write_profile   # shared helper that writes a valid profile JSON


@pytest.fixture
def pg():
    import os
    os.environ["SDL_VIDEODRIVER"] = os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((900, 650))
    get_font.cache_clear()
    yield pygame
    pygame.quit()
    get_font.cache_clear()


def save_photo(pg, path, size=(300, 200), color=(200, 120, 80)):
    surface = pg.Surface(size)
    surface.fill(color)
    pg.image.save(surface, str(path))
    return path


def test_profile_finds_face_by_name_png_first(tmp_path):
    write_profile(tmp_path)
    (tmp_path / "kid.jpg").write_bytes(b"x")
    (tmp_path / "kid.png").write_bytes(b"x")
    assert load_profile("kid", tmp_path).face == tmp_path / "kid.png"


def test_profile_without_face_picture(tmp_path):
    write_profile(tmp_path)
    assert load_profile("kid", tmp_path).face is None


def test_circular_crop_is_square_round_and_opaque_in_the_middle(pg):
    photo = pg.Surface((300, 200))
    photo.fill((200, 120, 80))
    face = circular_crop(photo)
    assert face.get_size() == (FACE_SIZE, FACE_SIZE)
    assert face.get_at((0, 0)).a == 0                              # corner is cut away
    assert face.get_at((FACE_SIZE // 2, FACE_SIZE // 2)).a == 255  # centre is kept
    assert tuple(face.get_at((FACE_SIZE // 2, FACE_SIZE // 2)))[:3] == pytest.approx((200, 120, 80), abs=3)


def test_face_replaces_dinosaur_not_added(pg, tmp_path):
    plain = SpriteManager(900, 650)
    with_face = SpriteManager(900, 650, face_path=save_photo(pg, tmp_path / "kid.png"))
    assert len(with_face.loaded_images) == len(plain.loaded_images)
    assert any(img.get_size() == (FACE_SIZE, FACE_SIZE) for img in with_face.loaded_images)


def test_unreadable_face_raises(pg, tmp_path):
    bad = tmp_path / "kid.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="Cannot read face picture"):
        load_face(bad)
    with pytest.raises(ValueError, match="Cannot read face picture"):
        load_face(tmp_path / "missing.png")


def test_draw_word_codes_and_typed_letters_turn_green(pg):
    from falling_words.ui import GREEN, draw_word
    pg.font.init()

    def green_pixels(typed, show_codes=True):
        surface = pg.Surface((300, 100))
        draw_word(surface, "haha", 10, 10, typed=typed, show_codes=show_codes)
        return sum(1 for x in range(300) for y in range(100) if tuple(surface.get_at((x, y)))[:3] == GREEN)

    assert green_pixels("") == 0
    assert green_pixels("ha") > 0
    assert green_pixels("hx") == 0          # a wrong letter highlights nothing
    assert green_pixels("ha", show_codes=False) == 0   # plain mode is unchanged
