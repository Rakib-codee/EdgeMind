"""Vercel serverless entry point for the EdgeMind API.

Vercel's Python runtime detects the ASGI `app` object exported here and
serves it as a serverless function. All routes are rewritten to this
function by vercel.json.

Serverless caveat (demo only): the simulated environment state lives in
module memory, so it persists across warm invocations but resets on cold
start, and concurrent function instances do not share state. For a
scheduling demo this is acceptable; the research evaluation never uses
this deployment path.
"""

from app.main import app

__all__ = ["app"]
