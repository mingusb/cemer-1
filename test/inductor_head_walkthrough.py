#!/usr/bin/env python3
"""Click the actual tutorial controls on a 1600x1000 X11 reference desktop.

Coordinates correspond to the generated project's saved layout; screenshots
are retained for visual review. Semantic assertions use the application's
server, while all task invocations and parameter edits use real GUI input.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

from inductor_head_gui_regression import GuiCase, GuiServer, capture_screenshot
from modern_stack_regressions import REPO, require, runtime_diagnostics


class Walkthrough(GuiServer):
    buttons = {'Generate': (542, 710), 'Show': (602, 710),
               'Run': (648, 710), 'Step': (691, 710), 'Evaluate': (747, 710)}

    interactive = False

    def project_window(self):
        return self.xdotool('search', '--all', '--onlyvisible', '--pid', self.process.pid,
                            '--name', 'InductorHead').splitlines()[0]

    def click(self, name, x, y):
        self.transcript.write(json.dumps({'gui_click': name, 'x': x, 'y': y}) + '\n')
        self.transcript.flush()
        self.xdotool('windowactivate', '--sync', self.project_window())
        self.xdotool('mousemove', x, y, 'click', 1)

    def screenshot(self, name):
        capture_screenshot(self.case.directory / (name + '.png'))

    def edit(self, name, row, value):
        self.click('edit ' + name, 508, (254 if self.interactive else 198) + 23 * row)
        self.xdotool('key', '--clearmodifiers', 'Home', 'shift+End', 'BackSpace')
        self.xdotool('type', '--clearmodifiers', '--delay', 10, str(value))
        self.xdotool('key', '--clearmodifiers', 'Tab')

    def apply(self):
        self.click('Apply', 745, 718 if self.interactive else 743)

    def checkbox(self, name, y, value):
        self.click(name, 488, y)
        self.apply()
        deadline = time.monotonic() + self.case.args.timeout
        while time.monotonic() < deadline:
            actual = self.variable('RunCircuit', name)
            if actual == value:
                self.case.equal(name + '_applied', actual, value)
                return
            time.sleep(0.05)
        raise TimeoutError(name + ' checkbox edit did not apply')

    def task(self, name):
        self.call('CollectConsoleOutput', enable=True)
        self.call('ClearConsoleOutput')
        x, y = self.buttons[name]
        self.click(name, x, 684 if self.interactive else y)
        deadline = time.monotonic() + self.case.args.timeout
        prefix = 'INDUCTOR_EVALUATION ' if name == 'Evaluate' else 'INDUCTOR '
        while time.monotonic() < deadline:
            output = self.call('GetConsoleOutput') or ''
            require(not runtime_diagnostics(output), 'task emitted a runtime diagnostic: ' + output)
            if re.search(r'(?:^|\n)' + prefix, output):
                require(int(self.call('GetRunState')) == 0, 'task did not finish')
                (self.case.directory / (name + '-button.log')).write_text(output)
                self.case.checks.append({'check': name + '_actual_button', 'actual': 'completed', 'expected': 'completed'})
                self.interactive = True
                return
            time.sleep(0.05)
        raise TimeoutError(name + ' button did not produce its result')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=REPO / 'build/bin/emergent')
    parser.add_argument('--project', type=Path, default=REPO / 'demo/InductorHead/InductorHead.proj')
    parser.add_argument('--output', type=Path, default=REPO / 'artifacts/inductor-walkthrough')
    parser.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    display = os.environ.get('DISPLAY', '')
    if not display or display.rsplit(':', 1)[-1] in {'0', '0.0'}:
        parser.error('Run GUI tests on a dedicated Xvfb display, e.g. DISPLAY=:93.')
    args.binary = args.binary.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    geometry = subprocess.check_output(['xdotool', 'getdisplaygeometry'], text=True).strip()
    require(geometry == '1600 1000', 'walkthrough requires a 1600x1000 X11 desktop')
    report = {'status': 'PASS', 'cases': []}
    saved = None
    try:
        for reopened in (False, True):
            case = GuiCase(args, 'reopened' if reopened else 'controls')
            case.fixture = case.directory / 'InductorHead.proj'
            shutil.copy2(saved if reopened else args.project, case.fixture)
            original_command = case.command
            case.command = lambda *extra, **kwargs: original_command(*extra, '-i', '-s', REPO / 'demo/InductorHead/open.css', **kwargs)
            report['cases'].append({'name': case.directory.name, 'checks': case.checks})
            with Walkthrough(case) as server:
                server.console('taMisc::ConsoleOutput("GUI_READY " + String(6*7));', 'GUI_READY 42')
                server.screenshot('01-startup')
                if reopened:
                    case.equal('saved_cursor_reopened', server.variable('RunCircuit', 'cursor'), 1)
                    case.equal('saved_prediction_reopened', server.variable('RunCircuit', 'prediction'), 6)
                    server.console('taMisc::ConsoleOutput("GUI_REOPEN_NATIVE " + String(.projects[0].networks["InductionCircuit"].layers["Next_Token_Prediction"].GetUnitIdx(6)->act > 0.99));', 'GUI_REOPEN_NATIVE true')
                    server.screenshot('02-reopened-live')
                    report['cases'][-1]['status'] = 'PASS'
                    continue
                server.task('Show')
                server.screenshot('02-show')
                server.edit('sequence_length', 0, 15)
                server.edit('vocabulary_size', 1, 10)
                server.edit('seed', 2, 2718)
                server.edit('temperature', 3, 0.2)
                server.apply()
                server.screenshot('02b-edited')
                for name, expected in [('sequence_length', 15), ('vocabulary_size', 10), ('seed', 2718), ('temperature', 0.2)]:
                    case.equal('edited_' + name, server.variable('RunCircuit', name), expected)
                server.task('Generate')
                case.equal('generated_cursor', server.variable('RunCircuit', 'cursor'), 14)
                case.equal('generated_prediction', server.variable('RunCircuit', 'prediction'), server.variable('RunCircuit', 'target'))
                server.console('taMisc::ConsoleOutput("GUI_RESIZED " + String(.projects[0].data["Sequence"].rows) + " " + String(.projects[0].networks["InductionCircuit"].layers["Token_Embeddings"].n_units_built));', 'GUI_RESIZED 15 150')
                server.screenshot('03-parameters-generated')
                clean_tokens = [server.cell('Sequence', row, 'token') for row in range(15)]
                server.edit('noise', 4, 0.5)
                server.apply()
                server.task('Generate')
                noisy_tokens = [server.cell('Sequence', row, 'token') for row in range(15)]
                case.equal('noise_preserves_first_exemplar', noisy_tokens[:7], clean_tokens[:7])
                case.equal('noise_preserves_final_query', noisy_tokens[-1], clean_tokens[-1])
                require(noisy_tokens[7:14] != clean_tokens[7:14], 'noise did not introduce an intermediate distractor')
                server.screenshot('03b-distractors')
                server.edit('noise', 4, 0.0)
                server.apply()
                server.task('Generate')
                server.checkbox('ablate_previous', 391, True)
                server.task('Run')
                require(server.variable('RunCircuit', 'confidence') < 0.5, 'previous-head ablation retained a sharp attention match')
                server.screenshot('04-previous-ablation')
                server.checkbox('ablate_previous', 391, False)
                server.checkbox('ablate_induction', 414, True)
                server.task('Run')
                case.equal('induction_ablation_prediction', server.variable('RunCircuit', 'prediction'), -1)
                case.equal('induction_ablation_confidence', server.variable('RunCircuit', 'confidence'), 0.0)
                server.screenshot('05-induction-ablation')
                server.checkbox('ablate_induction', 414, False)
                server.task('Evaluate')
                case.equal('held_out_intact_accuracy', server.variable('RunCircuit', 'accuracy'), 1.0)
                server.console('taMisc::ConsoleOutput("GUI_EVALUATION_ROWS " + String(.projects[0].data["Experiments"].rows));', 'GUI_EVALUATION_ROWS 192')
                server.screenshot('06-evaluation')
                server.click('ProjectDoc tab', 709, 125)
                time.sleep(2)
                server.screenshot('07-embedded-wiki')
                server.xdotool('mousemove', 777, 598, 'click', '--repeat', 5, '--delay', 100, 5)
                time.sleep(0.5)
                server.screenshot('08-wiki-scrolled')
                server.click('Laboratory tab', 578, 125)
                server.edit('sequence_length', 0, 13)
                server.edit('vocabulary_size', 1, 8)
                server.edit('seed', 2, 1729)
                server.edit('temperature', 3, 0.1)
                server.apply()
                server.task('Generate')
                server.task('Step')
                case.equal('step_cursor', server.variable('RunCircuit', 'cursor'), 1)
                # At position1 no earlier source has the current prefix. The
                # only causal value is token6; target2 is still in the future.
                case.equal('step_target', server.variable('RunCircuit', 'target'), 2)
                case.equal('early_query_causal_prediction', server.variable('RunCircuit', 'prediction'), 6)
                server.screenshot('09-stepped')
                before = case.fixture.stat().st_mtime_ns
                server.xdotool('windowactivate', '--sync', server.project_window())
                server.xdotool('key', '--clearmodifiers', 'ctrl+s')
                deadline = time.monotonic() + args.timeout
                while case.fixture.stat().st_mtime_ns == before and time.monotonic() < deadline:
                    time.sleep(0.1)
                require(case.fixture.stat().st_mtime_ns != before, 'GUI Save shortcut did not save the project')
                saved = case.fixture
                case.checks.append({'check': 'gui_save', 'actual': 'file updated', 'expected': 'file updated'})
            report['cases'][-1]['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], args.output / 'report.json')
    return report['status'] != 'PASS'


if __name__ == '__main__':
    sys.exit(main())
