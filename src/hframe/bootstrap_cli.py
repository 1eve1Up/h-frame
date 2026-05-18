"""Operator entrypoint: ``hframe-bootstrap [--vault] <git_url>``."""

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
    parser.add_argument(
        "--vault",
        action="store_true",
        help=(
            "Encrypt policy.allowlist and policy.denylist on disk; embed a one-time key "
            "only in hframe-membrane.pyz (requires: pip install 'hframe[vault]')."
        ),
    )
    args = parser.parse_args(argv)
    if args.vault:
        try:
            import cryptography  # noqa: F401
        except ImportError:
            sys.stderr.write(
                "hframe-bootstrap: --vault requires cryptography; "
                "install with: pip install 'hframe[vault]'\n"
            )
            return 1
    try:
        bootstrap_membrane(args.git_url, Path.cwd(), use_vault=args.vault)
    except Exception as e:
        sys.stderr.write(f"hframe-bootstrap: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
