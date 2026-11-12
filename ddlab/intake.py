"""Fail-closed intake for untrusted synthetic text and JSON (V1.4).

Every rejection carries a stable code that the browser implementation
(docs/intake.mjs) must reproduce for the shared vectors in
contracts/intake-vectors.json. Nothing here executes, fetches, stores or
authorizes anything: input is decoded, measured, checked and returned as data.

"Tokens" are whitespace-delimited runs of the decoded text, a cheap size bound;
they are not model tokens.
"""
from __future__ import annotations

import json
import math
import unicodedata
from typing import Any

DEFAULT_LIMITS = {"max_bytes": 524_288, "max_lines": 20_000, "max_tokens": 100_000, "max_depth": 32}
MAX_SAFE_INTEGER = 9_007_199_254_740_991
_MAX_INT_LITERAL_CHARS = 20
# Same six characters as the JSON grammar and the browser pre-parser: SP, HT, LF, CR.
_JSON_WS = " \t\n\r"
# ECMAScript WhiteSpace + LineTerminator, so token counts match String.prototype.split(/\s+/u).
_TOKEN_WS = frozenset("\t\n\x0b\x0c\r \xa0         "
                      "       　﻿")


class IntakeError(ValueError):
    """Input rejected. ``code`` is the cross-runtime contract; the message is advisory."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _limits(overrides: dict[str, int] | None) -> dict[str, int]:
    limits = dict(DEFAULT_LIMITS)
    for key, value in (overrides or {}).items():
        if key not in DEFAULT_LIMITS or isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise IntakeError("INVALID_LIMITS", key)
        limits[key] = value
    return limits


def check_string(text: str) -> None:
    """Character policy applied to raw text and again to every parsed JSON string."""
    for ch in text:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise IntakeError("LONE_SURROGATE")
        if (cp < 0x20 and ch not in "\t\n\r") or 0x7F <= cp <= 0x9F:
            raise IntakeError("CONTROL_CHARACTER", f"U+{cp:04X}")
        if 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
            raise IntakeError("BIDI_CONTROL_CHARACTER", f"U+{cp:04X}")
        if cp == 0xFEFF:
            raise IntakeError("BOM_OR_ZWNBSP")
    if unicodedata.normalize("NFC", text) != text:
        raise IntakeError("NOT_NFC", "normalize the source to NFC before import; offsets refer to the given bytes")


def _count_tokens(text: str) -> int:
    count, inside = 0, False
    for ch in text:
        if ch in _TOKEN_WS:
            inside = False
        elif not inside:
            inside = True
            count += 1
    return count


def read_text_strict(raw: bytes, limits: dict[str, int] | None = None) -> str:
    """Decode bounded UTF-8 text or raise IntakeError. No normalization is applied."""
    if not isinstance(raw, (bytes, bytearray)):
        raise IntakeError("EXPECTED_BYTES")
    lim = _limits(limits)
    if len(raw) > lim["max_bytes"]:
        raise IntakeError("TOO_MANY_BYTES")
    try:
        text = bytes(raw).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise IntakeError("INVALID_UTF8", f"byte offset {exc.start}") from None
    check_string(text)
    if text.count("\n") + 1 > lim["max_lines"]:
        raise IntakeError("TOO_MANY_LINES")
    if _count_tokens(text) > lim["max_tokens"]:
        raise IntakeError("TOO_MANY_TOKENS")
    return text


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise IntakeError("DUPLICATE_KEY", key[:80])
        out[key] = value
    return out


def _parse_int(literal: str) -> int:
    if len(literal) > _MAX_INT_LITERAL_CHARS:
        raise IntakeError("UNSAFE_NUMBER", "integer literal too long")
    return int(literal)


def _reject_constant(literal: str) -> Any:
    raise IntakeError("INVALID_JSON", f"non-finite literal {literal}")


def _walk(value: Any, max_depth: int) -> None:
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > max_depth:
            raise IntakeError("TOO_DEEP")
        if isinstance(item, bool) or item is None:
            continue
        if isinstance(item, str):
            check_string(item)
        elif isinstance(item, int):
            if abs(item) > MAX_SAFE_INTEGER:
                raise IntakeError("UNSAFE_NUMBER", "integer outside the IEEE-754 safe range")
        elif isinstance(item, float):
            if not math.isfinite(item) or (item.is_integer() and abs(item) > MAX_SAFE_INTEGER):
                raise IntakeError("UNSAFE_NUMBER", "non-finite or unsafe integral number")
        elif isinstance(item, dict):
            for key, child in item.items():
                check_string(key)
                pending.append((child, depth + 1))
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)


def parse_json_strict(raw: bytes, limits: dict[str, int] | None = None) -> Any:
    """Bounded, strict UTF-8 JSON: no duplicate keys, unsafe numbers or hidden controls."""
    lim = _limits(limits)
    text = read_text_strict(raw, lim)
    if not text.strip(_JSON_WS):
        raise IntakeError("INVALID_JSON", "empty document")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_parse_int, parse_constant=_reject_constant)
    except IntakeError:
        raise
    except RecursionError:
        raise IntakeError("TOO_DEEP") from None
    except ValueError as exc:
        raise IntakeError("INVALID_JSON", str(exc)[:120]) from None
    _walk(value, lim["max_depth"])
    return value
