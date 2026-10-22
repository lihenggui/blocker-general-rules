#!/usr/bin/env python3
"""Validate rule/component sources, paths, types and exact generated file freshness."""

import argparse
from pathlib import Path

from build import build
from rulelib import ROOT, RuleError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="accepted for clarity; validation always checks freshness")
    args = parser.parse_args()
    try:
        build(args.root, check=True)
    except (RuleError, OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
