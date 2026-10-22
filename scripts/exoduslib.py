"""Conservative linking and human-readable Exodus change summaries."""

import re

from rulelib import merge_keywords, normalize_keyword as normalize, render_rule, signatures


def prefix_overlap(left, right):
    left, right = normalize(left), normalize(right)
    if not left or not right:
        return False
    if left == right:
        return True
    # Prefix matching only makes sense for literal package prefixes. Regex
    # metacharacters and leading-dot component fragments require exact evidence.
    literal = r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+"
    if not re.fullmatch(literal, left) or not re.fullmatch(literal, right):
        return False
    return left.startswith(right + ".") or right.startswith(left + ".")


def substring_overlap(left, right):
    """Weak sync evidence: dotted fragments count in either direction.

    Component matching in the app is case-insensitive. This broader check only
    defers imports to manual review; automatic linking still uses prefix_overlap.
    """
    left, right = (value.strip().strip(".").casefold() for value in (left, right))
    return bool(left and right) and (left in right or right in left)


def tracker_overlap(sources, tracker, trackers):
    """Guard imports using every source, including upstream-only sources."""
    code = signatures(tracker["code_signature"])
    matches = []
    for _, rule in sources:
        rendered = render_rule(rule, "en", trackers)
        evidence = [(a, b) for a in rendered.get("searchKeyword", []) for b in code if substring_overlap(a, b)]
        if evidence:
            matches.append({"id": rule["id"], "name": rendered["name"], "evidence": evidence})
    return matches


def link_candidates(sources, trackers, ignored=()):
    """Return exact/prefix evidence; a unique prefix alone is not enough to link."""
    by_rule = {}
    by_tracker = {}
    already_linked = {rule["upstream"]["exodus"] for _, rule in sources if "upstream" in rule}
    for path, rule in sources:
        if "upstream" in rule:
            continue
        local = merge_keywords("", rule["keywords"], rule.get("excludeKeywords", []))
        candidates = []
        for tracker_id, tracker in sorted(trackers.items()):
            if tracker_id in ignored:
                continue
            code = signatures(tracker["code_signature"])
            evidence = [(a, b) for a in local for b in code if prefix_overlap(a, b)]
            if evidence:
                exact = sum(normalize(a) == normalize(b) for a, b in evidence)
                candidates.append({"tracker_id": tracker_id, "exact": exact, "evidence": evidence})
                by_tracker.setdefault(tracker_id, set()).add(rule["id"])
        by_rule[rule["id"]] = (path, rule, candidates)
    certain, ambiguous, unmatched = [], [], []
    for rule_id, (path, rule, candidates) in sorted(by_rule.items()):
        if not candidates:
            unmatched.append((path, rule))
            continue
        candidate = candidates[0]
        tracker_id = candidate["tracker_id"]
        if (len(candidates) == 1 and candidate["exact"] > 0
                and len(by_tracker[tracker_id]) == 1 and tracker_id not in already_linked):
            certain.append((path, rule, tracker_id))
        else:
            ambiguous.append((path, rule, candidates))
    return certain, ambiguous, unmatched


def markdown(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("`", "'")


def candidate_report(ambiguous, unmatched, trackers, ignored=None):
    lines = [
        "# Exodus link candidates", "",
        "Only reciprocal, unique matches with an exact keyword after stripping trailing dots are linked automatically.",
        "Prefix-only, multiple-tracker, and multiple-local-rule matches need human review. App ids are never Exodus ids.",
        "", "## Ambiguous matches", "",
        "| App id | Local rule | Exodus candidates and keyword evidence |",
        "| --- | --- | --- |",
    ]
    for _, rule, candidates in ambiguous:
        details = []
        for candidate in candidates:
            tid = candidate["tracker_id"]
            evidence = "; ".join(f"{a} ↔ {b}" for a, b in candidate["evidence"])
            details.append(f"{tid} {trackers[tid]['name']}: {evidence}")
        lines.append(f"| {rule['id']} | {markdown(rule['i18n']['en'].get('name', ''))} | {markdown('; '.join(details))} |")
    if not ambiguous:
        lines.append("| — | No ambiguous matches | — |")
    lines.extend(["", "## No keyword overlap", ""])
    lines.extend(f"- {rule['id']}: {markdown(rule['i18n']['en'].get('name', path.stem))}" for path, rule in unmatched)
    if not unmatched:
        lines.append("None.")
    lines.extend(["", "## Ignored trackers", ""])
    lines.extend(f"- {tid}: {markdown(reason)}" for tid, reason in sorted((ignored or {}).items()))
    if not ignored:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def signature_changes(before, after):
    old = {row["id"]: row for row in before["en"]}
    changes = []
    for row in after["en"]:
        if row["id"] not in old:
            continue
        for field in ("searchKeyword", "networkSignature"):
            a, b = old[row["id"]].get(field, []), row.get(field, [])
            if a != b:
                key = normalize if field == "searchKeyword" else lambda value: value
                old_keys, new_keys = {key(v) for v in a}, {key(v) for v in b}
                changes.append({
                    "id": row["id"], "name": row["name"], "field": field,
                    "added": [v for v in b if key(v) not in old_keys],
                    "removed": [v for v in a if key(v) not in new_keys],
                    "order_changed": old_keys == new_keys,
                })
    return changes


def stats(changes, field):
    relevant = [c for c in changes if c["field"] == field and c["added"]]
    return sum(len(c["added"]) for c in relevant), len({c["id"] for c in relevant})


def summary(title, old_rendered, new_rendered, new_rules=(), notes=()):
    changes = signature_changes(old_rendered, new_rendered)
    code_count, code_rules = stats(changes, "searchKeyword")
    network_count, network_rules = stats(changes, "networkSignature")
    lines = [
        f"# {title}", "",
        f"- New rule files: {len(new_rules)}.",
        f"- Existing rules: {code_count} code keywords added to {code_rules} rules; "
        f"{network_count} network signatures added to {network_rules} rules (English output).",
    ]
    lines.extend(f"- {note}" for note in notes)
    lines.extend(["", "## New trackers", ""])
    for rule in new_rules:
        lines.append(f"- Exodus {rule['upstream']['exodus']} → app {rule['id']}: "
                     f"{markdown(rule['i18n']['en']['name'])} (no `safeToBlock`).")
    if not new_rules:
        lines.append("None.")
    lines.extend(["", "## Existing rule keyword changes", ""])
    for change in changes:
        detail = []
        if change["added"]:
            detail.append("added " + ", ".join(f"`{markdown(v)}`" for v in change["added"]))
        if change["removed"]:
            detail.append("removed " + ", ".join(f"`{markdown(v)}`" for v in change["removed"]))
        if change["order_changed"]:
            detail.append("order normalized to upstream first")
        lines.append(f"- App {change['id']} {markdown(change['name'])}, {change['field']}: {'; '.join(detail)}.")
    if not changes:
        lines.append("None.")
    return "\n".join(lines) + "\n"
