#!/usr/bin/env python3
"""Preserve the authored Cats and Dogs circuit and make its cached wiki local."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil

from modern_stack_regressions import Case, Server, REPO, require
from migrate_cecn_chapter2 import OfflineArticle, INVENTORY

SHA256 = '6578de031f4d909cf0d5fd5adaecb219c2bc2d89b27a59957a6724520f5fa60f'
SOURCE = 'https://www.ida.liu.se/~729G83/labs/bio/lab_files/chapter_3/cats_and_dogs.proj'
ARTICLE = 'https://grey.colorado.edu/CompCogNeuro/index.php/CCNBook/Sims/Networks/Cats_and_Dogs'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=REPO/'demo/LegacyModels/cecn/chapter_3')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--binary', type=Path, default=REPO/'tools/run-emergent')
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    for field in ['source','destination','output','binary']: setattr(args,field,getattr(args,field).resolve())
    raw = args.source.read_bytes(); require(hashlib.sha256(raw).hexdigest()==SHA256,'source hash mismatch')
    source = raw.decode(); require('license=GPLv2;' in source,'project license missing')
    cached = json.loads(re.search(r'html_text=("(?:\\.|[^"\\])*");',source).group(1),strict=False)
    require('creativecommons.org/licenses/by-sa/3.0/' in cached,'wiki license missing')
    article = OfflineArticle(); article.feed(cached)
    require(article.parts and article.depth==0,'cached article extraction failed')
    body = ''.join(article.parts)
    require(not re.search(r'<(?:img|script|link)\b',body,re.I),'article contains external assets')
    html = '''<html><head><meta charset="utf-8"><style>body{font:16px sans-serif;line-height:1.45;padding:14px;color:#17212b;background:white}table{max-width:100%}a{color:#1659a0}.provenance{background:#edf4fa;padding:10px}</style></head><body>
<div class="provenance"><b>Cats and Dogs — associative memory and constraint satisfaction</b><p>Use the native ControlPanel to Init and Run. The default input is Morris. In StdInputData, select the red arrow and click input units to change the cue. Turn off the old cue before selecting a new name or species. Step Cycle shows settling; CycleHarmonyData plots how well the constraints agree.</p><p>This is the author-maintained Emergent 8.5 tutorial. Its network, fixed weights and native programs are unchanged. The cached author article below is available offline.</p></div>'''
    html += body + '<hr><p>Randall C. O’Reilly / CCNLab, Regents of the University of Colorado. <a href="'+escape(ARTICLE,quote=True)+'">Original CCNBook article</a>. Article and this offline formatting adaptation: <a rel="license" href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0 Unported</a>. Wiki navigation and external assets were omitted. Project: GPLv2, as declared in its metadata.</p></body></html>'
    args.output.mkdir(parents=True,exist_ok=False);args.destination.mkdir(parents=True,exist_ok=True)
    target=args.destination/'cats_and_dogs.proj';document=args.destination/'cats_and_dogs.html'
    require(not target.exists() and not document.exists(),'refusing to overwrite migration output')
    document.write_text(html)
    case=Case(args,'original');case.fixture=case.directory/'cats_and_dogs.proj';shutil.copy2(args.source,case.fixture)
    with Server(case) as server:
        before=server.console(' '.join(INVENTORY.splitlines()),'CORPUS_COMPLETE')
        server.console('String cats_html; cats_html.LoadFromFile('+json.dumps(str(document))+'); taDoc* cats_doc=.projects[0].docs[0]; cats_doc.wiki=""; cats_doc.url="local"; cats_doc.text=cats_html; cats_doc.UpdateAfterEdit(); .projects[0].SaveCopy('+json.dumps(str(target))+'); cout << "CATS_SAVED" << endl;','CATS_SAVED')
    reopened=Case(args,'reopened');reopened.fixture=target
    with Server(reopened) as server:after=server.console(' '.join(INVENTORY.splitlines()),'CORPUS_COMPLETE')
    listing=lambda s:s[s.index('\nCORPUS_NETWORKS '):s.rindex('\nCORPUS_COMPLETE')]
    require(listing(before)==listing(after),'network or native program listing changed')
    record={'name':'cats_and_dogs','source_url':SOURCE,'source_sha256':SHA256,'source_format':source.splitlines()[0],
            'project_file':target.name,'project_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'offline_html':document.name,'offline_html_sha256':hashlib.sha256(document.read_bytes()).hexdigest(),
            'cached_original_html_sha256':hashlib.sha256(cached.encode()).hexdigest(),'author':'Randall C. O’Reilly',
            'license':'GPLv2 project; CC BY-SA 3.0 wiki article','article_url':ARTICLE,
            'migration':'Ordinary Load/SaveCopy; cached documentation made local. Network, weights, data, parameters and native programs retained. No external weights required.',
            'native_listing_preserved':True,'checks':case.checks+reopened.checks}
    (args.destination/'provenance.json').write_text(json.dumps({'models':[record]},indent=2)+'\n')
    (args.output/'report.json').write_text(json.dumps({'status':'PASS','model':record},indent=2)+'\n')
    print('PASS',target)


if __name__=='__main__':main()
