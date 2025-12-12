import os

from app import create_app


def _get_bool_env(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


app = create_app()

if __name__ == "__main__":
    # Nunca dejar debug forzado en producción; se controla vía variables de entorno.
    debug_enabled = _get_bool_env("FLASK_DEBUG", False)
    app.run(debug=debug_enabled)
