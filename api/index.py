"""
Vercel entry point for FastAPI application
"""
import os
from pathlib import Path

# Configure for Vercel environment
if os.environ.get('VERCEL'):
    # Use /tmp for file storage on Vercel
    os.environ['UPLOAD_DIR'] = '/tmp/uploads'
    os.environ['RESULTS_DIR'] = '/tmp/results'
    
    # Ensure /tmp directories exist
    Path('/tmp/uploads').mkdir(parents=True, exist_ok=True)
    Path('/tmp/results').mkdir(parents=True, exist_ok=True)

from backend.main import app

# Export app for Vercel
__all__ = ['app']
