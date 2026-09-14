from pathlib import Path
import csv
import re
from difflib import SequenceMatcher

from nltk.stem import LancasterStemmer, PorterStemmer

ROOT = Path(__file__).resolve().parents[1]
NGSL_PATH = ROOT / "data" / "NGSL_1.2.txt"
REMAINDER_PATH = ROOT / "analysis" / "NAWL_remaining.txt"
OUT_PATH = ROOT / "analysis" / "family_review_candidates.csv"

porter = PorterStemmer()
lancaster = LancasterStemmer()

PREFIXES = (
    "under", "inter", "trans", "super", "multi", "post", "over",
    "anti", "non", "pre", "sub", "re", "un", "in", "im", "ir", "dis",
)

SUFFIX_RULES = (
    ("ically", ("ic", "ical")),
    ("ically", ("ic",)),
    ("ality", ("al",)),
    ("ility", ("le", "")),
    ("ability", ("able", "")),
    ("ization", ("ize", "")),
    ("ification", ("ify", "")),
    ("ation", ("ate", "e", "")),
    ("ition", ("ite", "e", "")),
    ("tion", ("te", "t", "")),
    ("sion", ("se", "d", "")),
    ("ically", ("ic", "")),
    ("ical", ("ic", "")),
    ("ically", ("ic",)),
    ("ically", ("ic",)),
    ("ology", ("",)),
    ("ologist", ("ology", "")),
    ("graphical", ("graph",)),
    ("ship", ("",)),
    ("hood", ("",)),
    ("ward", ("",)),
    ("wards", ("",)),
    ("ness", ("", "y")),
    ("ment", ("", "e")),
    ("ance", ("", "e")),
    ("ence", ("", "e")),
    ("ancy", ("ant", "")),
    ("ency", ("ent", "")),
    ("ity", ("", "e", "y")),
    ("ism", ("",)),
    ("ist", ("", "y")),
    ("ive", ("", "e")),
    ("ative", ("ate", "")),
    ("ous", ("",)),
    ("al", ("",)),
    ("ary", ("", "y")),
    ("ory", ("",)),
    ("ic", ("",)),
    ("ly", ("",)),
    ("er", ("", "e")),
    ("or", ("", "e")),
    ("ure", ("e", "")),
)


def load_words(path: Path):
    return [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def affix_bases(word: str):
    out = set()
    for prefix in PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= 4:
            out.add((word[len(prefix):], f"strip-prefix:{prefix}"))
    for suffix, replacements in SUFFIX_RULES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stem = word[:-len(suffix)]
            for repl in replacements:
                candidate = stem + repl
                if len(candidate) >= 4:
                    out.add((candidate, f"suffix:{suffix}->{repl or '∅'}"))
    return out


def common_prefix_len(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


ngsl = load_words(NGSL_PATH)
remaining = load_words(REMAINDER_PATH)
ngsl_set = set(ngsl)

ngsl_porter = {}
ngsl_lancaster = {}
for w in ngsl:
    ngsl_porter.setdefault(porter.stem(w), []).append(w)
    ngsl_lancaster.setdefault(lancaster.stem(w), []).append(w)

rows = []
for a in remaining:
    candidates = {}

    def add(g, signal, points):
        if g == a:
            return
        item = candidates.setdefault(g, {"score": 0, "signals": set()})
        if signal not in item["signals"]:
            item["signals"].add(signal)
            item["score"] += points

    p = porter.stem(a)
    if len(p) >= 4:
        for g in ngsl_porter.get(p, []):
            add(g, f"porter:{p}", 4)

    l = lancaster.stem(a)
    if len(l) >= 4:
        for g in ngsl_lancaster.get(l, []):
            add(g, f"lancaster:{l}", 3)

    for base, signal in affix_bases(a):
        if base in ngsl_set:
            add(base, signal, 6)

    # Also test whether an NGSL word is a clear base/prefix of the NAWL word.
    for g in ngsl:
        if len(g) >= 4 and len(a) > len(g) and a.startswith(g) and len(a) - len(g) <= 10:
            add(g, "ngsl-is-prefix", 4)

        # Orthographic fallback: only same initial 4 letters and similar length.
        if abs(len(a) - len(g)) <= 6 and common_prefix_len(a, g) >= 4:
            ratio = SequenceMatcher(None, a, g).ratio()
            if ratio >= 0.74:
                add(g, f"similarity:{ratio:.2f}", 2)

    ranked = sorted(
        ((g, v["score"], sorted(v["signals"])) for g, v in candidates.items()),
        key=lambda x: (-x[1], -SequenceMatcher(None, a, x[0]).ratio(), x[0]),
    )

    # Keep a compact review queue: strong candidates, maximum 5 per NAWL word.
    kept = 0
    for g, score, signals in ranked:
        if score < 4:
            continue
        rows.append((a, g, score, "; ".join(signals)))
        kept += 1
        if kept >= 5:
            break

OUT_PATH.parent.mkdir(exist_ok=True)
with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["NAWL_word", "NGSL_candidate", "score", "signals"])
    writer.writerows(rows)

print(f"Review candidates: {len(rows)} pairs covering {len({r[0] for r in rows})} NAWL words")
