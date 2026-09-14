import json,shutil
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
r=Path('/home/b/cemer');out=r/'artifacts/go-models/necker-state-probe';out.mkdir(exist_ok=False)
c=Case(SimpleNamespace(output=out,binary=r/'project/tools/run-emergent',timeout=60),'probe');c.fixture=c.directory/'necker_cube.proj';shutil.copy2(r/'artifacts/go-models/necker-native-candidate1/necker_cube.proj',c.fixture)
with Server(c) as s:
 print(s.console('LeabraNetwork* n=.projects[0].networks[0]; LeabraLayer* l=n->layers[0]; LeabraUnGpState_cpp* gp=n->GetUnGpState(l->ungp_idx); cout << "GP_AVG " << gp->acts_eq.avg << endl; gp->acts_eq.avg=0; cout << "GP_DONE" << endl;','GP_DONE'))
