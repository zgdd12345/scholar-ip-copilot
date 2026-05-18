"""EviDraft -> OpenCode adapter (planned, stub).

The renderer is intentionally a no-op for v0.1. The CLI still loads and
validates the plugin so users get lint feedback today.
"""

__all__ = ["load_plugin", "render", "validate", "main"]


def __getattr__(name: str):  # pragma: no cover
    if name in __all__:
        from . import generate as _g

        return getattr(_g, name)
    raise AttributeError(name)
