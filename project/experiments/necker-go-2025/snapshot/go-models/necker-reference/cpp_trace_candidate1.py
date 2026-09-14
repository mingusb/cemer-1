import os,json,shutil,sys
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
sys.path.insert(0,'/home/b/cemer/artifacts/corpus-necker')
from necker_regressions import setup,trial
root=Path('/home/b/cemer');args=SimpleNamespace(output=root/'artifacts/go-models/necker-cpp-candidate1-traces',binary=root/'project/tools/run-emergent',timeout=120)
args.output.mkdir(exist_ok=False)
for name,noise,adapt,quarter in [('zero-noise',0,False,25),('zero-noise-adaptation',0,True,250),('authored-default',.01,False,25),('authored-adaptation',.01,True,250)]:
 c=Case(args,name);c.fixture=c.directory/'necker_cube.proj';shutil.copy2(root/'artifacts/corpus-necker/staged-final/necker_cube.proj',c.fixture)
 with Server(c) as s:
  setup(s)
  s.console('ncspec->e_rev.k=0.25; ncspec->UpdateAfterEdit(); cout << "CPP_GO_EREV" << endl;','CPP_GO_EREV')
  s.console('for(int vi=0;vi<3;vi++) { String vn; if(vi==0) vn="gc_i"; if(vi==1) vn="v_m_eq"; if(vi==2) vn="noise"; NetMonItem* nm=ncmon->AddLayer(nclay,vn); nm->name_style=NetMonItem::MY_NAME; nm->name=vn; nm->UpdateAfterEdit(); } cout << "CPP_OBSERVERS" << endl;','CPP_OBSERVERS')
  trial(c,s,name,noise,adapt,quarter,1)
 print('PASS',name,flush=True)
