"""
JSON Sanitizer Middleware.
Normalizes UTF-8 smart/curly quotes (“ ” ‘ ’) into standard ASCII quotes (" ')
to prevent JSON decode errors from macOS Safari text substitutions and rich text copy-pastes.
"""

from starlette.types import ASGIApp, Scope, Receive, Send


class JsonSanitizerMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            content_type = headers.get(b"content-type", b"").decode("latin1").lower()
            
            if "application/json" in content_type:
                body_chunks = []
                more_body = True
                while more_body:
                    message = await receive()
                    if message["type"] == "http.request":
                        body_chunks.append(message.get("body", b""))
                        more_body = message.get("more_body", False)
                
                raw_bytes = b"".join(body_chunks)
                
                # Replace UTF-8 smart quotes:
                # \xe2\x80\x9c = “ , \xe2\x80\x9d = ” , \xe2\x80\x98 = ‘ , \xe2\x80\x99 = ’
                cleaned_bytes = (
                    raw_bytes.replace(b"\xe2\x80\x9c", b'"')
                    .replace(b"\xe2\x80\x9d", b'"')
                    .replace(b"\xe2\x80\x98", b"'")
                    .replace(b"\xe2\x80\x99", b"'")
                )
                
                sent = False

                async def custom_receive():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {
                            "type": "http.request",
                            "body": cleaned_bytes,
                            "more_body": False,
                        }
                    return {
                        "type": "http.request",
                        "body": b"",
                        "more_body": False,
                    }

                await self.app(scope, custom_receive, send)
                return

        await self.app(scope, receive, send)
