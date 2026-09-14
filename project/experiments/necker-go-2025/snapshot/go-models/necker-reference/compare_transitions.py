import json,math,hashlib,sys
from pathlib import Path
root=Path('/home/b/cemer/artifacts/go-models');native=root/'necker-native-validation5';report={'status':'PASS','cases':[]}
def flat(v):return sum((flat(x) for x in v),[]) if isinstance(v,list) else [v]
def transitions(rows):
 result=[];old=0
 for i,a in enumerate(rows):
  d=sum(a[:8])/8-sum(a[8:])/8;state=1 if d>.5 else -1 if d<-.5 else 0
  if state and state!=old:result.append([i+1,state]);old=state
 return result
for name,cycles in [('zero-noise',100),('zero-noise-adaptation',1000),('authored-default',100),('authored-adaptation',1000)]:
 gofile=root/'necker-reference/traces-all'/f'{name}.json';cppfile=native/name/'cycles.json'
 if not cppfile.exists():raise RuntimeError(f'{name} native trace not complete')
 go=json.loads(gofile.read_text())['Rows'];cpp={x['name']:x['values'] for x in json.loads(cppfile.read_text())['columns']};acts=[flat(x) for x in cpp['act']]
 item={'name':name,'trials':[],'reference_sha256':hashlib.sha256(gofile.read_bytes()).hexdigest(),'native_sha256':hashlib.sha256(cppfile.read_bytes()).hexdigest()};report['cases'].append(item)
 for trial in range(100):
  start=trial*cycles;gt=transitions([r['Act'] for r in go[start:start+cycles]]);ct=transitions(acts[start:start+cycles]);same=[x[1] for x in gt]==[x[1] for x in ct];timing=max([abs(a[0]-b[0]) for a,b in zip(gt,ct)],default=0) if same else None
  item['trials'].append({'trial':trial,'go_transitions':gt,'native_transitions':ct,'same_order':same,'maximum_cycle_timing_difference':timing})
 item['same_order_all100']=all(x['same_order'] for x in item['trials']);item['maximum_cycle_timing_difference']=max((x['maximum_cycle_timing_difference'] for x in item['trials'] if x['maximum_cycle_timing_difference'] is not None),default=0)
 if not item['same_order_all100']:report['status']='FAIL'
 print(name,item['same_order_all100'],item['maximum_cycle_timing_difference'],flush=True)
(native/'transition-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
