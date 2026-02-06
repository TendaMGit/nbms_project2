import uuid

from nbms_app.services.request_id import reset_current_request_id, set_current_request_id


class RequestIDMiddleware:
    """Propagate X-Request-ID through request context and responses."""

    header_name = "HTTP_X_REQUEST_ID"
    response_header_name = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming_request_id = (request.META.get(self.header_name) or "").strip()
        request_id = incoming_request_id or uuid.uuid4().hex
        request.META[self.header_name] = request_id
        request.request_id = request_id

        token = set_current_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            reset_current_request_id(token)

        response[self.response_header_name] = request_id
        return response
