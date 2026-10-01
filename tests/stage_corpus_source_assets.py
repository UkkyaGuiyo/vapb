"""Stage exact package assets for the independent source Oracle, never export.

CLI: --context JSON --package-lock JSON --project NEW_PRIVATE_PROJECT
     --output-lock JSON --output-context JSON
Requires package_hashes in the existing input lock. Copies every source asset,
including scripts, with exact meta bytes. No Blender/Unity process is launched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from unitypackage_blender_importer.export.raw_assets import RawAssetRepository
from unitypackage_blender_importer.export.staging import StagedUnityAsset, StagingTree


class StageError(ValueError):
    pass


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage(context, package_lock, project, output_lock, output_context):
    project, output_lock, output_context = map(lambda path: Path(path).resolve(),
                                              (project, output_lock, output_context))
    repo = Path(__file__).resolve().parents[1]
    if project.exists() or project.is_relative_to(repo):
        raise StageError('FRESH_PRIVATE_PROJECT_REQUIRED')
    if output_lock.exists() or output_context.exists() or not output_lock.is_relative_to(project.parent) or not output_context.is_relative_to(project.parent):
        raise StageError('FRESH_PRIVATE_OUTPUT_REQUIRED')
    paths = context.get('package_paths', [])
    expected = package_lock.get('package_hashes', {})
    if not paths or not context.get('prefab_guids') or not isinstance(expected, dict):
        raise StageError('INPUT_LOCK_REQUIRED')
    tree, packages = StagingTree(), []
    for raw_path in paths:
        source = Path(raw_path).resolve()
        if project.is_relative_to(source.parent):
            raise StageError('PROJECT_IN_INPUT_DIRECTORY')
        wanted = expected.get(raw_path)
        if not isinstance(wanted, str) or not re.fullmatch(r'[0-9a-f]{64}', wanted):
            raise StageError('SOURCE_SHA_REQUIRED')
        if digest(source) != wanted:
            raise StageError('SOURCE_SHA_MISMATCH')
        try:
            assets = RawAssetRepository(source).read_all()
            for asset in assets:
                tree.add(StagedUnityAsset(asset.guid, asset.pathname, asset.asset_bytes,
                                         asset.meta_bytes, asset.preview_bytes))
        except ValueError as error:
            raise StageError('PACKAGE_CONTENT_OR_IDENTITY_CONFLICT') from error
        packages.append(dict(path=str(source), sha256=wanted))
    selected = context['prefab_guids']
    known = {entry.guid for entry in tree.entries if entry.pathname.lower().endswith('.prefab')}
    if len(set(selected)) != len(selected) or not set(selected) <= known:
        raise StageError('REQUESTED_PREFAB_NOT_IN_EXACT_INPUT')
    payloads, folders = {}, []
    assets_root = project / 'Assets'
    for entry in tree.entries:
        if not entry.pathname.startswith('Assets/'):
            raise StageError('ASSETS_SCOPE_REQUIRED')
        folder = bool(re.search(rb'(?m)^folderAsset:\s*yes\s*$', entry.meta_bytes))
        if entry.pathname == 'Assets/CorpusProbe' or entry.pathname.startswith('Assets/CorpusProbe/'):
            raise StageError('PROBE_PATH_CONFLICT')
        if folder:
            folders.append(entry.pathname)
        fields = [(entry.pathname + '.meta', entry.meta_bytes)]
        if not folder:
            fields.append((entry.pathname, entry.asset_bytes))
        for unity_path, payload in fields:
            target = (project / unity_path).resolve()
            if not target.is_relative_to(assets_root):
                raise StageError('ASSET_PATH_ESCAPE')
            key = str(target).casefold()
            if key in payloads and payloads[key][1] != payload:
                raise StageError('DESTINATION_FIELD_CONFLICT')
            payloads[key] = (unity_path, payload)
    # Complete input validation precedes every copy. The project is expendable
    # on filesystem failure; original archives remain read-only throughout.
    project.mkdir(parents=True)
    for unity_path in folders:
        (project / unity_path).mkdir(parents=True, exist_ok=True)
    files = []
    for unity_path, payload in sorted(payloads.values()):
        target = project / unity_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(payload)
        sha = hashlib.sha256(payload).hexdigest()
        if digest(target) != sha:
            raise StageError('STAGED_FILE_CHANGED')
        files.append(dict(unity_path=unity_path, sha256=sha))
    if any(digest(Path(row['path'])) != row['sha256'] for row in packages):
        raise StageError('SOURCE_CHANGED')
    editor = assets_root / 'CorpusProbe' / 'Editor'
    if editor.exists():
        raise StageError('PROBE_PATH_CONFLICT')
    shutil.copytree(repo / 'tests' / 'unity_corpus_probe' / 'Editor', editor)
    (project / 'Packages').mkdir()
    shutil.copy2(repo / 'tests' / 'unity_alias_oracle' / 'Packages' / 'manifest.json',
                 project / 'Packages' / 'manifest.json')
    (project / 'ProjectSettings').mkdir()
    (project / 'ProjectSettings' / 'ProjectVersion.txt').write_text(
        'm_EditorVersion: 2022.3.22f1\n', encoding='utf-8')
    lock = dict(schema='vapb-source-asset-staging-1', project_path=str(project),
                source_packages=packages, files=files, prefab_guids=selected,
                exact_asset_meta_bytes=True, source_original_package_sha_preserved=True)
    output_lock.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    runtime = dict(context, capture_mode='EXACT_ASSET_EXTRACTION_CAPTURE',
                   staging_lock_path=str(output_lock), native_import_status='NOT_PASS')
    output_context.write_text(json.dumps(runtime, indent=2), encoding='utf-8')
    return dict(assets=len(tree.entries), files=len(files), packages=len(packages))


def main():
    parser = argparse.ArgumentParser()
    for name in ('context', 'package-lock', 'project', 'output-lock', 'output-context'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        counts = stage(json.loads(Path(args.context).read_text(encoding='utf-8-sig')),
            json.loads(Path(args.package_lock).read_text(encoding='utf-8-sig')),
            args.project, args.output_lock, args.output_context)
        print('SOURCE_STAGE verdict=PASS reason=NONE assets={} files={} packages={}'.format(
            counts['assets'], counts['files'], counts['packages']))
    except StageError as error:
        print('SOURCE_STAGE verdict=BLOCKED reason=INPUT_INVALID detail=' + str(error))
        return 1
    except Exception:
        print('SOURCE_STAGE verdict=UNPROVEN reason=HARNESS_ERROR')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
