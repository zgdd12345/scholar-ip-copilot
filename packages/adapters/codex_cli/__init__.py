"""EviDraft to Codex CLI adapter."""


def main(argv=None):
    from .generate import main as _main

    return _main(argv)

__all__ = ["main"]
