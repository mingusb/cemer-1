#!/usr/bin/env python3
"""Build the pinned ncurses/Readline sources with audited compiler diagnostics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent

def run(command, cwd, env, log):
    with log.open('w') as stream:
        stream.write(shlex.join(map(str, command)) + '\n')
        stream.flush()
        subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def archive_readline_backups(prefix):
    # ldconfig treats libreadline.so.8.3.old as a SONAME candidate and may
    # redirect the live link to that older binary. Retain backups out of its
    # scan directory, then point the public links at this installation.
    library_dir = prefix / 'lib'
    backup_dir = library_dir / '.readline-build-backups'
    for stem in ('libreadline', 'libhistory'):
        for backup in library_dir.glob(stem + '.*.old'):
            backup_dir.mkdir(exist_ok=True)
            digest = hashlib.sha256(backup.read_bytes()).hexdigest()[:12]
            backup.rename(backup_dir / (backup.name + '.' + digest))
        installed = library_dir / (stem + '.so.8.3')
        if installed.exists():
            link = library_dir / (stem + '.so.8')
            if link.is_symlink():
                link.unlink()
            link.symlink_to(installed.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='+', choices=('ncurses', 'readline'))
    parser.add_argument('--root', type=Path, default=Path.home() / 'toolchains')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--build-suffix', default='')
    args = parser.parse_args()
    prefix = args.root / 'deps'
    env = os.environ.copy()
    env.update(CC='/usr/lib/llvm-24/bin/clang', CXX='/usr/lib/llvm-24/bin/clang++',
               CFLAGS='-O2', CXXFLAGS='-O2 -stdlib=libc++',
               LDFLAGS=f'-fuse-ld=lld -L{prefix}/lib -Wl,-rpath,{prefix}/lib',
               CPPFLAGS=f'-I{prefix}/include',
               PKG_CONFIG_PATH=f'{prefix}/lib/pkgconfig',
               LD_LIBRARY_PATH=f'{prefix}/lib:' + env.get('LD_LIBRARY_PATH', ''))
    manifest = json.loads((HERE / 'dependencies.json').read_text())['dependencies']
    for name in args.names:
        pin = next(item for item in manifest if item['name'] == name)
        source = args.root / 'sources' / name
        if not (source / '.git').exists():
            subprocess.run(['git', 'clone', '--filter=blob:none', pin['source_url'], source], check=True)
            subprocess.run(['git', 'checkout', '--detach', pin['revision']], cwd=source, check=True)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        if revision != pin['revision']:
            raise RuntimeError(f'{name}: checked-out source differs from pin')
        patch = HERE / 'patches' / (name + '.patch')
        if patch.exists():
            if subprocess.run(['git', 'apply', '--check', patch], cwd=source,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                subprocess.run(['git', 'apply', patch], cwd=source, check=True)
            else:
                subprocess.run(['git', 'apply', '--reverse', '--check', patch], cwd=source, check=True)
        build = args.root / 'build-deps' / (name + args.build_suffix)
        build.mkdir(parents=True, exist_ok=True)
        options = (['--with-shared', '--with-termlib', '--enable-widec',
                    f'--with-pkg-config-libdir={prefix}/lib/pkgconfig', '--enable-pc-files',
                    '--with-versioned-syms'] if name == 'ncurses' else
                   ['--enable-shared', '--with-curses=-ltinfow'])
        commands = [[str(source / 'configure'), f'--prefix={prefix}', *options],
                    ['make', f'-j{args.jobs}', 'CFLAGS=-O2 -Wall -Werror',
                     'CXXFLAGS=-O2 -stdlib=libc++ -Wall -Wextra -Werror -Woverloaded-virtual',
                     *(['SHLIB_LIBS=-Wl,-z,defs'] if name == 'readline' else [])],
                    ['make', 'install']]
        for stage, command in zip(('configure', 'build', 'install'), commands):
            print(name, stage, flush=True)
            run(command, build, env, build / (stage + '.log'))
            if stage == 'build':
                text = (build / 'build.log').read_text()
                if re.search(r'\b(?:warning|error):|(?<!\S)(?:-w|-Wno-[^\s]+|-Qunused-arguments)(?!\S)', text):
                    raise RuntimeError(f'{name}: build diagnostics or warning suppression; inspect raw log')
        if name == 'readline':
            archive_readline_backups(prefix)
        record = {'name': name, 'revision': revision, 'version': pin['version'],
                  'source_url': pin['source_url'], 'source_path': str(source),
                  'build_path': str(build), 'install_prefix': str(prefix),
                  'commands': commands, 'environment': {k: env[k] for k in
                    ('CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS')},
                  'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest() if patch.exists() else None,
                  'log_sha256': {stage: hashlib.sha256((build / (stage + '.log')).read_bytes()).hexdigest()
                                 for stage in ('configure', 'build', 'install')}}
        (build / 'recipe.json').write_text(json.dumps(record, indent=2) + '\n')

if __name__ == '__main__':
    main()
