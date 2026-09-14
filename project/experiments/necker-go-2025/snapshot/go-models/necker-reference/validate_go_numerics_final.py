#!/usr/bin/env python3
import hashlib,json,math,os,shutil,sys,traceback,gc,struct
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server,require
sys.path.insert(0,'/home/b/cemer/artifacts/corpus-necker')
from necker_regressions import setup,flat

def paged_data(server, count):
 path=server.case.directory/'cycles.json'
 server.console('DataTable* export_cycles=.projects[0].data.FindLeafName("CycleOutputData"); export_cycles->ExportDataJSON('+json.dumps(str(path))+'); cout << "NATIVE_ALL_CYCLES_EXPORTED" << endl;','NATIVE_ALL_CYCLES_EXPORTED')
 return json.loads(path.read_text())["result"]

root=Path('/home/b/cemer');base=root/'artifacts/go-models';args=SimpleNamespace(output=base/'necker-go-numerics-final',binary=root/'project/tools/run-emergent',timeout=360)
args.output.mkdir(exist_ok=False);report={'status':'PASS','cases':[],'scope':'All100 native trials, exact author model-pinned Go reference; injected reference noise only in disposable validation copy to isolate RNG differences.'}
try:
 for name,noise,adapt,quarter in [('zero-noise',0,False,25),('zero-noise-adaptation',0,True,250),('authored-default',.01,False,25),('authored-high-noise',.1,False,25),('authored-low-noise',.001,False,25),('authored-adaptation',.01,True,250),('authored-long-no-adaptation',.01,False,250)]:
  c=Case(args,name);c.fixture=c.directory/'necker_cube.proj';shutil.copy2(base/'necker-native-candidate6/necker_cube.proj',c.fixture)
  item={'name':name,'checks':c.checks,'maximum_absolute_differences':{}};report['cases'].append(item)
  reference=json.loads((base/'necker-reference/traces-all'/f'{name}.json').read_text());rows=reference['Rows'];cycles=quarter*4
  if noise:
   noise_file=c.directory/'noise.tsv'
   with noise_file.open('w') as f:
    f.write('\t'.join('Noise'+str(i) for i in range(16))+'\n')
    for row in rows:f.write('\t'.join(str(x) for x in row['Noise'])+'\n')
  with Server(c) as s:
   setup(s);s.set_variable('LeabraCycle','clear_cycle_log',False)
   s.console('for(int vi=0;vi<3;vi++) { String vn; if(vi==0) vn="gc_i"; if(vi==1) vn="v_m_eq"; if(vi==2) vn="noise"; NetMonItem* nm=ncmon->AddLayer(nclay,vn); nm->name_style=NetMonItem::MY_NAME; nm->name=vn; nm->UpdateAfterEdit(); } cout << "CPP_ALL_OBSERVERS" << endl;','CPP_ALL_OBSERVERS')
   if noise:
    s.console('ncspec->noise_type.trial_fixed=true; ncspec->UpdateAfterEdit(); DataTable* nr=.projects[0].data.New(1,taMisc::FindTypeName("DataTable"),"ReferenceNoise"); nr->LoadAnyData('+json.dumps(str(noise_file))+'); cout << "REPLAY_ROWS " << nr->rows << endl;','REPLAY_ROWS '+str(len(rows)))
    code='DataTable* replay=.projects[0].data.FindLeafName("ReferenceNoise"); int rr=network.trial*network.times.quarter*4+network.cycle; for(int ni=0;ni<16;ni++) network.layers[0].GetUnitIdx(ni)->noise=replay->GetVal(ni,rr);'
    s.console('Program* rp=.projects[0].programs.Leaf(4); UserScript* rs=rp->prog_code.New(1,taMisc::FindTypeName("UserScript")); rs->script.expr='+json.dumps(code)+'; rs->UpdateAfterEdit(); rp->prog_code.MoveIdx(rp->prog_code.size-1,0); rp->UpdateAfterEdit(); cout << "REPLAY_HOOK" << endl;','REPLAY_HOOK')
   s.console('ncspec->noise.var='+str(noise)+'; ncspec->kna_adapt.on='+str(adapt).lower()+'; ncspec->UpdateAfterEdit(); ncnet->times.quarter='+str(quarter)+'; ncnet->UpdateAfterEdit(); ns.Init(1); ncepoch->Init(); cout << "CPP_ALL_INIT" << endl;','CPP_ALL_INIT')
   s.run('LeabraEpoch');values=paged_data(s,100*cycles);cols={x['name']:x['values'] for x in values['columns']}
   c.equal('all100_trials_ran',len(cols['cycle']),100*cycles)
   c.equal('correct_cycle_counters',cols['cycle']==[i%cycles+1 for i in range(100*cycles)],True)
   c.equal('correct_trial_counters',cols['run_no']==[i//cycles+1 for i in range(100*cycles)],True)
   for go,cpp in [('Noise','noise'),('Act','act'),('Ge','net'),('Gi','gc_i'),('Vm','v_m_eq'),('KFast','gc_kna_f'),('KMed','gc_kna_m'),('KSlow','gc_kna_s')]:
    maximum=0;at=None;bit_mismatches=0
    for row,actual in zip(rows,cols[cpp]):
     vals=flat(actual);require(len(vals)==16 and all(math.isfinite(x) for x in vals),'nonfinite or wrong-shaped native trace')
     for ui,(a,b) in enumerate(zip(row[go],vals)):
      go_bits=struct.pack("f",a);cpp_bits=struct.pack("f",b)
      bit_mismatches += go_bits != cpp_bits
      delta=abs(struct.unpack("f",go_bits)[0]-struct.unpack("f",cpp_bits)[0])
      if delta>maximum:maximum=delta;at={'trial':row['Trial'],'cycle':row['Cycle'],'unit':ui,'go':a,'cpp':b}
    item['maximum_absolute_differences'][go]={'maximum':maximum,'at':at,'bit_mismatches':bit_mismatches}
   (c.directory/'comparison.json').write_text(json.dumps(item['maximum_absolute_differences'],indent=2)+'\n')
   # No tolerance is widened after observing results. Preserve exact failure data.
   c.equal('noise_replay_exact_float32',item['maximum_absolute_differences']['Noise']['maximum']==0,True)
   for field,comparison in item['maximum_absolute_differences'].items(): c.equal(field+'_exact_float32_bits',comparison['bit_mismatches'],0)
  c.equal('css_diagnostics',[x for x in (c.directory/'emergent.log').read_text(errors='replace').splitlines() if x.startswith(('Warning:','Error:'))],[])
  (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n'); print('PASS',name,item['maximum_absolute_differences']['Act'],flush=True);del reference,rows,values,cols;gc.collect()
except Exception as e:report.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],args.output/'report.json',flush=True)
