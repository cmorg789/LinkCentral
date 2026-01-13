"""Main application entry point.

Combines FastAPI REST API with Spyne SOAP service.
"""
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.wsgi import WSGIMiddleware

from app import __version__
from app.config import settings
from app.database.connection import init_db
from app.soap.service import wsgi_application as soap_wsgi
from app.api.routes import router as api_router
from app.api.auth_routes import router as auth_router
from app.api.setup_routes import router as setup_router
from app.api.user_routes import router as user_router

# Path to built frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"ScriptLink Workflow Engine v{__version__}")
    print(f"Initializing database...")
    init_db()
    print(f"Database initialized.")
    print(f"SOAP endpoint: {settings.soap_path}")
    print(f"REST API: /api")
    yield
    # Shutdown
    print("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title="ScriptLink Workflow Engine",
    description="Visual workflow builder for Netsmart myAvatar ScriptLink",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(setup_router, prefix="/api", tags=["setup"])
app.include_router(user_router, prefix="/api", tags=["users"])

# Mount SOAP service at the configured path
# Spyne's WSGI app handles both the service and WSDL
app.mount(settings.soap_path, WSGIMiddleware(soap_wsgi))


# Serve frontend static files if built
if FRONTEND_DIR.exists():
    # Mount static assets (JS, CSS, images)
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_root():
        """Serve the frontend app."""
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.exception_handler(StarletteHTTPException)
    async def spa_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle 404s by serving SPA for frontend routes."""
        if exc.status_code == 404:
            path = request.url.path.lstrip("/")
            # Try to serve static file first
            file_path = FRONTEND_DIR / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            # Otherwise return index.html for SPA routing
            return FileResponse(FRONTEND_DIR / "index.html")
        # Return proper JSON response for other HTTP exceptions
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
else:
    @app.get("/")
    async def root():
        """Root endpoint with service info (no frontend built)."""
        return {
            "name": "ScriptLink Workflow Engine",
            "version": __version__,
            "soap_endpoint": settings.soap_path,
            "wsdl": f"{settings.soap_path}?wsdl",
            "api": "/api",
            "docs": "/docs",
            "frontend": "Not built. Run 'npm run build' in frontend/ directory.",
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
        reload=True,
    )


if __name__ == "__main__":
    main()
