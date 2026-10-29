# Blocker general rules

Rule data for the Android app Blocker. Old app versions read
`rules/en/general.json` and `rules/zh-CN/general.json` directly from the `main`
branch archive. Keep those paths and their JSON schema compatible.

## Editing and generating rules

Contributors edit `src/` only and should not commit generated files.
`rules/*/general.json` is generated. **Do not edit these files by hand.**
After each merge or push to `main`, CI regenerates `rules/`, `components/`, and
`component-details/` and commits any changes as `github-actions[bot]`. Generated
outputs stay committed on `main` so existing apps can continue to read them.

- `src/rules/<slug>.yaml`: one rule per file, with a permanent app `id`, local
  `keywords`, optional `upstream.exodus`, and translations under `i18n`.
- `upstream/exodus/trackers.json`: trimmed Exodus snapshot, sorted by Exodus id.
  Only id, name, code/network signatures, website, description, and categories
  are retained. App ids and Exodus ids are separate namespaces.
- `scripts/`: migration, sync, conservative linking, build, validation, and tests.
- `src/components/<class path>.yaml`: shared component metadata and translations;
  generates `components/en/` and `components/zh-CN/` (see below).
- `icon/`: existing app assets; this pipeline does not write them.

Use Python 3.10+ and PyYAML (the only third-party dependency):

```sh
python3 -m pip install -r scripts/requirements.txt
python3 scripts/build.py
python3 scripts/build.py --check
python3 scripts/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Builds are offline and deterministic. Rules publish both languages sorted by app
id, with two-space JSON indentation and no new app-visible fields. Missing
optional keys are omitted, never set to null. Local English text wins over
Exodus; missing Chinese text falls back to English. `safeToBlock` and
`sideEffect` are always local. Language-neutral fields use English data in both
outputs; contributors use the ordered union of English names followed by
Chinese-only names. Name, description, sideEffect, and company belong under
`i18n.<lang>`, with Chinese text falling back to English when absent. Company
names retain their original translations; they are never top-level source
metadata. Exodus supplies no company field, so newly synced rules omit it.

Signature merging keeps upstream group order first, then local order. Code
keywords are deduplicated after stripping trailing dots, with the local spelling
preferred: local `com.facebook.ads.` plus upstream `com.facebook.ads` publishes
only `com.facebook.ads.`. An upstream code keyword is also omitted when it
contains a normalized local keyword: the app searches component names by
case-insensitive substring. This removes redundant entries such as
`com.google.android.gms.ads.AdView` when local `com.google.android.gms.ads.`
already covers them. Local keywords are retained. `excludeKeywords` uses the
same normalization.
Network signatures use exact deduplication and exact `excludeNetworkSignatures`;
trailing dots in network signatures remain significant.
Empty search signatures are retained with validator warnings. An explicit
`useRegexSearch: true` requires all published signatures to compile.

## Editing and generating components

`components/en/**/*.json` and `components/zh-CN/**/*.json` are generated.
**Edit `src/components/` and do not commit generated JSON.** One YAML source
represents one component; for example
`src/components/com/google/android/gms/ads/AdActivity.yaml`:

```yaml
recommendToBlock: false
contributor: Mercury
lastUpdateTime: '2023-11-19T16:45:01.937788900Z'
i18n:
  en:
    description: English component description
    disableEffect: Optional English effect
  zh-CN:
    description: 中文组件说明
```

These are the only source fields. `recommendToBlock` and
`i18n.en.description` are required; contributor, lastUpdateTime, disableEffect,
and Chinese text are optional. Empty strings remain explicit text. Quote
lastUpdateTime so YAML keeps the exact ISO instant string and its fractional
digits. Path segments must be Java identifiers; `$` is allowed for nested
classes. `name` comes from the path, and `sdkName` is computed, never stored in
YAML. Version fields are not supported.

The existing build and validation commands handle rules and components
together. Every component publishes both `en` and `zh-CN`, with missing Chinese
text falling back to English separately for description and disableEffect.
This is necessary because the app reads only its selected language directory
and has no English fallback. Both outputs share the English-preferred metadata.
Optional absent fields are omitted, never null. Component JSON uses four-space
indentation, unescaped Unicode, and the existing app keys in order: name,
sdkName, description, disableEffect, contributor, recommendToBlock,
lastUpdateTime. Orphan JSON is removed only under `components/en/`,
`components/zh-CN/`, and `component-details/`; `--check` detects stale, missing,
and orphan files without writing anything.

`component-details/<lang>.json` bundles the same component objects and key order
as the per-file outputs in a JSON array sorted by `name`, with one compact
object per line. The existing per-file paths and formatting remain available
for older apps.

For each language, sdkName is the localized name of a published general rule
whose rendered searchKeyword matches the dotted component name by
case-insensitive literal substring. The longest matching keyword wins; ties
use the lowest rule id. No match omits sdkName. This includes keywords and name
fallbacks from the existing rule pipeline, and does not interpret keywords as
regular expressions for SDK assignment.

`python3 scripts/migrate_components.py` is the one-time migration from the
legacy component JSON. It refuses to overwrite YAML, drops all old sdkName
values, keeps only Chinese text differing from English, and prints counts and
metadata conflicts (English wins, including presence/absence differences).
The original inventory had 863 English components, all with descriptions,
34 Chinese components, and no Chinese-only components. Migration will report
and stop on a Chinese-only component requiring an English description rather
than inventing English text.

## Exodus updates

For initial linking (or to resume after an unavailable network fetch):

```sh
python3 scripts/sync_exodus.py --snapshot-only --summary-file .local/exodus-fetch.md
python3 scripts/link_exodus.py --dry-run
python3 scripts/link_exodus.py --summary-file .local/exodus-links.md
python3 scripts/sync_exodus.py --from-snapshot --summary-file .local/exodus-sync.md
python3 scripts/build.py
python3 scripts/validate.py
```

After linking, `python3 scripts/sync_exodus.py` fetches the API, trims the
snapshot, creates new sources, and writes `.local/exodus-sync-summary.md`.
Then build and validate. Use `--from-snapshot` for offline sync; `--input FILE`
accepts an explicit API-response fixture and is never described as a live fetch.
The snapshot is created only after a successful fetch/validation; a failed
fetch leaves the previous snapshot and sources intact.
The API currently works without a token, as verified by the reviewer supplying
the initial 432-tracker snapshot. Optional `EXODUS_API_TOKEN` support remains:
set it locally or as a repository Actions secret if authentication is needed
later; it is used only by the fetch step. See the
[official Exodus API documentation](https://github.com/Exodus-Privacy/exodus/blob/v1/doc/api.md).

Only unique, reciprocal keyword matches containing an exact match after
stripping trailing dots are linked automatically. Prefix-only or conflicting
matches are listed in `upstream/exodus/link_candidates.md` for review. Linking
never changes app ids or local text/safety. Before creating any unlinked tracker,
sync checks for **any substring overlap in either direction** with every existing
source, including their upstream keywords. This guard
strips leading/trailing dots and compares case-insensitively, so fragments such
as `.amazon.device.ads.`, `.supersonicads.`, and `.jpush.` prevent duplicate
imports. An overlapping tracker is listed under **Needs manual link** in the PR
summary and gets no new source. Automatic linking keeps its stricter criteria.
Only trackers with a nonempty code signature and no such overlap receive a
fresh app id above the maximum source id. Never reuse retired app ids.

`upstream/exodus/ignore.yaml` permanently suppresses automatic linking/imports
with a list of `{id, reason}` entries. It initially excludes Exodus 363 Pangle:
its `com.bytedance` signature covers the whole ByteDance namespace, including
TikTok internals. Keep specific reviewed local Pangolin signatures instead.

New Exodus rules have no `safeToBlock` and are published once the sync PR is
merged, so review new trackers in that PR (add translations, assess safety, or
add the tracker to `ignore.yaml`). Upstream removal never deletes a local rule
or reuses its id; a missing tracker warns and uses available local data.

The weekly/manual workflow fetches, links conservatively, syncs, builds,
validates, and opens or updates a single review PR with new trackers and
signature changes. It needs the repository setting permitting GitHub Actions
to create pull requests. The push/PR workflow runs tests, builds generated
files in the runner checkout, and validates the result, so PRs can contain only
source edits even when their generated files are stale or absent. A separate
workflow regenerates and commits app data on `main` after the merge; the bot
commit lets older apps polling the latest default-branch commit detect the new
data. All workflows pin actions to full version tags.

## Migration and app integration

`scripts/migrate_from_json.py` is a one-time tool and refuses to overwrite
existing YAML. It records collision/content decisions and the original git
revision in `scripts/migration_manifest.json`. `scripts/compare_legacy.py`
compares generated objects against that revision, handling colliding legacy
ids using the audited name/id mapping. It summarizes differences by language
and category; `--details` prints individual field differences. Whole-array
ordering is ignored, but signature order is compared. The migration preserves
Honor's published id 466, keeps Sohu at 465, and moves Teemo/FidZup/Krux to
468/469/470. Both unrelated stray copies at id 467 are removed after retaining
their network/website data under Gigya 168 and AppLovin 101.

Local run evidence and sync simulations belong in ignored
`.local/MIGRATION_REPORT.md`, outside the published repository files.

APK asset packaging should exclude `src/`, `upstream/`, `scripts/`, and
`.github/`; keep the generated rules, components, and icons.

Crowdin configuration is unchanged. Its documented
[parser options](https://support.crowdin.com/project-settings/parser-configuration/)
and [configuration file](https://support.crowdin.com/developer/configuration-file/)
provide selected translatable paths for XML, with no documented equivalent
that both selects nested YAML `i18n.en` text and merges translations back into
sibling `i18n.zh-CN` keys. Pointing Crowdin at whole sources would also expose
metadata and existing translations. The current `%locale_with_underscore%`
path writes `zh_CN`, which the app never reads, and edits to generated JSON
are overwritten by the source build. A future integration should extract just
the English text into temporary YAML (reusing the existing format), import only
translated description/disableEffect into source `i18n.zh-CN`, use the exact
`zh-CN` locale, and rebuild. No extraction files, new format, or configuration
options are introduced by this migration. General-rule text can use the same
approach for name, description, sideEffect, and company.
