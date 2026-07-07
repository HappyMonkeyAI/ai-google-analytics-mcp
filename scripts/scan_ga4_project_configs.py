#!/usr/bin/env python3
"""Scan ~/projects for .ga4.config.json and print a markdown inventory table."""

from __future__ import annotations

import sys
from pathlib import Path

from ga4_provision_mcp.inventory import inventory_markdown_table, scan_local_ga4_configs


def main(argv: list[str]) -> int:
    roots = [Path(p) for p in argv[1:]] if len(argv) > 1 else None
    result = scan_local_ga4_configs(roots)
    print(inventory_markdown_table(result.get("configs") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))