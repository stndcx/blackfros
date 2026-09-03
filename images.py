"""
BLACKFROS - images
v3.0.0-pre.2
"""

import os
import re
import subprocess
import tempfile

CHAFA_TIMEOUT = 10
DEFAULT_WIDTH = 40
_CURSOR_CTRL_RE = re.compile(r"\x1b\[\?25[lh]")


def render_image_ansi(raw_bytes: bytes, width: int = DEFAULT_WIDTH) -> str:

    fd, path = tempfile.mkstemp(suffix=".img")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw_bytes)
        result = subprocess.run(
            ["chafa", f"--size={width}x{width // 2}", "--animate=off", path],
            capture_output=True, text=True, timeout=CHAFA_TIMEOUT,
        )
        if result.returncode != 0:
            return f"(couldn't render image: {result.stderr.strip() or 'unknown error'})"
        return _CURSOR_CTRL_RE.sub("", result.stdout)
    except FileNotFoundError:
        return "(chafa not installed - run: sudo apt install chafa)"
    except subprocess.TimeoutExpired:
        return "(image rendering timed out)"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass