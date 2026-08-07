# backend/api_vercel/index.py
# Vercel serverless entry point — wraps FastAPI app with Mangum
# Mangum translates AWS Lambda / Vercel Function events into ASGI.

import sys
import os

# Add the backend directory to the path so all imports resolve correctly
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)

# Import the FastAPI app
from api import app  # noqa: E402

# Wrap with Mangum for serverless execution
# lifespan="off" prevents Mangum from running the startup lifespan
# (the auto-pipeline thread) — startup is handled manually below.
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="auto")
except ImportError:
    handler = None

# Vercel calls `handler` directly — this file must be importable.
