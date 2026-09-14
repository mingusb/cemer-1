import json,struct,math
from pathlib import Path
p=Path('/home/b/cemer/artifacts/go-models');g=json.load(open(p/'necker-reference/traces-all/authored-adaptation.json'))['Rows'];c={x['name']:x['values'] for x in json.load(open(p/'necker-native-validation5/authored-adaptation/cycles.json'))['columns']}
def flat(v):return sum((flat(x) for x in v),[]) if isinstance(v,list) else [v]
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
r={'earliest_float32_bit_differences':{},'trial_activation_maxima':[]}
for go,cpp in [('Noise','noise'),('Act','act'),('Ge','net'),('Gi','gc_i'),('Vm','v_m_eq'),('KFast','gc_kna_f'),('KMed','gc_kna_m'),('KSlow','gc_kna_s')]:
 first=None
 for i,row in enumerate(g):
  for ui,(a,b) in enumerate(zip(row[go],flat(c[cpp][i]))):
   a=f32(a);b=f32(b)
   if a!=b:first={'trial':row['Trial'],'cycle':row['Cycle'],'unit':ui,'go':a,'cpp':b,'delta':a-b};break
  if first:break
 r['earliest_float32_bit_differences'][go]=first
for t in range(100):
 ds=[]
 for i in range(t*1000,(t+1)*1000):ds.append(max(abs(f32(a)-f32(b)) for a,b in zip(g[i]['Act'],flat(c['act'][i]))))
 r['trial_activation_maxima'].append({'trial':t,'max':max(ds),'cycle':ds.index(max(ds))+1,'first_cycle_over_01':next((i+1 for i,x in enumerate(ds) if x>.01),None)})
(p/'necker-native-validation5/earliest-mismatch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['earliest_float32_bit_differences'],indent=2));print('first_over_01',next(x for x in r['trial_activation_maxima'] if x['max']>.01))
