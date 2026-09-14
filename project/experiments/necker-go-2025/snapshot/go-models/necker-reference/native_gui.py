#!/usr/bin/env python3
"""Current Go Necker candidate: real native Run/Step/parameter/save controls."""
import argparse,hashlib,json,math,os,shutil,sys,time,traceback
from pathlib import Path
ROOT=Path('/home/b/cemer');sys.path[:0]=[str(ROOT/'project/test'),str(ROOT/'artifacts/corpus-necker/ready-test')]
from cecn_necker_gui import NeckerGUI
from cecn_necker_regressions import setup,collect,coherent,flat,weights
from inductor_head_gui_regression import GuiCase
from modern_stack_regressions import require

def step_trial(case,server,label,capture=False):
 server.click('Native Step Trial '+label,571,733)
 captured=set();deadline=time.monotonic()+case.args.timeout
 while time.monotonic()<deadline:
  state=int(server.call('GetRunState'))
  if capture:
   cycles=server.values('CycleOutputData','cycle')
   if cycles:
    values=flat(server.call('GetData',table='CycleOutputData',column='act',row_from=len(cycles)-1,rows=1)['columns'][0]['values'][0])
    delta=sum(values[:8])/8-sum(values[8:])/8;winner=1 if delta>.5 else -1 if delta<-.5 else 0
    if winner and winner not in captured:
     server.screenshot(label+('-left' if winner==1 else '-right'));captured.add(winner)
  if state==3:break
  time.sleep(.5)
 else:raise TimeoutError('native Step Trial did not pause')
 case.equal(label+'.native_step_trial_pauses',state,3)
 return captured

def task(case,server):
 time.sleep(2);server.screenshot('01-current-go-offline-wiki');setup(server)
 server.click('ControlPanel tab',610,131);server.click('Position Units',445,733);server.done()
 server.initialize(initial=True);server.click('Step Cycle',680,733);server.wait_state(3)
 case.equal('step_cycle_records_first_cycle',server.values('CycleOutputData','cycle'),[1]);server.screenshot('02-step-cycle')
 before=weights(server,'before');server.run_native();baseline=collect(case,server,'default_final_trial',100,False);coherent(case,baseline)
 case.equal('native_Run_completes_all100_trials',server.values('TrialOutputData','trial'),list(range(100)))
 case.equal('cycle_log_contains_only_current_trial',set(baseline['columns']['run_no']),{100})
 server.screenshot('03-native100-trials-complete')
 server.edit('noise',528,243,0);server.click('Apply noise',703,766);server.initialize();step_trial(case,server,'zero_noise')
 zero=collect(case,server,'zero_noise_first_trial',100,False);case.equal('actual_zero_noise_control_preserves_symmetry',all(max(x)==min(x) for x in zero['activations']),True);server.screenshot('04-zero-noise-symmetry')
 server.edit('noise',528,243,.01);server.edit('quarter cycles',340,266,250);server.click('KNa adaptation',324,289);server.click('Apply adaptation',703,766);server.initialize()
 captured=step_trial(case,server,'05-native-adaptation',True);adapt=collect(case,server,'adaptation_first_trial',1000,True)
 case.equal('adaptation_switches',adapt['switches']>=2,True);case.equal('adaptation_visits_both_interpretations',{x for x in adapt['states'] if x},{-1,1});case.equal('both_interpretations_captured',captured,{-1,1})
 server.screenshot('06-first-trial-adaptation-harmony')
 previous={name:flat(adapt['columns'][name][-1]) for name in ['gc_kna_f','gc_kna_m','gc_kna_s']}
 server.click('Step Cycle into next trial',680,733);server.wait_state(3)
 case.equal('next_trial_step_resets_cycle_log',server.values('CycleOutputData','cycle'),[1])
 case.equal('next_trial_step_retains_trial_counter',server.values('CycleOutputData','run_no'),[2])
 for name,tau in [('gc_kna_f',50),('gc_kna_m',200),('gc_kna_s',1000)]:
  actual=flat(server.values('CycleOutputData',name)[0]);case.equal(name+'.first_cycle_carry_and_decay',all(math.isclose(a,b-b/tau,abs_tol=1e-7) for a,b in zip(actual,previous[name])),True)
 server.screenshot('07-next-trial-adaptation-carry')
 case.equal('fixed_weights_unchanged',weights(server,'after')==before,True)
 server.console('taMisc::ConsoleOutput("GO_NECKER_GUI_CSS42 " + String(6*7));','GO_NECKER_GUI_CSS42 42');case.equal('actual_typed_CSS42',True,True);server.screenshot('08-console-prompt')
 server.save();return adapt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture',type=Path,default=ROOT/'artifacts/go-models/necker-native-candidate4/necker_cube.proj');p.add_argument('--timeout',type=float,default=900);a=p.parse_args();a.binary=ROOT/'project/tools/run-emergent';a.output.mkdir(exist_ok=False)
 require(os.environ.get('DISPLAY')==':93' and os.environ.get('QT_QPA_PLATFORM')=='xcb','use only isolated DISPLAY=:93 and QT_QPA_PLATFORM=xcb')
 prefix=Path(os.environ['EMERGENT_PREFIX_DIR']);hashes={str(x.resolve()):hashlib.sha256(x.read_bytes()).hexdigest() for x in [prefix/'bin/emergent',prefix/'lib/libtemt.so',prefix/'lib/libemergentlib.so']}
 report={'status':'PASS','installed_sha256':hashes,'fixture_sha256':hashlib.sha256(a.fixture.read_bytes()).hexdigest(),'cases':[]}
 try:
  c=GuiCase(a,'necker_cube');c.fixture=c.directory/'necker_cube.proj';shutil.copy2(a.fixture,c.fixture);c.original_digest=report['fixture_sha256'];report['cases'].append({'name':'native-current-model-controls','checks':c.checks})
  with NeckerGUI(c) as s:expected=task(c,s)
  c2=GuiCase(a,'reopened');c2.fixture=c2.directory/'necker_cube.proj';shutil.copy2(c.fixture,c2.fixture);report['cases'].append({'name':'saved-reopened','checks':c2.checks})
  with NeckerGUI(c2) as s:
   time.sleep(2);setup(s);s.initialize(initial=True);step_trial(c2,s,'reopened');actual=collect(c2,s,'reopened_first_trial',1000,True)
   c2.equal('same_seed_reopened_activation_reproduced',actual['activations']==expected['activations'],True);c2.equal('same_seed_reopened_harmony_reproduced',actual['harmony']==expected['harmony'],True);s.screenshot('09-reopened-native-circuit')
  for case in [c,c2]:case.equal('css_diagnostics',[x for x in (case.directory/'emergent.log').read_text(errors='replace').splitlines() if x.startswith(('Warning:','Error:'))],[])
 except Exception as e:report.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
 for path,digest in hashes.items():require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,'installed binary changed')
 (a.output/'report.json').write_text(json.dumps(report,indent=2,default=lambda x:sorted(x))+'\n');print(report['status'],a.output/'report.json',flush=True);return report['status']!='PASS'
if __name__=='__main__':sys.exit(main())
