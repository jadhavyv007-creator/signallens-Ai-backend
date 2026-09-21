"""
Vercel Serverless Entrypoint for SignalLens AI.
"""

import os
import sys
import json
import traceback

# Ensure repository root and api directory are on sys.path in serverless runtime
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["VERCEL"] = "1"

try:
    from api.main import app as fastapi_instance
    
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        try:
            await fastapi_instance(scope, receive, send)
        except Exception as exc:
            tb = traceback.format_exc()
            print("❌ SERVERLESS RUNTIME ERROR:\n", tb, flush=True)
            err_dict = {
                "success": False,
                "error": {
                    "code": "SERVERLESS_RUNTIME_ERROR",
                    "message": str(exc),
                    "traceback": tb.splitlines(),
                }
            }
            body = json.dumps(err_dict).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })

except Exception as e:
    tb = traceback.format_exc()
    print("🔥 CRITICAL IMPORT ERROR IN VERCEL:\n", tb, flush=True)
    
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif msg["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        err_dict = {
            "success": False,
            "error": {
                "code": "STARTUP_IMPORT_FAILED",
                "message": str(e),
                "traceback": tb.splitlines(),
            }
        }
        body = json.dumps(err_dict).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("utf-8")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })

__all__ = ["app"]




