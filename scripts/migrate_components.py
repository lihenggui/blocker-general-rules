#!/usr/bin/env python3
"""One-time migration of component JSON to the approved shared YAML sources."""

import argparse
import json
from pathlib import Path

from rulelib import (
    COMPONENT_METADATA_TYPES, COMPONENT_OUTPUT_TYPES, COMPONENT_TEXT_FIELDS,
    LANGUAGES, ROOT, RuleError, check_component_source, component_name, json_text,
    write_text, yaml_text,
)


def migrate_components(legacy_root=ROOT, output_root=ROOT):
    legacy_root, output_root = Path(legacy_root), Path(output_root)
    if list((output_root / "src/components").rglob("*.yaml")):
        raise RuleError("src/components already contains YAML; migration refuses to overwrite sources")
    data = {}
    for lang in LANGUAGES:
        directory = legacy_root / f"components/{lang}"
        data[lang] = {}
        for path in sorted(directory.rglob("*.json")):
            relative = path.relative_to(directory)
            row = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(row, dict) or set(row) - set(COMPONENT_OUTPUT_TYPES):
                raise RuleError(f"{path}: unexpected legacy component fields")
            for field, expected in COMPONENT_OUTPUT_TYPES.items():
                if field in row and type(row[field]) is not expected:
                    raise RuleError(f"{path}.{field}: expected {expected.__name__}")
            if row.get("name") != component_name(relative):
                raise RuleError(f"{path}: legacy name does not match the component path")
            if "recommendToBlock" not in row:
                raise RuleError(f"{path}: recommendToBlock is required")
            data[lang][relative] = row
    zh_only = sorted(set(data["zh-CN"]) - set(data["en"]))
    if zh_only:
        # There are none in the legacy data. Do not relabel Chinese prose as
        # English or extend the approved schema if a future input has any.
        raise RuleError("components only in zh-CN require English descriptions before migration: "
                        + ", ".join(component_name(path) for path in zh_only))
    report = {
        "migrated": len(data["en"]),
        "zh-CN_only": [component_name(path) for path in zh_only],
        "en_missing_description": sum("description" not in row for row in data["en"].values()),
        "dropped_sdkName": {lang: sum("sdkName" in row for row in rows.values())
                            for lang, rows in data.items()},
        "conflicts": [],
    }
    planned = []
    for relative, en in data["en"].items():
        zh = data["zh-CN"].get(relative)
        component = {"recommendToBlock": en["recommendToBlock"]}
        component.update({field: en[field] for field in ("contributor", "lastUpdateTime") if field in en})
        component["i18n"] = {"en": {field: en[field] for field in COMPONENT_TEXT_FIELDS if field in en}}
        if zh is not None:
            for field in COMPONENT_METADATA_TYPES:
                if (field in en, en.get(field)) != (field in zh, zh.get(field)):
                    report["conflicts"].append({
                        "component": component_name(relative), "field": field,
                        "en": {field: en[field]} if field in en else {},
                        "zh-CN": {field: zh[field]} if field in zh else {},
                    })
            translated = {field: zh[field] for field in COMPONENT_TEXT_FIELDS
                          if field in zh and (field not in en or zh[field] != en[field])}
            if translated:
                component["i18n"]["zh-CN"] = translated
        check_component_source(component, relative.as_posix())
        planned.append((output_root / "src/components" / relative.with_suffix(".yaml"), yaml_text(component)))
    # Validate every input before creating the first source. PyYAML quotes
    # timestamp-looking strings, retaining all original fractional digits.
    for path, content in planned:
        write_text(path, content)
    print(json_text(report), end="")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        migrate_components(args.legacy_root, args.output_root)
    except (RuleError, OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
