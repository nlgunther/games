"""Sound helper is safe on any OS and rejects typos."""
import pytest

from falling_words import sounds


def test_every_beep_plays_without_error():
    for name in sounds.BEEPS:
        sounds.play(name)  # no-op off Windows


def test_unknown_sound_raises():
    with pytest.raises(KeyError):
        sounds.play("tada")
