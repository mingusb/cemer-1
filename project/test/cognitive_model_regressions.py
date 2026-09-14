#!/usr/bin/env python3
"""Run shipped cognitive tutorials with fixed task-level assertions.

  python3 test/cognitive_model_regressions.py --binary tools/run-emergent

Uses checked-in serializer migrations of untouched shipped projects. It never
creates or accepts expected-output baselines and never edits the source models.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import traceback

from modern_stack_regressions import Case, REPO, require, runtime_diagnostics

COUNT_MODEL = '.projects[0].programs["Count"].objs["CountModel"]'
COUNT_RUN = '''
cout << "COGNITIVE_INITIAL " << cognitive_model->GoalModule()->init_chunk[0].GetSlotValLiteral("start") << " " << cognitive_model->GoalModule()->init_chunk[0].GetSlotValLiteral("end") << endl;
cognitive_model->Run();
cout << "COGNITIVE_STATE " << cognitive_model->run_state << endl;
cout << "COGNITIVE_TIME " << cognitive_model->cur_time << endl;
cout << "COGNITIVE_GOAL_COUNT " << cognitive_model->buffers["goal"].CurChunk()->GetSlotValLiteral("count") << endl;
DataTable* cognitive_log = cognitive_model->log_table;
for(int cognitive_row=0; cognitive_row<cognitive_log->rows; cognitive_row++) {
 String cognitive_action = cognitive_log->GetValAsString("action",cognitive_row);
 if(cognitive_action == "PRODUCTION_FIRED") cout << "COGNITIVE_FIRED " << cognitive_log->GetValAsString("params",cognitive_row) << " " << cognitive_log->GetValAsString("time",cognitive_row) << endl;
 if(cognitive_action == "RETRIEVED_CHUNK") cout << "COGNITIVE_RETRIEVED " << cognitive_log->GetValAsString("params",cognitive_row) << endl;
}
cout << "MODERN_PASS cognitive_count_completed" << endl;
cout << "MODERN_COMPLETE" << endl;
'''


def verify_count(case, name, start, end):
    text = (case.directory / (name + '.log')).read_text()
    expected_numbers = list(range(start, end + 1))
    numbers = [int(x) for x in re.findall(r'^count is: (\d+)$', text, re.MULTILINE)]
    fired = re.findall(r'^COGNITIVE_FIRED (\S+) (\S+)$', text, re.MULTILINE)
    expected_productions = ['START'] + ['INCREMENT'] * (end - start) + ['STOP']
    case.equal(name + '.spoken_count', numbers, expected_numbers)
    case.equal(name + '.fired_productions', [x[0] for x in fired], expected_productions)
    case.equal(name + '.initial_goal', re.findall(r'^COGNITIVE_INITIAL (\d+) (\d+)$', text, re.MULTILINE),
               [(str(start), str(end))])
    case.equal(name + '.terminal_goal_count', re.findall(r'^COGNITIVE_GOAL_COUNT (\d+)$', text, re.MULTILINE), [str(end)])
    case.equal(name + '.stop_state', re.findall(r'^COGNITIVE_STATE (\S+)$', text, re.MULTILINE), ['DONE'])
    clock = re.findall(r'^COGNITIVE_TIME (\S+)$', text, re.MULTILINE)
    require(len(clock) == 1, 'missing final model clock')
    case.equal(name + '.simulated_time', float(clock[0]), 0.05 * len(expected_productions))
    for index, (_, timestamp) in enumerate(fired, 1):
        case.equal(name + '.production_time_' + str(index), float(timestamp), 0.05 * index)
    # Each new counter value is obtained from the unchanged successor-memory
    # chunks b..f, including the last retrieval immediately before STOP.
    chunks = re.findall(r'^COGNITIVE_RETRIEVED (\S+)$', text, re.MULTILINE)
    case.equal(name + '.retrieved_successor_chunks', chunks,
               [chr(ord('A') + value) + '_0' for value in expected_numbers])


def actr_count(case, provenance):
    source = REPO / provenance['source']
    fixture = REPO / provenance['destination']
    for label, path, expected in [('shipped_original', source, provenance['source_sha256']),
                                  ('migrated_fixture', fixture, provenance['destination_sha256'])]:
        case.equal(label + '.sha256', hashlib.sha256(path.read_bytes()).hexdigest(), expected)
    case.fixture = case.directory / 'ActrCount.proj'
    shutil.copy2(fixture, case.fixture)
    start_script = f'ActrModel* cognitive_model = {COUNT_MODEL};\n'
    case.css(start_script + COUNT_RUN, ['cognitive_count_completed'], name='default')
    verify_count(case, 'default', 2, 4)
    saved = case.directory / 'count-one-to-five.proj'
    changed_script = start_script + f'''
cognitive_model->GoalModule()->init_chunk[0].SetSlotValLiteral("start", "1");
cognitive_model->GoalModule()->init_chunk[0].SetSlotValLiteral("end", "5");
.projects[0].SaveCopy("{saved}");
''' + COUNT_RUN
    case.css(changed_script, ['cognitive_count_completed'], name='parameterized')
    verify_count(case, 'parameterized', 1, 5)
    require(saved.is_file(), 'parameterized project was not saved')
    case.css(start_script + COUNT_RUN, ['cognitive_count_completed'], name='reopened', project=saved)
    verify_count(case, 'reopened', 1, 5)
    case.equal('original_still_unchanged', hashlib.sha256(source.read_bytes()).hexdigest(), provenance['source_sha256'])


SEMANTIC_MODEL = '.projects[0].programs["ActRTest"].objs["semantic"]'
SEMANTIC_RUN = """
cout << "COGNITIVE_INITIAL " << cognitive_model->GoalModule()->init_chunk[0].GetSlotValLiteral("object") << " " << cognitive_model->GoalModule()->init_chunk[0].GetSlotValLiteral("category") << endl;
cognitive_model->Run();
ActrVisionModule* cognitive_vision = cognitive_model->modules["vision"];
cout << "COGNITIVE_VISION " << cognitive_vision->buffer->name << " " << cognitive_vision->location_buffer->name << endl;
cout << "COGNITIVE_STATE " << cognitive_model->run_state << endl;
cout << "COGNITIVE_TIME " << cognitive_model->cur_time << endl;
ActrChunk* cognitive_final = cognitive_model->buffers["goal"].CurChunk();
cout << "COGNITIVE_FINAL " << cognitive_final->GetSlotValLiteral("object") << " " << cognitive_final->GetSlotValLiteral("category") << " " << cognitive_final->GetSlotValLiteral("judgment") << endl;
DataTable* cognitive_log = cognitive_model->log_table;
for(int cognitive_row=0; cognitive_row<cognitive_log->rows; cognitive_row++) {
 String cognitive_action = cognitive_log->GetValAsString("action",cognitive_row);
 if(cognitive_action == "PRODUCTION_FIRED") cout << "COGNITIVE_FIRED " << cognitive_log->GetValAsString("params",cognitive_row) << " " << cognitive_log->GetValAsString("time",cognitive_row) << endl;
 if(cognitive_action == "RETRIEVED_CHUNK") cout << "COGNITIVE_RETRIEVED " << cognitive_log->GetValAsString("params",cognitive_row) << endl;
 if(cognitive_action == "RETRIEVAL_FAILURE") cout << "COGNITIVE_RETRIEVAL_FAILURE " << cognitive_log->GetValAsString("time",cognitive_row) << endl;
}
cout << "MODERN_PASS cognitive_semantic_completed" << endl;
cout << "MODERN_COMPLETE" << endl;
"""
# Derived from the shipped property facts and production rules: p14 is
# canary->bird and p20 is bird->animal; animal has no parent-category fact.
# This native fixture uses 1 s retrievals and 0.05 s production firings.
SEMANTIC_EXPECTED = {
    'bird': ('canary', 'yes', ['initial_retrieve', 'direct_verify'], [0.05, 1.1], ['p14_0'], []),
    'animal': ('bird', 'yes', ['initial_retrieve', 'chain_category', 'direct_verify'], [0.05, 1.1, 2.15], ['p14_0', 'p20_0'], []),
    'fish': ('animal', 'no', ['initial_retrieve', 'chain_category', 'chain_category', 'fail'], [0.05, 1.1, 2.15, 3.2], ['p14_0', 'p20_0'], [3.15]),
}


def verify_semantic(case, name, category):
    text = (case.directory / (name + '.log')).read_text()
    final_object, judgment, productions, times, retrieved, failures = SEMANTIC_EXPECTED[category]
    case.equal(name + '.initial_goal', re.findall(r'^COGNITIVE_INITIAL (\S+) (\S+)$', text, re.MULTILINE), [('canary', category)])
    case.equal(name + '.final_goal', re.findall(r'^COGNITIVE_FINAL (\S+) (\S+) (\S+)$', text, re.MULTILINE), [(final_object, category, judgment)])
    case.equal(name + '.vision_buffers', re.findall(r'^COGNITIVE_VISION (\S+) (\S+)$', text, re.MULTILINE), [('visual', 'visual_location')])
    case.equal(name + '.stop_state', re.findall(r'^COGNITIVE_STATE (\S+)$', text, re.MULTILINE), ['DONE'])
    fired = re.findall(r'^COGNITIVE_FIRED (\S+) (\S+)$', text, re.MULTILINE)
    case.equal(name + '.production_order', [p for p, _ in fired], productions)
    for index, ((_, actual), expected) in enumerate(zip(fired, times), 1):
        case.equal(name + '.production_time_' + str(index), float(actual), expected)
    clock = re.findall(r'^COGNITIVE_TIME (\S+)$', text, re.MULTILINE)
    require(len(clock) == 1, 'missing final semantic clock')
    case.equal(name + '.simulated_time', float(clock[0]), times[-1])
    case.equal(name + '.retrieved_category_facts', re.findall(r'^COGNITIVE_RETRIEVED (\S+)$', text, re.MULTILINE), retrieved)
    actual_failures = re.findall(r'^COGNITIVE_RETRIEVAL_FAILURE (\S+)$', text, re.MULTILINE)
    case.equal(name + '.retrieval_failure_count', len(actual_failures), len(failures))
    for index, (actual, expected) in enumerate(zip(actual_failures, failures), 1):
        case.equal(name + '.retrieval_failure_time_' + str(index), float(actual), expected)


def actr_semantic(case, provenance, legacy=False):
    source = REPO / provenance['source']
    fixture = source if legacy else REPO / provenance['destination']
    case.equal('shipped_original.sha256', hashlib.sha256(source.read_bytes()).hexdigest(), provenance['source_sha256'])
    case.equal('loaded_fixture.sha256', hashlib.sha256(fixture.read_bytes()).hexdigest(),
               provenance['source_sha256' if legacy else 'destination_sha256'])
    case.fixture = case.directory / 'semantic.proj'
    shutil.copy2(fixture, case.fixture)
    prefix = f'ActrModel* cognitive_model = {SEMANTIC_MODEL};\n'
    if legacy:
        # Exercise normal Run directly from the exact old serialized project.
        # No test workaround repairs the two vision-buffer references.
        script = prefix + """
ActrVisionModule* cognitive_old_vision = cognitive_model->modules["vision"];
cout << "COGNITIVE_LEGACY_VISION " << cognitive_old_vision->buffer->name << " " << (cognitive_old_vision->location_buffer == NULL) << endl;
""" + SEMANTIC_RUN
        case.css(script, ['cognitive_semantic_completed'], name='original')
        text = (case.directory / 'original.log').read_text()
        expected = provenance['legacy_diagnostics']
        for check in case.checks:
            if check['check'] == 'original.runtime_diagnostics': check['expected'] = expected
        case.equal('original.known_serialization_warnings', runtime_diagnostics(text), expected)
        case.equal('original.incomplete_legacy_reference', re.findall(r'^COGNITIVE_LEGACY_VISION (\S+) (\S+)$', text, re.MULTILINE), [('visual_location', 'true')])
        verify_semantic(case, 'original', 'animal')
    else:
        for category in SEMANTIC_EXPECTED:
            script = prefix + f'cognitive_model->GoalModule()->init_chunk[0].SetSlotValLiteral("category", "{category}");\n' + SEMANTIC_RUN
            case.css(script, ['cognitive_semantic_completed'], name=category)
            verify_semantic(case, category, category)
    case.equal('original_still_unchanged', hashlib.sha256(source.read_bytes()).hexdigest(), provenance['source_sha256'])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    args.binary = args.binary.resolve()
    args.output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='emergent-cognitive-'))
    if not args.output.exists(): args.output.mkdir(parents=True)
    require(not any(args.output.iterdir()), 'output directory must be empty')
    provenance_path = REPO / 'test/fixtures/modern/cognitive-provenance.json'
    provenance = json.loads(provenance_path.read_text())
    prefix = Path(os.environ.get('EMERGENT_PREFIX_DIR', REPO / 'install'))
    installed = [prefix / 'bin/emergent', prefix / 'lib/libtemt.so', prefix / 'lib/libemergentlib.so']
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in installed}
    records = {Path(record['source']).stem: record for record in provenance['fixtures']}
    report = {'status': 'PASS', 'binary': str(args.binary), 'installed_sha256': hashes,
              'fixture_provenance': str(provenance_path), 'cases': [],
              'historical_failures': {
                  'original_semantic_incomplete_vision_reference': 'artifacts/cognitive-semantic-gdb/report.json',
                  'semantic_lisp_import_duplicate_slot_constraint': 'artifacts/cognitive-model-inspection/semantic-lisp/run.log'},
              'legacy_boundary': 'Original semantic project is explicitly checked with its two known serialization warnings; migrated task runs require zero runtime diagnostics.'}
    started = time.monotonic()
    for name, function, record, legacy in [
        ('actr-count', actr_count, records['count'], False),
        ('actr-semantic-original', actr_semantic, records['semantic'], True),
        ('actr-semantic', actr_semantic, records['semantic'], False),
    ]:
        case = Case(args, name, allow_diagnostics=legacy)
        result = {'name': name, 'status': 'PASS', 'checks': case.checks}
        if legacy: result['fixture_status'] = 'STALE_SERIALIZATION_WITH_EXPECTED_DIAGNOSTICS'
        report['cases'].append(result)
        try:
            if function == actr_count: function(case, record)
            else: function(case, record, legacy=legacy)
            for path, digest in hashes.items(): require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'installed library changed')
        except Exception as error:
            report['status'] = 'FAIL'
            result.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    report['seconds'] = round(time.monotonic() - started, 3)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], args.output / 'report.json', report.get('error', ''), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
