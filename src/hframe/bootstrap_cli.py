"""Operator entrypoint: ``hframe-bootstrap <git_url>`` (single argument)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hframe.membrane_bootstrap import bootstrap_membrane


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hframe-bootstrap",
        description=(
            "Bootstrap H-Frame membrane: <slug>_repo/, <slug>_workspace_repo/, and ./hframe."
        ),
    )
    parser.add_argument(
        "git_url",
        help="Git remote URL to clone; directory names are derived from the repository basename.",
    )
    args = parser.parse_args(argv)
    try:
        bootstrap_membrane(args.git_url, Path.cwd())
    except Exception as e:
        sys.stderr.write(f"hframe-bootstrap: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
