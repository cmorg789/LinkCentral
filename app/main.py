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


class ProxyPrefixMiddleware:
    """ASGI middleware that sets root_path from X-Forwarded-Prefix header.

    When behind a reverse proxy that strips a path prefix (e.g. Caddy handle_path),
    this ensures FastAPI redirects include the correct external path.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            prefix = headers.get(b"x-forwarded-prefix")
            if prefix:
                scope["root_path"] = prefix.decode() + scope.get("root_path", "")
                logger.debug("X-Forwarded-Prefix: %s -> root_path: %s",
                             prefix.decode(), scope["root_path"])
        await self.app(scope, receive, send)


class StripRootPathMiddleware:
    """ASGI middleware that clears root_path before the WSGI translation layer.

    a2wsgi translates root_path into SCRIPT_NAME, but Spyne also appends
    PATH_INFO which already contains the service path — causing duplication.
    This clears root_path so a2wsgi leaves SCRIPT_NAME alone.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            scope["root_path"] = ""
        await self.app(scope, receive, send)


def _wsgi_proxy_prefix(app):
    """WSGI middleware that sets SCRIPT_NAME from X-Forwarded-Prefix header.

    Reads the proxy prefix directly from the HTTP header and prepends it to
    SCRIPT_NAME so Spyne generates the correct WSDL soap:address.
    """
    def middleware(environ, start_response):
        prefix = environ.get("HTTP_X_FORWARDED_PREFIX", "")
        if prefix:
            environ["SCRIPT_NAME"] = prefix + environ.get("SCRIPT_NAME", "")
        return app(environ, start_response)
    return middleware


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

# Mount SOAP service:
# StripRootPathMiddleware prevents a2wsgi from translating root_path into SCRIPT_NAME
# _wsgi_proxy_prefix reads X-Forwarded-Prefix directly and sets SCRIPT_NAME once
_app.mount(
    settings.soap_path,
    StripRootPathMiddleware(WSGIMiddleware(_wsgi_proxy_prefix(soap_wsgi))),
)

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
