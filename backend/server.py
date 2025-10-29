"""
AIDA Backend Server Entry Point
This module imports and exposes the FastAPI app from aida.server
for uvicorn to run via supervisor.
"""
from aida.server import app

# Expose the app for uvicorn
__all__ = ["app"]
