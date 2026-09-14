from collections import defaultdict
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis" / "same_family_candidates.csv"
OUTPUT = ROOT / "data" / "NAWL_family_linked.csv"


def split_words(cell: str):
    return [part.strip() for part in cell.split(";") if part.strip()]


linked = defaultdict(lambda: {"ngsl": set(), "families": set()})

with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    required = {"family_key", "NGSL_words", "NAWL_words"}
    if not required.issubset(reader.fieldnames or []):
        raise RuntimeError(f"Unexpected columns in {SOURCE}")

    for row in reader:
        family_key = row["family_key"].strip()
        ngsl_words = split_words(row["NGSL_words"])
        nawl_words = split_words(row["NAWL_words"])
        for nawl_word in nawl_words:
            linked[nawl_word]["ngsl"].update(ngsl_words)
            linked[nawl_word]["families"].add(family_key)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["NAWL_word", "NGSL_family_words", "family_keys"])
    for nawl_word in sorted(linked):
        writer.writerow([
            nawl_word,
            "; ".join(sorted(linked[nawl_word]["ngsl"])),
            "; ".join(sorted(linked[nawl_word]["families"])),
        ])

print(f"Wrote {len(linked)} linked NAWL words to {OUTPUT}")
