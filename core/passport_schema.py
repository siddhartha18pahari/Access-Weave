"""
Typed Access Passport schema.

The passport describes *how software should behave for this person* — functional
preferences only. There is deliberately no diagnosis field. Validation is done
with pydantic so that untrusted input (imported passports, API bodies) can never
put a malformed or unsafe preference set into the interface.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class InputMode(str, Enum):
    KEYBOARD = "keyboard"
    TOUCH = "touch"
    VOICE = "voice"
    SWITCH = "switch"
    DWELL = "dwell"


class Contrast(str, Enum):
    SYSTEM = "system"
    HIGH = "high"
    DARK = "dark"
    LIGHT = "light"


class ConfirmationLevel(str, Enum):
    STANDARD = "standard"
    STRONG = "strong"
    BLOCK = "block"


class OutputPreferences(BaseModel):
    text_scale: float = Field(default=1.0, ge=0.8, le=3.0)
    contrast: Contrast = Contrast.SYSTEM
    speech_enabled: bool = False
    speech_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    captions: bool = True
    reduced_motion: bool = False
    symbols_with_text: bool = False
    reading_ruler: bool = False


class CognitivePreferences(BaseModel):
    plain_language: bool = False
    one_step_at_a_time: bool = False
    show_progress: bool = True
    recovery_instructions: bool = True
    reduced_choice_mode: bool = False


class PrivacyPreferences(BaseModel):
    store_images: bool = False
    store_transcripts: bool = False
    location_policy: str = "off"
    supporter_access: bool = False


class SafetyPreferences(BaseModel):
    """
    Confirmation strength the user wants before AccessWeave does something.

    Platform policy sets a *floor*: these can be made stricter but never weaker
    than the platform minimum (enforced in `safety.py`).
    """

    external_action: ConfirmationLevel = ConfirmationLevel.STRONG
    financial_action: ConfirmationLevel = ConfirmationLevel.STRONG
    medical_action: ConfirmationLevel = ConfirmationLevel.BLOCK
    legal_action: ConfirmationLevel = ConfirmationLevel.STRONG


class AccessPassportPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    input_modes: list[InputMode] = Field(default_factory=lambda: [InputMode.KEYBOARD])
    minimum_target_px: int = Field(default=44, ge=44, le=96)
    output: OutputPreferences = Field(default_factory=OutputPreferences)
    cognitive: CognitivePreferences = Field(default_factory=CognitivePreferences)
    privacy: PrivacyPreferences = Field(default_factory=PrivacyPreferences)
    safety: SafetyPreferences = Field(default_factory=SafetyPreferences)

    @field_validator("input_modes")
    @classmethod
    def require_input_mode(cls, value):
        if not value:
            raise ValueError("At least one input mode is required.")
        # de-duplicate while preserving order
        seen, out = set(), []
        for mode in value:
            if mode not in seen:
                seen.add(mode)
                out.append(mode)
        return out


def validate_payload(data: dict) -> dict:
    """Validate raw dict -> normalized dict. Raises pydantic ValidationError."""
    model = AccessPassportPayload.model_validate(data or {})
    return model.model_dump(mode="json")


def default_payload(name: str = "My profile") -> dict:
    return AccessPassportPayload(name=name).model_dump(mode="json")
