import threading
import time

import uvicorn
import webview

from backend.main import app, api


def start_server():
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )


if __name__ == "__main__":
    server_thread = threading.Thread(
        target=start_server,
        daemon=True,
    )

    server_thread.start()

    time.sleep(1)

    # frameless + easy_drag=False hands window dragging to only the elements
    # marked with the `pywebview-drag-region` class (the custom title bar in
    # frontend/index.html). easy_drag=True (the pywebview default) makes the
    # ENTIRE window surface draggable from any point, which is why the whole
    # app used to move around when clicking anywhere and also blocked the
    # edge-hit-testing pywebview needs to let a frameless window be resized.
    webview.create_window(
        "Game Library",
        "http://127.0.0.1:8000",
        width=1400,
        height=850,
        min_size=(1000, 650),
        resizable=True,
        frameless=True,
        easy_drag=False,
        background_color="#0a0a0a",
        js_api=api,
    )

    webview.start()
