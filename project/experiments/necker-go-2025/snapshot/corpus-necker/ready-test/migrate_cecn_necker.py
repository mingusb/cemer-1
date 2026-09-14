#!/usr/bin/env python3
"""Migrate the pinned author's Necker Cube project, preserving native model code."""
import argparse, base64, hashlib, json, re, shutil, sys
from html import escape
from pathlib import Path
from modern_stack_regressions import Case, Server, REPO, require
from migrate_cecn_chapter2 import OfflineArticle, INVENTORY
PIN = '85125e0468938134a54f973172fc1ac6141fcc96f4dfa6dda958940937cd48bc'
FIGURE_PIN = 'e60c589195cb350a748c602b9df8b4d5aa9d35bcf40fcfce10a880d1196be9a6'
SOURCE = 'https://www.ida.liu.se/~729G83/labs/bio/lab_files/chapter_3/'
FIGURE = 'https://raw.githubusercontent.com/CompCogNeuro/sims/619a8bf188722ab0ea68dd73f4d83446dbea0567/ch3/necker_cube/fig_necker_cube.png'
ARTICLE = 'https://grey.colorado.edu/CompCogNeuro/index.php/CCNBook/Sims/Networks/Necker_Cube'

class NeckerArticle(OfflineArticle):

    def __init__(self, figure):
        super().__init__()
        self.figure = figure
        self.images = 0

    def handle_starttag(self, tag, attributes):
        if self.depth and tag == 'img' and ('fig_necker_cube' in dict(attributes).get('src', '')):
            self.parts.append('<img alt="a: ambiguous cube; b and c: its two coherent interpretations" width="300" height="96" src="data:image/png;base64,' + base64.b64encode(self.figure).decode() + '">')
            self.images += 1
            return
        super().handle_starttag(tag, attributes)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--figure', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    p.add_argument('--timeout', type=float, default=90)
    args = p.parse_args()
    for field in ['source', 'figure', 'destination', 'output', 'binary']:
        setattr(args, field, getattr(args, field).resolve())
    raw = args.source.read_bytes()
    figure = args.figure.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PIN, 'source pin mismatch')
    require(hashlib.sha256(figure).hexdigest() == FIGURE_PIN, 'author figure pin mismatch')
    source = raw.decode()
    require('license=GPLv2;' in source, 'missing source license')
    cached = json.loads(re.search('html_text=("(?:\\\\.|[^"\\\\])*");', source).group(1), strict=False)
    require('creativecommons.org/licenses/by-sa/3.0/' in cached, 'missing cached wiki license')
    article = NeckerArticle(figure)
    article.feed(cached)
    require(article.images == 1 and article.depth == 0, 'incomplete cached article/figure')
    html = '<html><head><meta charset="utf-8"><style>body{font:16px sans-serif;line-height:1.45;padding:14px;color:#17212b;background:white}table{max-width:100%}a{color:#1659a0}.provenance{background:#edf4fa;padding:10px}img{max-width:100%}</style></head><body><div class="provenance"><b>Necker Cube — competing interpretations</b><p>Open ControlPanel, use PositionUnits_Run to arrange the two cubes, then Init and Run. Step Cycle shows settling; CycleOutputData plots harmony. Noise variance 0 keeps the alternatives tied; restore 0.01 to break symmetry. To explore switching, enable kna_adapt_on and set quarter_cycles to 250, then Init and Run.</p><p>This is the author\'s maintained 8.5 project, whose changelog explicitly updates adaptation and unit positioning. Its current mechanisms are FFFB pooled inhibition, Gaussian noise added to net input, and sodium-activated potassium-channel adaptation. The cached older article below refers to kWTA, membrane-potential noise and AdEx; those historical mechanisms are not claimed reproduced here. The network, embedded fixed weights and native programs remain unchanged.</p></div>'
    html += ''.join(article.parts) + '<hr><p>Randall C. O’Reilly / CCNLab, Regents of the University of Colorado. <a href="' + escape(ARTICLE, quote=True) + '">Original CCNBook article</a>. Article, figure and this offline formatting adaptation: <a rel="license" href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0 Unported</a>. Figure retained from the authors’ <a href="' + FIGURE + '">pinned simulation repository</a>. Project: GPLv2, as declared in its metadata.</p></body></html>'
    args.output.mkdir(parents=True, exist_ok=False)
    args.destination.mkdir(parents=True, exist_ok=True)
    target = args.destination / 'necker_cube.proj'
    document = args.destination / 'necker_cube.html'
    require(not target.exists() and (not document.exists()), 'refusing to overwrite migration output')
    document.write_text(html)
    case = Case(args, 'original')
    case.fixture = case.directory / args.source.name
    shutil.copy2(args.source, case.fixture)
    with Server(case) as server:
        before = server.console(' '.join(INVENTORY.splitlines()), 'CORPUS_COMPLETE')
        server.console('String necker_html; necker_html.LoadFromFile(' + json.dumps(str(document)) + '); taDoc* necker_doc=.projects[0].docs[0]; necker_doc.wiki=""; necker_doc.url="local"; necker_doc.text=necker_html; necker_doc.UpdateAfterEdit(); .projects[0].SaveCopy(' + json.dumps(str(target)) + '); cout << "NECKER_SAVED" << endl;', 'NECKER_SAVED')
    reopened = Case(args, 'reopened')
    reopened.fixture = target
    with Server(reopened) as server:
        after = server.console(' '.join(INVENTORY.splitlines()), 'CORPUS_COMPLETE')
    listing = lambda text: text[text.index('\nCORPUS_NETWORKS '):text.rindex('\nCORPUS_COMPLETE')]
    require(listing(before) == listing(after), 'native network/program listing changed')
    figure_target = args.destination / 'fig_necker_cube.png'
    shutil.copy2(args.figure, figure_target)
    companions = []
    for name in ['NeckerCubeNet.wts', 'necker_cube_weights.wts', 'necker_cube_img1.iv', 'necker_cube_img2.iv']:
        path = args.source.parent / name
        shutil.copy2(path, args.destination / name)
        companions.append({'file': name, 'source_url': SOURCE + name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'runtime_required': False, 'note': 'Original course companion retained; current project embeds its weights and positions units natively.'})
    record = {'name': 'necker_cube', 'source_url': SOURCE + 'necker_cube.proj', 'source_sha256': PIN, 'source_format': source.splitlines()[0], 'project_file': target.name, 'project_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'offline_html': document.name, 'offline_html_sha256': hashlib.sha256(document.read_bytes()).hexdigest(), 'cached_original_html_sha256': hashlib.sha256(cached.encode()).hexdigest(), 'figure': {'file': figure_target.name, 'source_url': FIGURE, 'sha256': FIGURE_PIN}, 'companions': companions, 'license': 'GPLv2 project; CC BY-SA 3.0 author wiki/figure and offline formatting adaptation', 'article_url': ARTICLE, 'migration': 'Ordinary Load/SaveCopy; cached author article and pinned figure made local. Network, parameters, native programs and embedded weights unchanged.', 'native_listing_preserved': True, 'historical_mechanism_boundary': 'Current authored 8.5 uses FFFB inhibition, net-input noise and KNa adaptation; cached earlier kWTA/membrane-noise/AdEx narrative is retained with an explicit version note.', 'checks': case.checks + reopened.checks}
    (args.destination / 'necker-provenance.json').write_text(json.dumps(record, indent=2) + '\n')
    (args.output / 'report.json').write_text(json.dumps({'status': 'PASS', 'model': record}, indent=2) + '\n')
    print('PASS', target)
if __name__ == '__main__':
    main()
