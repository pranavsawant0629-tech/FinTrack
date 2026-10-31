"""
Deterministic Indian Number and Denomination Parser for FinTrack.

Parses strings containing Indian numbering conventions (lakhs, crores, thousands, k)
and rupee symbols into exact floating-point values.

Enforces a strict ValueError contract for any malformed, ambiguous, or unsupported input.
Never silently guesses a financial amount.
"""

from __future__ import annotations

import re


MAX_ALLOWABLE_VALUE = 1e15  # 1,000 Trillion

UNSUPPORTED_CURRENCIES = [
    ("$", "USD ($)"),
    ("€", "EUR (€)"),
    ("¥", "JPY/CNY (¥)"),
    ("£", "GBP (£)"),
    ("¢", "Cents (¢)"),
    ("CHF", "CHF"),
    ("AUD", "AUD"),
    ("CAD", "CAD"),
    ("USD", "USD"),
    ("EUR", "EUR"),
    ("GBP", "GBP"),
    ("JPY", "JPY"),
    ("CNY", "CNY"),
]

# Denomination multipliers
MULTIPLIERS = {
    "crore": 1e7,
    "crores": 1e7,
    "cr": 1e7,
    "crs": 1e7,
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "l": 1e5,
    "thousand": 1e3,
    "thousands": 1e3,
    "k": 1e3,
}


def _validate_comma_grouping(num_str: str) -> None:
    """
    Validate that commas conform either to standard Indian comma grouping (2-digit grouping after thousand)
    or standard international 3-digit comma grouping.

    Valid Indian:
        - 1,000
        - 10,000
        - 1,00,000
        - 10,00,000
        - 1,00,00,000
    Valid International:
        - 1,000
        - 10,000
        - 100,000
        - 1,000,000
    """
    if "," not in num_str:
        return

    # Check for consecutive or boundary commas
    if ",," in num_str or num_str.startswith(",") or num_str.endswith(","):
        raise ValueError(f"Malformed comma placement in numerical input: '{num_str}'")

    # Split integer and decimal parts
    parts = num_str.split(".")
    if len(parts) > 2:
        raise ValueError(f"Multiple decimal points in numerical input: '{num_str}'")

    int_part = parts[0]
    if not int_part:
        raise ValueError(f"Missing integer digits before decimal: '{num_str}'")

    # Regex for valid Indian grouping: 1-2 digits, followed by optional groups of 2 digits, ending with 3 digits
    # Or simply 1-3 digits with one comma (e.g. 1,000)
    indian_regex = re.compile(r"^\d{1,2}(,\d{2})*,\d{3}$|^\d{1,3},\d{3}$")
    # Regex for standard 3-digit grouping
    intl_regex = re.compile(r"^\d{1,3}(,\d{3})+$")

    if not (indian_regex.match(int_part) or intl_regex.match(int_part)):
        raise ValueError(
            f"Malformed comma grouping: '{num_str}'. "
            "Commas must follow valid Indian (e.g. 1,00,000) or standard (e.g. 100,000) notation."
        )


def parse_indian_number(text: str) -> float:
    """
    Parse a string containing an Indian financial amount into an exact float.

    Args:
        text: Input string (e.g. '5 lakhs', '1.5 crore', '25k', '₹1,00,000', '-50k').

    Returns:
        Exact float representation.

    Raises:
        ValueError: If input is empty, whitespace, malformed, ambiguous, exceeds 1e15,
                    contains unsupported currency symbols, or cannot be parsed without guessing.
    """
    if text is None:
        raise ValueError("Input text cannot be None.")

    if not isinstance(text, str):
        raise ValueError(f"Expected string input, got: {type(text).__name__}")

    if not text:
        raise ValueError("Input text cannot be empty.")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Input text contains only whitespace.")

    # 1. Reject unsupported currency symbols
    for symbol, label in UNSUPPORTED_CURRENCIES:
        if symbol.isalpha():
            if re.search(rf"\b{re.escape(symbol)}\b", cleaned, re.IGNORECASE):
                raise ValueError(
                    f"Unsupported currency symbol detected: '{symbol}' ({label}). "
                    "The Indian number parser strictly supports INR (₹, Rs., Rs, INR) or raw numbers."
                )
        else:
            if symbol in cleaned:
                raise ValueError(
                    f"Unsupported currency symbol detected: '{symbol}' ({label}). "
                    "The Indian number parser strictly supports INR (₹, Rs., Rs, INR) or raw numbers."
                )

    # 2. Reject ambiguous numerical ranges or choices
    if re.search(r"\b(?:to|or|between)\b", cleaned, re.IGNORECASE):
        raise ValueError(
            f"Ambiguous numerical range or choice detected in '{text}'. A single exact numerical amount is required."
        )
    if re.search(r"\d+\s*[-–—]\s*\d+", cleaned):
        raise ValueError(
            f"Ambiguous numerical range detected in '{text}'. A single exact numerical amount is required."
        )

    # 3. Detect and handle sign
    is_negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()
    elif cleaned.startswith("-") or cleaned.startswith("−"):
        is_negative = True
        cleaned = cleaned[1:].strip()
    elif cleaned.lower().startswith("negative"):
        is_negative = True
        cleaned = cleaned[8:].strip()
    elif cleaned.startswith("+"):
        cleaned = cleaned[1:].strip()

    # 4. Strip valid INR currency prefixes and suffixes
    cleaned = re.sub(r"^(?:₹|\brs\.?\s*|\binr\s*)", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"(?:\s*inr|\s*rupees?)$", "", cleaned, flags=re.IGNORECASE).strip()

    if not cleaned:
        raise ValueError(f"No numerical content found in input: '{text}'")

    # Reject leading multipliers where multiplier precedes digits (e.g. 'k 50', 'lakh 5', 'crore 10', 'k50')
    if re.match(r"^(?:crores?|crs?|lakhs?|lacs?|l|thousands?|k)(?:\b|\d)", cleaned, flags=re.IGNORECASE):
        raise ValueError(
            f"Malformed input: denomination multiplier cannot precede numerical digits in '{text}'."
        )

    # 5. Check for malformed multiplier chaining (e.g. '5 lakh crore', '10 k thousand')
    # Words matching multipliers
    found_multipliers = re.findall(
        r"\b(crores?|crs?|lakhs?|lacs?|\bl\b|thousands?|\bk\b)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Also detect attached multiplier suffixes like 5lakh or 10k or 2.5cr
    attached_matches = re.findall(
        r"\d+(?:\.\d+)?(crores?|crs?|lakhs?|lacs?|l|thousands?|k)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    all_multipliers = found_multipliers + [m for m in attached_matches if m not in found_multipliers]

    if len(all_multipliers) > 1:
        raise ValueError(
            f"Malformed denomination chaining detected in '{text}': multiple multipliers {all_multipliers}. "
            "Compounded multipliers like 'lakh crore' are not permitted."
        )

    multiplier_val = 1.0
    mult_word = all_multipliers[0].lower() if all_multipliers else None

    if mult_word:
        multiplier_val = MULTIPLIERS.get(mult_word, 1.0)
        # Remove multiplier word from string to isolate the number
        # Handles both attached suffix (e.g. 2.5cr, 10k, 1.5lakh) and standalone word (e.g. 2.5 crore)
        cleaned = re.sub(
            rf"(?<=\d)\s*{re.escape(mult_word)}\b|\b{re.escape(mult_word)}\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

    # 6. Validate comma grouping before stripping commas
    _validate_comma_grouping(cleaned)
    num_clean = cleaned.replace(",", "").strip()

    # 7. Validate that remaining text is a valid integer or float
    if not re.match(r"^\d+(?:\.\d+)?$", num_clean):
        raise ValueError(
            f"Could not parse a valid numerical amount from '{text}'. Unrecognized or malformed tokens remaining: '{num_clean}'."
        )

    base_num = float(num_clean)
    final_val = base_num * multiplier_val

    if is_negative:
        final_val = -final_val

    # 8. Check maximum allowable threshold (1e15)
    if abs(final_val) > MAX_ALLOWABLE_VALUE:
        raise ValueError(
            f"Numerical value {final_val:,.2f} exceeds maximum allowable threshold (1e15 / 1,000 Trillion)."
        )

    return float(final_val)


def try_parse_indian_number(text: str) -> float | None:
    """
    Safely attempt to parse an Indian number, returning None on any parsing error.
    Used by conversational agents for soft parameter extraction without throwing.
    """
    try:
        return parse_indian_number(text)
    except (ValueError, TypeError):
        return None
