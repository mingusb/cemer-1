#!/usr/bin/env python3
"""Exercise the original Mollick et al. (2020) PVLV model through native programs.

Checks one initial appetitive conditioning episode and a serialization roundtrip.
This is not a reproduction of the paper's learned phenomena or full test suite.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time
import traceback

from modern_stack_regressions import Case, Server, REPO, require, runtime_diagnostics

FIXTURE = REPO / 'demo/LegacyModels/publications/MollickHazyKruegerEtAl20/bvPVLV_cel.proj'
INVENTORY = '''
cout << "PVLV_INVENTORY_BEGIN" << endl;
cout << "PVLV_PROJECT " << .projects[0].name << endl;
cout << "PVLV_NETWORKS " << .projects[0].networks.size << endl;
for(int ni=0;ni<.projects[0].networks.size;ni++) {
 Network* net=.projects[0].networks[ni];
 cout << "PVLV_NETWORK " << net->name << " " << net->layers.leaves << endl;
 for(int li=0;li<net->layers.leaves;li++) {
  Layer* lay=net->layers.Leaf(li);
  cout << "PVLV_LAYER " << lay->name << " " << lay->un_geom.x << " " << lay->un_geom.y << " " << lay->gp_geom.x << " " << lay->gp_geom.y << " " << lay->projections.size << endl;
 }
}
cout << "PVLV_PROGRAMS " << .projects[0].programs.leaves << endl;
for(int pi=0;pi<.projects[0].programs.leaves;pi++) {
 Program* pg=.projects[0].programs.Leaf(pi);
 cout << "PVLV_PROGRAM " << pg->name << endl;
 cout << pg->ProgramListing() << endl;
}
cout << "PVLV_INVENTORY_END" << endl;
'''


def inventory(server):
    text = server.console(' '.join(INVENTORY.splitlines()), 'PVLV_INVENTORY_END')
    return text.split('\nPVLV_INVENTORY_BEGIN\n', 1)[1].split('\nPVLV_INVENTORY_END', 1)[0]


def flattened(value):
    if isinstance(value, list):
        for item in value:
            yield from flattened(item)
    else:
        yield value


def installed_evidence():
    prefix = Path(os.environ.get("EMERGENT_PREFIX_DIR", REPO / "install")).resolve()
    return [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in [prefix / "bin/emergent", prefix / "lib/libtemt.so", prefix / "lib/libemergentlib.so"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=REPO / 'tools/run-emergent')
    parser.add_argument('--project', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    args.binary = args.binary.resolve()
    args.project = args.project.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.project.read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    provenance = json.loads(FIXTURE.with_name('provenance.json').read_text())
    require(source_hash == provenance['sha256'], 'project differs from pinned author source')
    report = {'status': 'IN_PROGRESS', 'scope': 'Native load/save/reopen and one untrained appetitive conditioning episode; no full-paper reproduction claimed.', 'project_sha256': source_hash, 'cases': []}
    report['installed_files_before'] = installed_evidence()
    started = time.monotonic()
    try:
        load_case = Case(args, 'load-and-save')
        load_case.fixture = load_case.directory / args.project.name
        shutil.copy2(args.project, load_case.fixture)
        entry = {'name': 'load_and_save', 'checks': load_case.checks}
        report['cases'].append(entry)
        with Server(load_case) as server:
            before = inventory(server)
            load_case.equal('one_network', 'PVLV_NETWORKS 1' in before, True)
            load_case.equal('authored_36_layers', 'PVLV_NETWORK bvPVLVNet 36' in before, True)
            load_case.equal('authored_46_programs', 'PVLV_PROGRAMS 46' in before, True)
            saved = load_case.directory / args.project.name
            server.console('.projects[0].SaveCopy(' + json.dumps(str(saved)) + '); cout << "PVLV_SAVED" << endl;', 'PVLV_SAVED')
        entry['status'] = 'PASS'
        (load_case.directory / 'native-inventory.txt').write_text(before)
        run_case = Case(args, 'reopen-and-acquisition')
        run_case.fixture = saved
        entry = {'name': 'reopen_and_acquisition', 'checks': run_case.checks}
        report['cases'].append(entry)
        with Server(run_case) as server:
            after = inventory(server)
            run_case.equal('topology_and_full_native_program_listings_preserved', before == after, True)
            server.console('ParamSet* pvlv_acq=.projects[0].active_params.FindLeafName("pos_acq_b100"); if(pvlv_acq != NULL) { pvlv_acq->Activate(); cout << "PVLV_ACQUISITION_SELECTED" << endl; }', 'PVLV_ACQUISITION_SELECTED')
            run_case.equal('authored_100_percent_reward_environment', server.variable('bvPVLVEnv', 'env_params_table'), 'PosAcq_B100')
            server.run('bvPVLVInit')
            text = server.console('cout << "PVLV_BUILD " << .projects[0].networks[0].n_units << " " << .projects[0].networks[0].n_cons << endl; cout << "PVLV_BUILD_COMPLETE" << endl;', 'PVLV_BUILD_COMPLETE')
            match = re.search(r'^PVLV_BUILD (\d+) (\d+)$', text, re.M)
            require(match is not None, 'native build inventory missing')
            run_case.equal('built_units', int(match[1]), 1813)
            run_case.equal('built_connections', int(match[2]), 213649)
            for tick in range(5):
                server.run('bvPVLVRun')
                text = server.console('cout << "PVLV_TICK ' + str(tick) + ' " << .projects[0].networks[0].trial << " " << .projects[0].networks[0].cycle << endl; cout << "PVLV_TICK_COMPLETE" << endl;', 'PVLV_TICK_COMPLETE')
                match = re.search(r'^PVLV_TICK ' + str(tick) + r' (\d+) (\d+)$', text, re.M)
                require(match is not None, 'native trial counter missing')
                run_case.equal('trial_counter_' + str(tick), int(match[1]), tick + 1)
                run_case.equal('alpha_cycle_count_' + str(tick), int(match[2]), 100)
            tables = {name: server.call('GetData', table=name, row_from=0) for name in ['StdInputData', 'TrialOutputData']}
            (run_case.directory / 'native-tables.json').write_text(json.dumps(tables, indent=2) + '\n')
            inputs = {c['name']: c['values'] for c in tables['StdInputData']['columns']}
            outputs = {c['name']: c['values'] for c in tables['TrialOutputData']['columns']}
            trial_name = inputs['AlphTrialName'][0].rsplit('_t', 1)[0]
            run_case.equal('authored_acquisition_cue', trial_name in ['A_Rf_POS', 'B_Rf_POS'], True)
            run_case.equal('authored_alpha_trial_names', inputs['AlphTrialName'], [trial_name + '_t' + str(t) for t in range(5)])
            run_case.equal('cue_presentation_sequence', [sum(float(x) for x in flattened(row)) for row in inputs['Stim_In']], [0., 1., 1., 1., 0.])
            run_case.equal('appetitive_reward_sequence', [sum(float(x) for x in flattened(row)) for row in inputs['PosPV']], [0., 0., 0., 1., 0.])
            run_case.equal('no_aversive_reward_in_positive_task', [sum(float(x) for x in flattened(row)) for row in inputs['NegPV']], [0.] * 5)
            run_case.equal('native_monitor_trials', outputs['trial'], list(range(5)))
            run_case.equal('native_monitor_ticks', outputs['tick'], list(range(5)))
            dopamine = outputs['VTAp_act']
            run_case.equal('dopamine_monitor_has_five_samples', len(dopamine), 5)
            run_case.equal('dopamine_samples_finite', all(math.isfinite(x) for x in dopamine), True)
            run_case.equal('unconditioned_positive_dopamine_burst_at_reward', dopamine[3] > 0.5, True)
            run_case.equal('untrained_baseline_and_cue_response_near_zero', all(abs(dopamine[i]) < 1e-5 for i in [0, 1, 2, 4]), True)
        entry['status'] = 'PASS'
        report.update(status='PASS', source_unchanged=args.project.read_bytes() == source, saved_project_sha256=hashlib.sha256(saved.read_bytes()).hexdigest())
    except Exception as error:
        report.update(status='FAIL', error=str(error), traceback=traceback.format_exc())
    report['seconds'] = round(time.monotonic() - started, 3)
    report['check_count'] = sum(len(case['checks']) for case in report['cases'])
    report['installed_files'] = installed_evidence()
    report['runtime_unchanged'] = report['installed_files_before'] == report['installed_files']
    if not report['runtime_unchanged']:
        report.update(status='FAIL', error='installed runtime changed during regression')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], report['check_count'], args.output / 'report.json')
    return report['status'] != 'PASS'


if __name__ == '__main__':
    sys.exit(main())
