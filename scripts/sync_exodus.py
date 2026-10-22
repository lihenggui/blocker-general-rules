#!/usr/bin/env python3
"""Fetch a trimmed Exodus snapshot and add previously unlinked code trackers."""

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import rulelib
from exoduslib import markdown, summary, tracker_overlap
from rulelib import (
    ROOT, RuleError, check_rules, json_text, load_snapshot, load_sources, load_ignored, render_all,
    signatures, slugify, trim_trackers, write_text, yaml_text,
)

EXODUS_URL = "https://reports.exodus-privacy.eu.org/api/trackers"


def fetch_trackers():
    headers = {
        "Accept": "application/json",
        "User-Agent": "Blocker-rule-sync/1.0",
    }
    if os.environ.get("EXODUS_API_TOKEN"):
        headers["Authorization"] = "Token " + os.environ["EXODUS_API_TOKEN"]
    request = urllib.request.Request(EXODUS_URL, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.load(response)
    trackers = trim_trackers(payload)
    if not trackers:
        raise RuleError("Exodus returned no trackers; refusing to replace the snapshot")
    return trackers


def sync(root=ROOT, snapshot_only=False, from_snapshot=False, input_file=None, summary_file=None):
    root = Path(root)
    sources, old_trackers = load_sources(root), load_snapshot(root)
    ignored = load_ignored(root)
    check_rules(sources, old_trackers)
    before = render_all(sources, old_trackers)
    if from_snapshot:
        trackers_list = list(old_trackers.values())
        source_note = "Used the existing local trimmed snapshot; no network fetch."
    elif input_file:
        trackers_list = trim_trackers(json.loads(Path(input_file).read_text(encoding="utf-8")))
        source_note = "Used an explicit API-response input file; no network fetch."
    else:
        trackers_list = fetch_trackers()
        source_note = f"Fetched {EXODUS_URL}."
    if not trackers_list:
        raise RuleError("no tracker data; snapshot and rule sources were not changed")
    trackers = {t["id"]: t for t in trackers_list}
    linked = {rule["upstream"]["exodus"] for _, rule in sources if "upstream" in rule}
    next_id = max(rule["id"] for _, rule in sources) + 1
    planned, new_rules, manual_links = [], [], []
    if not snapshot_only:
        for tracker_id, tracker in sorted(trackers.items()):
            if tracker_id in linked or tracker_id in ignored or not signatures(tracker["code_signature"]):
                continue
            overlap = tracker_overlap(sources + planned, tracker, trackers)
            if overlap:
                manual_links.append((tracker_id, tracker, overlap))
                continue
            rule = {
                "id": next_id,
                "upstream": {"exodus": tracker_id},
                "keywords": [],
                "contributors": ["Exodus Tracker Investigation Platform"],
                "reviewed": False,
                "i18n": {"en": {"name": tracker["name"], "description": tracker["description"]}},
            }
            if tracker["website"]:
                rule["website"] = tracker["website"]
            path = root / f"src/rules/exodus-{tracker_id}-{slugify(tracker['name'])}.yaml"
            if path.exists():
                raise RuleError(f"refusing to overwrite existing source: {path}")
            planned.append((path, rule))
            new_rules.append(rule)
            next_id += 1
    all_sources = sorted(sources + planned, key=lambda pair: pair[1]["id"])
    check_rules(all_sources, trackers)
    after = render_all(all_sources, trackers)
    added_trackers = sorted(trackers.keys() - old_trackers.keys())
    removed_trackers = sorted(old_trackers.keys() - trackers.keys())
    notes = [
        source_note,
        f"Snapshot contains {len(trackers)} trackers; {len(added_trackers)} new snapshot ids.",
        f"Unreviewed rules are {'published' if rulelib.PUBLISH_UNREVIEWED else 'withheld until reviewed: true'} "
        "via rulelib.PUBLISH_UNREVIEWED; safeToBlock is never imported.",
    ]
    if snapshot_only:
        notes.append("Snapshot-only mode: no new rule files created. Link existing rules before the first full sync.")
    if removed_trackers:
        notes.append("Removed upstream tracker ids (local rules retained): " + ", ".join(map(str, removed_trackers)) + ".")
    report = summary("Exodus synchronization", before, after, new_rules, notes)
    report += "\n## Needs manual link\n\n"
    for tracker_id, tracker, overlap in manual_links:
        details = "; ".join(
            f"app {match['id']} {markdown(match['name'])}: "
            + ", ".join(f"`{markdown(a)}` ↔ `{markdown(b)}`" for a, b in match["evidence"])
            for match in overlap
        )
        report += f"- Exodus {tracker_id} {markdown(tracker['name'])}: {details}. No rule created.\n"
    if not manual_links:
        report += "Not assessed in snapshot-only mode.\n" if snapshot_only else "None.\n"
    report += "\n## Ignored trackers\n\n"
    report += "\n".join(f"- Exodus {tid}: {markdown(reason)}" for tid, reason in sorted(ignored.items())) or "None."
    report += "\n"
    report += "\n## New snapshot trackers\n\n"
    report += "\n".join(f"- {tid}: {trackers[tid]['name']}" for tid in added_trackers) or "None."
    report += "\n"
    # Nothing is written until the entire fetched payload and generated plan pass.
    if not from_snapshot:
        write_text(root / "upstream/exodus/trackers.json", json_text(trackers_list))
    for path, rule in planned:
        write_text(path, yaml_text(rule))
    if summary_file is not None:
        write_text(summary_file, report)
    print(f"Synced {len(trackers)} trackers; created {len(new_rules)} unreviewed rule files; "
          f"{len(manual_links)} need manual link; {len(ignored)} ignored")
    return new_rules, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--snapshot-only", action="store_true", help="fetch snapshot without creating rule files (initial linking)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--from-snapshot", action="store_true", help="use the existing trimmed snapshot without fetching again")
    group.add_argument("--input", type=Path, help="explicit offline API-response file; not a live fetch")
    parser.add_argument("--summary-file", type=Path, help="defaults to <root>/.local/exodus-sync-summary.md")
    args = parser.parse_args()
    try:
        sync(args.root, args.snapshot_only, args.from_snapshot, args.input,
             args.summary_file or args.root / ".local/exodus-sync-summary.md")
    except (RuleError, OSError, ValueError, urllib.error.URLError) as exc:
        parser.exit(1, f"ERROR: Exodus sync failed; {exc}\n")


if __name__ == "__main__":
    main()
