import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Normalizes all DRF error responses to:
        { "error": { "code": <http_status>, "message": <str> } }
    so the frontend's api client can handle errors uniformly regardless of
    which view raised them.
    """
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception — log the full traceback so it appears in
        # the Django dev server terminal, then return a clean 500.
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            {"error": {"code": 500, "message": "Internal server error."}},
            status=500,
        )

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
    elif isinstance(detail, list) and detail:
        message = str(detail[0])
    elif isinstance(detail, dict):
        # Field validation errors — flatten into one readable string.
        parts = []
        for field, errors in detail.items():
            if isinstance(errors, list):
                parts.append(f"{field}: {errors[0]}")
            else:
                parts.append(f"{field}: {errors}")
        message = "; ".join(parts) if parts else "Invalid request."
    else:
        message = str(detail)

    response.data = {"error": {"code": response.status_code, "message": message}}
    return response
