from collections import defaultdict
from pathlib import Path
import csv
import re

from nltk.stem.snowball import SnowballStemmer
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
NGSL_PATH = ROOT / "data" / "NGSL_1.2.txt"
NAWL_PATH = ROOT / "data" / "NAWL_1.2.txt"
OUT_DIR = ROOT / "analysis"

EXPECTED_NAWL_TOTAL = 957
EXPECTED_NAWL_WITH_NGSL_FAMILY = 184
EXPECTED_NAWL_REMAINING = 773

stemmer = SnowballStemmer("english")
VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")

ACADEMIC_SUFFIXES = (
    "tion", "sion", "ation", "ition", "ment", "ness", "ence", "ance",
    "ity", "ism", "ology", "graphy", "ical", "ative", "itive", "ous",
    "ive", "ary", "ory", "al", "ic",
)
ACADEMIC_PREFIXES = ("anti", "multi", "neo", "non", "sub", "trans")

# Obvious everyday/concrete words that are especially easy to understand even
# when raw corpus frequency alone would place them slightly lower.
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


ngsl = load_words(NGSL_PATH)
nawl = load_words(NAWL_PATH)
ngsl_set = set(ngsl)
nawl_set = set(nawl)

exact = sorted(ngsl_set & nawl_set)

ngsl_by_stem = defaultdict(list)
nawl_by_stem = defaultdict(list)
for word in ngsl:
    ngsl_by_stem[stem(word)].append(word)
for word in nawl:
    nawl_by_stem[stem(word)].append(word)

families = []
for key in sorted(set(ngsl_by_stem) & set(nawl_by_stem)):
    if len(key) < 4:
        continue
    g_words = sorted(set(ngsl_by_stem[key]))
    a_words = sorted(set(nawl_by_stem[key]))
    # Keep cross-list families where there is at least one non-identical pair.
    if any(g != a for g in g_words for a in a_words):
        families.append((key, g_words, a_words))

nawl_with_ngsl_family = sorted({word for _, _, a_words in families for word in a_words})
nawl_remaining = sorted(nawl_set - set(nawl_with_ngsl_family))

# These checks make the current NGSL/NAWL 1.2 study split explicit and prevent
# silently publishing a file with a misleading count if the source data or
# family-analysis method changes later.
if len(nawl) != EXPECTED_NAWL_TOTAL:
    raise RuntimeError(f"Expected {EXPECTED_NAWL_TOTAL} NAWL words, found {len(nawl)}")
if len(nawl_with_ngsl_family) != EXPECTED_NAWL_WITH_NGSL_FAMILY:
    raise RuntimeError(
        f"Expected {EXPECTED_NAWL_WITH_NGSL_FAMILY} NAWL words with an NGSL family match, "
        f"found {len(nawl_with_ngsl_family)}"
    )
if len(nawl_remaining) != EXPECTED_NAWL_REMAINING:
    raise RuntimeError(
        f"Expected {EXPECTED_NAWL_REMAINING} remaining NAWL words, found {len(nawl_remaining)}"
    )

# Classify the 773 remaining words. Inside each group, put easier/higher-
# frequency words first so the files can also be used directly as study queues.
scores = {word: study_ease_score(word) for word in nawl_remaining}
difficulty = {"easy": [], "medium": [], "hard": []}
for word in nawl_remaining:
    difficulty[classify_difficulty(word, scores[word])].append(word)
for group in difficulty.values():
    group.sort(key=lambda w: (-scores[w], w))

if sum(len(group) for group in difficulty.values()) != EXPECTED_NAWL_REMAINING:
    raise RuntimeError("Difficulty groups do not add up to 773 words")
if set().union(*(set(group) for group in difficulty.values())) != set(nawl_remaining):
    raise RuntimeError("Difficulty groups do not exactly cover the 773-word remainder")
if any(set(difficulty[a]) & set(difficulty[b]) for a, b in (("easy", "medium"), ("easy", "hard"), ("medium", "hard"))):
    raise RuntimeError("A word appears in more than one difficulty group")

OUT_DIR.mkdir(exist_ok=True)

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

with (OUT_DIR / "NAWL_remaining_773.txt").open("w", encoding="utf-8") as f:
    for word in nawl_remaining:
        f.write(word + "\n")

for level in ("easy", "medium", "hard"):
    with (OUT_DIR / f"NAWL_remaining_{level}.txt").open("w", encoding="utf-8") as f:
        for word in difficulty[level]:
            f.write(word + "\n")

pct = lambda n: n / EXPECTED_NAWL_REMAINING * 100
summary = f"""# NGSL–NAWL overlap analysis

- NGSL words: {len(ngsl)}
- NAWL words: {len(nawl)}
- Exact overlaps: {len(exact)}
- Cross-list same-stem family groups: {len(families)}
- NAWL words with at least one NGSL same-family candidate: {len(nawl_with_ngsl_family)}
- NAWL words remaining after excluding those family-linked words: {len(nawl_remaining)}

## Difficulty classification of the 773 remaining words

- Easy: {len(difficulty['easy'])} ({pct(len(difficulty['easy'])):.1f}%)
- Medium: {len(difficulty['medium'])} ({pct(len(difficulty['medium'])):.1f}%)
- Hard: {len(difficulty['hard'])} ({pct(len(difficulty['hard'])):.1f}%)
- Total classified: {sum(len(group) for group in difficulty.values())}

Files:
- `NAWL_remaining_easy.txt`
- `NAWL_remaining_medium.txt`
- `NAWL_remaining_hard.txt`

Words inside each difficulty file are ordered from easier/higher-frequency to harder/lower-frequency according to the same score.

Difficulty is a study estimate, not an official CEFR level. It combines English word frequency (wordfreq Zipf frequency), word length, approximate syllable/form complexity, common academic affixes, and a small curated override for obviously concrete/everyday words.

## Study file

`NAWL_remaining_773.txt` contains the {len(nawl_remaining)} NAWL 1.2 words that do not currently have an NGSL same-family candidate under this project's analysis method. It is generated automatically from the source lists and the same family analysis used for `study_pairs.csv`.

## Family-analysis method

Exact overlap is a case-insensitive exact word match.

Same-family candidates are generated with NLTK's English Snowball stemmer. They are useful study groupings, but stemming is heuristic and can occasionally group words that are not true lexical-family members. Very short stems (<4 characters) are excluded to reduce false positives.
"""
(OUT_DIR / "SUMMARY.md").write_text(summary, encoding="utf-8")

print(summary)
