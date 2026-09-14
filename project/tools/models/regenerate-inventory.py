#!/usr/bin/env python3
"""Verify and regenerate native model metadata from pinned original source bytes.

No project, CSS program, plugin or downloaded executable is ever executed.
Network acquisition is opt-in with --fetch; existing verified cache blobs work offline.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive_member(data, name):
    stream = io.BytesIO(data)
    if zipfile.is_zipfile(stream):
        with zipfile.ZipFile(stream) as archive:
            return archive.read(name)
    stream.seek(0)
    with tarfile.open(fileobj=stream, mode='r:*') as archive:
        member = archive.getmember(name)
        if not member.isfile():
            raise ValueError('Required archive member is not a regular file: ' + name)
        return archive.extractfile(member).read()


def metadata(data):
    decoded = gzip.decompress(data) if data.startswith(b'\x1f\x8b') else data
    text = decoded.decode('utf-8', errors='replace')
    header = text.splitlines()[0] if text.splitlines() else ''
    root = re.search(r'^([A-Za-z_][A-Za-z_0-9]*)\s+\.?projects(?:\[|\s)', text[:1000], re.M)
    native = decoded.lstrip().startswith(b'// ta_Dump File') and bool(root) and root.group(1).endswith('Project')
    if not native:
        raise ValueError('Bytes are not a native Project ta_Dump; no execution attempted')
    version = re.search(r'ta_Dump File v([\d.]+)(?: -- code v([\d.]+))?(?: rev(\d+))?', header)
    blocks = re.findall(r'(?m)^\s*license\s*\{[^}]*\}', text)
    return {'stored_sha256':digest(data), 'stored_bytes':len(data),
            'decoded_sha256':digest(decoded), 'decoded_bytes':len(decoded),
            'format_header':header, 'dump_version':version.group(1) if version else None,
            'code_version':version.group(2) if version else None,
            'code_revision':version.group(3) if version else None,
            'project_class':root.group(1),
            'embedded_license_identifiers':sorted(set(re.findall(r'\blicense=([A-Za-z_0-9]+);','\n'.join(blocks))))}


class Reader:
    def __init__(self, args):
        self.args = args
        self.git = {}
        for mapping in args.git_checkout:
            repository, directory = mapping.rsplit('=',1)
            self.git[repository.rstrip('/')] = Path(directory).resolve()
        (args.cache/'blobs').mkdir(parents=True,exist_ok=True)
        (args.cache/'archives').mkdir(parents=True,exist_ok=True)

    def source_bytes(self, source):
        if source['kind'] == 'url':
            cached = self.args.cache/'archives'/source['sha256']
            if cached.is_file():
                data = cached.read_bytes()
            elif self.args.fetch:
                url = source['url']
                if not url.startswith(('https://','http://')):
                    raise ValueError('Only public HTTP(S) source acquisition is supported')
                print('Fetching',url,flush=True)
                with urllib.request.urlopen(url,timeout=60) as response:
                    data = response.read()
                if digest(data) != source['sha256']:
                    raise ValueError('Source URL checksum mismatch: '+url)
                cached.write_bytes(data)
            else:
                raise FileNotFoundError('Source archive absent from cache; use --fetch: '+source['url'])
            if digest(data) != source['sha256']:
                raise ValueError('Cached source archive checksum mismatch')
        elif source['kind'] == 'git':
            repository = source['repository'].rstrip('/')
            checkout = self.git.get(repository,self.args.cache/'git'/digest(repository.encode())[:20])
            if not checkout.exists():
                if not self.args.fetch:
                    raise FileNotFoundError('Pinned Git source absent; use --git-checkout or --fetch: '+repository)
                checkout.parent.mkdir(parents=True,exist_ok=True)
                subprocess.run(['git','init','--bare','--quiet',str(checkout)],check=True)
            object_name=source['revision']+':'+source['path']
            result=subprocess.run(['git','-C',str(checkout),'show',object_name],capture_output=True)
            if result.returncode and self.args.fetch:
                subprocess.run(['git','-C',str(checkout),'fetch','--quiet','--depth=1',repository,source['revision']],check=True)
                result=subprocess.run(['git','-C',str(checkout),'show',object_name],capture_output=True)
            if result.returncode:
                raise ValueError('Pinned Git object unavailable: '+repository+' '+object_name)
            data=result.stdout
        else:
            raise ValueError('Unsupported source locator: '+source['kind'])
        for member in source.get('archive_members',[]):
            data=archive_member(data,member)
        return data

    def file_bytes(self, record):
        cached=self.args.cache/'blobs'/record['sha256']
        data=cached.read_bytes() if cached.is_file() else self.source_bytes(record['source'])
        if len(data)!=record['bytes'] or digest(data)!=record['sha256']:
            raise ValueError('Pinned file bytes differ: '+record['id'])
        if not cached.exists():cached.write_bytes(data)
        return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,
                        default=Path(__file__).resolve().parents[2]/'demo'/'ModelCatalog')
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scope',choices=('selected','all-native'),default='selected')
    parser.add_argument('--with-companions',action='store_true')
    parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--git-checkout',action='append',default=[],metavar='REPOSITORY=PATH')
    args=parser.parse_args()
    sources=json.loads((args.catalog/'sources.json').read_text())
    selection=json.loads((args.catalog/'selection.json').read_text())
    if args.scope=='all-native':
        model_ids={mid for mid,m in sources['native_models'].items() if m['native_project'] and m['content_complete']}
    else:
        model_ids=set()
        for selected in selection['selections'].values():
            if not (selected['selection_status'].startswith('SELECTED_') or selected['selection_status']=='CURRENT_NATIVE_APPLICATION_UTILITY'):
                continue
            iid=selected['selected_implementation']
            if iid.startswith('native:'):model_ids.add(iid.removeprefix('native:'))
            model_ids.update(selected.get('required_current_configuration_variant_ids',[]))
    assert model_ids and model_ids <= sources['native_models'].keys()
    reader=Reader(args)
    regenerated={}
    for mid in sorted(model_ids):
        original=sources['native_models'][mid]
        assert original['native_project'] and original['content_complete'],mid
        data=reader.file_bytes(sources['files'][mid])
        actual=metadata(data)
        for key,value in actual.items():
            expected=original['license']['embedded_identifiers'] if key=='embedded_license_identifiers' else original[key]
            if value!=expected:raise ValueError('Regenerated metadata differs: '+mid+' '+key)
        regenerated[mid]=actual
    associated=set()
    if args.with_companions:
        for mid in model_ids:
            associated.update(sources['native_models'][mid].get('same_directory_companion_file_ids',[]))
            associated.update(sources['native_models'][mid]['license'].get('notice_file_ids',[]))
        for fid in sorted(associated):reader.file_bytes(sources['files'][fid])
    result={'schema_version':1,'status':'SOURCE_BYTES_AND_METADATA_VERIFIED',
            'scope':'No native model, CSS script, plugin, downloaded binary or numerical simulation was executed. This is not a runtime/scientific acceptance report.',
            'selection_manifest_sha256':digest((args.catalog/'selection.json').read_bytes()),
            'sources_manifest_sha256':digest((args.catalog/'sources.json').read_bytes()),
            'model_occurrences':len(regenerated),'associated_files_verified':len(associated),
            'models':regenerated}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],len(regenerated),'native occurrences;',len(associated),'associated files')


if __name__=='__main__':
    main()
