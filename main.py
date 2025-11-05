"""Top-level ASGI application entrypoint for uvicorn and console scripts."""

import os
import sys
from pathlib import Path

import uvicorn

_ROOT = Path(__file__).resolve().parent
_SRC_PATH = _ROOT / "src"
if _SRC_PATH.exists():
    src_str = str(_SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from src.main import app as app  # re-export for `uvicorn main:app`

__all__ = ["app", "main"]


def _as_bool(value: str, default: bool = False) -> bool:
    """Interpret truthy environment flag values."""
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _resolve_host(default: str = "0.0.0.0") -> str:
    """Resolve bind host from common environment variable names."""
    return (
        os.getenv("UVICORN_HOST")
        or os.getenv("HOST")
        or os.getenv("APP_HOST")
        or os.getenv("BIND_HOST")
        or default
    )


def _resolve_port(default: int = 8000) -> int:
    """Resolve listen port from common environment variable names."""
    for key in ("UVICORN_PORT", "PORT", "APP_PORT", "BIND_PORT"):
        value = os.getenv(key)
        if value:
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(f"Invalid integer for {key}={value!r}") from exc
    return default


def main() -> None:
    """Run the FastAPI application using uvicorn."""
    host = _resolve_host()
    port = _resolve_port()
    reload_enabled = _as_bool(os.getenv("UVICORN_RELOAD"), default=False)
    uvicorn.run(app, host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
