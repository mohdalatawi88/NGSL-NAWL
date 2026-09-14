from collections import defaultdict
from pathlib import Path
import csv

from nltk.stem.snowball import SnowballStemmer

ROOT = Path(__file__).resolve().parents[1]
NGSL_PATH = ROOT / "data" / "NGSL_1.2.txt"
NAWL_PATH = ROOT / "data" / "NAWL_1.2.txt"
OUT_DIR = ROOT / "analysis"

EXPECTED_NAWL_TOTAL = 957
EXPECTED_NAWL_WITH_NGSL_FAMILY = 184
EXPECTED_NAWL_REMAINING = 773

stemmer = SnowballStemmer("english")


def load_words(path: Path):
    return sorted({line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})


def stem(word: str) -> str:
    return stemmer.stem(word)


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

summary = f"""# NGSL–NAWL overlap analysis

- NGSL words: {len(ngsl)}
- NAWL words: {len(nawl)}
- Exact overlaps: {len(exact)}
- Cross-list same-stem family groups: {len(families)}
- NAWL words with at least one NGSL same-family candidate: {len(nawl_with_ngsl_family)}
- NAWL words remaining after excluding those family-linked words: {len(nawl_remaining)}

## Study file

`NAWL_remaining_773.txt` contains the {len(nawl_remaining)} NAWL 1.2 words that do not currently have an NGSL same-family candidate under this project's analysis method. It is generated automatically from the source lists and the same family analysis used for `study_pairs.csv`.

## Method

Exact overlap is a case-insensitive exact word match.

Same-family candidates are generated with NLTK's English Snowball stemmer. They are useful study groupings, but stemming is heuristic and can occasionally group words that are not true lexical-family members. Very short stems (<4 characters) are excluded to reduce false positives.
"""
(OUT_DIR / "SUMMARY.md").write_text(summary, encoding="utf-8")

print(summary)
