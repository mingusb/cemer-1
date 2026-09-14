#!/usr/bin/env python3
"""Migrate pinned, author-maintained CECN chapter 2 projects without model edits.

Supply the downloaded course chapter_2 directory with --source. Existing output
projects are never overwritten. This migration does not create test baselines.
"""
import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urljoin

from modern_stack_regressions import Case, Server, REPO, require, runtime_diagnostics

PINNED = {
    'neuron': '58f4983ceee6ea48af4082df69d926320f8e7e1c9eaa9c22326add7d7b52f9f5',
    'detector': 'f79b4c995effeffe1cd6278ae2fb0c5b89411d8afeca099f71ca4bb39cd52e7c',
}
SOURCE = 'https://www.ida.liu.se/~729G83/labs/bio/lab_files/chapter_2/'
WIKI = 'https://grey.colorado.edu/CompCogNeuro/index.php/CCNBook/Sims/Neuron/'


class OfflineArticle(HTMLParser):
    """Keep the cached article, its text and inline styling; omit wiki chrome."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if not self.depth:
            if tag == 'div' and attrs.get('id') == 'mw-content-text': self.depth = 1
            return
        if tag == 'div': self.depth += 1
        if tag == 'img':
            # The sole scientific image in these two articles is this equation.
            # Preserve its mathematical content offline using ordinary HTML.
            alt = attrs.get('alt', '')
            if 'g_e(t)' in alt:
                self.parts.append('<span class="equation">g<sub>e</sub>(t) = (1/n) ∑<sub>i</sub> x<sub>i</sub> w<sub>i</sub></span>')
            else:
                self.parts.append(escape(alt))
            return
        if tag == 'a' and attrs.get('href', '').startswith('/'):
            attrs['href'] = urljoin('https://grey.colorado.edu/', attrs['href'])
        self.parts.append('<' + tag + ''.join(' ' + k + ('="' + escape(v, quote=True) + '"' if v is not None else '') for k, v in attrs.items()) + '>')

    def handle_endtag(self, tag):
        if not self.depth: return
        if tag == 'div':
            self.depth -= 1
            if not self.depth: return
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        if self.depth: self.parts.append(data)

    def handle_entityref(self, name):
        if self.depth: self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        if self.depth: self.parts.append('&#' + name + ';')


def offline_document(source, name):
    match = re.search(r'html_text=("(?:\\.|[^"\\])*");', source)
    require(match is not None, 'cached author documentation missing')
    cached = json.loads(match.group(1), strict=False)
    require('creativecommons.org/licenses/by-sa/3.0/' in cached, 'cached wiki license missing')
    parser = OfflineArticle(); parser.feed(cached)
    require(parser.parts and parser.depth == 0, 'cached article extraction failed')
    title = 'Neuron' if name == 'neuron' else 'Detector'
    text = '<html><head><meta charset="utf-8"><style>body{font:16px sans-serif;line-height:1.45;padding:14px;color:#17212b;background:#fff}table{max-width:100%}a{color:#1659a0}.equation{font-size:1.2em} .provenance{background:#edf4fa;padding:10px}</style></head><body>'
    instructions = ('Open <b>ControlPanel</b>, click <b>Defaults</b>, then <b>Init</b> and <b>Run</b>. '
                    '<b>CycleOutputData</b> shows spikes and membrane voltage. <b>Step Cycle</b> advances one cycle; '
                    '<b>Stop</b> pauses. This author-maintained version uses sodium-activated potassium-channel adaptation.'
                    if name == 'neuron' else
                    'Open <b>ControlPanel</b>, click <b>Init</b>, then <b>Run</b>. '
                    '<b>TrialOutputData</b> shows responses to all ten digits. <b>Step Trial</b> advances one digit. '
                    'Change leak conductance <b>g_bar.l</b> from 2 to 1.8 to explore broader responses.')
    text += '<div class="provenance"><b>' + title + ' laboratory</b><br>' + instructions + '<br>The author tutorial below is available offline. <a href="' + WIKI + title + '">Original article</a>.</div>'
    text += ''.join(parser.parts)
    text += '<hr><p>Computational Cognitive Neuroscience Wiki / CCNLab, Regents of the University of Colorado. Article licensed under <a rel="license" href="https://creativecommons.org/licenses/by-sa/3.0/">Creative Commons Attribution-ShareAlike 3.0 Unported</a>. This offline formatting adaptation retains that license. The accompanying project declares GPLv2; see the project license metadata.</p></body></html>'
    return text, hashlib.sha256(cached.encode()).hexdigest()


INVENTORY = '''
cout << "CORPUS_NETWORKS " << .projects[0].networks.size << endl;
for(int ci=0;ci<.projects[0].networks.size;ci++) { Network* cn=.projects[0].networks[ci]; cout << "CORPUS_NETWORK " << cn->name << " " << cn->layers.leaves << endl; for(int cj=0;cj<cn->layers.leaves;cj++) { Layer* cl=cn->layers.Leaf(cj); cout << "CORPUS_LAYER " << cl->name << " " << cl->un_geom.x << " " << cl->un_geom.y << " " << cl->projections.size << endl; } }
for(int ci=0;ci<.projects[0].programs.leaves;ci++) { Program* cp=.projects[0].programs.Leaf(ci); cout << "CORPUS_PROGRAM " << cp->name << endl; cout << cp->ProgramListing() << endl; }
cout << "CORPUS_COMPLETE" << endl;
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=REPO / 'demo/LegacyModels/cecn/chapter_2')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    args.source = args.source.resolve(); args.destination = args.destination.resolve()
    args.binary = args.binary.resolve(); args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False); args.destination.mkdir(parents=True, exist_ok=True)
    records = []
    for name, digest in PINNED.items():
        source = args.source / (name + '.proj'); original = source.read_bytes()
        require(hashlib.sha256(original).hexdigest() == digest, 'source does not match pinned author project: ' + name)
        destination = args.destination / (name + '.proj')
        require(not destination.exists(), 'refusing to overwrite ' + str(destination))
        html, cached_digest = offline_document(original.decode(), name)
        html_path = args.destination / (name + '.html'); require(not html_path.exists(), 'refusing to overwrite document')
        html_path.write_text(html)
        case = Case(args, name); case.fixture = case.directory / (name + '.proj'); shutil.copy2(source, case.fixture)
        with Server(case) as server:
            before = server.console(' '.join(INVENTORY.splitlines()), 'CORPUS_COMPLETE')
            script = 'String corpus_html; corpus_html.LoadFromFile(' + json.dumps(str(html_path)) + '); taDoc* corpus_doc=.projects[0].docs[0]; corpus_doc.wiki=""; corpus_doc.url="local"; corpus_doc.text=corpus_html; corpus_doc.UpdateAfterEdit(); .projects[0].SaveCopy(' + json.dumps(str(destination)) + '); cout << "CORPUS_SAVED" << endl;'
            server.console(script, 'CORPUS_SAVED')
        reload_case = Case(args, name + '-reopened'); reload_case.fixture = destination
        with Server(reload_case) as server:
            after = server.console(' '.join(INVENTORY.splitlines()), 'CORPUS_COMPLETE')
        # Console output also contains readline echoes. Compare the actual
        # listing segment, starting at the first standalone inventory marker.
        listing = lambda text: text[text.index('\nCORPUS_NETWORKS '):text.rindex('\nCORPUS_COMPLETE')]
        require(listing(before) == listing(after), 'network or native program listing changed')
        records.append({'name':name, 'source_url':SOURCE+name+'.proj', 'source_sha256':digest,
                        'source_format':original.decode().splitlines()[0], 'project_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
                        'project_file':name+'.proj', 'offline_html':name+'.html', 'offline_html_sha256':hashlib.sha256(html.encode()).hexdigest(),
                        'cached_original_html_sha256':cached_digest, 'license':'GPLv2 project; CC BY-SA 3.0 wiki article',
                        'migration':'Ordinary Load/SaveCopy; documentation converted to local cached article; network, parameters, data and native programs unchanged.',
                        'native_listing_preserved':True, 'diagnostics':runtime_diagnostics((case.directory/'emergent.log').read_text(errors='replace')),
                        'reopen_diagnostics':runtime_diagnostics((reload_case.directory/'emergent.log').read_text(errors='replace')), 'evidence':str(case.directory)})
        print('Migrated', name, flush=True)
    (args.destination/'provenance.json').write_text(json.dumps({'models':records},indent=2)+'\n')


if __name__ == '__main__': main()
