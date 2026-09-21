# NGSL internal lexical-family analysis

- Total NGSL words: 2809
- Multi-word lexical families: 258
- NGSL words inside multi-word families: 547
- Singleton NGSL words: 2262
- Effective study units (families + singletons): 2520
- Reduction versus memorizing every surface form separately: 289 words (10.3%)
- Verified manual override rows contributing NGSL-to-NGSL links: 21
- Curated false/misleading pair exclusions applied: 21

## Generated files

- `data/NGSL_internal_families.csv` — one row per multi-word NGSL family.
- `data/NGSL_singletons.csv` — NGSL words not currently linked to another NGSL word.
- `data/NGSL_word_family_map.csv` — one row per NGSL word, including its family and related words when applicable.
- `data/NGSL_family_exclusions.csv` — auditable exclusions for false or misleading automatic matches.

## Method

The analysis uses three conservative layers:
1. NLTK English Snowball stemming, only when the stem has at least 4 characters.
2. Previously verified manual family overrides when the NGSL side contains multiple NGSL words.
3. Curated exclusions that override automatic matching for false or misleading learner-oriented families.

This is a reproducible study-oriented lexical-family analysis. It is intentionally conservative and can be refined further as additional ambiguous families are manually reviewed.
