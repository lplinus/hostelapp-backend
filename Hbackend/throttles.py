from rest_framework.throttling import SimpleRateThrottle


class BookingOTPThrottle(SimpleRateThrottle):
    """
    Limits how often booking OTPs (SMS / email) can be sent, per client IP,
    for both logged-in and anonymous users. Rate is set by "booking_otp" in
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """

    scope = "booking_otp"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
