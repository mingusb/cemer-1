#!/usr/bin/env python3
"""Run the unchanged author-maintained CECN neuron and digit-detector tutorials.

The assertions express textbook mechanisms and fixed inputs, not captured output
baselines. All parameter changes and saved projects stay in the artifact tree.
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
import tempfile
import time
import traceback

from modern_stack_regressions import Case, Server, REPO, require

FIXTURES = REPO / 'demo/LegacyModels/cecn/chapter_2'
OVERLAPS = [6, 6, 12, 13, 5, 14, 12, 6, 17, 12]
WEIGHT_PATTERN = [int(x) for x in '01110100011000101110100011000101110']


def flatten(value):
    if isinstance(value, list):
        return [item for child in value for item in flatten(child)]
    return [value]


def table(server, name, filename, rows):
    data = server.call('GetData', table=name, row_from=0, rows=rows)
    (server.case.directory / filename).write_text(json.dumps(data, indent=2) + '\n')
    return {column['name']: column['values'] for column in data['columns']}


def scalars(values):
    result = []
    for value in values:
        value = flatten(value)
        require(len(value) == 1, 'expected scalar neuron observation')
        result.append(float(value[0]))
    return result


def checked_fixture(case, name, provenance):
    fixture = FIXTURES / (name + '.proj')
    case.equal('fixture.sha256', hashlib.sha256(fixture.read_bytes()).hexdigest(), provenance['project_sha256'])
    case.fixture = case.directory / (name + '.proj')
    shutil.copy2(fixture, case.fixture)
    html = (FIXTURES / (name + '.html')).read_text()
    case.equal('offline_document.sha256', hashlib.sha256(html.encode()).hexdigest(), provenance['offline_html_sha256'])
    case.equal('offline_document_no_external_assets', any(tag in html.lower() for tag in ['<script', '<img', '<link']), False)
    case.equal('offline_document_attribution', 'creativecommons.org/licenses/by-sa/3.0/' in html, True)


def neuron_run(case, server, name, overrides=None):
    values = {'act_fun': 1, 'g_bar_e': .3, 'g_bar_l': .3, 'adapt_on': True,
              'noise_var': 0, 'n_cycles': 200, 'on_cycle': 10, 'off_cycle': 160}
    values.update(overrides or {})
    for key, value in values.items(): server.set_variable('SetDefaults', key, value)
    server.run('SetDefaults')
    # Init is a real native button. It resets the cycle log; Run intentionally
    # accumulates rows when called repeatedly without Init.
    server.console('.projects[0].programs.gp[0][0].Init(); cout << "CH2_INIT" << endl;', 'CH2_INIT')
    server.run('LeabraSettle')
    raw = table(server, 'CycleOutputData', name + '.json', 200)
    data = {key: scalars(value) for key, value in raw.items()}
    case.equal(name + '.cycles', data['cycle'], list(range(1, 201)))
    case.equal(name + '.all_observations_finite', all(math.isfinite(x) for column in data.values() for x in column), True)
    case.equal(name + '.binary_spikes', set(data['spike']).issubset({0, 1}), True)
    case.equal(name + '.no_spikes_before_input', sum(data['spike'][:10]), 0)
    case.equal(name + '.no_spikes_after_input', sum(data['spike'][160:]), 0)
    case.equal(name + '.input_excitation_plateau', data['net'][100], values['g_bar_e'])
    case.equal(name + '.input_removed', data['net'][-1], 0.0)
    return data


def neuron(case, provenance):
    checked_fixture(case, 'neuron', provenance)
    with Server(case) as server:
        runs = {}
        for name, override in [('baseline', {}), ('no_adaptation', {'adapt_on': False}),
                               ('no_excitation', {'g_bar_e': 0}), ('strong_excitation', {'g_bar_e': .6}),
                               ('strong_leak', {'g_bar_l': .6})]:
            runs[name] = neuron_run(case, server, name, override)
        spike_count = lambda name: sum(runs[name]['spike'])
        case.equal('excitation_required_for_firing', spike_count('no_excitation'), 0)
        case.equal('stimulus_evokes_firing', spike_count('baseline') > 0, True)
        case.equal('more_excitation_increases_firing', spike_count('strong_excitation') > spike_count('baseline'), True)
        case.equal('more_leak_reduces_firing', spike_count('strong_leak') < spike_count('baseline'), True)
        case.equal('adaptation_reduces_firing', spike_count('baseline') < spike_count('no_adaptation'), True)
        for channel in ['gc_kna_f', 'gc_kna_m', 'gc_kna_s']:
            case.equal(channel + '.recruited_by_spikes', max(runs['baseline'][channel]) > 0, True)
            case.equal(channel + '.absent_when_disabled', max(runs['no_adaptation'][channel]), 0.0)
            case.equal(channel + '.absent_without_spikes', max(runs['no_excitation'][channel]), 0.0)
        times = [cycle for cycle, spike in zip(runs['baseline']['cycle'], runs['baseline']['spike']) if spike]
        intervals = [right-left for left, right in zip(times, times[1:])]
        case.equal('adaptation_lengthens_interspike_interval', intervals[-1] > intervals[0], True)
        times = [cycle for cycle, spike in zip(runs['no_adaptation']['cycle'], runs['no_adaptation']['spike']) if spike]
        case.equal('unadapted_constant_interspike_interval', len({b-a for a, b in zip(times, times[1:])}), 1)
        case.equal('poststimulus_rate_estimate_decays', runs['baseline']['act_eq'][-1] < runs['baseline']['act_eq'][159], True)
        for key, value in {'g_bar_e_start': .125, 'g_bar_e_end': .625, 'g_bar_e_inc': .125,
                           'n_samples': 1, 'noise_var': 0}.items():
            server.set_variable('SpikeVsRate', key, value)
        server.run('SetDefaults')
        server.run('SpikeVsRate')
        curve = table(server, '.programs[1].objs[0]', 'spike-versus-rate.json', 5)
        case.equal('spike_rate.input_grid', scalars(curve['g_bar_e']), [.125, .25, .375, .5, .625])
        for column in ['spike', 'rate']:
            response = scalars(curve[column])
            case.equal('spike_rate.' + column + '_finite_nonnegative', all(math.isfinite(x) and x >= 0 for x in response), True)
            case.equal('spike_rate.' + column + '_rises_with_excitation', all(b >= a for a, b in zip(response, response[1:])) and response[-1] > response[0], True)
        saved = case.directory / 'neuron-saved.proj'
        neuron_run(case, server, 'saved-no-adaptation', {'adapt_on': False})
        server.console('.projects[0].SaveCopy(' + json.dumps(str(saved)) + '); cout << "CH2_SAVED" << endl;', 'CH2_SAVED')
    reopened = Case(case.args, 'neuron-reopened'); reopened.fixture = saved
    with Server(reopened) as server:
        reopened.equal('saved_adaptation_control', server.variable('SetDefaults', 'adapt_on'), False)
        rerun = neuron_run(reopened, server, 'reopened-no-adaptation', {'adapt_on': False})
        reopened.equal('saved_task_firing_reproduced', rerun['spike'], runs['no_adaptation']['spike'])
    case.checks.extend(reopened.checks)


def detector_run(case, server, leak):
    server.console(f'LeabraNetwork* ch2_net=.projects[0].networks[0]; LeabraUnitSpec* ch2_spec=ch2_net->specs["LeabraUnitSpec_0"]; ch2_spec->g_bar.l={leak}; ch2_spec->UpdateAfterEdit(); ch2_net->Init_Weights(); ch2_net->Init_Acts(); cout << "CH2_INIT" << endl;', 'CH2_INIT')
    server.run('LeabraEpoch')
    data = table(server, 'TrialOutputData', 'leak-' + str(leak) + '.json', 10)
    case.equal(str(leak) + '.digit_order', data['trial_name'], list(map(str, range(10))))
    net = scalars(data['net']); act = scalars(data['act'])
    case.equal(str(leak) + '.finite_responses', all(math.isfinite(x) and 0 <= x <= 1 for x in net+act), True)
    for digit, count in enumerate(OVERLAPS):
        case.equal(str(leak) + '.weighted_input_digit_' + str(digit), net[digit], .95 * count / 17)
    case.equal(str(leak) + '.preferred_digit', max(range(10), key=act.__getitem__), 8)
    return act


def detector(case, provenance):
    checked_fixture(case, 'detector', provenance)
    with Server(case) as server:
        inputs = table(server, 'digits', 'original-digits.json', 10)
        digits = [flatten(pattern) for pattern in inputs['Input']]
        case.equal('ten_5x7_patterns', [len(p) for p in digits], [35]*10)
        case.equal('binary_input_patterns', all(x in (0, 1) for p in digits for x in p), True)
        case.equal('digit8_matches_weight_pattern', digits[8], WEIGHT_PATTERN)
        case.equal('fixed_weighted_overlap_counts', [sum(x*w for x, w in zip(p, WEIGHT_PATTERN)) for p in digits], OVERLAPS)
        responses = {leak: detector_run(case, server, leak) for leak in [2, 1.8, 1.5, 2.3]}
        expected_active = {2:[8], 1.8:[5,8], 1.5:[2,3,5,6,8,9], 2.3:[8]}
        for leak, response in responses.items():
            case.equal(str(leak) + '.digits_above_half_activation', [i for i, act in enumerate(response) if act > .5], expected_active[leak])
        case.equal('default_selective_response', responses[2][8] > .9 and max(responses[2][:8]+responses[2][9:]) < .02, True)
        case.equal('lower_leak_increases_responsivity', all(responses[1.5][i] >= responses[1.8][i] >= responses[2][i] >= responses[2.3][i] for i in range(10)), True)
        weights = case.directory/'actual-weights.wts'
        server.console('.projects[0].networks[0].SaveWeights(' + json.dumps(str(weights)) + '); cout << "CH2_WEIGHTS" << endl;', 'CH2_WEIGHTS')
        match = re.search(r'<Cn 35>\s*(.*?)</Cn>', weights.read_text(), re.S)
        require(match is not None, 'actual 35 detector connections were not saved')
        case.equal('native_weights_unchanged', [float(line.split()[1]) for line in match.group(1).splitlines() if line.strip()], WEIGHT_PATTERN)
        detector_run(case, server, 1.8)
        saved = case.directory/'detector-saved.proj'
        server.console('.projects[0].SaveCopy(' + json.dumps(str(saved)) + '); cout << "CH2_SAVED" << endl;', 'CH2_SAVED')
    reopened = Case(case.args, 'detector-reopened'); reopened.fixture = saved
    with Server(reopened) as server:
        text = server.console('LeabraUnitSpec* ch2_spec=.projects[0].networks[0].specs["LeabraUnitSpec_0"]; cout << "CH2_SAVED_LEAK " << ch2_spec->g_bar.l << endl; cout << "CH2_STATE" << endl;', 'CH2_STATE')
        values = re.findall(r'^CH2_SAVED_LEAK (\S+)$', text, re.M)
        reopened.equal('saved_leak_control', [float(x) for x in values], [1.8])
        response = detector_run(reopened, server, 1.8)
        for digit in range(10): reopened.equal('saved_response_digit_' + str(digit), response[digit], responses[1.8][digit])
    case.checks.extend(reopened.checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=REPO/'tools/run-emergent')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args(); args.binary = args.binary.resolve()
    args.output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='cecn-ch2-'))
    args.output.mkdir(parents=True, exist_ok=True); require(not any(args.output.iterdir()), 'output directory must be empty')
    provenance = {m['name']:m for m in json.loads((FIXTURES/'provenance.json').read_text())['models']}
    prefix = Path(os.environ.get('EMERGENT_PREFIX_DIR', str(REPO/'install')))
    installed = [prefix/'bin/emergent',prefix/'lib/libtemt.so',prefix/'lib/libemergentlib.so']
    hashes = {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in installed}
    report = {'status':'PASS','installed_sha256':hashes,'cases':[], 'scope':'Author-maintained 8.5 neuron/KNa and digit detector. Earlier 8.0 AdEx adaptation is not claimed reproduced.'}
    started = time.monotonic()
    for name, function in [('neuron',neuron),('detector',detector)]:
        case = Case(args,name); row={'name':name,'status':'PASS','checks':case.checks};report['cases'].append(row)
        try: function(case,provenance[name])
        except Exception as error: row.update(status='FAIL',error=str(error),traceback=traceback.format_exc());report['status']='FAIL'
    for p, digest in hashes.items(): require(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,'installed library changed during test')
    report['seconds']=round(time.monotonic()-started,3)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],args.output/'report.json',flush=True)
    return report['status']!='PASS'


if __name__=='__main__':sys.exit(main())
