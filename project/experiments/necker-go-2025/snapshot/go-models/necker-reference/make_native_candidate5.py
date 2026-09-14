import ast,json,shutil,hashlib,re
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
r=Path('/home/b/cemer');b=r/'artifacts/go-models';o=b/'necker-native-candidate5';shutil.copytree(b/'necker-native-candidate4',o,ignore=shutil.ignore_patterns('generation'));(o/'generation').mkdir();c=Case(SimpleNamespace(output=o/'generation',binary=r/'project/tools/run-emergent',timeout=60),'generate');c.fixture=c.directory/'necker_cube.proj';shutil.copy2(o/'necker_cube.proj',c.fixture)
a=ast.parse((b/'necker-reference/make_native_candidate.py').read_text());code=next(ast.literal_eval(x.value) for x in a.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in x.targets))
new='''go_u->gc_kna_f=go_previous[go_i,0];
    go_u->gc_kna_m=go_previous[go_i,1];
    go_u->gc_kna_s=go_previous[go_i,2];
    go_spec->kna_adapt.Compute_dKNa_rate(go_u->act_raw,go_u->gc_kna_f,go_u->gc_kna_m,go_u->gc_kna_s);'''
code,n=re.subn(r'float go_rate=.*?go_u->gc_kna_s=.*?;',new,code,flags=re.S);assert n==1
with Server(c) as s:
 s.console('Program* gp=.projects[0].programs.Leaf(4); UserScript* gh=gp->prog_code[2]; gh->script.expr='+json.dumps(code)+'; gh->UpdateAfterEdit(); gp->UpdateAfterEdit(); .projects[0].SaveCopy('+json.dumps(str(o/'necker_cube.proj'))+'); cout << "GO_NATIVE_CHANNEL_RECURRENCE_SAVED" << endl;','GO_NATIVE_CHANNEL_RECURRENCE_SAVED')
p=json.loads((o/'provenance.json').read_text());p['project_sha256']=hashlib.sha256((o/'necker_cube.proj').read_bytes()).hexdigest();p['changes'].append('Use existing native KNaAdaptSpec.Compute_dKNa_rate on restored channels after first-cycle act; preserves float32 expression ordering instead of CSS double intermediates.');(o/'provenance.json').write_text(json.dumps(p,indent=2)+'\n')
