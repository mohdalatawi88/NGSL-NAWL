# NGSL internal lexical-family analysis

- Total NGSL words: 2809
- Multi-word lexical families: 271
- NGSL words inside multi-word families: 577
- Singleton NGSL words: 2232
- Effective study units (families + singletons): 2503
- Reduction versus memorizing every surface form separately: 306 words (10.9%)
- Verified manual override rows contributing NGSL-to-NGSL links: 21

## Generated files

- `data/NGSL_internal_families.csv` — one row per multi-word NGSL family.
- `data/NGSL_singletons.csv` — NGSL words not currently linked to another NGSL word.
- `data/NGSL_word_family_map.csv` — one row per NGSL word, including its family and related words when applicable.

## Method

The analysis merges words using two conservative layers:
1. NLTK English Snowball stemming, only when the stem has at least 4 characters.
2. Previously verified manual family overrides when the NGSL side contains multiple NGSL words.

This is a reproducible study-oriented lexical-family analysis, not a claim that every morphological or etymological relationship in English has been captured. Manual review can further refine missed or ambiguous families.
