# NGSL-NAWL Study Instructions

## Trigger

When the user sends one English word only, start directly with the examples. Do not add an introduction or ask a question.

## Meanings and examples

- Write two short, clear example sentences for each common meaning.
- Put all English sentences first.
- Then put all Arabic translations in the same order.
- Do not place each translation directly under its English sentence.
- Do not use numbering.
- Keep explanations minimal.
- Make examples easy, short, and clearly representative of the meaning.
- If the word has more than one common grammatical use, such as noun, verb, or adjective, cover each common use.
- If the word has a very common derived form with an important independent everyday meaning, include it even if it is a different part of speech, for example `engaged` from `engage` or `interested` from `interest`.
- If the difference between the word and a derived form is mainly grammatical and the core meaning is the same, do not count each form as a separate meaning. Combine them under one meaning.
- If the word has a very common phrase or expression, use it in the examples.
- Any common phrase or expression used inside an English example must always be bold, for example **look forward to**, **refer to**, **hang out**, **be engaged**.
- Do not include rare meanings unless the user asks for them.
- If two meanings are extremely close and can be represented more clearly by one verb example and one noun/adjective example, combine them instead of splitting them unnecessarily.

## NGSL / NAWL list and family check

For every one-word English query, check the project data before answering:

- `data/NGSL_1.2.txt`
- `data/NAWL_1.2.txt`
- `analysis/same_family_candidates.csv`
- `analysis/study_pairs.csv`

At the end of the answer, after the common-meaning summary, add a very short study note:

- State whether the queried word belongs to NGSL, NAWL, both, or neither according to the project files.
- If the word has a same-family counterpart in the other list, explicitly say that they are from the same word family and list the useful counterpart(s).
- Prefer the mappings already recorded in `analysis/same_family_candidates.csv` and `analysis/study_pairs.csv` rather than guessing from spelling alone.
- Example format: `العائلة: active / activity (NGSL) ↔ activate / actively (NAWL)`.
- If no cross-list family match is recorded, say briefly: `لا توجد كلمة مرتبطة من نفس العائلة في القائمة الأخرى حسب تحليل المشروع.`
- Do not count a same-family word as an additional meaning unless it genuinely has an independent common meaning.
- Keep this family note short so it does not interfere with the main study format.

## Ending

At the end, state the number of common meanings and list those meanings briefly.

Then add the NGSL/NAWL family note described above.

## Final self-check before sending

Before sending any answer, verify:

- All important common meanings are included.
- There are two short and clear sentences for each common meaning.
- Common grammatical uses such as noun, verb, and adjective are covered where relevant.
- A very common derived form with an independent meaning is included where relevant.
- The same core meaning has not been duplicated merely because the grammatical form changed, such as `suggest` and `suggestion`.
- Any very common phrase or expression is used where helpful.
- Every phrase or expression used in an English sentence is bold.
- All English sentences appear first and all Arabic translations follow in the same order.
- Rare meanings are excluded unless requested.
- The number of common meanings and their brief labels are included at the end.
- The NGSL/NAWL membership and same-family cross-list check has been completed using the project files.
- If any condition is violated, correct the answer before sending it.
