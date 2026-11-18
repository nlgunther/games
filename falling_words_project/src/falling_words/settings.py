"""Game-wide tuning values, kept in JSON so they can be changed without touching the code.

Two files are read, the second overriding the first key by key:
  1. game_settings.json   packaged defaults, shipped inside the wheel (the wheel holds only the package,
                          so the defaults cannot live in the project's top folder)
  2. settings.json        optional, in the folder that holds the profiles folder: the project's top folder
                          here, the folder with the wheel on a kid's PC. Tune one PC with no rebuild.
                          settings.example.json in the top folder is a template to copy.

Unknown keys and bad values raise, so a typo never passes silently.

To add a setting: put its default in game_settings.json, add a field to `Settings`, and add a rule
to `_RULES`. The tests fail if the three get out of step.

Example settings.json (only the keys to change):
    {"finger_codes_speed_factor": 0.25, "ramp_up_by_default": true}
"""
import json
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_SETTINGS_PATH = Path(__file__).with_name("game_settings.json")
OVERRIDE_NAME = "settings.json"


@dataclass(frozen=True)
class Settings:
    finger_codes_speed_factor: float   # speed multiplier while "Show finger codes" is ticked (1 = no change)
    ramp_up_by_default: bool           # whether "Speed up as I go" starts ticked
    speed_jitter: float                # each word's speed varies by up to +/- this fraction (0 = none, 0.1 = 10%)


def _fraction(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < 1


def _positive_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


# key -> (is the value acceptable?, what an acceptable value looks like)
_RULES = {
    "finger_codes_speed_factor": (_positive_number, "a number greater than 0, such as 0.5"),
    "ramp_up_by_default": (lambda value: isinstance(value, bool), "true or false"),
    "speed_jitter": (_fraction, "a number from 0 up to (but not including) 1, such as 0.1"),
}


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: not valid JSON ({e})") from e
    if not isinstance(data, dict):
        raise ValueError(f"{path}: must be a JSON object of settings, like {{\"name\": value}}")
    allowed = {f.name for f in fields(Settings)}
    if unknown := set(data) - allowed:
        raise ValueError(f"{path}: unknown settings {sorted(unknown)}; allowed: {sorted(allowed)}")
    for key, value in data.items():
        accepted, expected = _RULES[key]
        if not accepted(value):
            raise ValueError(f"{path}: {key} is {value!r}; it must be {expected}")
    return data


def override_dir_for(profiles_dir: Path) -> Path:
    """The folder that holds the profiles folder, where an optional settings.json goes.

    Example:
        override_dir_for(Path("profiles"))   # the current folder, i.e. the project's top folder
    """
    return Path(profiles_dir).resolve().parent


def load_settings(override_dir: Path | None = None) -> Settings:
    """Packaged defaults, overridden by `override_dir/settings.json` when that file exists.

    Example:
        load_settings(override_dir_for(Path("profiles"))).ramp_up_by_default   # False unless overridden
    """
    merged = _read(DEFAULT_SETTINGS_PATH)
    if override_dir is not None and (override := Path(override_dir) / OVERRIDE_NAME).is_file():
        merged |= _read(override)
    if missing := {f.name for f in fields(Settings)} - set(merged):
        raise ValueError(f"{DEFAULT_SETTINGS_PATH} is missing settings: {sorted(missing)}")
    return Settings(**merged)
