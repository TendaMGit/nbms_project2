from django.conf import settings


class SessionSecurityMiddleware:
    """Rotate authenticated sessions once to mitigate session fixation."""

    SESSION_REKEY_FLAG = "_nbms_session_rekeyed"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            if not request.session.get(self.SESSION_REKEY_FLAG):
                request.session.cycle_key()
                request.session[self.SESSION_REKEY_FLAG] = True
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Attach security headers configured at settings level."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        csp = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if csp:
            header_name = (
                "Content-Security-Policy-Report-Only"
                if getattr(settings, "CONTENT_SECURITY_POLICY_REPORT_ONLY", False)
                else "Content-Security-Policy"
            )
            if header_name not in response:
                response[header_name] = csp

        if "X-Content-Type-Options" not in response and getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False):
            response["X-Content-Type-Options"] = "nosniff"

        referrer_policy = getattr(settings, "SECURE_REFERRER_POLICY", "")
        if referrer_policy and "Referrer-Policy" not in response:
            response["Referrer-Policy"] = referrer_policy

        x_frame_options = getattr(settings, "X_FRAME_OPTIONS", "")
        if x_frame_options and "X-Frame-Options" not in response:
            response["X-Frame-Options"] = x_frame_options

        permissions_policy = getattr(settings, "PERMISSIONS_POLICY", "")
        if permissions_policy and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = permissions_policy

        cross_origin_opener_policy = getattr(settings, "SECURE_CROSS_ORIGIN_OPENER_POLICY", "")
        if cross_origin_opener_policy and "Cross-Origin-Opener-Policy" not in response:
            response["Cross-Origin-Opener-Policy"] = cross_origin_opener_policy
        return response
