#!/usr/bin/env python3
"""Link existing rules conservatively; leave ambiguous keyword overlap for review."""

import argparse
import copy
from pathlib import Path

from exoduslib import candidate_report, link_candidates, stats, signature_changes, summary
from rulelib import (
    ROOT, RuleError, check_rules, load_snapshot, load_sources, render_all, write_text, yaml_text,
    load_ignored, normalize_keyword,
)


def link(root=ROOT, dry_run=False, summary_file=None):
    root = Path(root)
    sources, trackers = load_sources(root), load_snapshot(root)
    if not trackers:
        raise RuleError("no Exodus snapshot; first run sync_exodus.py --snapshot-only with network access")
    check_rules(sources, trackers)
    ignored = load_ignored(root)
    certain, ambiguous, unmatched = link_candidates(sources, trackers, ignored)
    before = render_all(sources, trackers)
    planned = {rule["id"]: tracker_id for _, rule, tracker_id in certain}
    updated = []
    for path, rule in sources:
        rule = copy.deepcopy(rule)
        if rule["id"] in planned:
            rule["upstream"] = {"exodus": planned[rule["id"]]}
        updated.append((path, rule))
    check_rules(updated, trackers)
    after = render_all(updated, trackers)
    for lang in before:
        for old, new in zip(before[lang], after[lang]):
            # Linking may merge signatures, but must not change text, metadata,
            # safety, field types, or the app primary key.
            omit = {"searchKeyword", "networkSignature"}
            if {k: v for k, v in old.items() if k not in omit} != {k: v for k, v in new.items() if k not in omit}:
                raise RuleError(f"link would change non-signature fields for {lang} app {old['id']}")
            for field in omit:
                key = normalize_keyword if field == "searchKeyword" else lambda value: value
                if {key(v) for v in old.get(field, [])} - {key(v) for v in new.get(field, [])}:
                    raise RuleError(f"link would remove {field} from {lang} app {old['id']}")
    notes = [
        f"High-confidence new links: {len(certain)}; ambiguous rules: {len(ambiguous)}; no overlap: {len(unmatched)}.",
        f"Total linked sources: {sum('upstream' in rule for _, rule in updated)}; ignored trackers: {len(ignored)}.",
        "App ids and local text/safety fields are preserved; equivalent code signatures retain their local spelling.",
    ]
    report = summary("Exodus linking summary", before, after, notes=notes)
    if not dry_run:
        for path, rule in updated:
            if rule["id"] in planned:
                write_text(path, yaml_text(rule))
        write_text(root / "upstream/exodus/link_candidates.md", candidate_report(ambiguous, unmatched, trackers, ignored))
        if summary_file is not None:
            write_text(summary_file, report)
    count, affected = stats(signature_changes(before, after), "searchKeyword")
    print(f"{'Would link' if dry_run else 'Linked'} {len(certain)} rules; "
          f"{len(ambiguous)} ambiguous; {len(unmatched)} unmatched; "
          f"{count} code keywords added to {affected} rules")
    return certain, ambiguous, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true", help="calculate links and keyword additions without writing")
    parser.add_argument("--summary-file", type=Path, help="defaults to <root>/.local/exodus-links.md")
    args = parser.parse_args()
    try:
        link(args.root, args.dry_run, args.summary_file or args.root / ".local/exodus-links.md")
    except (RuleError, OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
