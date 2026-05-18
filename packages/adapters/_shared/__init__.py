"""Shared helpers for EviDraft adapters."""

__all__ = [
    "FrontmatterDoc",
    "Plugin",
    "load_plugin",
    "split_frontmatter",
    "validate_plugin",
]


def __getattr__(name: str):  # pragma: no cover
    if name in __all__:
        from . import loader as _l

        if name == "validate_plugin":
            return _l.validate
        return getattr(_l, name)
    raise AttributeError(name)
