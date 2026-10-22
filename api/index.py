"""Vercel serverless entry point for the EdgeMind API.

In the combined Next.js + FastAPI deployment, next.config.mjs rewrites
``/api/*`` to this function. Vercel's Python runtime invokes the exported
ASGI ``app`` with the original request path (``/api/state`` etc.), so the
wrapper below strips the ``/api`` prefix before dispatching to the real
FastAPI application — the routes in ``app.main`` keep their unprefixed
form and the research/test paths stay unchanged.

Serverless caveat (demo only): the simulated environment state lives in
module memory, so it persists across warm invocations but resets on cold
start, and concurrent function instances do not share state. For a
scheduling demo this is acceptable; the research evaluation never uses
this deployment path.
"""

from app.main import app as _fastapi_app


async def app(scope, receive, send):
    if scope["type"] in {"http", "websocket"}:
        path = scope.get("path", "")
        if path.startswith("/api"):
            scope = dict(scope)
            scope["path"] = path[len("/api"):] or "/"
            scope["root_path"] = "/api"
    await _fastapi_app(scope, receive, send)
