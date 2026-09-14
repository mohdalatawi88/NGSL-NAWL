#!/usr/bin/env python3
"""
Strict validator for one-word NGSL/NAWL study answers.

It validates the deterministic parts of AGENTS.md:
- the query is exactly one English word;
- no numbered/bulleted answer lines;
- all English examples come before all Arabic translations;
- exactly two English examples and two Arabic translations per declared common meaning;
- a common-meaning summary is present;
- NGSL/NAWL membership is correct against the project files;
- cross-list family note is correct against the project analysis files;
- selected common expressions are bold when used;
- selected high-value derived forms can be required.

Semantic completeness ("all important common meanings") cannot be proven by
syntax alone. This validator makes that limitation explicit and allows curated
requirements to be extended through constants below or a JSON rules file.

Exit code:
  0 = validation passed
  1 = validation failed
  2 = configuration / file error
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
ENGLISH_WORD_RE = re.compile(r"^[A-Za-z]+(?:['’-][A-Za-z]+)?$")
NUMBERING_RE = re.compile(r"^\s*(?:[-*•]\s+|\d+\s*[\.\):\-]\s*)")
SUMMARY_RE = re.compile(r"^\s*المعاني الشائعة\s*:\s*(\d+)\s*(?:[—–-]\s*(.+))?\s*$")
LIST_RE = re.compile(r"^\s*القائمة\s*:\s*(NGSL|NAWL|both|neither)\s*$", re.I)
FAMILY_PREFIX_RE = re.compile(r"^\s*العائلة\s*:\s*(.+?)\s*$")
NO_FAMILY_TEXT = "لا توجد كلمة مرتبطة من نفس العائلة في القائمة الأخرى حسب تحليل المشروع."

DEFAULT_COMMON_PHRASES = {
    "look forward to",
    "refer to",
    "hang out",
    "be engaged",
}

DEFAULT_REQUIRED_DERIVATIVES = {
    "engage": {"engaged"},
    "interest": {"interested"},
}


@dataclass(frozen=True)
class FamilyRow:
    key: str
    ngsl: tuple[str, ...]
    nawl: tuple[str, ...]


@dataclass
class ValidationResult:
    ok: bool
    word: str
    errors: list[str]
    warnings: list[str]
    details: dict

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


class ProjectData:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ngsl = self._load_word_list(root / "data" / "NGSL_1.2.txt")
        self.nawl = self._load_word_list(root / "data" / "NAWL_1.2.txt")
        self.families = self._load_families(root / "analysis" / "same_family_candidates.csv")

    @staticmethod
    def _load_word_list(path: Path) -> set[str]:
        if not path.exists():
            raise FileNotFoundError(f"Missing project file: {path}")
        return {
            line.strip().casefold()
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        }

    @staticmethod
    def _split_words(cell: str) -> tuple[str, ...]:
        return tuple(part.strip().casefold() for part in cell.split(";") if part.strip())

    def _load_families(self, path: Path) -> list[FamilyRow]:
        if not path.exists():
            raise FileNotFoundError(f"Missing project file: {path}")
        rows: list[FamilyRow] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"family_key", "NGSL_words", "NAWL_words"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"Unexpected family CSV columns in {path}")
            for row in reader:
                rows.append(
                    FamilyRow(
                        key=(row["family_key"] or "").strip(),
                        ngsl=self._split_words(row["NGSL_words"] or ""),
                        nawl=self._split_words(row["NAWL_words"] or ""),
                    )
                )
        return rows

    def membership(self, word: str) -> str:
        w = word.casefold()
        in_ngsl = w in self.ngsl
        in_nawl = w in self.nawl
        if in_ngsl and in_nawl:
            return "both"
        if in_ngsl:
            return "NGSL"
        if in_nawl:
            return "NAWL"
        return "neither"

    def family_rows_for(self, word: str) -> list[FamilyRow]:
        w = word.casefold()
        return [row for row in self.families if w in row.ngsl or w in row.nawl]

    def cross_list_counterparts(self, word: str) -> set[str]:
        w = word.casefold()
        out: set[str] = set()
        for row in self.family_rows_for(w):
            if w in row.ngsl:
                out.update(row.nawl)
            if w in row.nawl:
                out.update(row.ngsl)
        out.discard(w)
        return out


def load_optional_rules(root: Path) -> tuple[set[str], dict[str, set[str]]]:
    phrases = set(DEFAULT_COMMON_PHRASES)
    derivatives = {k: set(v) for k, v in DEFAULT_REQUIRED_DERIVATIVES.items()}
    path = root / "config" / "validator_rules.json"
    if not path.exists():
        return phrases, derivatives

    payload = json.loads(path.read_text(encoding="utf-8"))
    for phrase in payload.get("common_phrases", []):
        if isinstance(phrase, str) and phrase.strip():
            phrases.add(phrase.strip().casefold())
    for word, forms in payload.get("required_derivatives", {}).items():
        if not isinstance(word, str) or not isinstance(forms, list):
            continue
        derivatives.setdefault(word.casefold(), set()).update(
            form.casefold() for form in forms if isinstance(form, str) and form.strip()
        )
    return phrases, derivatives


def _is_arabic_line(line: str) -> bool:
    return bool(ARABIC_RE.search(line))


def _strip_bold(text: str) -> str:
    return text.replace("**", "")


def _phrase_is_bold(line: str, phrase: str) -> bool:
    pattern = re.compile(r"\*\*" + re.escape(phrase) + r"\*\*", re.I)
    return bool(pattern.search(line))


def _contains_word(text: str, word: str) -> bool:
    return bool(re.search(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", text, re.I))


def _meaning_summary(lines: list[str]) -> tuple[int | None, str | None, int | None]:
    for i, line in enumerate(lines):
        match = SUMMARY_RE.match(line)
        if match:
            return int(match.group(1)), (match.group(2) or "").strip(), i
    return None, None, None


def _find_line(lines: list[str], regex: re.Pattern[str]) -> tuple[str | None, int | None, re.Match[str] | None]:
    for i, line in enumerate(lines):
        match = regex.match(line)
        if match:
            return line, i, match
    return None, None, None


def validate(
    word: str,
    response: str,
    data: ProjectData,
    common_phrases: set[str] | None = None,
    required_derivatives: dict[str, set[str]] | None = None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    word = word.strip()
    w = word.casefold()
    common_phrases = common_phrases or set(DEFAULT_COMMON_PHRASES)
    required_derivatives = required_derivatives or {
        k: set(v) for k, v in DEFAULT_REQUIRED_DERIVATIVES.items()
    }

    if not ENGLISH_WORD_RE.fullmatch(word):
        errors.append("The query must contain exactly one English word.")

    raw_lines = [line.rstrip() for line in response.replace("\r\n", "\n").split("\n")]
    lines = [line.strip() for line in raw_lines if line.strip()]

    if not lines:
        errors.append("The response is empty.")
        return ValidationResult(False, word, errors, warnings, {})

    for line in lines:
        if NUMBERING_RE.match(line):
            errors.append(f"Numbering/bullets are not allowed: {line!r}")

    meaning_count, meaning_labels, summary_i = _meaning_summary(lines)
    if meaning_count is None or summary_i is None:
        errors.append("Missing required final line: 'المعاني الشائعة: N — ...'.")
    else:
        if meaning_count < 1:
            errors.append("The number of common meanings must be at least 1.")
        if not meaning_labels:
            errors.append("The common-meaning summary must briefly name the meanings.")

    list_line, list_i, list_match = _find_line(lines, LIST_RE)
    expected_membership = data.membership(word) if ENGLISH_WORD_RE.fullmatch(word) else "neither"
    if list_line is None or list_match is None:
        errors.append("Missing required list note: 'القائمة: NGSL|NAWL|both|neither'.")
    else:
        actual_membership = list_match.group(1)
        normalized_actual = actual_membership if actual_membership in {"NGSL", "NAWL"} else actual_membership.lower()
        normalized_expected = expected_membership if expected_membership in {"NGSL", "NAWL"} else expected_membership.lower()
        if normalized_actual != normalized_expected:
            errors.append(f"Incorrect list membership: expected {expected_membership}, got {actual_membership}.")

    family_line, family_i, family_match = _find_line(lines, FAMILY_PREFIX_RE)
    counterparts = data.cross_list_counterparts(word) if ENGLISH_WORD_RE.fullmatch(word) else set()
    if family_line is None or family_match is None:
        errors.append("Missing required family note beginning with 'العائلة:'.")
    else:
        family_body = family_match.group(1)
        if counterparts:
            if NO_FAMILY_TEXT in family_body:
                errors.append("A cross-list family match exists, but the response says none exists.")
            if not any(_contains_word(family_body, counterpart) for counterpart in counterparts):
                errors.append(
                    "Family note does not include any verified counterpart from the other list. "
                    f"Expected one of: {', '.join(sorted(counterparts))}."
                )
        else:
            if NO_FAMILY_TEXT not in family_body:
                errors.append("No verified cross-list family match exists; use the required no-family sentence.")

    if summary_i is not None and list_i is not None and family_i is not None:
        expected_indices = [len(lines) - 3, len(lines) - 2, len(lines) - 1]
        if [summary_i, list_i, family_i] != expected_indices:
            errors.append(
                "The final three nonblank lines must be, in order: common meanings, list membership, family note."
            )

    example_lines: list[str] = lines[:summary_i] if summary_i is not None else []
    english_lines: list[str] = []
    arabic_lines: list[str] = []
    seen_arabic = False

    for line in example_lines:
        if _is_arabic_line(line):
            seen_arabic = True
            arabic_lines.append(line)
        else:
            if seen_arabic:
                errors.append(
                    f"English text appears after Arabic translations: {line!r}. All English examples must come first."
                )
            english_lines.append(line)

    if meaning_count is not None and meaning_count >= 1:
        expected_examples = meaning_count * 2
        if len(english_lines) != expected_examples:
            errors.append(
                f"Expected exactly {expected_examples} English examples (2 × {meaning_count} meanings), "
                f"found {len(english_lines)}."
            )
        if len(arabic_lines) != expected_examples:
            errors.append(
                f"Expected exactly {expected_examples} Arabic translations (2 × {meaning_count} meanings), "
                f"found {len(arabic_lines)}."
            )

    if len(english_lines) != len(arabic_lines):
        errors.append(f"English/Arabic example counts differ: {len(english_lines)} vs {len(arabic_lines)}.")

    for line in english_lines:
        plain = _strip_bold(line)
        words = re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)?", plain)
        if len(words) > 14:
            warnings.append(f"English example may be too long ({len(words)} words): {line!r}")

    for line in english_lines:
        plain = _strip_bold(line).casefold()
        for phrase in common_phrases:
            if phrase in plain and not _phrase_is_bold(line, phrase):
                errors.append(f"Common phrase must be bold: **{phrase}** in {line!r}")

    for required in sorted(required_derivatives.get(w, set())):
        if not any(_contains_word(_strip_bold(line), required) for line in english_lines):
            errors.append(f"Required common derived form {required!r} is missing from the English examples.")

    warnings.append(
        "Semantic completeness (whether every important common meaning and grammatical use is covered) "
        "still requires a language model or curated dictionary; this validator enforces the deterministic rules."
    )

    details = {
        "membership": expected_membership,
        "verified_cross_list_counterparts": sorted(counterparts),
        "declared_common_meanings": meaning_count,
        "english_example_count": len(english_lines),
        "arabic_translation_count": len(arabic_lines),
    }
    return ValidationResult(not errors, word, errors, warnings, details)


def build_study_note(word: str, data: ProjectData) -> str:
    membership = data.membership(word)
    counterparts = sorted(data.cross_list_counterparts(word))
    list_line = f"القائمة: {membership}"
    if counterparts:
        family_line = f"العائلة: {word} ↔ " + " / ".join(counterparts)
    else:
        family_line = f"العائلة: {NO_FAMILY_TEXT}"
    return list_line + "\n" + family_line


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "data" / "NGSL_1.2.txt").exists() and (candidate / "AGENTS.md").exists():
            return candidate
    raise FileNotFoundError("Could not find project root containing AGENTS.md and data/NGSL_1.2.txt.")


def read_response(path_value: str | None) -> str:
    if path_value in (None, "-"):
        return sys.stdin.read()
    return Path(path_value).read_text(encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate NGSL/NAWL one-word study responses.")
    parser.add_argument("word", help="The queried English word.")
    parser.add_argument("response", nargs="?", default="-", help="Response text file. Use '-' or omit for stdin.")
    parser.add_argument("--root", type=Path, help="Project root. Auto-detected when omitted.")
    parser.add_argument(
        "--print-study-note",
        action="store_true",
        help="Print the required NGSL/NAWL study note for the word and exit.",
    )
    parser.add_argument("--json", action="store_true", help="Print the validation report as JSON.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        root = args.root.resolve() if args.root else find_project_root()
        data = ProjectData(root)
        phrases, derivatives = load_optional_rules(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2

    if args.print_study_note:
        print(build_study_note(args.word, data))
        return 0

    try:
        response = read_response(args.response)
    except OSError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2

    result = validate(args.word, response, data, phrases, derivatives)

    if args.json:
        print(result.to_json())
    else:
        print("PASS" if result.ok else "FAIL")
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"- {error}")
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        print("\nDetails:")
        for key, value in result.details.items():
            print(f"- {key}: {value}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
