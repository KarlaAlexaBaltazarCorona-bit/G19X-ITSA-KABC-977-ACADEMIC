"""Punto de entrada / Launcher raíz para Azure App Service y ejecución local."""

from app.main import app  # noqa: F401

__all__ = ["app"]

if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")  # nosec B104
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
