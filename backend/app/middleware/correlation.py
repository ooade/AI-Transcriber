from starlette.middleware.base import BaseHTTPMiddleware
from asgi_correlation_id import correlation_id
import uuid

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Header name for request ID
        header_name = "X-Request-ID"

        # Check if header exists
        request_id = request.headers.get(header_name)

        # If not, generate one
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set the correlation ID context var
        correlation_id.set(request_id)

        # Process request
        response = await call_next(request)

        # Return ID in response header
        response.headers[header_name] = request_id

        return response
