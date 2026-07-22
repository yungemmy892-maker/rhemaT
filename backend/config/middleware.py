class SecurityHeadersMiddleware:
    """
    Adds Content-Security-Policy and X-XSS-Protection to every response.

    The CSP here is shaped specifically around analytics/templates/
    admin_dashboard.html — the one HTML page this Django app actually
    serves (everything else is a JSON API, where CSP is inert but
    harmless to include anyway). That page embeds its CSS and JS inline
    with no nonce/hash setup, and loads Chart.js from cdnjs plus a
    Google Font — so 'unsafe-inline' is a real, deliberate loosening of
    what CSP is normally for (blocking injected inline scripts), not an
    oversight. The stronger version of this would thread a per-request
    nonce into that template's <script>/<style> tags and drop
    'unsafe-inline' entirely; worth doing if that page ever needs to
    defend against a real XSS vector, not just as a checkbox.
    """

    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", self.CSP)
        # Deprecated and ignored by every current browser (Chrome removed
        # the XSS Auditor it controlled back in 2019) — sent anyway for
        # defense-in-depth on any older browser still checking it, and
        # because it was asked for explicitly. CSP above is what actually
        # matters for modern browsers.
        response.setdefault("X-XSS-Protection", "1; mode=block")
        return response
