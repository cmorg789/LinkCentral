"""SOAP middleware for Netsmart myAvatar ScriptLink."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware

from app import __version__
from app.config import settings
from app.db import init_db
from app.soap.service import wsgi_application as soap_wsgi

logging.basicConfig(level=logging.INFO)


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

# Mount SOAP service
app.mount(settings.soap_path, WSGIMiddleware(soap_wsgi))


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
