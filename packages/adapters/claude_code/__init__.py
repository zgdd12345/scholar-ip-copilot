"""EviDraft to Claude Code adapter."""


def main(argv=None):
    from .generate import main as _main

    return _main(argv)

__all__ = ["main"]
