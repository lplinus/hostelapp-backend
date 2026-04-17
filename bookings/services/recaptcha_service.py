"""
Google reCAPTCHA v3 verification service.
Provides reusable server-side token validation with score, action, and hostname checks.
"""

import logging
from typing import Optional

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

GOOGLE_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

VALID_HOSTNAMES = frozenset({
    "localhost",
    "127.0.0.1",
    "hostelin.online",
    "www.hostelin.online",
})

DEFAULT_SCORE_THRESHOLD = 0.5
DEFAULT_TIMEOUT = 5


class RecaptchaService:
    """
    Validates Google reCAPTCHA v3 tokens against the Google verification API.

    Usage:
        RecaptchaService.verify(token, action="booking")
    """

    @staticmethod
    def _get_secret_key() -> Optional[str]:
        return getattr(settings, "RECAPTCHA_SECRET_KEY", None)

    @staticmethod
    def _get_score_threshold() -> float:
        return getattr(settings, "RECAPTCHA_SCORE_THRESHOLD", DEFAULT_SCORE_THRESHOLD)

    @staticmethod
    def _get_valid_hostnames() -> frozenset:
        custom = getattr(settings, "RECAPTCHA_VALID_HOSTNAMES", None)
        if custom:
            return frozenset(custom)
        return VALID_HOSTNAMES

    @classmethod
    def verify(cls, token: Optional[str], action: str = "submit") -> bool:
        secret_key = cls._get_secret_key()

        if not secret_key:
            logger.debug("reCAPTCHA secret key not configured — skipping verification.")
            return True

        if not token:
            if settings.DEBUG:
                logger.debug("reCAPTCHA token missing in DEBUG mode — skipping verification.")
                return True
            raise ValidationError({
                "recaptcha_token": "reCAPTCHA token is missing. Please refresh the page and try again."
            })

        try:
            response = requests.post(
                GOOGLE_VERIFY_URL,
                data={"secret": secret_key, "response": token},
                timeout=DEFAULT_TIMEOUT,
            )
            result = response.json()
        except requests.exceptions.Timeout:
            raise ValidationError({
                "recaptcha_token": "CAPTCHA verification timed out. Please try again."
            })
        except requests.exceptions.RequestException:
            raise ValidationError({
                "recaptcha_token": "CAPTCHA verification failed. Please try again later."
            })

        if settings.DEBUG:
            logger.debug("reCAPTCHA response: %s", result)

        if not result.get("success"):
            error_codes = result.get("error-codes", [])
            logger.warning("reCAPTCHA verification failed. Errors: %s", error_codes)
            raise ValidationError({
                "recaptcha_token": "Invalid reCAPTCHA. Please try again."
            })

        score = result.get("score", 0)
        threshold = cls._get_score_threshold()
        if score < threshold:
            logger.warning("reCAPTCHA score too low: %.2f (threshold: %.2f)", score, threshold)
            raise ValidationError({
                "recaptcha_token": "Suspicious activity detected. Booking blocked."
            })

        response_action = result.get("action", "")
        if response_action != action:
            logger.warning(
                "reCAPTCHA action mismatch: expected '%s', got '%s'", action, response_action
            )
            raise ValidationError({
                "recaptcha_token": "reCAPTCHA action mismatch. Please try again."
            })

        hostname = result.get("hostname", "")
        valid_hostnames = cls._get_valid_hostnames()
        if hostname not in valid_hostnames:
            logger.warning("reCAPTCHA hostname mismatch: '%s' not in %s", hostname, valid_hostnames)
            raise ValidationError({
                "recaptcha_token": "reCAPTCHA hostname verification failed."
            })

        return True
