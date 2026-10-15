"""Punto de entrada / Launcher raíz para Azure App Service y ejecución local."""

from app.main import app  # noqa: F401

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
