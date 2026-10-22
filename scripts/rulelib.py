"""Shared source, snapshot, and publishing contracts (stdlib + PyYAML only)."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "zh-CN")
TRACKER_FIELDS = (
    "id", "name", "code_signature", "network_signature", "website",
    "description", "categories",
)
TEXT_FIELDS = ("name", "description", "sideEffect", "company")
OUTPUT_TYPES = {
    "id": int, "name": str, "iconUrl": str, "company": str,
    "searchKeyword": list, "networkSignature": list, "useRegexSearch": bool,
    "description": str, "safeToBlock": bool, "sideEffect": str,
    "website": str, "contributors": list,
}
SOURCE_FIELDS = {
    "id", "upstream", "keywords", "excludeKeywords", "networkSignature",
    "excludeNetworkSignatures", "useRegexSearch", "safeToBlock", "iconUrl",
    "website", "contributors", "i18n",
}


class RuleError(ValueError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject YAML typos that would otherwise silently overwrite a field."""


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise RuleError("YAML mapping keys must be strings")
        if key in result:
            raise RuleError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_text(path, text):
    path = Path(path)
    if path.exists() and path.read_bytes() == text.encode("utf-8"):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def yaml_text(value):
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tracker"


def unique(values):
    return list(dict.fromkeys(values))


def signatures(value):
    return unique(part.strip() for part in value.split("|") if part.strip())


def normalize_keyword(value):
    return value.strip().rstrip(".")


def merge_keywords(upstream, local, excluded=()):
    """Keep local spellings and omit upstream keywords already covered locally.

    The app performs case-insensitive substring searches on component names.
    Only upstream code keywords are subsumed; local values and network regexes
    keep their existing contracts.
    """
    local_spelling = {}
    for value in local:
        local_spelling.setdefault(normalize_keyword(value), value)
    excluded = {normalize_keyword(value) for value in excluded}
    active_local = [(key.casefold(), spelling) for key, spelling in local_spelling.items()
                    if key and key not in excluded]
    upstream_values = []
    for value in signatures(upstream):
        key = normalize_keyword(value)
        # Keep the local representative at the first covered upstream position.
        # This drops the redundant upstream value without moving a legacy local
        # keyword behind the rest of its group.
        representative = local_spelling.get(key)
        if representative is None:
            representative = next((spelling for local_key, spelling in active_local
                                   if local_key in key.casefold()), None)
        upstream_values.append(representative if representative is not None else value)
    seen = set()
    result = []
    for value in upstream_values + local:
        key = normalize_keyword(value)
        if not key or key in seen or key in excluded:
            continue
        seen.add(key)
        result.append(local_spelling.get(key, value))
    return result


def merge_signatures(upstream, local, excluded=()):
    """Network signatures use exact deduplication; trailing dots are significant."""
    excluded = set(excluded)
    return [x for x in unique(signatures(upstream) + local) if x not in excluded]


def _strings(value, label):
    if not isinstance(value, list) or any(type(v) is not str for v in value):
        raise RuleError(f"{label}: expected a list of strings")


def trim_trackers(payload):
    """Validate the API envelope and retain only the seven public fields."""
    if not isinstance(payload, dict) or not isinstance(payload.get("trackers"), dict):
        raise RuleError("Exodus response must contain a trackers object")
    result = []
    for key, tracker in payload["trackers"].items():
        if not isinstance(tracker, dict) or not str(key).isdigit():
            raise RuleError(f"invalid Exodus tracker: {key!r}")
        tracker_id = int(key)
        if "id" in tracker and tracker["id"] != tracker_id:
            raise RuleError(f"Exodus tracker key/id mismatch: {key}")
        item = {"id": tracker_id}
        for field in TRACKER_FIELDS[1:-1]:
            value = tracker.get(field, "")
            if type(value) is not str:
                raise RuleError(f"Exodus {key}.{field}: expected a string")
            item[field] = value
        categories = tracker.get("categories", [])
        _strings(categories, f"Exodus {key}.categories")
        item["categories"] = sorted(set(categories))
        result.append(item)
    result.sort(key=lambda t: t["id"])
    check_snapshot(result)
    return result


def check_snapshot(trackers):
    if not isinstance(trackers, list):
        raise RuleError("snapshot must be a JSON array")
    seen = set()
    for tracker in trackers:
        if not isinstance(tracker, dict) or set(tracker) != set(TRACKER_FIELDS):
            raise RuleError("snapshot must contain exactly the seven trimmed fields")
        tracker_id = tracker["id"]
        if type(tracker_id) is not int or tracker_id <= 0 or tracker_id in seen:
            raise RuleError(f"invalid or duplicate snapshot id: {tracker_id}")
        seen.add(tracker_id)
        for field in TRACKER_FIELDS[1:-1]:
            if type(tracker[field]) is not str:
                raise RuleError(f"snapshot {tracker_id}.{field}: expected a string")
        _strings(tracker["categories"], f"snapshot {tracker_id}.categories")
    if trackers != sorted(trackers, key=lambda t: t["id"]):
        raise RuleError("snapshot must be sorted by id")


def load_snapshot(root=ROOT):
    path = Path(root) / "upstream/exodus/trackers.json"
    if not path.exists():
        return {}
    trackers = json.loads(path.read_text(encoding="utf-8"))
    check_snapshot(trackers)
    return {t["id"]: t for t in trackers}


def load_ignored(root=ROOT):
    path = Path(root) / "upstream/exodus/ignore.yaml"
    if not path.exists():
        return {}
    entries = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(entries, list):
        raise RuleError("Exodus ignore.yaml must be a list of {id, reason} entries")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id", "reason"}:
            raise RuleError("each Exodus ignore entry must contain only id and reason")
        tracker_id, reason = entry["id"], entry["reason"]
        if type(tracker_id) is not int or tracker_id <= 0 or tracker_id in result:
            raise RuleError(f"invalid or duplicate ignored Exodus id: {tracker_id}")
        if type(reason) is not str or not reason.strip():
            raise RuleError(f"ignored Exodus {tracker_id} requires a nonempty reason")
        result[tracker_id] = reason
    return result


def check_source(rule, label):
    if not isinstance(rule, dict):
        raise RuleError(f"{label}: expected a YAML mapping")
    unknown = set(rule) - SOURCE_FIELDS
    if unknown:
        raise RuleError(f"{label}: unknown source keys: {sorted(unknown)}")
    if type(rule.get("id")) is not int or rule["id"] <= 0:
        raise RuleError(f"{label}: id must be a positive integer")
    if "keywords" not in rule:
        raise RuleError(f"{label}: keywords is required (may be empty)")
    for field in ("keywords", "excludeKeywords", "networkSignature",
                  "excludeNetworkSignatures", "contributors"):
        if field in rule:
            _strings(rule[field], f"{label}.{field}")
    for field in ("website", "iconUrl"):
        if field in rule and type(rule[field]) is not str:
            raise RuleError(f"{label}.{field}: expected a string")
    for field in ("safeToBlock", "useRegexSearch"):
        if field in rule and type(rule[field]) is not bool:
            raise RuleError(f"{label}.{field}: expected a boolean")
    if "upstream" in rule:
        upstream = rule["upstream"]
        if (not isinstance(upstream, dict) or set(upstream) != {"exodus"}
                or type(upstream["exodus"]) is not int or upstream["exodus"] <= 0):
            raise RuleError(f"{label}: upstream must be {{exodus: <positive integer>}}")
    i18n = rule.get("i18n")
    if not isinstance(i18n, dict) or "en" not in i18n:
        raise RuleError(f"{label}: i18n.en is required")
    for lang, text in i18n.items():
        if lang not in LANGUAGES or not isinstance(text, dict):
            raise RuleError(f"{label}: invalid i18n language: {lang}")
        if set(text) - set(TEXT_FIELDS) or any(type(v) is not str for v in text.values()):
            raise RuleError(f"{label}: invalid {lang} text fields")


def load_sources(root=ROOT):
    paths = sorted((Path(root) / "src/rules").glob("*.yaml"))
    if not paths:
        raise RuleError("no rule sources found in src/rules")
    result = []
    seen = {}
    for path in paths:
        rule = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        check_source(rule, path.name)
        if rule["id"] in seen:
            raise RuleError(f"duplicate rule id {rule['id']}: {seen[rule['id']]} and {path.name}")
        seen[rule["id"]] = path.name
        result.append((path, rule))
    return sorted(result, key=lambda pair: pair[1]["id"])


def render_rule(rule, lang, trackers):
    tracker_id = rule.get("upstream", {}).get("exodus")
    tracker = trackers.get(tracker_id, {})
    en = rule["i18n"]["en"]
    localized = rule["i18n"].get(lang, {})
    result = {"id": rule["id"]}
    for field in TEXT_FIELDS:
        if field in localized:
            result[field] = localized[field]
        elif field in en:
            result[field] = en[field]
        elif field in ("name", "description") and field in tracker:
            # This is the English value; other locales fall back to it.
            result[field] = tracker[field]
    for field in ("iconUrl", "website", "contributors",
                  "safeToBlock", "useRegexSearch"):
        if field in rule and field not in result:
            result[field] = rule[field]
    keywords = merge_keywords(
        tracker.get("code_signature", ""), rule["keywords"], rule.get("excludeKeywords", [])
    )
    if keywords:
        result["searchKeyword"] = keywords
    network = merge_signatures(
        tracker.get("network_signature", ""), rule.get("networkSignature", []),
        rule.get("excludeNetworkSignatures", []),
    )
    if network or "networkSignature" in rule:
        result["networkSignature"] = network
    # An explicit allowlist is the only route to the APK/download JSON schema.
    return {key: result[key] for key in OUTPUT_TYPES if key in result}


def render_all(sources, trackers):
    return {
        lang: [render_rule(rule, lang, trackers) for _, rule in sources]
        for lang in LANGUAGES
    }


def check_rules(sources, trackers):
    warnings = []
    for path, rule in sources:
        en = render_rule(rule, "en", trackers)
        if not en.get("name", "").strip():
            raise RuleError(f"{path.name}: every rule must have an English name")
        if not en.get("searchKeyword"):
            warnings.append(f"id {rule['id']} {en['name']}: empty searchKeyword (retained)")
        upstream_id = rule.get("upstream", {}).get("exodus")
        if upstream_id is not None and upstream_id not in trackers:
            # Retain local data if Exodus later removes a tracker; never delete an app id.
            warnings.append(f"id {rule['id']}: Exodus {upstream_id} missing from snapshot; using local data")
        for lang in LANGUAGES:
            rendered = render_rule(rule, lang, trackers)
            for field, value in rendered.items():
                if type(value) is not OUTPUT_TYPES[field]:
                    raise RuleError(f"{path.name}: {field} has an invalid published type")
                if isinstance(value, list):
                    _strings(value, f"{path.name}.{field}")
            if rendered.get("useRegexSearch"):
                for pattern in rendered.get("searchKeyword", []) + rendered.get("networkSignature", []):
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        raise RuleError(f"{path.name}: invalid {lang} regex {pattern!r}: {exc}") from exc
    return warnings


def prepared(root=ROOT):
    load_ignored(root)
    sources = load_sources(root)
    trackers = load_snapshot(root)
    warnings = check_rules(sources, trackers)
    return sources, trackers, render_all(sources, trackers), warnings


def stale_outputs(root, rendered):
    return [f"rules/{lang}/general.json" for lang, data in rendered.items()
            if not (Path(root) / f"rules/{lang}/general.json").is_file()
            or (Path(root) / f"rules/{lang}/general.json").read_bytes() != json_text(data).encode("utf-8")]
