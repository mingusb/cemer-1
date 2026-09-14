import json,shutil,hashlib
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
r=Path('/home/b/cemer');b=r/'artifacts/go-models';o=b/'necker-native-candidate6';shutil.copytree(b/'necker-native-candidate5',o,ignore=shutil.ignore_patterns('generation'));(o/'generation').mkdir();c=Case(SimpleNamespace(output=o/'generation',binary=r/'project/tools/run-emergent',timeout=60),'generate');c.fixture=c.directory/'necker_cube.proj';shutil.copy2(o/'necker_cube.proj',c.fixture)
with Server(c) as s:
 s.console('LeabraLayerSpec* gls=.projects[0].networks[0].specs[2]; gls->inhib_misc.net_thr=-3.4028234663852886e38; gls->inhib_misc.thr_rel=false; gls->UpdateAfterEdit(); .projects[0].SaveCopy('+json.dumps(str(o/'necker_cube.proj'))+'); cout << "GO_INCLUSIVE_GE_STATISTICS_SAVED" << endl;','GO_INCLUSIVE_GE_STATISTICS_SAVED')
p=json.loads((o/'provenance.json').read_text());p['project_sha256']=hashlib.sha256((o/'necker_cube.proj').read_bytes()).hexdigest();p['changes'].append('Map Go inclusive poolGe statistics using native absolute net_thr=-FLT_MAX and thr_rel=false.');(o/'provenance.json').write_text(json.dumps(p,indent=2)+'\n')
