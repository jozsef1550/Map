"""
Fantasy Map Engine — FastAPI application entry point
"""
import json
import os

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router


class _NumpyEncoder(json.JSONEncoder):
    """Convert numpy scalar/array types to native Python types for JSON."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class _NumpyJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, cls=_NumpyEncoder).encode("utf-8")


app = FastAPI(
    title="Fantasy Map Engine",
    description="Full-Stack Fantasy Map Generator & Editor",
    version="1.0.0",
    default_response_class=_NumpyJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Serve frontend build if it exists
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
