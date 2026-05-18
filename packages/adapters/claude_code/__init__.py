"""EviDraft -> Claude Code plugin adapter (MVP, first-class)."""

__all__ = ["load_plugin", "render", "validate", "main"]


def __getattr__(name: str):  # pragma: no cover - thin re-export shim
    if name in __all__:
        from . import generate as _g

        return getattr(_g, name)
    raise AttributeError(name)
