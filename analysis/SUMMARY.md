# NGSL–NAWL overlap analysis

- NGSL words: 2809
- NAWL words: 957
- Exact overlaps: 0
- Cross-list lexical-family groups: 157
- Verified manual family overrides applied: 1
- NAWL words with at least one NGSL same-family candidate: 185
- NAWL words remaining after excluding those family-linked words: 772

## Difficulty classification of all 2809 NGSL words

- Easy: 2563 (91.2%)
- Medium: 233 (8.3%)
- Hard: 13 (0.5%)
- Total classified: 2809

Files:
- `NGSL_easy.txt`
- `NGSL_medium.txt`
- `NGSL_hard.txt`

## Difficulty classification of the 772 remaining NAWL words

- Easy: 297 (38.5%)
- Medium: 385 (49.9%)
- Hard: 90 (11.7%)
- Total classified: 772

Files:
- `NAWL_remaining_easy.txt`
- `NAWL_remaining_medium.txt`
- `NAWL_remaining_hard.txt`

Words inside each difficulty file are ordered from easier/higher-frequency to harder/lower-frequency according to the same score.

Difficulty is a study estimate, not an official CEFR level. It combines English word frequency (wordfreq Zipf frequency), word length, approximate syllable/form complexity, common academic affixes, and a small curated override for obviously concrete/everyday NAWL words.

## Study file

`NAWL_remaining.txt` contains the current 772 NAWL 1.2 words that do not have an NGSL same-family candidate under the project's current verified analysis. The filename deliberately does not encode a fixed count because the total can decrease as verified family links are added.

## Family-analysis method

Exact overlap is a case-insensitive exact word match.

Cross-list family candidates use two layers:
1. NLTK English Snowball stemming for broad candidate discovery.
2. `data/family_overrides.csv` for manually verified lexical families that Snowball misses, such as `develop / development ↔ developmental`.

The override layer is intentionally conservative and auditable. We do not automatically strip arbitrary prefixes/suffixes because that can create false family matches. The remaining count should therefore be treated as the current verified study remainder, not as a permanent linguistic truth.
