"""Lightweight Persian/Arabic text normalisation and language detection.

The original prompt is never modified: callers keep it for the skills and use the
normalised copy only for routing heuristics and calculator parsing.
"""
from __future__ import annotations

import re
import unicodedata

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "0123456789"

_TO_ASCII_DIGITS = str.maketrans(PERSIAN_DIGITS + ARABIC_INDIC_DIGITS, ASCII_DIGITS * 2)
_TO_PERSIAN_DIGITS = str.maketrans(ASCII_DIGITS, PERSIAN_DIGITS)

# Arabic letter variants -> Persian letters.
_LETTERS = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})

# Persian / typographic punctuation and operators -> ASCII equivalents.
_PUNCTUATION = str.maketrans({
    "،": ",", "؛": ";", "؟": "?", "٪": "%", "٫": ".", "٬": ",",
    "«": '"', "»": '"', "“": '"', "”": '"', "’": "'", "‘": "'",
    "×": "*", "·": "*", "÷": "/", "−": "-", "–": "-", "—": "-",
})

_TATWEEL_AND_MARKS = re.compile("[ـً-ٰٟ‎‏‪-‮⁦-⁩]")
_PRESENTATION_FORMS = re.compile("[ﭐ-﷿ﹰ-ﻼ]")
_ZWNJ = "‌"
_MULTI_ZWNJ = re.compile(_ZWNJ + "{2,}")
_ZWNJ_AROUND_SPACE = re.compile(rf"{_ZWNJ}+(?=\s)|(?<=\s){_ZWNJ}+")
_WHITESPACE = re.compile(r"[^\S\n]+")

_PERSIAN_ONLY_LETTERS = set("پچژگکی")  # also Persian ک and ی
_ARABIC_SCRIPT = re.compile("[؀-ۿݐ-ݿࢠ-ࣿ]")
_LATIN = re.compile("[A-Za-z]")


def to_ascii_digits(text: str) -> str:
    """Convert Persian and Arabic-Indic digits to ASCII digits."""
    return text.translate(_TO_ASCII_DIGITS)


def to_persian_digits(text: str) -> str:
    """Convert ASCII digits to Persian digits (used for Persian output)."""
    return text.translate(_TO_PERSIAN_DIGITS)


def normalize_text(text: str) -> str:
    """Return a normalised copy of ``text`` for routing and calculator parsing.

    Unifies Arabic/Persian letter variants, converts digits and punctuation to ASCII,
    removes tatweel/diacritics/bidi marks, collapses ZWNJ and whitespace.
    The input string is not modified.
    """
    text = _PRESENTATION_FORMS.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)
    text = text.translate(_LETTERS).translate(_TO_ASCII_DIGITS).translate(_PUNCTUATION)
    text = _TATWEEL_AND_MARKS.sub("", text)
    text = _MULTI_ZWNJ.sub(_ZWNJ, text)
    text = _ZWNJ_AROUND_SPACE.sub("", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def detect_language(text: str) -> str:
    """Script-based language hint: ``fa``, ``ar``, ``en`` or ``unknown``.

    Only letters are counted, so digits and math symbols never make a prompt "English".
    Arabic-script text is ``fa`` when it contains Persian-specific letters (پ چ ژ گ,
    Persian ک / ی) and ``ar`` otherwise.
    """
    arabic = sum(1 for ch in text if ch.isalpha() and _ARABIC_SCRIPT.match(ch))
    latin = len(_LATIN.findall(text))
    if arabic == 0 and latin == 0:
        return "unknown"
    if arabic >= latin:
        return "fa" if any(ch in _PERSIAN_ONLY_LETTERS for ch in text) else "ar"
    return "en"
