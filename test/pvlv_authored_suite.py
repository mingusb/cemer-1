#!/usr/bin/env python3
"""Run all unchanged, authored PVLV learning tests; this can take over an hour."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import time
import traceback

from modern_stack_regressions import Case, Server, REPO, require, runtime_diagnostics
from pvlv_publication_regression import FIXTURE, installed_evidence

SUCCESS = '***WARNING: PVLV test suit PASSED!'


def audit(specification, output):
    columns = {column['name']: column['values'] for column in specification['columns']}
    rows = [dict(zip(columns, values)) for values in zip(*columns.values())]
    require(len(rows) == 206, 'authored TestSpec must contain 206 rows')
    require(Counter(row['should_pass'] for row in rows) == {1: 156, 0: 50}, 'mandatory/exploratory criteria changed')
    configs = list(dict.fromkeys(row['config_id'] for row in rows))
    actual_configs = re.findall(r'^============ (\S+) ============$', output, re.M)
    require(actual_configs == configs, 'configuration coverage/order differs from authored TestSpec')
    require('Could not find paramset' not in output and 'No data generated!' not in output, 'configuration or measurement was skipped')
    results = re.findall(r'^\s+[-*]+ (.+?): (PASSED|FAILED)\s+(\w+)_mean: ([^ ]+) ([<>=]) ([-.0-9]+)\s*$', output, re.M)
    require(len(results) == len(rows), 'each authored row must produce exactly one numeric result')
    audit_rows = []
    for index, (row, result) in enumerate(zip(rows, results)):
        name, status, measure, value, operator, criterion = result
        expected_measure, expected_operator, expected_value = row['test'].split()
        require(name.strip() == row['Name'].strip(), 'test name/order mismatch at row ' + str(index))
        require((measure, operator) == (expected_measure, expected_operator), 'measurement/operator mismatch at row ' + str(index))
        require(float(criterion) == float(expected_value), 'authored threshold changed at row ' + str(index))
        actual, threshold = float(value), float(expected_value)
        require(math.isfinite(actual), 'nonfinite measurement at row ' + str(index))
        margin = row['test_margin'] if row['test_margin'] >= 0.01 else 0.15
        passed = actual < threshold if operator == '<' else actual > threshold if operator == '>' else threshold - margin <= actual <= threshold + margin
        require((status == 'PASSED') == passed, 'native comparison disagrees with reported measurement at row ' + str(index))
        audit_rows.append({'row': index, **row, 'actual': actual, 'reported': status, 'mandatory': bool(row['should_pass'])})
    failures = [row for row in audit_rows if row['mandatory'] and row['reported'] != 'PASSED']
    return {'configuration_count': len(configs), 'criterion_count': len(rows), 'mandatory_count': 156,
            'exploratory_count': 50, 'mandatory_failures': failures, 'rows': audit_rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    parser.add_argument('--project', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=7200)
    args = parser.parse_args()
    args.binary = args.binary.resolve(); args.project = args.project.resolve(); args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    original = args.project.read_bytes()
    provenance = json.loads(FIXTURE.with_name('provenance.json').read_text())
    require(hashlib.sha256(original).hexdigest() == provenance['sha256'], 'model differs from pinned author source')
    case = Case(args, 'all-configurations', allow_diagnostics=True)
    case.fixture = case.directory / args.project.name
    shutil.copy2(args.project, case.fixture)
    report = {'status': 'RUNNING', 'scope': 'All 206 unmodified authored TestSpec criteria, across 25 configurations. This is not an independent reproduction of every paper figure.',
              'project_sha256': provenance['sha256'], 'installed_files_before': installed_evidence(), 'checks': case.checks}
    started = time.monotonic()
    report_path = args.output / 'report.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    try:
        with Server(case) as server:
            specification = server.call('GetData', table='.projects[0].programs.gp[0][1].objs[0]')
            (args.output / 'TestSpec.json').write_text(json.dumps(specification, indent=2) + '\n')
            server.set_variable('AutomatedTestProg', 'select_config_id', 'all_autotst')
            # The pinned author's dynamic enum assigns all_autotst value 0.
            case.equal('all_authored_configurations_selected', server.variable('AutomatedTestProg', 'select_config_id'), 0)
            server.set_variable('AutomatedTestProg', 'full_output', True)
            output = server.run('AutomatedTestProg')
            global_result = server.variable('AutomatedTestProg', 'passed_test_global')
            loop_index = server.variable('AutomatedTestProg', 'data_loop_index')
        diagnostics = [line.strip() for line in runtime_diagnostics((case.directory / 'emergent.log').read_text(errors='replace'))]
        # The original model intentionally reports success through Warning().
        # Require that exact notification and preserve every other diagnostic.
        for check in case.checks:
            if check['check'] == 'server.runtime_diagnostics':
                check['expected'] = [SUCCESS]
                check['actual'] = [line.strip() for line in check['actual']]
        results = audit(specification, output)
        (args.output / 'criteria-audit.json').write_text(json.dumps(results, indent=2) + '\n')
        case.equal('exact_authored_success_notification_only', diagnostics, [SUCCESS])
        case.equal('all_mandatory_authored_criteria_pass', results['mandatory_failures'], [])
        case.equal('authored_global_result', global_result, True)
        case.equal('all_test_rows_visited', loop_index, 206)
        case.equal('source_project_unchanged', args.project.read_bytes() == original, True)
        report.update(status='PASS', configuration_count=25, mandatory_criterion_count=156, exploratory_criterion_count=50)
    except Exception as error:
        report.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    report['installed_files'] = installed_evidence()
    report['runtime_unchanged'] = report['installed_files_before'] == report['installed_files']
    if not report['runtime_unchanged']:
        report.update(status='FAIL', error='installed runtime changed during regression')
    report['seconds'] = round(time.monotonic() - started, 3)
    report['check_count'] = len(case.checks)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], report_path)
    return report['status'] != 'PASS'


if __name__ == '__main__':
    sys.exit(main())
