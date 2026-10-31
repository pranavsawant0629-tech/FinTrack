"""
Unit tests for the Indian Number & Currency Parser.
Verifies parsing of Indian numbering conventions (lakh, crore, k, thousands),
currency prefixes (₹, Rs., INR), comma formatting, negative values,
and strict rejection of ambiguous, malformed, or unsupported inputs.
"""

import pytest
from app.tools.calc.parser import parse_indian_number, try_parse_indian_number


class TestValidIndianNumberParsing:
    """Tests for successfully parsed Indian numbers."""

    def test_plain_integers_and_decimals(self):
        assert parse_indian_number("500") == 500.0
        assert parse_indian_number("12345") == 12345.0
        assert parse_indian_number("12.50") == 12.50
        assert parse_indian_number("0.75") == 0.75

    def test_standard_indian_comma_grouping(self):
        """Standard Indian comma grouping: 3 digits, then groups of 2 digits."""
        assert parse_indian_number("1,000") == 1000.0
        assert parse_indian_number("10,000") == 10000.0
        assert parse_indian_number("1,00,000") == 100000.0
        assert parse_indian_number("12,34,567") == 1234567.0
        assert parse_indian_number("1,00,00,000") == 10000000.0
        assert parse_indian_number("12,34,56,789.50") == 123456789.50

    def test_standard_international_comma_grouping(self):
        """Accepts standard 3-digit comma grouping as well."""
        assert parse_indian_number("100,000") == 100000.0
        assert parse_indian_number("1,000,000") == 1000000.0

    def test_denomination_multipliers(self):
        """Test k, thousand, lakh, crore denominations."""
        assert parse_indian_number("50k") == 50000.0
        assert parse_indian_number("50 K") == 50000.0
        assert parse_indian_number("25 thousand") == 25000.0
        assert parse_indian_number("1.5L") == 150000.0
        assert parse_indian_number("1.5 lakh") == 150000.0
        assert parse_indian_number("2 Lakhs") == 200000.0
        assert parse_indian_number("5 lac") == 500000.0
        assert parse_indian_number("10 lacs") == 1000000.0
        assert parse_indian_number("2.5Cr") == 25000000.0
        assert parse_indian_number("2.5 crore") == 25000000.0
        assert parse_indian_number("10 Crores") == 100000000.0

    def test_rupee_symbols_and_prefixes(self):
        """Test ₹, Rs., Rs, INR prefixes and suffixes."""
        assert parse_indian_number("₹50,000") == 50000.0
        assert parse_indian_number("₹ 1,50,000") == 150000.0
        assert parse_indian_number("Rs 50000") == 50000.0
        assert parse_indian_number("Rs. 1.5 Lakh") == 150000.0
        assert parse_indian_number("INR 25,000") == 25000.0
        assert parse_indian_number("50000 inr") == 50000.0
        assert parse_indian_number("10 lakh rupees") == 1000000.0

    def test_negative_numbers(self):
        """Test negative representations: -, −, negative, and accounting parentheses."""
        assert parse_indian_number("-500") == -500.0
        assert parse_indian_number("-₹1,000") == -1000.0
        assert parse_indian_number("−25k") == -25000.0
        assert parse_indian_number("negative 50k") == -50000.0
        assert parse_indian_number("(50,000)") == -50000.0
        assert parse_indian_number("(₹1.5 Lakh)") == -150000.0

    def test_positive_sign_numbers(self):
        """Explicit positive sign numbers."""
        assert parse_indian_number("+500") == 500.0
        assert parse_indian_number("+ ₹ 50,000") == 50000.0
        assert parse_indian_number("+2.5L") == 250000.0


class TestInvalidNumberRejection:
    """Tests for inputs that must be rejected with ValueError by parse_indian_number."""

    def test_empty_and_whitespace(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_indian_number("")

        with pytest.raises(ValueError, match="only whitespace"):
            parse_indian_number("   ")

    def test_unsupported_foreign_currencies(self):
        """Strictly rejects non-INR currency symbols and ISO currency words."""
        for symbol in ["$", "€", "¥", "£", "USD", "EUR", "GBP", "JPY"]:
            with pytest.raises(ValueError, match="Unsupported currency symbol"):
                parse_indian_number(f"{symbol} 500")

    def test_leading_multiplier_rejected(self):
        """Rejects numbers where multiplier precedes digits."""
        bad_leading = ["k 50", "lakh 5", "crore 10", "k50", "lakh5"]
        for bad in bad_leading:
            with pytest.raises(ValueError, match="denomination multiplier cannot precede"):
                parse_indian_number(bad)

    def test_malformed_comma_grouping(self):
        """Rejects nonsensical comma placements."""
        malformed = ["1,2345,67", "12,,345", ",1000", "1000,", "12,34"]
        for bad in malformed:
            with pytest.raises(ValueError, match="[Mm]alformed comma"):
                parse_indian_number(bad)

    def test_ambiguous_ranges(self):
        """Rejects ranges like 10-20k or 50 to 100."""
        with pytest.raises(ValueError, match="Ambiguous numerical range"):
            parse_indian_number("10-20k")

        with pytest.raises(ValueError, match="Ambiguous numerical range"):
            parse_indian_number("50 to 100 lakh")

        with pytest.raises(ValueError, match="Ambiguous numerical range"):
            parse_indian_number("between 10k and 20k")

    def test_chained_multipliers(self):
        """Rejects compounding multipliers like '50 lakh crore' or '10 k thousand'."""
        with pytest.raises(ValueError, match="Malformed denomination chaining"):
            parse_indian_number("50 lakh crore")

        with pytest.raises(ValueError, match="Malformed denomination chaining"):
            parse_indian_number("10 k thousand")

    def test_exceeding_maximum_threshold(self):
        """Rejects values greater than 1e15 (1,000 Trillion)."""
        with pytest.raises(ValueError, match="exceeds maximum allowable threshold"):
            parse_indian_number("2000000000000000")

    def test_garbage_and_non_numeric(self):
        with pytest.raises(ValueError):
            parse_indian_number("hello world")

        with pytest.raises(ValueError):
            parse_indian_number("abc")

    def test_distinguishes_percentage_and_currency(self):
        """Percentages with % symbol are rejected as currency amounts."""
        with pytest.raises(ValueError):
            parse_indian_number("10%")

        # Whereas raw 10 is parsed as 10.0
        assert parse_indian_number("10") == 10.0


class TestTryParseWrapper:
    """Tests for non-throwing try_parse_indian_number."""

    def test_try_parse_success(self):
        assert try_parse_indian_number("₹ 2.5 Lakh") == 250000.0
        assert try_parse_indian_number("10,000") == 10000.0

    def test_try_parse_graceful_none(self):
        assert try_parse_indian_number("") is None
        assert try_parse_indian_number("   ") is None
        assert try_parse_indian_number("$500") is None
        assert try_parse_indian_number("10-20k") is None
        assert try_parse_indian_number("1,2345,67") is None
        assert try_parse_indian_number("50 lakh crore") is None
        assert try_parse_indian_number("invalid") is None

