class SecurityHeadersMiddleware:


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
