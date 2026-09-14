#!/usr/bin/env python3
"""Replay Necker Cube's authored controls on a dedicated 1600x1000 X11 desktop."""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys, time, traceback
from pathlib import Path
from cecn_chapter2_gui import ChapterGUI
from inductor_head_gui_regression import GuiCase
from modern_stack_regressions import REPO, require
from cecn_necker_regressions import setup, collect, coherent, flat

class NeckerGUI(ChapterGUI):

    def window(self):
        return self.xdotool('search', '--all', '--onlyvisible', '--pid', self.process.pid, '--name', 'projects.*necker_cube').splitlines()[0]

    def click(self, name, x, y):
        geometry = subprocess.check_output(['xwininfo', '-id', self.window()], text=True)
        top = int(re.search('Absolute upper-left Y:\\s+(-?\\d+)', geometry).group(1))
        height = int(re.search('Height:\\s+(\\d+)', geometry).group(1))
        if y == 733:
            y = top + height - 101
        elif y == 766:
            y = top + height - 68
        else:
            y = top + y - 37
        super().click(name, x, y)

    def edit(self, name, x, y, value):
        self.click('Edit ' + name, x, y)
        self.xdotool('key', '--clearmodifiers', 'Home', 'shift+End', 'BackSpace')
        self.xdotool('type', '--clearmodifiers', '--delay', 20, str(value))
        self.xdotool('key', '--clearmodifiers', 'Tab')

    def seed(self):
        self.console('ns.Init(1); taMisc::ConsoleOutput("NECKER_GUI_SEED");', 'NECKER_GUI_SEED')

    def initialize(self, initial=False):
        self.seed()
        self.click('ControlPanel tab', 610, 131)
        self.click('Native Init', 529 if initial else 452, 733)
        self.done()

    def run_native(self):
        self.click('Native Run', 491, 733)
        self.done()

    def screenshot(self, name):
        time.sleep(0.5)
        super().screenshot(name)

def exercise(case, server):
    time.sleep(2)
    server.screenshot('01-offline-wiki-version-note')
    setup(server)
    server.click('ControlPanel tab', 610, 131)
    server.click('Native Position Units', 445, 733)
    server.done()
    server.console('bool nc_position_ok=true; for(int ni=0;ni<16;ni++) { int k=ni%8; if(nclay->GetUnitIdx(ni)->disp_pos_x != (ni<8?0:5)+2*(k%2)+(k%4)/2 || nclay->GetUnitIdx(ni)->disp_pos_y != k/2) nc_position_ok=false; } taMisc::ConsoleOutput("NECKER_POSITIONS " + String(nc_position_ok));', 'NECKER_POSITIONS true')
    case.equal('native_PositionUnits_places_all_vertices', True, True)
    server.initialize(initial=True)
    server.click('Native Step Cycle', 680, 733)
    server.wait_state(3)
    case.equal('native_StepCycle_pauses', int(server.call('GetRunState')), 3)
    case.equal('native_StepCycle_records_cycle1', server.values('CycleOutputData', 'cycle'), [1])
    server.screenshot('02-step-cycle')
    server.run_native()
    base = collect(case, server, 'gui_default', 100, False)
    coherent(case, base)
    server.screenshot('03-coherent-cube-and-harmony')
    server.edit('noise variance', 528, 243, 0)
    server.click('Apply noise setting', 703, 766)
    server.console('taMisc::ConsoleOutput("NECKER_GUI_NOISE_ZERO " + String(ncspec->noise.var==0));', 'NECKER_GUI_NOISE_ZERO true')
    case.equal('actual_noise_field_zero', True, True)
    server.initialize()
    server.run_native()
    zero = collect(case, server, 'gui_zero_noise', 100, False)
    case.equal('actual_zero_noise_control_preserves_symmetry', all((max(row) == min(row) for row in zero['activations'])), True)
    server.screenshot('04-noise-zero-symmetry')
    server.edit('noise variance', 528, 243, 0.01)
    server.edit('quarter cycles', 340, 266, 250)
    server.click('KNa adaptation checkbox', 324, 289)
    server.click('Apply adaptation settings', 703, 766)
    server.console('taMisc::ConsoleOutput("NECKER_GUI_ADAPT_PARAMETERS " + String(ncspec->noise.var==0.01 && ncnet->times.quarter==250 && ncspec->kna_adapt.on));', 'NECKER_GUI_ADAPT_PARAMETERS true')
    case.equal('actual_adaptation_parameter_controls', True, True)
    server.initialize()
    server.click('Run adaptation experiment', 491, 733)
    captured = set()
    deadline = time.monotonic() + case.args.timeout
    while time.monotonic() < deadline:
        state = int(server.call('GetRunState'))
        rows = server.values('CycleOutputData', 'act')
        if rows:
            values = flat(rows[-1])
            delta = sum(values[:8]) / 8 - sum(values[8:]) / 8
            winner = 1 if delta > 0.5 else -1 if delta < -0.5 else 0
            if winner and winner not in captured:
                server.screenshot('05-adaptation-left' if winner == 1 else '06-adaptation-right')
                captured.add(winner)
        if state == 0:
            break
        time.sleep(0.1)
    else:
        raise TimeoutError('native adaptation run did not complete')
    adapt = collect(case, server, 'gui_adaptation', 1000, True)
    case.equal('actual_adaptation_switches_repeatedly', adapt['switches'] >= 2, True)
    case.equal('actual_adaptation_visits_both_interpretations', {state for state in adapt['states'] if state}, set([-1, 1]))
    case.equal('both_interpretations_captured_during_native_run', captured, set([-1, 1]))
    server.screenshot('07-adaptation-complete-harmony')
    server.console('taMisc::ConsoleOutput("NECKER_GUI_CSS42 " + String(6*7));', 'NECKER_GUI_CSS42 42')
    case.equal('actual_typed_CSS42', 42, 42)
    server.screenshot('08-visible-console-prompt')
    server.click('ProjectDocs tab', 445, 131)
    server.xdotool('mousemove', 708, 695, 'click', '--repeat', 8, '--delay', 80, 5)
    time.sleep(0.7)
    server.screenshot('09-offline-author-figure')
    server.click('ControlPanel tab', 610, 131)
    server.save()
    return adapt

def reopen(case, server, expected):
    time.sleep(2)
    setup(server)
    server.console('taMisc::ConsoleOutput("NECKER_GUI_SAVED_PARAMETERS " + String(ncspec->noise.var==0.01 && ncnet->times.quarter==250 && ncspec->kna_adapt.on));', 'NECKER_GUI_SAVED_PARAMETERS true')
    case.equal('saved_native_parameter_controls', True, True)
    server.initialize(initial=True)
    server.run_native()
    actual = collect(case, server, 'gui_adaptation_reopened', 1000, True)
    case.equal('saved_reopened_activation_trace_reproduced', actual['activations'], expected['activations'])
    case.equal('saved_reopened_harmony_reproduced', actual['harmony'], expected['harmony'])
    server.screenshot('10-reopened-adaptation-model')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    p.add_argument('--fixture', type=Path, default=REPO / 'demo/LegacyModels/cecn/chapter_3/necker_cube.proj')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--timeout', type=float, default=360)
    args = p.parse_args()
    display = os.environ.get('DISPLAY', '')
    if not display or display.rsplit(':', 1)[-1] in {'0', '0.0'}:
        p.error('Use an isolated Xvfb display such as :93; never the user desktop.')
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    require(subprocess.check_output(['xdotool', 'getdisplaygeometry'], text=True).strip() == '1600 1000', 'requires1600x1000 isolated X11 desktop')
    for name in ['binary', 'fixture', 'output']:
        setattr(args, name, getattr(args, name).resolve())
    args.output.mkdir(parents=True, exist_ok=False)
    prefix = Path(os.environ.get('EMERGENT_PREFIX_DIR', str(REPO / 'install')))
    hashes = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in [prefix / 'bin/emergent', prefix / 'lib/libtemt.so', prefix / 'lib/libemergentlib.so']}
    source_hash = hashlib.sha256(args.fixture.read_bytes()).hexdigest()
    report = {'status': 'PASS', 'installed_sha256': hashes, 'fixture_sha256': source_hash, 'display': display, 'cases': []}
    try:
        case = GuiCase(args, 'necker_cube')
        case.fixture = case.directory / 'necker_cube.proj'
        shutil.copy2(args.fixture, case.fixture)
        case.original_digest = source_hash
        report['cases'].append({'name': 'native-controls', 'checks': case.checks})
        with NeckerGUI(case) as server:
            expected = exercise(case, server)
        reopened = GuiCase(args, 'reopened')
        reopened.fixture = reopened.directory / 'necker_cube.proj'
        shutil.copy2(case.fixture, reopened.fixture)
        report['cases'].append({'name': 'saved-project-reopened', 'checks': reopened.checks})
        with NeckerGUI(reopened) as server:
            reopen(reopened, server, expected)
        for item in [case, reopened]:
            item.equal('css_diagnostics', [line for line in (item.directory / 'emergent.log').read_text(errors='replace').splitlines() if re.search('^Warning:|^Error:', line)], [])
    except Exception as error:
        report.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    for path, digest in hashes.items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'installed library changed during GUI test')
    require(hashlib.sha256(args.fixture.read_bytes()).hexdigest() == source_hash, 'original fixture changed during GUI test')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2, default=lambda x: sorted(x)) + '\n')
    print(report['status'], args.output / 'report.json', flush=True)
    return report['status'] != 'PASS'
if __name__ == '__main__':
    sys.exit(main())
