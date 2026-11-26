"""
Shared booking rules for hotels and vacation rentals:
- refund amount according to the property's cancellation policy
- which statuses can be cancelled / checked in
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

# (min hours before check-in, refund fraction) — first matching rule wins.
# Policy keys are the values already stored on Hotel / VacationRental.cancellation_policy.
REFUND_RULES = {
    # Hotels
    "free_cancellation": [(24, Decimal("1.00"))],
    "moderate": [(72, Decimal("1.00"))],          # hotel moderate: full refund up to 3 days
    "non_refundable": [],
    # Vacation rentals
    "flexible": [(24, Decimal("1.00"))],
    "rental_moderate": [(120, Decimal("1.00"))],  # rental moderate: full refund up to 5 days
    "strict": [(168, Decimal("0.50"))],
}


def hours_until_check_in(check_in_date):
    """Hours from now until the start of the check-in day (local time)."""
    tz = timezone.get_current_timezone()
    check_in_start = timezone.make_aware(
        timezone.datetime.combine(check_in_date, timezone.datetime.min.time()), tz
    )
    return (check_in_start - timezone.now()).total_seconds() / 3600


def calculate_refund(policy_key, paid_amount, check_in_date, cancelled_by_property=False):
    """
    Returns the refund amount for a cancellation.
    - Property (hotel/host/staff) cancels: guest always gets everything they paid back.
    - Guest cancels: refund follows the property's cancellation policy.
    - Nothing paid yet: nothing to refund.
    """
    paid_amount = Decimal(str(paid_amount or 0))
    if paid_amount <= 0:
        return Decimal("0.00")
    if cancelled_by_property:
        return paid_amount.quantize(Decimal("0.01"))

    hours_left = hours_until_check_in(check_in_date)
    for min_hours, fraction in REFUND_RULES.get(policy_key, []):
        if hours_left >= min_hours:
            return (paid_amount * fraction).quantize(Decimal("0.01"))
    return Decimal("0.00")


def check_in_window_error(check_in_date, check_out_date):
    """None if today is within the stay (check-in day up to the day before check-out), else a message."""
    today = timezone.localdate()
    if today < check_in_date:
        return f"Check-in opens on {check_in_date:%d %b %Y}."
    if today >= check_out_date:
        return "This stay has already ended; it can no longer be checked in."
    return None
