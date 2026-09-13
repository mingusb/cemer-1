#!/usr/bin/env python3
"""Check actual GUI startup, native circuit state and visible CSS console input.

Run inside an X11 desktop (or Xvfb with a window manager). Uses the real Qt
windows and xdotool keyboard input. Root GUI walkthrough also checks the task
buttons and rendered appearance with screenshots.
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

from modern_stack_regressions import Case, Server, REPO, require, runtime_diagnostics, stop

class GuiCase(Case):
    def command(self, *extra, **kwargs):
        result = super().command(*extra, **kwargs)
        result.remove('-nogui')
        # Case records commands before the GUI specialization removes -nogui.
        # Keep the evidence equal to the actual argv passed to Popen.
        command_log = self.directory / 'commands.jsonl'
        commands = command_log.read_text().splitlines()
        commands[-1] = json.dumps(result)
        command_log.write_text('\n'.join(commands) + '\n')
        return result

class GuiServer(Server):
    def xdotool(self, *arguments):
        return subprocess.check_output(['xdotool', *map(str, arguments)], text=True, timeout=10).strip()

    def console(self, code, marker):
        self.call('CollectConsoleOutput', enable=True)
        self.call('ClearConsoleOutput')
        deadline = time.monotonic() + self.case.args.timeout
        window = None
        while time.monotonic() < deadline:
            result = subprocess.run(['xdotool', 'search', '--all', '--onlyvisible', '--pid',
                                     str(self.process.pid), '--name', '^css Console$'],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if result.returncode == 0:
                window = result.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        require(window is not None, 'visible CSS console window was not found')
        self.transcript.write(json.dumps({'gui_console_input': code}) + '\n')
        self.transcript.flush()
        self.xdotool('windowactivate', '--sync', window)
        geometry = self.xdotool('getwindowgeometry', '--shell', window)
        height = int(re.search(r'^HEIGHT=(\d+)$', geometry, re.M).group(1))
        self.xdotool('mousemove', '--window', window, 250, height - 35)
        self.xdotool('click', 1)
        self.xdotool('windowraise', window)
        self.xdotool('windowfocus', '--sync', window)
        focused = self.xdotool('getwindowfocus')
        self.transcript.write(json.dumps({'console_window': window, 'focused_window': focused, 'geometry': geometry}) + '\n')
        self.transcript.flush()
        require(focused == window, 'X11 input focus is not the CSS console')
        self.xdotool('key', '--clearmodifiers', 'ctrl+e')
        self.xdotool('type', '--clearmodifiers', '--delay', '1', code)
        self.xdotool('key', '--clearmodifiers', 'Return')
        while time.monotonic() < deadline:
            output = self.call('GetConsoleOutput') or ''
            if re.search(r'(?:^|\n)' + re.escape(marker) + r'\r?(?:\n|$)', output):
                (self.case.directory / (marker.split()[0] + '.log')).write_text(output)
                require(not runtime_diagnostics(output), 'GUI CSS command emitted a runtime diagnostic')
                return
            time.sleep(0.1)
        raise AssertionError(f'GUI console output marker missing: {marker}')

    def __exit__(self, exception_type, *_):
        try:
            if self.process and exception_type is None:
                self.console('taMisc::ConsoleOutput("GUI_CLEAN_CLOSE");', 'GUI_CLEAN_CLOSE')
                self.xdotool('type', '--clearmodifiers', '--delay', '1', '.projects[0].setDirty(false);')
                self.xdotool('key', '--clearmodifiers', 'Return')
                time.sleep(0.2)
                window = self.xdotool('search', '--all', '--onlyvisible', '--pid', self.process.pid,
                                      '--name', '^css Console$').splitlines()[0]
                self.xdotool('windowactivate', '--sync', window)
                self.xdotool('type', '--clearmodifiers', '--delay', '1', 'exit')
                self.xdotool('key', '--clearmodifiers', 'Return')
                self.case.equal('gui_console_exit', self.process.wait(timeout=30), 0)
                self.log.flush()
                diagnostics = runtime_diagnostics((self.case.directory / 'emergent.log').read_text())
                self.case.equal('gui_runtime_diagnostics', diagnostics, [])
        finally:
            if self.connection:
                self.connection.close()
            if self.process:
                stop(self.process)
                self.process.stdin.close()
            self.log.close()
            self.transcript.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=REPO / 'build/bin/emergent')
    parser.add_argument('--project', type=Path, default=REPO / 'demo/InductorHead/InductorHead.proj')
    parser.add_argument('--output', type=Path, default=REPO / 'artifacts/inductor-gui-regression')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    require(bool(os.environ.get('DISPLAY')), 'DISPLAY must select an existing X11 desktop')
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    args.binary = args.binary.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'PASS', 'cases': []}
    original = args.project.read_text()
    require('STARTUP_RUN_GUI' not in original, 'tutorial must use existing startup APIs only')
    try:
        for enabled in (True, False):
            case = GuiCase(args, 'enabled' if enabled else 'disabled')
            case.fixture = case.directory / 'InductorHead.proj'
            case.fixture.write_text(original)
            entry = {'startup_script_used': enabled, 'checks': case.checks}
            report['cases'].append(entry)
            if enabled:
                bootstrap = REPO / 'demo/InductorHead/open.css'
                original_command = case.command
                case.command = lambda *extra, **kwargs: original_command(*extra, '-i', '-s', bootstrap, **kwargs)
            with GuiServer(case) as server:
                case.equal('saved_default_sequence_length', server.variable('RunCircuit', 'sequence_length'), 13)
                case.equal('saved_default_seed', server.variable('RunCircuit', 'seed'), 1729)
                case.equal('saved_default_prediction', server.variable('RunCircuit', 'prediction'), 6)
                server.console('taMisc::ConsoleOutput("GUI_ARITHMETIC " + String(6*7));', 'GUI_ARITHMETIC 42')
                if enabled:
                    server.console('taMisc::ConsoleOutput("GUI_NATIVE_QUERY " + String(.projects[0].networks["InductionCircuit"].layers["Current_Query"].GetUnitIdx(0)->act));',
                                   'GUI_NATIVE_QUERY 1')
                else:
                    server.console('taMisc::ConsoleOutput("GUI_NOT_STARTED " + String(!.projects[0].networks["InductionCircuit"].CheckBuild(true)));',
                                   'GUI_NOT_STARTED true')
                case.checks.append({'check': 'startup_script_controls_initialization', 'actual': enabled, 'expected': enabled})
                subprocess.run(['import', '-window', 'root', str(case.directory / 'startup.png')], check=True)
                if enabled:
                    server.run('StepToken')
                    case.equal('step_token_cursor', server.variable('RunCircuit', 'cursor'), 1)
                    case.equal('step_token_target', server.variable('RunCircuit', 'target'), 2)
            entry['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], args.output / 'report.json')
    return report['status'] != 'PASS'

if __name__ == '__main__':
    sys.exit(main())
