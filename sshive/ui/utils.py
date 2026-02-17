"""UI utility functions."""

import os


def is_wayland() -> bool:
    """Check if the current session is running under Wayland."""
    return (
        os.environ.get("WAYLAND_DISPLAY") is not None
        or os.environ.get("QT_QPA_PLATFORM") == "wayland"
    )
