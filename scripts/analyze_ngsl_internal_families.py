from collections import defaultdict
from pathlib import Path
import csv

from nltk.stem.snowball import SnowballStemmer

ROOT = Path(__file__).resolve().parents[1]
NGSL_PATH = ROOT / "data" / "NGSL_1.2.txt"
OVERRIDES_PATH = ROOT / "data" / "family_overrides.csv"
DATA_DIR = ROOT / "data"
ANALYSIS_DIR = ROOT / "analysis"
EXPECTED_NGSL_TOTAL = 2809

stemmer = SnowballStemmer("english")


def load_words(path: Path):
    return sorted({line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})


def split_words(cell: str):
    return sorted({part.strip().lower() for part in cell.split(";") if part.strip()})


words = load_words(NGSL_PATH)
word_set = set(words)
if len(words) != EXPECTED_NGSL_TOTAL:
    raise RuntimeError(f"Expected {EXPECTED_NGSL_TOTAL} NGSL words, found {len(words)}")

# Union-find lets us merge evidence from multiple conservative sources.
parent = {w: w for w in words}
rank = {w: 0 for w in words}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    if rank[ra] == rank[rb]:
        rank[ra] += 1


# Layer 1: conservative Snowball stemming. Ignore very short stems, which are
# more likely to merge unrelated words accidentally.
by_stem = defaultdict(list)
for word in words:
    key = stemmer.stem(word)
    if len(key) >= 4:
        by_stem[key].append(word)

for group in by_stem.values():
    if len(group) >= 2:
        anchor = group[0]
        for word in group[1:]:
            union(anchor, word)

# Layer 2: reuse already verified manual cross-list family overrides when the
# NGSL side itself contains multiple NGSL words. This catches obvious families
# that Snowball can miss, such as evolve/evolution.
manual_links_used = 0
if OVERRIDES_PATH.exists():
    with OVERRIDES_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ngsl_words = [w for w in split_words(row.get("NGSL_words", "")) if w in word_set]
            if len(ngsl_words) >= 2:
                anchor = ngsl_words[0]
                for word in ngsl_words[1:]:
                    union(anchor, word)
                manual_links_used += 1

components = defaultdict(list)
for word in words:
    components[find(word)].append(word)

multi_groups = [sorted(group) for group in components.values() if len(group) >= 2]
singletons = sorted(group[0] for group in components.values() if len(group) == 1)

# Stable ordering: largest families first, then alphabetically by representative.
def representative(group):
    # Shortest form is usually the most convenient study anchor; alphabetical tie-break.
    return sorted(group, key=lambda w: (len(w), w))[0]

multi_groups.sort(key=lambda g: (-len(g), representative(g), g))

family_rows = []
word_map_rows = []
for idx, group in enumerate(multi_groups, start=1):
    family_id = f"NGSL-F{idx:04d}"
    rep = representative(group)
    family_rows.append((family_id, rep, len(group), "; ".join(group)))
    for word in group:
        related = [w for w in group if w != word]
        word_map_rows.append((word, family_id, rep, len(group), "; ".join(related)))

for word in singletons:
    word_map_rows.append((word, "", word, 1, ""))
word_map_rows.sort(key=lambda row: row[0])

linked_word_count = sum(len(group) for group in multi_groups)
effective_units = len(multi_groups) + len(singletons)
reduction = len(words) - effective_units

DATA_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)

with (DATA_DIR / "NGSL_internal_families.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["family_id", "representative", "word_count", "NGSL_words"])
    writer.writerows(family_rows)

with (DATA_DIR / "NGSL_singletons.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["NGSL_word"])
    for word in singletons:
        writer.writerow([word])

with (DATA_DIR / "NGSL_word_family_map.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["NGSL_word", "family_id", "representative", "family_size", "related_NGSL_words"])
    writer.writerows(word_map_rows)

summary = f"""# NGSL internal lexical-family analysis

- Total NGSL words: {len(words)}
- Multi-word lexical families: {len(multi_groups)}
- NGSL words inside multi-word families: {linked_word_count}
- Singleton NGSL words: {len(singletons)}
- Effective study units (families + singletons): {effective_units}
- Reduction versus memorizing every surface form separately: {reduction} words ({reduction / len(words) * 100:.1f}%)
- Verified manual override rows contributing NGSL-to-NGSL links: {manual_links_used}

## Generated files

- `data/NGSL_internal_families.csv` — one row per multi-word NGSL family.
- `data/NGSL_singletons.csv` — NGSL words not currently linked to another NGSL word.
- `data/NGSL_word_family_map.csv` — one row per NGSL word, including its family and related words when applicable.

## Method

The analysis merges words using two conservative layers:
1. NLTK English Snowball stemming, only when the stem has at least 4 characters.
2. Previously verified manual family overrides when the NGSL side contains multiple NGSL words.

This is a reproducible study-oriented lexical-family analysis, not a claim that every morphological or etymological relationship in English has been captured. Manual review can further refine missed or ambiguous families.
"""
(ANALYSIS_DIR / "NGSL_INTERNAL_SUMMARY.md").write_text(summary, encoding="utf-8")

print(summary)
