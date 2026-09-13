#!/usr/bin/env python3
"""Install the pinned Qt 6.12 Beta4 SDK described by the adjacent URL/hash files."""
import concurrent.futures
import hashlib
import pathlib
import subprocess
import sys
import urllib.request

here = pathlib.Path(__file__).resolve().parent
prefix = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else here / 'Qt'
archives = here / 'downloads'
expected = dict(line.split('  ', 1)[::-1] for line in (archives / 'SHA256SUMS').read_text().splitlines())
urls = (archives / 'qt-archives.urls').read_text().splitlines()

def fetch(url):
    # Installer URLs prepend the exact package version to the archive basename.
    filename = url.rsplit('/', 1)[1].removeprefix('6.12.0-0-202609010620')
    archive = archives / filename
    if not archive.exists():
        urllib.request.urlretrieve(url, archive)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != expected[filename]:
        raise RuntimeError(f'Checksum mismatch: {filename}')
    return archive

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
    downloaded = list(executor.map(fetch, urls))
prefix.mkdir(parents=True, exist_ok=True)
for archive in downloaded:
    result = subprocess.run(['7z', 'x', '-y', f'-o{prefix}', str(archive)], capture_output=True, text=True)
    errors = [line for line in result.stderr.splitlines() if line.startswith('ERROR:')]
    if result.returncode and not errors:
        raise RuntimeError(result.stdout + result.stderr)
    for error in errors:
        if not error.startswith('ERROR: Dangerous link via another link was ignored : lib/'):
            raise RuntimeError(error)
        relative_path, target = error.split(' : ')[1:]
        link = prefix / relative_path
        link.unlink(missing_ok=True)
        link.symlink_to(target)
for library in prefix.glob('libicu*'):
    library.replace(prefix / 'lib' / library.name)
for directory in ['bin', 'libexec']:
    (prefix / directory / 'qt.conf').write_text('[Paths]\nPrefix=..\n')
print(f'Qt SDK installed in {prefix}')
