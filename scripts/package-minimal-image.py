"""Replace only the binary in an exported original runtime; emit a Docker archive.

Usage: python scripts/package-minimal-image.py ARTIFACT_DIRECTORY
Inputs: original-rootfs.tar, original-image-config.json, nfs-subdir-external-provisioner.
No archive members are extracted to the host filesystem.
"""
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
binary = root / 'nfs-subdir-external-provisioner'
assert binary.read_bytes()[:4] == b'\x7fELF'
config = json.loads((root / 'original-image-config.json').read_text(encoding='utf-8-sig'))
assert config['os'] == 'linux' and config['architecture'] == 'amd64'
target = config['config']['Entrypoint'][0].lstrip('/')
layer_path = root / 'minimal-layer.tar'
replaced = 0
unchanged = 0
with tarfile.open(root / 'original-rootfs.tar') as original, tarfile.open(layer_path, 'w') as output:
    for member in original:
        source = original.extractfile(member) if member.isfile() else None
        if member.name.lstrip('./') == target:
            assert member.isfile()
            member.size = binary.stat().st_size
            with binary.open('rb') as stream:
                output.addfile(member, stream)
            replaced += 1
        else:
            output.addfile(member, source)
            unchanged += 1
        if source is not None:
            source.close()
assert replaced == 1, 'Expected exactly one original provisioner binary'
layer_hash = hashlib.sha256(layer_path.read_bytes()).hexdigest()
config['rootfs'] = {'type': 'layers', 'diff_ids': ['sha256:' + layer_hash]}
config['history'] = [{'created_by': 'Replace v4.0.2 binary with Go 1.26.9 / x/net v0.17.0; flatten original runtime'}]
config['config'].setdefault('Labels', {})['org.opencontainers.image.version'] = '4.0.2-kev.2'
config_bytes = json.dumps(config, separators=(',', ':')).encode()
config_name = hashlib.sha256(config_bytes).hexdigest() + '.json'
tag = 'localhost/nfs-subdir-external-provisioner:4.0.2-kev.2'
manifest = [{'Config': config_name, 'RepoTags': [tag], 'Layers': ['layer.tar']}]
archive_path = root / 'nfs-subdir-external-provisioner-4.0.2-kev.2.tar'
with tarfile.open(archive_path, 'w') as archive:
    for name, data in [(config_name, config_bytes), ('manifest.json', json.dumps(manifest).encode())]:
        entry = tarfile.TarInfo(name)
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
    archive.add(layer_path, arcname='layer.tar')
print(json.dumps({'image': tag, 'layers': 1, 'unchanged_runtime_entries': unchanged,
                  'replaced_binary_entries': replaced,
                  'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest()}, indent=2))
