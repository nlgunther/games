"""Build src/falling_words/words_config.json, graded by QWERTY rows used.

Grade = number of letter rows a word touches; the level name says which rows.
Row membership is computed from the letters, never hand-labelled.

Usage (build-time only; needs the `tools` dependency group):
    uv run --group tools python tools/build_words.py            # writes src/falling_words/words_config.json
    uv run --group tools python tools/build_words.py --preview  # prints levels, writes nothing
"""
import argparse
import json
import random
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from seed_v1 import GENERIC_WORDS, THEMES  # noqa: E402

EXTRA_ZIP = HERE.parent / "extra.zip"   # local-only; holds the kid-safety blocklist
OUT_PATH = HERE.parent / "src" / "falling_words" / "words_config.json"

TOP, HOME, BOTTOM = "qwertyuiop", "asdfghjkl", "zxcvbnm"
LEFT_HOME, RIGHT_HOME = "asdfg", "hjkl"

MIN_LEN, MAX_LEN = 3, 8
PER_LENGTH_CAP = 12        # spread difficulty: at most this many words per length
MIN_DRILLS = 30            # drill levels (no real words exist) are padded to this
CANDIDATES = 15000         # how deep into the frequency list to look
DEFAULT_LEVEL = "1 Home: left"



def load_blocklist() -> tuple[set, tuple]:
    """Read blocklist.py straight from extra.zip (no extraction). Missing zip raises:
    building without the kid filter must never happen silently."""
    if not EXTRA_ZIP.exists():
        raise FileNotFoundError(f"{EXTRA_ZIP} is required to build word lists (it is deliberately not in git)")
    with zipfile.ZipFile(EXTRA_ZIP) as z:
        source = z.read("blocklist.py").decode("utf-8")
    namespace: dict = {}
    exec(compile(source, f"{EXTRA_ZIP.name}/blocklist.py", "exec"), namespace)
    return namespace["BLOCK"], namespace["BLOCK_SUBSTR"]


def rows_of(word: str) -> str:
    """Row signature, e.g. 'HT' for a word using home and top rows ('?' = other)."""
    sig = set()
    for ch in word.lower():
        sig.add("T" if ch in TOP else "H" if ch in HOME else "B" if ch in BOTTOM else "?")
    return "".join(sorted(sig, key="HTB?".index))


def is_blocked(word: str, block: set, block_substr: tuple) -> bool:
    return word in block or any(s in word for s in block_substr)


def allowed(word: str, block: set, block_substr: tuple) -> bool:
    """A real-looking word: lowercase letters, has a vowel, not blocked."""
    return (word.isascii() and word.isalpha() and word.islower()
            and MIN_LEN <= len(word) <= MAX_LEN
            and any(c in "aeiouy" for c in word)
            and not is_blocked(word, block, block_substr))


def candidate_words(block: set, block_substr: tuple) -> list:
    """Common English words by frequency, plus the v1 hand-picked words."""
    from wordfreq import top_n_list
    seen, out = set(), []
    for w in list(GENERIC_WORDS) + top_n_list("en", CANDIDATES):
        if w not in seen and allowed(w, block, block_substr):
            seen.add(w)
            out.append(w)
    return out


def pick(words, pred) -> list:
    """First-by-frequency words passing pred, at most PER_LENGTH_CAP per length."""
    per_len, out = {}, []
    for w in words:
        if pred(w) and per_len.get(len(w), 0) < PER_LENGTH_CAP:
            per_len[len(w)] = per_len.get(len(w), 0) + 1
            out.append(w)
    return sorted(out, key=lambda w: (len(w), w))


def drills(letters: str, existing, count: int, seed: str, blocked) -> list:
    """Pronounce-free practice strings (length 2-4, no triple repeats) from `letters`, skipping blocked ones."""
    rng = random.Random(seed)
    out = list(existing)
    while len(out) < count:
        s = "".join(rng.choice(letters) for _ in range(rng.choice((2, 3, 3, 4, 4))))
        if s not in out and not blocked(s) and not any(s[i] == s[i + 1] == s[i + 2] for i in range(len(s) - 2)):
            out.append(s)
    return sorted(out, key=lambda w: (len(w), w))


def build() -> dict:
    block, block_substr = load_blocklist()
    words = candidate_words(block, block_substr)
    blocked = lambda w: is_blocked(w, block, block_substr)   # noqa: E731
    only = lambda letters: (lambda w: set(w) <= set(letters))          # noqa: E731
    sig = lambda s: (lambda w: rows_of(w) == s)                         # noqa: E731

    levels = {   # name -> (rows, kind, words)
        "1 Home: left":   ("H", "left hand", drills(LEFT_HOME, pick(words, only(LEFT_HOME)), MIN_DRILLS, "hl", blocked)),
        "1 Home: right":  ("H", "right hand", drills(RIGHT_HOME, pick(words, only(RIGHT_HOME)), MIN_DRILLS, "hr", blocked)),
        "1 Home: all":    ("H", "words", pick(words, sig("H"))),
        "1 Top row":      ("T", "words", pick(words, sig("T"))),
        "1 Bottom row":   ("B", "drills", drills(BOTTOM, pick(words, sig("B")), MIN_DRILLS, "b", blocked)),
        "2 Home+Top":     ("HT", "words", pick(words, sig("HT"))),
        "2 Home+Bottom":  ("HB", "words", pick(words, sig("HB"))),
        "2 Top+Bottom":   ("TB", "words", pick(words, sig("TB"))),
        "3 All rows":     ("HTB", "words", pick(words, sig("HTB"))),
    }
    out_levels, meta = {}, {}
    for name, (rows, kind, ws) in levels.items():
        out_levels[name] = ws
        meta[name] = {"grade": len(rows), "rows": rows, "kind": kind}
    for name, ws in THEMES.items():
        out_levels[name] = list(ws)
        meta[name] = {"grade": None, "rows": "mixed", "kind": "theme"}
    return {"meta": meta, "levels": out_levels, "default_level": DEFAULT_LEVEL}


def render(cfg: dict) -> str:
    """JSON with one wrapped line-group per level so the file stays readable."""
    lines = ["{", '  "meta": {']
    items = [f'    {json.dumps(k)}: {json.dumps(v)}' for k, v in cfg["meta"].items()]
    lines.append(",\n".join(items))
    lines += ["  },", '  "levels": {']
    blocks = []
    for name, ws in cfg["levels"].items():
        rows, row = [], ""
        for w in ws:
            tok = json.dumps(w) + ", "
            if len(row) + len(tok) > 96:
                rows.append(row.rstrip()); row = ""
            row += tok
        rows.append(row.rstrip().rstrip(","))
        body = "\n".join("      " + r for r in rows)
        blocks.append(f'    {json.dumps(name)}: [\n{body}\n    ]')
    lines.append(",\n".join(blocks))
    lines += ["  },", f'  "default_level": {json.dumps(cfg["default_level"])}', "}", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="print levels, write nothing")
    args = ap.parse_args()
    cfg = build()
    text = render(cfg)
    json.loads(text)  # must stay valid JSON
    if args.preview:
        for n, ws in cfg["levels"].items():
            print(f"\n## {n} ({len(ws)})\n{' '.join(ws)}")
        return
    OUT_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT_PATH} ({len(cfg['levels'])} levels)")


if __name__ == "__main__":
    main()
