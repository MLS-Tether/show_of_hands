from fastapi import WebSocket


def ws_token_from_subprotocol(websocket: WebSocket) -> str:
    """Extracts the auth token from the Sec-WebSocket-Protocol handshake
    header. The frontend passes it as the WebSocket constructor's
    `protocols` arg instead of a `?token=` query param, since query strings
    end up in proxy/CDN access logs and browser history."""
    raw = websocket.headers.get("sec-websocket-protocol", "")
    token = raw.split(",")[0].strip()
    if not token:
        raise ValueError("Missing auth token in WebSocket subprotocol.")
    return token
