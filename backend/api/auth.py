from fastapi import Depends, Header, HTTPException, status, WebSocket

from backend.utils.config import Settings, get_settings


async def validate_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate API Key passed in the custom X-API-Key header.

    If settings.api_key is None, verification is bypassed.
    """
    if settings.api_key is not None:
        if not x_api_key or x_api_key.strip() != settings.api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key header",
            )


async def validate_ws_api_key(websocket: WebSocket, api_key: str | None = None) -> None:
    """Validate API Key passed as a query parameter for WebSockets.

    If settings.api_key is None, verification is bypassed.
    """
    settings = get_settings()
    if settings.api_key is not None:
        # Check if the API key matches
        if not api_key or api_key.strip() != settings.api_key.strip():
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing api_key query parameter",
            )

