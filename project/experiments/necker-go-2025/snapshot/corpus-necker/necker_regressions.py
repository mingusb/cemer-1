#!/usr/bin/env python3
"""Validate the author's fixed Necker Cube attractors, noise and adaptation tasks.

Adds read-only native monitor columns to disposable test copies. The original
network, recurrent weights and native programs are never changed. Expectations
are symmetry, cube connectivity, coherent attractors, and adaptation-dependent
switching; no captured numeric baseline is accepted.
"""
import argparse,hashlib,json,math,os,re,shutil,sys,traceback
from pathlib import Path
ROOT=Path('/home/b/cemer')
CODE=ROOT/'project' if (ROOT/'project/test').exists() else ROOT
sys.path.insert(0,str(CODE/'test'))
from modern_stack_regressions import Case,Server,require


def flat(value):
 return sum((flat(x) for x in value),[]) if isinstance(value,list) else [value]


def setup(server):
 server.console('LeabraNetwork* ncnet=.projects[0].networks[0]; LeabraLayer* nclay=ncnet->layers[0]; LeabraUnitSpec* ncspec=ncnet->specs[0]; Program* ncepoch=.projects[0].programs.Leaf(1); RndSeed ns; NetMonitor* ncmon=.projects[0].programs.Leaf(7)->objs[0]; cout << "NECKER_SETUP" << endl;','NECKER_SETUP')
 existing=server.call('GetData',table='CycleOutputData')['columns']
 if not any(column['name']=='act' for column in existing):
  server.console('for(int vi=0;vi<6;vi++) { String vn; if(vi==0) vn="act"; if(vi==1) vn="net"; if(vi==2) vn="act_eq"; if(vi==3) vn="gc_kna_f"; if(vi==4) vn="gc_kna_m"; if(vi==5) vn="gc_kna_s"; NetMonItem* nm=ncmon->AddLayer(nclay,vn); nm->name_style=NetMonItem::MY_NAME; nm->name=vn; nm->UpdateAfterEdit(); } cout << "NECKER_OBSERVERS_READY" << endl;','NECKER_OBSERVERS_READY')


def weights(server,name):
 path=server.case.directory/(name+'.wts')
 server.console('ncnet->SaveWeights('+json.dumps(str(path))+'); cout << "NECKER_WEIGHTS_'+name+'" << endl;','NECKER_WEIGHTS_'+name)
 result={}
 for layer,body in re.findall(r'<Lay ([^>]+)>(.*?)</Lay>',path.read_text(),re.S):
  for destination,unit in re.findall(r'<UgUn (\d+) [^>]*>(.*?)</UgUn>',body,re.S):
   for sender,group in re.findall(r'<Cg \d+ Fm:([^>]+)>(.*?)</Cg>',unit,re.S):
    for source,value in re.findall(r'^(\d+) ([\d.eE+-]+)$',group,re.M):
     key=(layer,int(destination),sender,int(source));require(key not in result,'duplicate connection');result[key]=float(value)
 require(result,'native weights missing')
 return result


def collect(case,server,name,cycles,adapt):
 data=server.call('GetData',table='CycleOutputData');columns={column['name']:column['values'] for column in data['columns']}
 acts=list(map(flat,columns['act']));net=list(map(flat,columns['net']));act_eq=list(map(flat,columns['act_eq']));harmony=columns['harmony']
 case.equal(name+'.native_cycle_sequence',columns['cycle'],list(range(1,cycles+1)))
 case.equal(name+'.sixteen_units_each_cycle',all(len(row)==16 for row in acts),True)
 case.equal(name+'.finite_bounded_activations',all(math.isfinite(value) and 0<=value<=1 for row in acts for value in row),True)
 case.equal(name+'.finite_harmony',all(math.isfinite(value) for value in harmony),True)
 case.equal(name+'.author_harmony_formula',all(math.isclose(sum(n*a for n,a in zip(nr,ar))/16,h,rel_tol=1e-6,abs_tol=1e-7) for nr,ar,h in zip(net,act_eq,harmony)),True)
 differences=[sum(row[:8])/8-sum(row[8:])/8 for row in acts]
 states=[1 if delta>.5 else -1 if delta<-.5 else 0 for delta in differences]
 decided=[state for state in states if state];switches=sum(a!=b for a,b in zip(decided,decided[1:]))
 for channel in ['gc_kna_f','gc_kna_m','gc_kna_s']:
  values=flat(columns[channel]);case.equal(name+'.'+channel+'_finite_nonnegative',all(math.isfinite(value) and value>=0 for value in values),True)
  case.equal(name+'.'+channel+'_follows_adaptation_control',max(values)>0 if adapt else max(values)==0,True)
 result={'name':name,'columns':columns,'activations':acts,'harmony':harmony,'states':states,'switches':switches}
 (case.directory/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
 return result


def trial(case,server,name,noise,adapt,quarter,seed):
 server.console('ncspec->noise.var='+str(noise)+'; ncspec->kna_adapt.on='+str(adapt).lower()+'; ncspec->UpdateAfterEdit(); ncnet->times.quarter='+str(quarter)+'; ncnet->UpdateAfterEdit(); ns.Init('+str(seed)+'); ncepoch->Init(); cout << "NECKER_INIT_'+name+'" << endl;','NECKER_INIT_'+name)
 server.run('LeabraEpoch')
 result=collect(case,server,name,quarter*4,adapt)
 result['condition']={'noise_variance':noise,'kna_adaptation':adapt,'quarter_cycles':quarter,'seed':seed}
 return result


def coherent(case,result):
 last=result['activations'][-1];winner=0 if sum(last[:8])>sum(last[8:]) else 1
 active=last[winner*8:(winner+1)*8];inactive=last[(1-winner)*8:(2-winner)*8]
 case.equal(result['name']+'.all_winning_vertices_active',min(active)>.5,True)
 case.equal(result['name']+'.other_interpretation_inactive',max(inactive)<.01,True)
 case.equal(result['name']+'.exactly_eight_active_vertices',sum(value>.5 for value in last),8)
 case.equal(result['name']+'.settling_increases_harmony',result['harmony'][-1]>result['harmony'][0],True)
 return winner


def run(case):
 setup_source=case.args.fixture;provenance=json.loads(case.args.provenance.read_text())
 case.equal('pinned_migrated_fixture',hashlib.sha256(setup_source.read_bytes()).hexdigest(),provenance['project_sha256'])
 case.fixture=case.directory/'necker_cube.proj';shutil.copy2(setup_source,case.fixture)
 with Server(case) as server:
  setup(server)
  a=trial(case,server,'default_seed1',.01,False,25,1);b=trial(case,server,'default_seed3',.01,False,25,3)
  case.equal('both_authored_attractors_reachable',set([coherent(case,a),coherent(case,b)]),set([0,1]))
  original=weights(server,'original')
  expected={('NeckerCube',i,'NeckerCube',j):float(i//8==j//8 and ((i%8)^(j%8)) in [1,2,4]) for i in range(16) for j in range(16) if i!=j}
  case.equal('fixed_connections_are_two_disjoint_cubes',original==expected,True)
  case.equal('native_off_diagonal_connections',len(original),240)
  case.equal('positive_directed_cube_edges',sum(value==1 for value in original.values()),48)
  symmetric=trial(case,server,'noise_zero',0,False,25,1)
  case.equal('zero_noise_cannot_break_symmetry',all(max(row)==min(row) for row in symmetric['activations']),True)
  case.equal('zero_noise_has_no_winning_interpretation',set(symmetric['states']),set([0]))
  case.equal('coherent_attractors_have_higher_harmony_than_symmetric_tie',min(a['harmony'][-1],b['harmony'][-1])>symmetric['harmony'][-1],True)
  for name,variance in [('noise_high',.1),('noise_low',.001)]:coherent(case,trial(case,server,name,variance,False,25,1))
  control=trial(case,server,'long_no_adaptation',.01,False,250,1);adapt=trial(case,server,'long_adaptation',.01,True,250,1)
  case.equal('no_adaptation_preserves_selected_interpretation',control['switches'],0)
  case.equal('adaptation_repeatedly_switches_interpretation',adapt['switches']>=2,True)
  case.equal('adaptation_reaches_both_interpretations',{state for state in adapt['states'] if state},set([-1,1]))
  case.equal('task_does_not_train_or_change_fixed_weights',weights(server,'queried')==original,True)
  saved=case.directory/'necker_cube-saved.proj';server.console('.projects[0].SaveCopy('+json.dumps(str(saved))+'); cout << "NECKER_SAVED" << endl;','NECKER_SAVED')
 reopened=Case(case.args,'reopened');reopened.fixture=saved
 with Server(reopened) as server:
  setup(server);repeat=trial(reopened,server,'adaptation_reopened',.01,True,250,1)
  case.equal('saved_reopened_unit_trace_reproduced',repeat['activations'],adapt['activations'])
  case.equal('saved_reopened_harmony_reproduced',repeat['harmony'],adapt['harmony'])
  case.equal('saved_reopened_weights_preserved',weights(server,'reopened')==original,True)
 case.checks.extend(reopened.checks)
 for item in [case,reopened]:
  warnings=[line for line in (item.directory/'emergent.log').read_text(errors='replace').splitlines() if re.search(r'^Warning:|^Error:',line)]
  case.equal(item.directory.name+'.css_diagnostics',warnings,[])


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binary',type=Path,default=CODE/'tools/run-emergent');parser.add_argument('--fixture',type=Path,default=ROOT/'artifacts/corpus-necker/staged-final/necker_cube.proj');parser.add_argument('--provenance',type=Path,default=ROOT/'artifacts/corpus-necker/staged-final/necker-provenance.json');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--timeout',type=float,default=90);args=parser.parse_args()
 for name in ['binary','fixture','provenance','output']:setattr(args,name,getattr(args,name).resolve())
 args.output.mkdir(parents=True,exist_ok=False);prefix=Path(os.environ.get('EMERGENT_PREFIX_DIR',str(ROOT/'install-legacy-checkpoint')))
 hashes={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in [prefix/'bin/emergent',prefix/'lib/libtemt.so',prefix/'lib/libemergentlib.so']}
 case=Case(args,'necker_cube');report={'status':'PASS','checks':case.checks,'installed_sha256':hashes,'scope':'Authored maintained8.5 FFFB/net-input-noise/KNa model; no old kWTA/AdEx equivalence claim. Added observers only in test copies.'}
 try:run(case)
 except Exception as error:report.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
 for path,digest in hashes.items():require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,'installed library changed during test')
 (args.output/'report.json').write_text(json.dumps(report,indent=2,default=lambda x:sorted(x))+'\n');print(report['status'],args.output/'report.json',flush=True);return report['status']!='PASS'
if __name__=='__main__':sys.exit(main())
