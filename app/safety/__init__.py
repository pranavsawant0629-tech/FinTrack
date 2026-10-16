"""
Safety package for Finova AI Phase 7.
Exports SecondarySafetyValidator and SafetyValidationResult.
"""

from app.safety.validator import (
    GLOBAL_REFUSAL_MESSAGE,
    INJECTION_REFUSAL_MESSAGE,
    SafetyValidationResult,
    SecondarySafetyValidator,
    secondary_safety_validator,
)

__all__ = [
    "GLOBAL_REFUSAL_MESSAGE",
    "INJECTION_REFUSAL_MESSAGE",
    "SafetyValidationResult",
    "SecondarySafetyValidator",
    "secondary_safety_validator",
]
