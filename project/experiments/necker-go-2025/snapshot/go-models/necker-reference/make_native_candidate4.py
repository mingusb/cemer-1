import json,shutil,hashlib
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
r=Path('/home/b/cemer');b=r/'artifacts/go-models';o=b/'necker-native-candidate4';shutil.copytree(b/'necker-native-candidate1',o,ignore=shutil.ignore_patterns('generation'));(o/'generation').mkdir();c=Case(SimpleNamespace(output=o/'generation',binary=r/'project/tools/run-emergent',timeout=60),'generate');c.fixture=c.directory/'necker_cube.proj';shutil.copy2(o/'necker_cube.proj',c.fixture)
code='''if(network.cycle==0) {
  LeabraLayer* go_layer=network.layers[0];
  for(int go_g=0;go_g<=go_layer->n_ungps;go_g++) {
    LeabraUnGpState_cpp* go_pool=network.GetUnGpState(go_layer->ungp_idx+go_g);
    LeabraLayerSpec* go_layer_spec=go_layer->GetMainLayerSpec();
    float go_decay=go_layer_spec->decay.trial;
    go_pool->acts.avg-=go_decay*go_pool->acts.avg;
    go_pool->acts.max-=go_decay*go_pool->acts.max;
    go_pool->netin.avg-=go_decay*go_pool->netin.avg;
    go_pool->netin.max-=go_decay*go_pool->netin.max;
  }
}'''
with Server(c) as s:
 s.console('Program* gp=.projects[0].programs.Leaf(4); UserScript* gh=gp->prog_code.New(1,taMisc::FindTypeName("UserScript")); gh->script.expr='+json.dumps(code)+'; gh->UpdateAfterEdit(); gp->prog_code.MoveIdx(gp->prog_code.size-1,0); gp->UpdateAfterEdit(); .projects[0].SaveCopy('+json.dumps(str(o/'necker_cube.proj'))+'); cout << "GO_POOL_DECAY_SAVED" << endl;','GO_POOL_DECAY_SAVED')
p=json.loads((o/'provenance.json').read_text());p['project_sha256']=hashlib.sha256((o/'necker_cube.proj').read_bytes()).hexdigest();p['changes'].append('Map current Go per-trial pool activity/conductance average decay before first cycle; native older trial decay omits these averages.');(o/'provenance.json').write_text(json.dumps(p,indent=2)+'\n')
