#!/usr/bin/env python3
"""Import JSON through the visible CSS console, edit a bool and save/reopen.

Run on an isolated 1600x1000 X11 display with a window manager. Screenshots
remain for LLM visual review; the script verifies actual data independently.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback

from inductor_head_gui_regression import GuiCase, GuiServer, capture_screenshot
from modern_stack_regressions import REPO, require


PAYLOAD = {"columns": [
    {"name": "activation", "type": "float", "matrix": True, "dimensions": [4],
     "values": [[0, .25, .5, 1], [1, .5, .25, 0], [-1, 0, 1, 2]]},
    {"name": "mask", "type": "bool", "matrix": False,
     "values": [False, True, False]},
    {"name": "condition", "type": "String", "matrix": False,
     "values": ["baseline", "learned", "reset"]},
]}


def project_window(server):
    return server.xdotool('search', '--all', '--onlyvisible', '--pid',
                          server.process.pid, '--name', 'InductorHead').splitlines()[0]


def click_mask(server, expected):
    server.xdotool('windowactivate', '--sync', project_window(server))
    server.xdotool('mousemove', 473, 181, 'click', 1)
    server.transcript.write(json.dumps({'gui_click': 'row0 mask checkbox',
                                       'x': 473, 'y': 181, 'expected': expected}) + '\n')
    server.transcript.flush()
    deadline = time.monotonic() + server.case.args.timeout
    while time.monotonic() < deadline:
        value = server.cell('Experiments', 0, 'mask')
        if value is expected:
            server.case.equal('checkbox_edit_' + str(expected), value, expected)
            # Separate two edits: rapid clicks invoke the table's double-click
            # cell-view action instead of toggling the checkbox twice.
            time.sleep(.6)
            return
        time.sleep(.05)
    raise TimeoutError('Actual boolean checkbox edit did not reach the JSON API')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    display = os.environ.get('DISPLAY', '')
    if not display or display.rsplit(':', 1)[-1] in {'0', '0.0'}:
        parser.error('Use a dedicated Xvfb display, e.g. DISPLAY=:94.')
    geometry = subprocess.check_output(['xdotool', 'getdisplaygeometry'], text=True).strip()
    require(geometry == '1600 1000', 'This walkthrough requires a 1600x1000 display')
    args.binary = args.binary.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'RUNNING', 'display': display, 'cases': []}
    saved = None
    try:
        for reopening in (False, True):
            case = GuiCase(args, 'reopened' if reopening else 'import')
            report['cases'].append({'name': case.directory.name, 'checks': case.checks})
            case.fixture = case.directory / 'InductorHead.proj'
            shutil.copy2(saved if reopening else REPO / 'demo/InductorHead/InductorHead.proj',
                         case.fixture)
            original_command = case.command
            case.command = lambda *extra, **kwargs: original_command(
                *extra, '-i', '-s', REPO / 'demo/InductorHead/open.css', **kwargs)
            with GuiServer(case) as server:
                server.console('taMisc::ConsoleOutput("JSON_GUI_READY " + String(6*7));',
                               'JSON_GUI_READY 42')
                if not reopening:
                    text = json.dumps(json.dumps(PAYLOAD, separators=(',', ':')))
                    server.console(
                        'DataTable* json_gui = .projects[0].data["Experiments"]; '
                        'json_gui->Reset(); json_gui->ImportDataJSONString(' + text + '); '
                        'json_gui->EditPanel(); '
                        'taMisc::ConsoleOutput("JSON_IMPORTED " + String(json_gui->rows));',
                        'JSON_IMPORTED 3')
                    output = server.call('GetConsoleOutput') or ''
                    require(not re.search(r'(?:Error|Warning):', output),
                            'JSON import emitted a runtime diagnostic')
                    time.sleep(.5)
                    click_mask(server, True)
                    click_mask(server, False)
                    server.xdotool('mousemove', 473, 181, 'click', '--repeat', 2,
                                   '--delay', 100, 1)
                    time.sleep(.6)
                    viewer = subprocess.run(
                        ['xdotool', 'search', '--all', '--onlyvisible', '--pid',
                         str(server.process.pid), '--name', 'cell view'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    case.equal('checkbox_double_click_opens_no_cell_view', viewer.returncode, 1)
                    case.equal('checkbox_double_click_updates_value',
                               server.cell('Experiments', 0, 'mask'), True)
                    click_mask(server, False)
                else:
                    server.console('.projects[0].data["Experiments"].EditPanel(); '
                                   'taMisc::ConsoleOutput("JSON_REOPENED");', 'JSON_REOPENED')
                data = server.call('GetData', table='Experiments', row_from=0, rows=3)
                actual = {column['name']: column['values'] for column in data['columns']}
                expected = {column['name']: column['values'] for column in PAYLOAD['columns']}
                case.equal('json_values_preserved', actual, expected)
                case.equal('mask_is_json_boolean', [type(v) is bool for v in actual['mask']],
                           [True] * 3)
                time.sleep(.7)
                capture_screenshot(case.directory / 'table-and-console.png')
                if not reopening:
                    before = case.fixture.stat().st_mtime_ns
                    server.xdotool('windowactivate', '--sync', project_window(server))
                    server.xdotool('key', '--clearmodifiers', 'ctrl+s')
                    deadline = time.monotonic() + args.timeout
                    while case.fixture.stat().st_mtime_ns == before and time.monotonic() < deadline:
                        time.sleep(.1)
                    require(case.fixture.stat().st_mtime_ns != before,
                            'Actual GUI Save shortcut did not update the project')
                    saved = case.fixture
                    case.checks.append({'check': 'actual_gui_save', 'actual': 'PASS',
                                        'expected': 'PASS'})
            report['cases'][-1]['status'] = 'PASS'
        report['status'] = 'AWAITING_VISION_REVIEW'
    except Exception as error:
        report.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'])
    return 1 if report['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
