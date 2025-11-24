# src/llm/json_postprocessor.py
"""
Utilities to extract and clean JSON produced by LLMs.

Improvements:
- _remove_comments now only strips comments that are outside of quoted strings,
  avoiding accidental removal of '//' inside URLs or other string values.
- Conservative repairs, extraction of the first balanced JSON block,
  fix for broken quoted strings (joining stray newlines inside quotes),
  and progressive parsing attempts with informative ParseError.detail.
"""

import re
import json
from typing import Optional, Dict, Any


class ParseError(ValueError):
    def __init__(self, message: str, detail: Dict[str, Any]):
        super().__init__(message)
        self.detail = detail


# -------------------------
# Basic helpers / cleaners
# -------------------------
def _remove_fences(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```", "", text)
    text = re.sub(r"~~~(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*~~~", "", text)
    return text.strip()


def _remove_comments(text: str) -> str:
    """
    Remove JavaScript style // and /* */ comments **only when they are outside
    of JSON double-quoted strings**. This scans char-by-char tracking whether
    we are inside a string (respecting backslash escapes).
    """
    if not text:
        return text

    out = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        ch = text[i]

        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\":
            # start escape sequence inside string (or literal backslash)
            out.append(ch)
            escape = True
            i += 1
            continue

        if ch == '"' :
            # toggle string state and output the quote
            in_string = not in_string
            out.append(ch)
            i += 1
            continue

        if not in_string and ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                # line comment outside string: skip until end of line
                i += 2
                while i < n and text[i] not in ("\n", "\r"):
                    i += 1
                # keep the newline char so structure/line numbers preserved
                continue
            elif nxt == "*":
                # block comment outside string: skip until closing */
                i += 2
                while i + 1 < n:
                    if text[i] == "*" and text[i + 1] == "/":
                        i += 2
                        break
                    i += 1
                continue

        # default: copy char
        out.append(ch)
        i += 1

    return "".join(out)


def _replace_smart_quotes(text: str) -> str:
    return text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")


def _remove_trailing_commas(text: str) -> str:
    return re.sub(r",\s*(?=[}\]])", "", text)


def _replace_single_quotes_conservative(text: str) -> str:
    """
    Replace single-quoted property names and values with double quotes
    in a conservative way (only when they look like JSON keys or JSON values).
    """
    # 'key':  -> "key":
    text = re.sub(r"(?<=\{|\[|\s)'([A-Za-z0-9_\- ]+)'\s*:", r'"\1":', text)
    # : 'value' (before comma or closing brace/bracket)
    text = re.sub(r":\s*'([^']*)'(?=\s*[,\}\]])", r': "\1"', text)
    return text


# -------------------------------------------------------
# Extract first balanced JSON substring (stack-aware)
# -------------------------------------------------------
def extract_first_json(text: str) -> Optional[str]:
    if not text:
        return None

    start_idx = None
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            start_idx = i
            break
    if start_idx is None:
        return None

    stack = []
    in_string = False
    escape = False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append(ch)
        elif ch == "}":
            if not stack:
                return None
            top = stack.pop()
            if top != "{":
                return None
            if not stack:
                return text[start_idx : i + 1]
        elif ch == "]":
            if not stack:
                return None
            top = stack.pop()
            if top != "[":
                return None
            if not stack:
                return text[start_idx : i + 1]
    # truncated JSON — return what we have
    return text[start_idx:]


# -------------------------------------------------------
# Fix quoted strings that were split across newlines
# -------------------------------------------------------
def _fix_broken_quoted_strings(text: str) -> str:
    """
    Remove stray newlines that appear inside JSON double-quoted strings,
    preserving escape sequences.
    """
    out_chars = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            out_chars.append(ch)
            escape = False
            continue

        if ch == "\\":
            out_chars.append(ch)
            escape = True
            continue

        if ch == '"' and not escape:
            in_string = not in_string
            out_chars.append(ch)
            continue

        if in_string and ch in ("\n", "\r"):
            # replace newline inside a quoted string with a single space (avoid collapsing structure)
            if out_chars and out_chars[-1] != " ":
                out_chars.append(" ")
            continue

        out_chars.append(ch)

    return "".join(out_chars)


# -------------------------
# High-level cleaning pass
# -------------------------
def clean_json_text(text: Optional[str]) -> str:
    if text is None:
        return ""

    t = text
    t = _remove_fences(t)
    t = _remove_comments(t)          # now safe relative to strings
    t = _replace_smart_quotes(t)

    # If there is extra prose surrounding JSON, extract the first JSON block
    extracted = extract_first_json(t)
    if extracted:
        t = extracted

    # conservative single-quote fixes
    t = _replace_single_quotes_conservative(t)

    # fix broken quoted strings (join split lines inside quotes)
    t = _fix_broken_quoted_strings(t)

    # remove trailing commas
    t = _remove_trailing_commas(t)

    return t.strip()


# -------------------------
# Parsing routine
# -------------------------
def parse_json_from_llm(text: Optional[str]):
    """
    Try progressive parsing strategies, return parsed object or raise ParseError with details.
    """
    original = text or ""
    attempts: Dict[str, Any] = {}

    # Attempt 0: direct parse
    try:
        attempts["direct"] = {"success": True, "text": original}
        return json.loads(original)
    except Exception as e:
        attempts["direct"] = {"success": False, "error": str(e)}

    # Attempt 1: cleaned
    cleaned = clean_json_text(original)
    try:
        attempts["cleaned"] = {"success": True, "text": cleaned}
        return json.loads(cleaned)
    except Exception as e:
        attempts["cleaned"] = {"success": False, "error": str(e), "text": cleaned}

    # Attempt 2: aggressive fallback - replace remaining single quotes inside strings and try again
    aggressive = re.sub(r"(?<!\\)'", '"', cleaned)  # naive fallback: replace remaining single quotes with double quotes
    aggressive = _remove_trailing_commas(aggressive)
    try:
        attempts["aggressive"] = {"success": True, "text": aggressive}
        return json.loads(aggressive)
    except Exception as e:
        attempts["aggressive"] = {"success": False, "error": str(e), "text": aggressive}

    # All attempts failed — raise ParseError with detail for debugging
    detail = {
        "original": original,
        "attempts": attempts,
    }
    raise ParseError("Failed to parse JSON from LLM output.", detail)
