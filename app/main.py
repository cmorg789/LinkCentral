"""SOAP middleware for Netsmart myAvatar ScriptLink."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from a2wsgi import WSGIMiddleware

from app import __version__
from app.config import settings
from app.db import init_db
from app.soap.service import wsgi_application as soap_wsgi

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)


def _proxy_prefix_middleware(app):
    """WSGI middleware that sets SCRIPT_NAME from X-Forwarded-Prefix header.

    When behind a reverse proxy that strips a path prefix (e.g. Caddy handle_path),
    this ensures the WSDL soap:address includes the correct external path.
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


app = FastAPI(
    title="LinkCentral",
    description="SOAP middleware for Netsmart myAvatar ScriptLink",
    version=__version__,
    lifespan=lifespan,
)

# Mount SOAP service with proxy prefix support
app.mount(settings.soap_path, WSGIMiddleware(_proxy_prefix_middleware(soap_wsgi)))


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "name": "LinkCentral",
        "version": __version__,
        "soap_endpoint": settings.soap_path,
        "wsdl": f"{settings.soap_path}?wsdl",
    }


@app.get("/health")
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
