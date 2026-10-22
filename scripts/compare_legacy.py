#!/usr/bin/env python3
"""Summarize legacy differences by category; --details shows individual objects."""

import argparse
from collections import Counter
import json
import subprocess
from pathlib import Path

from rulelib import LANGUAGES, ROOT, RuleError


MISSING = object()


def differences(legacy, current, lang, manifest):
    """Use the audited name/id table to resolve legacy collisions, never a dict overwrite."""
    by_id = {}
    for row in current:
        if row["id"] in by_id:
            raise RuleError(f"{lang}: duplicate generated id {row['id']}")
        by_id[row["id"]] = row
    seen = set()
    changes = []
    reassignments = {
        (entry[f"old_{lang}_id"], entry[f"{lang}_name"]): entry["new_id"]
        for entry in manifest["id_reassignments"]
    }
    for old in legacy:
        new_id = reassignments.get((old["id"], old["name"]), old["id"])
        if new_id in seen:
            raise RuleError(f"{lang}: unresolved legacy identity for {old['name']}")
        seen.add(new_id)
        new = by_id.get(new_id)
        if new is None:
            changes.append({"lang": lang, "id": new_id, "name": old["name"], "field": "REMOVED"})
            continue
        for key in sorted(old.keys() | new.keys()):
            a, b = old.get(key, MISSING), new.get(key, MISSING)
            if a != b:
                changes.append({"lang": lang, "id": new_id, "name": old["name"], "field": key, "old": a, "new": b})
    for rule_id in sorted(by_id.keys() - seen):
        changes.append({"lang": lang, "id": rule_id, "name": by_id[rule_id]["name"], "field": "ADDED"})
    return changes


def detail(change):
    prefix = f"{change['lang']} id {change['id']} ({change['name']}): {change['field']}"
    if change["field"] in ("ADDED", "REMOVED"):
        return prefix
    a, b = change["old"], change["new"]
    if change["field"] == "networkSignature" and isinstance(a, list) and isinstance(b, list) and list(dict.fromkeys(a)) == b:
        removed = {value: count for value, count in (Counter(a) - Counter(b)).items()}
        value = f"removed repeated entries {json.dumps(removed, ensure_ascii=False)} ({len(a)} -> {len(b)})"
    else:
        def display(value):
            return "<absent>" if value is MISSING else json.dumps(value, ensure_ascii=False)
        value = f"{display(a)} -> {display(b)}"
    return f"{prefix}: {value}"


def compare(legacy, current, lang, manifest):
    return [detail(change) for change in differences(legacy, current, lang, manifest)]


def summarize(changes):
    labels = {
        "REMOVED": "removed rules", "ADDED": "added rules", "id": "id reassignments",
        "company": "localized company", "contributors": "ordered contributor unions",
        "website": "websites", "networkSignature": "network signatures", "searchKeyword": "code keywords",
    }
    lines = []
    for lang in LANGUAGES:
        counts = Counter(c["field"] for c in changes if c["lang"] == lang)
        for field in sorted(counts, key=lambda key: list(labels).index(key) if key in labels else len(labels)):
            ids = sorted(c["id"] for c in changes if c["lang"] == lang and c["field"] == field)
            suffix = f" ({', '.join(map(str, ids))})" if field in ("REMOVED", "ADDED") else ""
            lines.append(f"{lang}: {labels.get(field, field)}: {counts[field]}{suffix}")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--legacy-root", type=Path, help="read the old rules from a directory instead of git")
    parser.add_argument("--legacy-ref", help="defaults to the migration manifest's recorded git revision")
    parser.add_argument("--fail-on-difference", action="store_true")
    parser.add_argument("--details", action="store_true", help="show individual field differences instead of category counts")
    args = parser.parse_args()
    try:
        manifest = json.loads((args.root / "scripts/migration_manifest.json").read_text(encoding="utf-8"))
        changes = []
        for lang in LANGUAGES:
            relative = f"rules/{lang}/general.json"
            if args.legacy_root:
                legacy = json.loads((args.legacy_root / relative).read_text(encoding="utf-8"))
            else:
                legacy = json.loads(subprocess.check_output([
                    "git", "-C", str(args.root), "show",
                    f"{args.legacy_ref or manifest['legacy_ref']}:{relative}",
                ]))
            current = json.loads((args.root / relative).read_text(encoding="utf-8"))
            changes.extend(differences(legacy, current, lang, manifest))
        lines = [detail(change) for change in changes] if args.details else summarize(changes)
        for line in lines:
            print(line)
        if args.fail_on_difference and lines:
            return 1
    except (RuleError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
