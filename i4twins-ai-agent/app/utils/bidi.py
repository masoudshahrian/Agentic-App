"""Render model output as HTML with per-line direction: Persian lines right-to-left, everything else left-to-right."""
from __future__ import annotations

import html
import re

# Arabic-script letters (Persian included) but not the digit ranges, so a bare number stays left-to-right.
_PERSIAN_LETTER = re.compile("[؀-؅ؐ-ؚ؜-ەۥ-ۿݐ-ݿﭐ-﷿ﹰ-ﻼ]")
_DIGIT_RANGES = re.compile("[٠-٩۰-۹]")


def is_rtl(line: str) -> bool:
    """True when the line contains Persian/Arabic letters (digits alone do not count)."""
    return bool(_PERSIAN_LETTER.search(_DIGIT_RANGES.sub("", line)))


def to_html(text: str) -> str:
    """One <div> per line with ``dir`` and alignment set from the line's own script. Input is HTML-escaped."""
    rows = []
    for line in text.splitlines() or [""]:
        if not line.strip():
            rows.append('<div class="gap">&nbsp;</div>')
            continue
        rtl = is_rtl(line)
        direction, align = ("rtl", "right") if rtl else ("ltr", "left")
        rows.append(f'<div dir="{direction}" style="text-align:{align}">{html.escape(line)}</div>')
    return "".join(rows)
