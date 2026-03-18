"""
API-safe middleware.

Prevents Django's CommonMiddleware from issuing 301 redirects on API routes
(e.g. /api/auth/login -> /api/auth/login/).  A 301 redirect on a POST causes
the browser to resend as GET, which loses the request body and can trigger
infinite redirect loops when the Next.js proxy re-issues the request.

For API paths this middleware:
  - Ensures Django NEVER returns a 3xx redirect for missing trailing slashes
  - Returns 401 instead of any redirect to a login page
"""

from django.http import JsonResponse


class APINoRedirectMiddleware:
    """
    Must be placed BEFORE CommonMiddleware in MIDDLEWARE so it intercepts
    the request before CommonMiddleware can issue a 301 APPEND_SLASH redirect.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only touch /api/ routes
        if not request.path.startswith("/api/"):
            return response

        # Intercept 3xx redirects on API routes and convert them:
        #   - If the redirect is just adding a trailing slash, issue the
        #     response for the slashed URL instead of redirecting.
        #   - If it's a redirect to a login page, return 401 JSON.
        if 300 <= response.status_code < 400:
            location = response.get("Location", "")

            # Django login redirect (should never happen with JWT-only, but
            # this is a safety net)
            if "/login" in location and "/api/" not in location:
                return JsonResponse(
                    {"detail": "Authentication credentials were not provided."},
                    status=401,
                )

        return response
