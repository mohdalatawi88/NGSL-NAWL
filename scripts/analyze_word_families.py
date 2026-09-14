from collections import defaultdict
from pathlib import Path
import csv
import re

from nltk.stem.snowball import SnowballStemmer
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
NGSL_PATH = ROOT / "data" / "NGSL_1.2.txt"
NAWL_PATH = ROOT / "data" / "NAWL_1.2.txt"
FAMILY_OVERRIDES_PATH = ROOT / "data" / "family_overrides.csv"
OUT_DIR = ROOT / "analysis"

EXPECTED_NGSL_TOTAL = 2809
EXPECTED_NAWL_TOTAL = 957

stemmer = SnowballStemmer("english")
VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")

ACADEMIC_SUFFIXES = (
    "tion", "sion", "ation", "ition", "ment", "ness", "ence", "ance",
    "ity", "ism", "ology", "graphy", "ical", "ative", "itive", "ous",
    "ive", "ary", "ory", "al", "ic",
)
ACADEMIC_PREFIXES = ("anti", "multi", "neo", "non", "sub", "trans")

# Obvious everyday/concrete NAWL words that are especially easy to understand
# even when raw corpus frequency alone would place them slightly lower.
EASY_OVERRIDES = {
    "airplane", "apple", "bat", "blank", "bonus", "bucket", "bullet",
    "cattle", "cheat", "cheer", "chess", "clay", "clever", "client",
    "clip", "clue", "deadline", "diary", "dictionary", "dose", "drain",
    "fever", "flip", "ghost", "goat", "graph", "grid", "homework",
    "kidney", "lab", "leaf", "leisure", "liver", "loop", "mall",
    "manual", "marble", "monkey", "nest", "noisy", "outlet", "parcel",
    "pardon", "pest", "plug", "poster", "punch", "puzzle", "quiz",
    "radar", "recipe", "robot", "rope", "ruler", "snake", "sneeze",
    "sniff", "spray", "stadium", "stripe", "sword", "textbook", "thumb",
    "triangle", "wheat", "wisdom", "workshop", "yeast",
}


def load_words(path: Path):
    return sorted({line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})


def split_words(cell: str):
    return sorted({part.strip().lower() for part in cell.split(";") if part.strip()})


def load_family_overrides(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"family_key", "NGSL_words", "NAWL_words", "reason"}
        if not required.issubset(reader.fieldnames or []):
            raise RuntimeError(f"Unexpected columns in {path}; expected {sorted(required)}")
        for row in reader:
            key = (row["family_key"] or "").strip().lower()
            g_words = split_words(row["NGSL_words"] or "")
            a_words = split_words(row["NAWL_words"] or "")
            reason = (row["reason"] or "").strip()
            if not key or not g_words or not a_words:
                raise RuntimeError(f"Invalid family override row: {row}")
            rows.append((key, g_words, a_words, reason))
    return rows


def stem(word: str) -> str:
    return stemmer.stem(word)


def study_ease_score(word: str) -> float:
    """Estimate study ease from English frequency and surface-form complexity.

    Higher is easier. The score is deliberately simple and reproducible; it is
    a study-priority aid, not an official CEFR classification.
    """
    score = zipf_frequency(word, "en")

    if len(word) <= 6:
        score += 0.12
    if len(word) > 8:
        score -= min((len(word) - 8) * 0.06, 0.42)

    vowel_groups = len(VOWEL_GROUP_RE.findall(word))
    if vowel_groups >= 5:
        score -= 0.15

    if word.endswith(ACADEMIC_SUFFIXES) and len(word) >= 8:
        score -= 0.10
    if word.startswith(ACADEMIC_PREFIXES) and len(word) >= 8:
        score -= 0.05

    return round(score, 3)


def classify_difficulty(word: str, score: float) -> str:
    if word in EASY_OVERRIDES:
        return "easy"
    if score >= 4.00:
        return "easy"
    if score >= 3.25:
        return "medium"
    return "hard"


def build_difficulty_groups(words):
    scores = {word: study_ease_score(word) for word in words}
    groups = {"easy": [], "medium": [], "hard": []}
    for word in words:
        groups[classify_difficulty(word, scores[word])].append(word)
    for group in groups.values():
        group.sort(key=lambda w: (-scores[w], w))
    return scores, groups


def validate_difficulty_groups(words, groups, label):
    expected = set(words)
    if sum(len(group) for group in groups.values()) != len(words):
        raise RuntimeError(f"{label} difficulty groups do not add up to {len(words)} words")
    if set().union(*(set(group) for group in groups.values())) != expected:
        raise RuntimeError(f"{label} difficulty groups do not exactly cover the source words")
    pairs = (("easy", "medium"), ("easy", "hard"), ("medium", "hard"))
    if any(set(groups[a]) & set(groups[b]) for a, b in pairs):
        raise RuntimeError(f"A word appears in more than one {label} difficulty group")


ngsl = load_words(NGSL_PATH)
nawl = load_words(NAWL_PATH)
ngsl_set = set(ngsl)
nawl_set = set(nawl)

if len(ngsl) != EXPECTED_NGSL_TOTAL:
    raise RuntimeError(f"Expected {EXPECTED_NGSL_TOTAL} NGSL words, found {len(ngsl)}")
if len(nawl) != EXPECTED_NAWL_TOTAL:
    raise RuntimeError(f"Expected {EXPECTED_NAWL_TOTAL} NAWL words, found {len(nawl)}")

exact = sorted(ngsl_set & nawl_set)

ngsl_by_stem = defaultdict(list)
nawl_by_stem = defaultdict(list)
for word in ngsl:
    ngsl_by_stem[stem(word)].append(word)
for word in nawl:
    nawl_by_stem[stem(word)].append(word)

# First pass: Snowball stemming. This is fast and catches most obvious
# derivational families, but it is not trusted as the only source of truth.
family_map = {}
for key in sorted(set(ngsl_by_stem) & set(nawl_by_stem)):
    if len(key) < 4:
        continue
    g_words = set(ngsl_by_stem[key])
    a_words = set(nawl_by_stem[key])
    if any(g != a for g in g_words for a in a_words):
        family_map[key] = [g_words, a_words]

# Second pass: verified manual overrides for real lexical families that the
# stemmer misses. This file is intentionally auditable instead of applying
# aggressive suffix/prefix stripping that can create false positives.
overrides = load_family_overrides(FAMILY_OVERRIDES_PATH)
for key, g_words, a_words, _reason in overrides:
    missing_ngsl = sorted(set(g_words) - ngsl_set)
    missing_nawl = sorted(set(a_words) - nawl_set)
    if missing_ngsl or missing_nawl:
        raise RuntimeError(
            f"Invalid family override {key!r}; missing NGSL={missing_ngsl}, NAWL={missing_nawl}"
        )
    bucket = family_map.setdefault(key, [set(), set()])
    bucket[0].update(g_words)
    bucket[1].update(a_words)

families = [
    (key, sorted(g_words), sorted(a_words))
    for key, (g_words, a_words) in sorted(family_map.items())
]

nawl_with_ngsl_family = sorted({word for _, _, a_words in families for word in a_words})
nawl_remaining = sorted(nawl_set - set(nawl_with_ngsl_family))

# Difficulty uses the same scoring model for all NGSL words and for the current
# NAWL remainder after verified cross-list families have been removed.
ngsl_scores, ngsl_difficulty = build_difficulty_groups(ngsl)
nawl_scores, nawl_difficulty = build_difficulty_groups(nawl_remaining)
validate_difficulty_groups(ngsl, ngsl_difficulty, "NGSL")
validate_difficulty_groups(nawl_remaining, nawl_difficulty, "NAWL remainder")

OUT_DIR.mkdir(exist_ok=True)

# Remove old count-encoded remainder files so a historical count is never
# mistaken for the current verified result.
for stale_path in OUT_DIR.glob("NAWL_remaining_[0-9]*.txt"):
    stale_path.unlink()

with (OUT_DIR / "exact_overlap.txt").open("w", encoding="utf-8") as f:
    for word in exact:
        f.write(word + "\n")

with (OUT_DIR / "same_family_candidates.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["family_key", "NGSL_words", "NAWL_words"])
    for key, g_words, a_words in families:
        writer.writerow([key, "; ".join(g_words), "; ".join(a_words)])

with (OUT_DIR / "study_pairs.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["family_key", "NGSL_word", "NAWL_word"])
    for key, g_words, a_words in families:
        for g in g_words:
            for a in a_words:
                if g != a:
                    writer.writerow([key, g, a])

with (OUT_DIR / "NAWL_remaining.txt").open("w", encoding="utf-8") as f:
    for word in nawl_remaining:
        f.write(word + "\n")

for level in ("easy", "medium", "hard"):
    with (OUT_DIR / f"NAWL_remaining_{level}.txt").open("w", encoding="utf-8") as f:
        for word in nawl_difficulty[level]:
            f.write(word + "\n")

    with (OUT_DIR / f"NGSL_{level}.txt").open("w", encoding="utf-8") as f:
        for word in ngsl_difficulty[level]:
            f.write(word + "\n")


def pct(n, total):
    return n / total * 100 if total else 0.0


summary = f"""# NGSL–NAWL overlap analysis

- NGSL words: {len(ngsl)}
- NAWL words: {len(nawl)}
- Exact overlaps: {len(exact)}
- Cross-list lexical-family groups: {len(families)}
- Verified manual family overrides applied: {len(overrides)}
- NAWL words with at least one NGSL same-family candidate: {len(nawl_with_ngsl_family)}
- NAWL words remaining after excluding those family-linked words: {len(nawl_remaining)}

## Difficulty classification of all {len(ngsl)} NGSL words

- Easy: {len(ngsl_difficulty['easy'])} ({pct(len(ngsl_difficulty['easy']), len(ngsl)):.1f}%)
- Medium: {len(ngsl_difficulty['medium'])} ({pct(len(ngsl_difficulty['medium']), len(ngsl)):.1f}%)
- Hard: {len(ngsl_difficulty['hard'])} ({pct(len(ngsl_difficulty['hard']), len(ngsl)):.1f}%)
- Total classified: {sum(len(group) for group in ngsl_difficulty.values())}

Files:
- `NGSL_easy.txt`
- `NGSL_medium.txt`
- `NGSL_hard.txt`

## Difficulty classification of the {len(nawl_remaining)} remaining NAWL words

- Easy: {len(nawl_difficulty['easy'])} ({pct(len(nawl_difficulty['easy']), len(nawl_remaining)):.1f}%)
- Medium: {len(nawl_difficulty['medium'])} ({pct(len(nawl_difficulty['medium']), len(nawl_remaining)):.1f}%)
- Hard: {len(nawl_difficulty['hard'])} ({pct(len(nawl_difficulty['hard']), len(nawl_remaining)):.1f}%)
- Total classified: {sum(len(group) for group in nawl_difficulty.values())}

Files:
- `NAWL_remaining_easy.txt`
- `NAWL_remaining_medium.txt`
- `NAWL_remaining_hard.txt`

Words inside each difficulty file are ordered from easier/higher-frequency to harder/lower-frequency according to the same score.

Difficulty is a study estimate, not an official CEFR level. It combines English word frequency (wordfreq Zipf frequency), word length, approximate syllable/form complexity, common academic affixes, and a small curated override for obviously concrete/everyday NAWL words.

## Study file

`NAWL_remaining.txt` contains the current {len(nawl_remaining)} NAWL 1.2 words that do not have an NGSL same-family candidate under the project's current verified analysis. The filename deliberately does not encode a fixed count because the total can decrease as verified family links are added.

## Family-analysis method

Exact overlap is a case-insensitive exact word match.

Cross-list family candidates use two layers:
1. NLTK English Snowball stemming for broad candidate discovery.
2. `data/family_overrides.csv` for manually verified lexical families that Snowball misses, such as `develop / development ↔ developmental`.

The override layer is intentionally conservative and auditable. We do not automatically strip arbitrary prefixes/suffixes because that can create false family matches. The remaining count should therefore be treated as the current verified study remainder, not as a permanent linguistic truth.
"""
(OUT_DIR / "SUMMARY.md").write_text(summary, encoding="utf-8")

print(summary)
