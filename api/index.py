"""
Vercel entry point for FastAPI application
"""
from backend.main import app

# Export app for Vercel
__all__ = ['app']
