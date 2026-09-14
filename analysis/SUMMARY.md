# NGSL–NAWL overlap analysis

- NGSL words: 2809
- NAWL words: 957
- Exact overlaps: 0
- Cross-list same-stem family groups: 156
- NAWL words with at least one NGSL same-family candidate: 184
- NAWL words remaining after excluding those family-linked words: 773

## Difficulty classification of the 773 remaining words

- Easy: 297 (38.4%)
- Medium: 385 (49.8%)
- Hard: 91 (11.8%)
- Total classified: 773

Files:
- `NAWL_remaining_easy.txt`
- `NAWL_remaining_medium.txt`
- `NAWL_remaining_hard.txt`

Words inside each difficulty file are ordered from easier/higher-frequency to harder/lower-frequency according to the same score.

Difficulty is a study estimate, not an official CEFR level. It combines English word frequency (wordfreq Zipf frequency), word length, approximate syllable/form complexity, common academic affixes, and a small curated override for obviously concrete/everyday words.

## Study file

`NAWL_remaining_773.txt` contains the 773 NAWL 1.2 words that do not currently have an NGSL same-family candidate under this project's analysis method. It is generated automatically from the source lists and the same family analysis used for `study_pairs.csv`.

## Family-analysis method

Exact overlap is a case-insensitive exact word match.

Same-family candidates are generated with NLTK's English Snowball stemmer. They are useful study groupings, but stemming is heuristic and can occasionally group words that are not true lexical-family members. Very short stems (<4 characters) are excluded to reduce false positives.
