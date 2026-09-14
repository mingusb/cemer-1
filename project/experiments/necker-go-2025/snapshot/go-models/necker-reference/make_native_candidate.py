#!/usr/bin/env python3
"""Build a native artifact candidate for the pinned current Go Necker model."""
import base64,hashlib,html,json,shutil,re
from pathlib import Path
from types import SimpleNamespace
from modern_stack_regressions import Case,Server
root=Path('/home/b/cemer');base=root/'artifacts/go-models';out=base/'necker-native-candidate1';out.mkdir(exist_ok=False)
args=SimpleNamespace(output=out/'generation',binary=root/'project/tools/run-emergent',timeout=120);args.output.mkdir()
case=Case(args,'generate');case.fixture=case.directory/'necker_cube.proj';source=root/'artifacts/corpus-necker/staged-final/necker_cube.proj';shutil.copy2(source,case.fixture)
readme=(base/'ccn-sims/ch3/necker_cube/README.md').read_text();figure=(base/'ccn-sims/ch3/necker_cube/fig_necker_cube.png').read_bytes()
intro='<html><head><meta charset="utf-8"><style>body{font:16px sans-serif;line-height:1.45;padding:14px;color:#17212b;background:white}pre{white-space:pre-wrap;font:inherit}img{max-width:100%}</style></head><body><h1>Necker Cube — current Go model port candidate</h1><p>Source: CompCogNeuro/sims revision619a8bf, with its pinned Leabra79e931d engine. This candidate uses Emergent’s native network, controls and 3D display. It maps the current potassium reversal potential0.25 and preserves adaptation channels between trials using native project code. Run executes100 trials. Init resets the run; Step Trial or Step Cycle shows settling. The native quarter_cycles field is one quarter of Cycles:25 means100;250 means1000.</p><p>The current source adds Gaussian noise to excitatory conductance Ge, despite the README’s older membrane-noise wording. The original model README follows. Cross-language acceptance is recorded separately; this artifact is not yet a released validated port.</p><img width="603" height="193" alt="The Necker Cube and its two interpretations" src="data:image/png;base64,'+base64.b64encode(figure).decode()+'"><pre>'+html.escape(readme)+'</pre><p>Go simulation: Emergent Authors, BSD license. Native host project derives from Randall C.O’Reilly’s GPLv2 C++ tutorial. Original cube figure: CC BY-SA3.0, CCNLab/Regents of University of Colorado.</p></body></html>'
(out/'necker_cube.html').write_text(intro);shutil.copy2(base/'ccn-sims/LICENSE',out/'GO-LICENSE');shutil.copy2(base/'ccn-sims/ch3/necker_cube/README.md',out/'GO-README.md')
# The Go engine resets aggregate Gk but retains its three adaptation channels at
# trial start. Native C++ resets the channels too. Correct only the first-cycle
# recurrence using saved channel states after Vm/Act used the zero aggregate.
code='''LeabraLayer* go_layer=network.layers[0];
LeabraUnitSpec* go_spec=network.specs[0];
DataTable* go_memory=.projects[0].data.FindLeafName("GoAdaptationState");
float_Matrix* go_previous=go_memory->GetValAsMatrix("Channels",0);
if(network.cycle==1 && network.trial>0 && go_spec->kna_adapt.on) {
  for(int go_i=0;go_i<16;go_i++) {
    LeabraUnit* go_u=go_layer->GetUnitIdx(go_i);
    float go_rate=go_u->act_raw*go_spec->kna_adapt.rate_rise;
    float go_f=go_previous[go_i,0]; float go_m=go_previous[go_i,1]; float go_s=go_previous[go_i,2];
    go_u->gc_kna_f=go_spec->kna_adapt.f_on ? go_f+go_rate*go_spec->kna_adapt.f_rise*(go_spec->kna_adapt.f_max-go_f)-go_spec->kna_adapt.f_dt*go_f : 0;
    go_u->gc_kna_m=go_spec->kna_adapt.m_on ? go_m+go_rate*go_spec->kna_adapt.m_rise*(go_spec->kna_adapt.m_max-go_m)-go_spec->kna_adapt.m_dt*go_m : 0;
    go_u->gc_kna_s=go_spec->kna_adapt.s_on ? go_s+go_rate*go_spec->kna_adapt.s_rise*(go_spec->kna_adapt.s_max-go_s)-go_spec->kna_adapt.s_dt*go_s : 0;
  }
}
if(network.cycle==4*network.times.quarter) {
  for(int go_i=0;go_i<16;go_i++) {
    LeabraUnit* go_u=go_layer->GetUnitIdx(go_i);
    go_previous[go_i,0]=go_u->gc_kna_f; go_previous[go_i,1]=go_u->gc_kna_m; go_previous[go_i,2]=go_u->gc_kna_s;
  }
}
if(network.cycle==1 && clear_cycle_log) {
  DataTable* go_cycles=.projects[0].data.FindLeafName("CycleOutputData"); go_cycles->ResetData();
}
update_net_view=(network.cycle%10==0);
'''
with Server(case) as s:
 s.console('LeabraNetwork* gn=.projects[0].networks[0]; LeabraUnitSpec* gs=gn->specs[0]; gs->e_rev.k=0.25; gs->UpdateAfterEdit(); DataTable* gi=.projects[0].data.FindLeafName("StdInputData"); gi->DuplicateRow(0,99); DataTable* gm=.projects[0].data.New(1,taMisc::FindTypeName("DataTable"),"GoAdaptationState"); gm->NewColMatrix(DataCol::VT_FLOAT,"Channels",2,16,3); gm->AddRows(1); gm->InitVals(0); cout << "GO_CANDIDATE_ROWS " << gi->rows << endl;','GO_CANDIDATE_ROWS 100')
 s.console('Program* gp=.projects[0].programs.Leaf(4); ProgVar* gc=gp->vars.New(1,taMisc::FindTypeName("ProgVar"),"clear_cycle_log"); gc->SetBool(true); UserScript* gh=gp->prog_code.New(1,taMisc::FindTypeName("UserScript")); gh->script.expr='+json.dumps(code)+'; gh->UpdateAfterEdit(); gp->prog_code.MoveIdx(gp->prog_code.size-1,1); gp->UpdateAfterEdit(); String gd; gd.LoadFromFile('+json.dumps(str(out/'necker_cube.html'))+'); .projects[0].docs[0].text=gd; .projects[0].docs[0].UpdateAfterEdit(); .projects[0].SaveCopy('+json.dumps(str(out/'necker_cube.proj'))+'); cout << "GO_CANDIDATE_SAVED" << endl;','GO_CANDIDATE_SAVED')
(out/'provenance.json').write_text(json.dumps({'status':'CANDIDATE_UNDER_VALIDATION','source_repository':'https://github.com/CompCogNeuro/sims','revision':'619a8bf188722ab0ea68dd73f4d83446dbea0567','source_path':'ch3/necker_cube','model_pinned_engine':'79e931d6fe3b','native_base_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'project_sha256':hashlib.sha256((out/'necker_cube.proj').read_bytes()).hexdigest(),'changes':['Map Erev.K from0.1 to current Go default0.25.','Use100 all-one input trials as in current Go looper.','Preserve three KNa channels across trials, while first-cycle Vm/Act uses decayed aggregateGk; native UserScript recurrence.','Keep only current trial cycle log, as in Go ResetLogBelow.','Refresh native view every10cycles, matching Go GUI interval.'],'limits':['Cross-language all100-trial validation pending.','Native quarter_cycles maps authored100/1000-cycle exercises; arbitrary nonmultiples-of-four GoCycles not yet mapped.','Original Go PlusPhase flag stays at75 after changingCycles1000; native quarter phase follows750. This nonlearning Input-layer task does not use target clamping, but internal phase flags are not yet equivalent.'],'generation_checks':case.checks},indent=2)+'\n')
print('CANDIDATE',out/'necker_cube.proj')
