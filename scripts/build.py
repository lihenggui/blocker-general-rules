#!/usr/bin/env python3
"""Generate the legacy app JSON; --check performs validation without writing."""

import argparse
import sys
from pathlib import Path

from rulelib import ROOT, RuleError, json_text, prepared, stale_outputs, write_text


def build(root=ROOT, check=False):
    _, _, rendered, warnings = prepared(root)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    stale = stale_outputs(root, rendered)
    if check and stale:
        raise RuleError("generated files are out of date: " + ", ".join(stale))
    if not check:
        for lang, data in rendered.items():
            write_text(Path(root) / f"rules/{lang}/general.json", json_text(data))
    print(f"{'Checked' if check else 'Built'} {len(rendered['en'])} rules in {len(rendered)} languages")
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="fail if generated files would change; never write")
    args = parser.parse_args()
    try:
        build(args.root, args.check)
    except (RuleError, OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
