import os,json,shutil,sys
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
sys.path.insert(0,'/home/b/cemer/artifacts/corpus-necker')
from necker_regressions import setup,trial
root=Path('/home/b/cemer');args=SimpleNamespace(output=root/'artifacts/go-models/necker-cpp-noise-replay2',binary=root/'project/tools/run-emergent',timeout=120)
args.output.mkdir(exist_ok=False)
for name,adapt,quarter in [('authored-default',False,25),('authored-adaptation',True,250)]:
 c=Case(args,name);c.fixture=c.directory/'necker_cube.proj';shutil.copy2(root/'artifacts/corpus-necker/staged-final/necker_cube.proj',c.fixture)
 reference=json.loads((root/'artifacts/go-models/necker-reference/traces'/f'{name}.json').read_text());noise=[row['Noise'] for row in reference['Rows'] if row['Trial']==0];noise_file=c.directory/'noise.tsv';noise_file.write_text('\t'.join('Noise'+str(i) for i in range(16))+'\n'+'\n'.join('\t'.join(str(x) for x in row) for row in noise)+'\n')
 with Server(c) as s:
  setup(s)
  s.console('ncspec->e_rev.k=0.25; ncspec->noise_type.trial_fixed=true; ncspec->UpdateAfterEdit(); DataTable* nr=.projects[0].data.New(1,taMisc::FindTypeName("DataTable"),"ReferenceNoise"); nr->LoadAnyData('+json.dumps(str(noise_file))+'); cout << "REPLAY_ROWS " << nr->rows << endl;','REPLAY_ROWS '+str(len(noise)))
  code='DataTable* replay=.projects[0].data.FindLeafName("ReferenceNoise"); for(int ni=0;ni<16;ni++) network.layers[0].GetUnitIdx(ni)->noise=replay->GetVal(ni,network.cycle);'
  s.console('Program* rp=.projects[0].programs.Leaf(4); UserScript* rs=rp->prog_code.New(1,taMisc::FindTypeName("UserScript")); rs->script.expr='+json.dumps(code)+'; rs->UpdateAfterEdit(); rp->prog_code.MoveIdx(rp->prog_code.size-1,0); rp->UpdateAfterEdit(); cout << "REPLAY_HOOK" << endl;','REPLAY_HOOK')
  s.console('for(int vi=0;vi<3;vi++) { String vn; if(vi==0) vn="gc_i"; if(vi==1) vn="v_m_eq"; if(vi==2) vn="noise"; NetMonItem* nm=ncmon->AddLayer(nclay,vn); nm->name_style=NetMonItem::MY_NAME; nm->name=vn; nm->UpdateAfterEdit(); } cout << "CPP_OBSERVERS" << endl;','CPP_OBSERVERS')
  trial(c,s,name,.01,adapt,quarter,1)
 print('PASS',name,flush=True)
