"""PyWebView floating native pop-up window launcher for Windows/macOS/Linux."""

import threading
import time
from typing import Optional
import uvicorn
import webview

from src.config import settings
from src.server.app import app


def start_server_in_background() -> None:
    """Runs the FastAPI server in a background daemon thread."""
    config = uvicorn.Config(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.0)  # Give server a moment to bind


def launch_popup(url: Optional[str] = None) -> None:
    """Launches the floating native pop-up window."""
    if url is None:
        start_server_in_background()
        url = f"http://{settings.server_host}:{settings.server_port}"

    window = webview.create_window(
        title="Codebase Assistant",
        url=url,
        width=settings.popup_width,
        height=settings.popup_height,
        frameless=False,  # Allows standard window borders or frameless toggle
        on_top=settings.popup_always_on_top,
        resizable=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    launch_popup()
