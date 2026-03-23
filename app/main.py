"""SOAP middleware for Netsmart myAvatar ScriptLink."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from a2wsgi import WSGIMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app import __version__
from app.config import settings
from app.db import init_db
from app.soap.service import wsgi_application as soap_wsgi

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

# Header name for proxy prefix
_PREFIX_HEADER = b"x-forwarded-prefix"


class ProxyPrefixMiddleware:
    """ASGI middleware that sets root_path from X-Forwarded-Prefix header.

    When behind a reverse proxy that strips a path prefix (e.g. Caddy handle_path),
    this ensures FastAPI redirects include the correct external path.

    The WSDL soap:address is handled separately by _wsgi_proxy_prefix since
    a2wsgi already translates root_path into SCRIPT_NAME for the mounted WSGI app.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            prefix = headers.get(_PREFIX_HEADER)
            if prefix:
                scope["root_path"] = prefix.decode() + scope.get("root_path", "")
                logger.debug("X-Forwarded-Prefix: %s -> root_path: %s",
                             prefix.decode(), scope["root_path"])
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print(f"LinkCentral v{__version__}")
    init_db()
    print(f"SOAP endpoint: {settings.soap_path}")
    print(f"WSDL: {settings.soap_path}?wsdl")
    yield


_app = FastAPI(
    title="LinkCentral",
    description="SOAP middleware for Netsmart myAvatar ScriptLink",
    version=__version__,
    lifespan=lifespan,
)

# Mount SOAP service
_app.mount(settings.soap_path, WSGIMiddleware(soap_wsgi))

# Wrap the entire ASGI app so root_path is set before FastAPI routing
app = ProxyPrefixMiddleware(_app)


@_app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "name": "LinkCentral",
        "version": __version__,
        "soap_endpoint": settings.soap_path,
        "wsdl": f"{settings.soap_path}?wsdl",
    }


@_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


def main():
    """Run the application with uvicorn."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
