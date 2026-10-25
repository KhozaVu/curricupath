"""Turn module NAMES that follow a status phrase into module codes.

"I failed Software Development II and Control I" becomes "I failed ELEN3009A and ELEN3016A", so the
same code-based reading of declared statuses handles names. Only exact catalogue titles are
replaced, only inside the part of the message that a status phrase governs, and only when the
title maps to one module; anything else is left alone, never guessed.
"""

from __future__ import annotations

import re
from typing import Iterable

_TRIGGER = re.compile(
    r"\b(?:failed|fail|flunked|did not pass|didn'?t pass|not passed|have not passed|haven'?t passed|"
    r"have not completed|haven'?t completed|not completed|have not done|haven'?t done|never passed|"
    r"never completed|completed|passed|finished|have done|already done|"
    r"(?:currently\s+)?(?:taking|doing|enrolled in|studying)|"
    r"plan(?:ning)?\s+to\s+(?:take|do)|will\s+(?:take|do)|going\s+to\s+(?:take|do))\s+"
    r"(?:the\s+)?(?:modules?\s+|courses?\s+)?",
    re.IGNORECASE,
)
# Where a status phrase stops governing the words after it.
_STOP = re.compile(
    r"[.?!;\n]|,?\s+(?:can|could|may|am|do|will|would|is|should|what|how)\s+(?:i|it|this)\b"
    r"|\s+(?:but|so|then|however)\s+",
    re.IGNORECASE,
)
_AFTER_FORM = re.compile(
    r"^\s*[\(,:-]?\s*(?:i\s+)?(?:failed|not passed|not completed|not done|was failed)\b",
    re.IGNORECASE,
)


def _names_to_codes(modules: Iterable[dict[str, object]]) -> dict[str, str]:
    """Lower-case exact title -> code, keeping only titles that map to a single module."""

    by_name: dict[str, set[str]] = {}
    for module in modules:
        name = " ".join(str(module["course_name"]).lower().split())
        by_name.setdefault(name, set()).add(str(module["course_code"]).upper())
    return {name: next(iter(codes)) for name, codes in by_name.items() if len(codes) == 1}


def _replace_names(segment: str, names: dict[str, str]) -> str:
    """Replace exact titles in `segment` by codes, longest titles first, no overlaps."""

    spans: list[tuple[int, int, str]] = []
    taken: list[tuple[int, int]] = []
    lowered = segment.lower()
    for name in sorted(names, key=len, reverse=True):
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", lowered):
            if any(match.start() < end and start < match.end() for start, end in taken):
                continue
            taken.append((match.start(), match.end()))
            spans.append((match.start(), match.end(), names[name]))
    out, cursor = [], 0
    for start, end, code in sorted(spans):
        out.append(segment[cursor:start])
        out.append(code)
        cursor = end
    out.append(segment[cursor:])
    return "".join(out)


def rewrite_declared_names(message: str, modules: Iterable[dict[str, object]]) -> str:
    """Return `message` with module titles governed by a status phrase replaced by codes."""

    names = _names_to_codes(modules)
    if not names:
        return message
    pieces, cursor = [], 0
    for trigger in _TRIGGER.finditer(message):
        if trigger.start() < cursor:
            continue
        tail_start = trigger.end()
        stop = _STOP.search(message, tail_start)
        tail_end = stop.start() if stop else len(message)
        pieces.append(message[cursor:tail_start])
        pieces.append(_replace_names(message[tail_start:tail_end], names))
        cursor = tail_end
    pieces.append(message[cursor:])
    rewritten = "".join(pieces)

    # "Software Development II (failed)": a title followed by a negative status.
    lowered = rewritten.lower()
    for name in sorted(names, key=len, reverse=True):
        for match in list(re.finditer(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", lowered)):
            if _AFTER_FORM.match(rewritten[match.end():]):
                rewritten = rewritten[: match.start()] + names[name] + rewritten[match.end():]
                lowered = rewritten.lower()
                break
    return rewritten
