"""WebSocket push: /ws/{session_id} streams tick / comment / state / click
messages published by the REST handlers through the store's broadcaster."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str) -> None:
    store = websocket.app.state.store
    await websocket.accept()
    queue = store.subscribe(session_id)
    try:
        await websocket.send_json({"type": "hello", "data": {"session_id": session_id}})
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        store.unsubscribe(session_id, queue)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
