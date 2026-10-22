"""Vercel serverless entry point for the EdgeMind API.

In the combined Next.js + FastAPI deployment, next.config.mjs rewrites
``/api/*`` to this function. Vercel's Python runtime invokes the exported
ASGI ``app`` with the original request path (``/api/state`` etc.), so a
middleware strips the ``/api`` prefix before routing — the routes in
``app.main`` keep their unprefixed form and the research/test paths stay
unchanged.

Serverless caveat (demo only): the simulated environment state lives in
module memory, so it persists across warm invocations but resets on cold
start, and concurrent function instances do not share state. For a
scheduling demo this is acceptable; the research evaluation never uses
this deployment path.
"""

from app.main import app


class _StripApiPrefix:
    """ASGI middleware: remove the /api prefix Vercel's rewrite preserves."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            path = scope.get("path", "")
            if path.startswith("/api"):
                scope = dict(scope)
                scope["path"] = path[len("/api"):] or "/"
                scope["root_path"] = "/api"
        await self.asgi_app(scope, receive, send)


app.add_middleware(_StripApiPrefix)
