#!/usr/bin/env python3
"""One-time, content-aware migration of the legacy English and Chinese JSON."""

import argparse
import json
import subprocess
from pathlib import Path

from rulelib import ROOT, RuleError, json_text, merge_keywords, normalize_keyword, slugify, unique, write_text, yaml_text

# The original local rules own their ids. The legacy Exodus-import inputs and
# 812c832 prove these collisions predate a3e5816; see .local/MIGRATION_REPORT.md.
REASSIGNED_NAMES = {
    (35, "Teemo"),
    (36, "FidZup"),
    (37, "Audience Studio (Krux)"),
}
TEXT_FIELDS = ("name", "description", "sideEffect", "company")
NEUTRAL_FIELDS = (
    "networkSignature", "useRegexSearch", "safeToBlock", "iconUrl",
    "website", "contributors",
)


def pair_languages(english, chinese):
    """Prefer an id AND content match, then content, then a documented id slot.

    Never turn a colliding-id list into a dict: that silently discards rules.
    Position is recorded as evidence but is never the primary matching key.
    """
    unused = set(range(len(chinese)))
    pairs = []
    for en_index, en in enumerate(english):
        keywords = set(en.get("searchKeyword", []))
        same_content = [i for i in sorted(unused)
                        if keywords and set(chinese[i].get("searchKeyword", [])) == keywords]
        same_both = [i for i in same_content if chinese[i]["id"] == en["id"]]
        same_id = [i for i in sorted(unused) if chinese[i]["id"] == en["id"]]
        if len(same_both) == 1:
            zh_index, method = same_both[0], "id-and-keywords"
        elif len(same_content) == 1:
            zh_index, method = same_content[0], "keywords-across-id"
        elif len(same_id) == 1:
            zh_index, method = same_id[0], "id-slot-needs-review"
        else:
            raise RuleError(f"cannot safely pair English index {en_index}: {en['name']}")
        unused.remove(zh_index)
        pairs.append((en_index, en, zh_index, chinese[zh_index], method))
    if unused:
        raise RuleError(f"unpaired Chinese rules require a decision: {sorted(unused)}")
    return pairs


def fold_stray_duplicates(data):
    """Retire the unrelated id-467 copies, retaining missing metadata by identity."""
    removed = []
    for lang, target_id in (("en", 168), ("zh-CN", 101)):
        strays = [row for row in data[lang] if row["id"] == 467]
        for stray in strays:
            targets = [row for row in data[lang] if row["id"] == target_id]
            if len(targets) != 1:
                raise RuleError(f"cannot fold {lang} id 467: target {target_id} is not unique")
            target = targets[0]
            old_keywords = {normalize_keyword(v) for v in stray.get("searchKeyword", [])}
            target_keywords = {normalize_keyword(v) for v in target.get("searchKeyword", [])}
            if not old_keywords or not old_keywords.issubset(target_keywords):
                raise RuleError(f"cannot fold {lang} id 467: keyword identity does not match {target_id}")
            record = {"lang": lang, "id": 467, "name": stray["name"], "kept_id": target_id}
            old_network = target.get("networkSignature", [])
            added = [v for v in unique(stray.get("networkSignature", [])) if v not in old_network]
            if added:
                target["networkSignature"] = unique(old_network + added)
                record["network_signatures_added"] = added
            if not target.get("website") and stray.get("website"):
                target["website"] = stray["website"]
                record["website_added"] = stray["website"]
            if lang != "en":
                # The retained rule has one neutral metadata set. Preserve the
                # removed Chinese copy's metadata in that English-backed set.
                canonical = [row for row in data["en"] if row["id"] == target_id]
                if len(canonical) != 1:
                    raise RuleError(f"canonical English target {target_id} is not unique")
                canonical = canonical[0]
                network = unique(canonical.get("networkSignature", []) + stray.get("networkSignature", []))
                if network:
                    canonical["networkSignature"] = network
                if not canonical.get("website") and stray.get("website"):
                    canonical["website"] = stray["website"]
            removed.append(record)
            data[lang].remove(stray)
    return removed


def migrate(legacy_root=ROOT, output_root=ROOT, legacy_ref=None):
    legacy_root, output_root = Path(legacy_root), Path(output_root)
    if list((output_root / "src/rules").glob("*.yaml")):
        raise RuleError("src/rules already contains YAML; migration refuses to overwrite sources")
    data = {
        lang: json.loads((legacy_root / f"rules/{lang}/general.json").read_text(encoding="utf-8"))
        for lang in ("en", "zh-CN")
    }
    if legacy_ref is None:
        legacy_ref = subprocess.check_output(
            ["git", "-C", str(legacy_root), "rev-parse", "HEAD"], text=True
        ).strip()
    next_id = max(rule["id"] for rules in data.values() for rule in rules) + 1
    manifest = {
        "legacy_ref": legacy_ref,
        "id_reassignments": [],
        "keyword_merges": [],
        "removed_rules": fold_stray_duplicates(data),
        "network_deduplications": [],
        "neutral_fields": "English values for non-text metadata; contributors are an ordered English-first union across locales.",
        "text_fields": "Name, description, sideEffect, and company are localized; missing Chinese text falls back to English.",
        "zh_only_id_decision": (
            "zh-CN id 466 is Honor Ad Alliance, also present in en under the duplicate id 465. "
            "Preserve the published Chinese id 466 and correct English Honor to 466; Sohu keeps 465."
        ),
    }
    planned = []
    used_ids, used_slugs = set(), set()
    for en_index, en, zh_index, zh, method in pair_languages(data["en"], data["zh-CN"]):
        rule_id = en["id"]
        if (rule_id, en["name"]) in REASSIGNED_NAMES:
            rule_id, next_id = next_id, next_id + 1
        elif rule_id == 465 and en["name"] == "Honor Ad Alliance":
            rule_id = 466
        if rule_id != en["id"] or rule_id != zh["id"]:
            manifest["id_reassignments"].append({
                "en_name": en["name"], "zh-CN_name": zh["name"],
                "old_en_id": en["id"], "old_zh-CN_id": zh["id"], "new_id": rule_id,
                "en_position": en_index, "zh-CN_position": zh_index,
            })
        if rule_id in used_ids:
            raise RuleError(f"unresolved duplicate id {rule_id}")
        used_ids.add(rule_id)
        keywords = merge_keywords("", en.get("searchKeyword", []) + zh.get("searchKeyword", []))
        source = {"id": rule_id, "keywords": keywords}
        if en.get("searchKeyword") != zh.get("searchKeyword"):
            manifest["keyword_merges"].append({
                "id": rule_id, "en_name": en["name"], "zh-CN_name": zh["name"],
                "en": en.get("searchKeyword", []), "zh-CN": zh.get("searchKeyword", []),
                "union": keywords,
            })
        if method == "id-slot-needs-review" and keywords:
            raise RuleError(f"keyword identity conflict requires a decision: {rule_id} {en['name']} / {zh['name']}")
        source.update({field: en[field] for field in NEUTRAL_FIELDS if field in en})
        contributors = unique(en.get("contributors", []) + zh.get("contributors", []))
        if contributors or "contributors" in en or "contributors" in zh:
            source["contributors"] = contributors
        source["reviewed"] = True
        source["i18n"] = {
            "en": {field: en[field] for field in TEXT_FIELDS if field in en},
            "zh-CN": {field: zh[field] for field in TEXT_FIELDS
                      if field in zh and (field == "company" or zh[field] != en.get(field))},
        }
        for lang, row in (("en", en), ("zh-CN", zh)):
            network = row.get("networkSignature", [])
            if unique(network) != network:
                manifest["network_deduplications"].append({
                    "id": rule_id, "lang": lang, "name": row["name"],
                    "before": len(network), "after": len(unique(network)),
                })
        slug = slugify(en["name"])
        if slug in used_slugs:
            slug = f"{slug}-{rule_id}"
        used_slugs.add(slug)
        planned.append((output_root / f"src/rules/{slug}.yaml", yaml_text(source)))
    # Prepare the complete plan before writing any sources.
    for path, content in planned:
        write_text(path, content)
    write_text(output_root / "scripts/migration_manifest.json", json_text(manifest))
    print(f"Migrated {len(planned)} rules; reassigned {len(manifest['id_reassignments'])} ids; "
          f"removed {len(manifest['removed_rules'])} stray locale rows; "
          f"merged {len(manifest['keyword_merges'])} keyword differences")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--legacy-ref", help="baseline git revision recorded for compare_legacy.py")
    args = parser.parse_args()
    try:
        migrate(args.legacy_root, args.output_root, args.legacy_ref)
    except (RuleError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
