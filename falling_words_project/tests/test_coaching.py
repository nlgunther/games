"""Tests for the pure coaching logic (no pygame)."""
from build_words import BOTTOM, HOME, TOP
from falling_words import coaching as c


def test_every_letter_has_a_finger():
    assert set(c.FINGER_OF) >= set("abcdefghijklmnopqrstuvwxyz;")


def test_rows_match_word_builder():
    assert (c.ROWS["top"], c.ROWS["home"], c.ROWS["bottom"]) == (
        "".join(sorted(TOP, key=c.KEY_ROWS[0].index)),
        "".join(sorted(HOME, key=c.KEY_ROWS[1].index)),
        "".join(sorted(BOTTOM, key=c.KEY_ROWS[2].index)),
    )


def test_display_name():
    assert c.display_name("adam") == "Adam"
    assert c.display_name("mary-ann") == "Mary Ann"


def test_intro_home_row_mentions_fingers_and_highlights_semicolon():
    card = c.intro_card("Adam", set("asdfjkl"))
    assert card.title == "Adam - now we're going to work on the home row."
    assert "A S D F" in card.lines[0] and "J K L ;" in card.lines[0]
    assert ";" in card.keys


def test_intro_without_name_is_capitalized():
    assert c.intro_card("", set("qwer")).title.startswith("Now we're")


def test_intro_all_rows():
    card = c.intro_card("Adam", set("qazsdfpl"))
    assert "all three rows" in card.title
    assert len(card.lines) == 3


def test_suggested_level():
    assert c.suggested_level(True, 100, "2 Home+Top") == "2 Home+Top"
    assert c.suggested_level(False, 100, "2 Home+Top") == ""
    assert c.suggested_level(True, 100, "") == ""
