"""Thin compatibility entry point for the three v2 host adapters."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Sequence

from evidraft.render import Host, render_plugin


def adapter_main(host: Host, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"evidraft-{host.value}")
    parser.add_argument("--plugin", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run:
        with tempfile.TemporaryDirectory(prefix=f"evidraft-{host.value}-dry-run-") as temp:
            temp_root = Path(temp).resolve()
            written = render_plugin(args.plugin, temp_root, host)
            for path in written:
                print(path.relative_to(temp_root))
        return 0

    written = render_plugin(args.plugin, args.out, host)
    print(f"[{host.value}] wrote {len(written)} file(s) to {args.out.resolve()}")
    return 0
