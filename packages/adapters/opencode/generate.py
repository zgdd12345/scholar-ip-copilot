"""Render the seven EviDraft workflows for OpenCode."""

from __future__ import annotations

from typing import Sequence

from evidraft.render import Host
from packages.adapters._shared.v2 import adapter_main


def main(argv: Sequence[str] | None = None) -> int:
    return adapter_main(Host.OPENCODE, argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
