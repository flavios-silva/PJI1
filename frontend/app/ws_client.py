import asyncio
import json
import websockets
from app.state import AppState


async def run_ws_listener(state: AppState, on_notification=None):
    """Connect to the backend WebSocket and listen for real-time notifications.
    Reconnects automatically on disconnect. Stops when state.token is None."""
    while state.is_authenticated:
        url = f"{state.ws_base}/ws/notifications?token={state.token}"
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                while state.is_authenticated:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(raw)
                        notif_type = data.get("type", "")
                        if notif_type in ("checklist_submitted", "checklist_reviewed"):
                            state.unread_count += 1
                        state.dispatch_notification(data)
                        if on_notification:
                            on_notification(data)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
        except Exception:
            pass
        if state.is_authenticated:
            await asyncio.sleep(5)
