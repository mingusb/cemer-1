import json,struct,gc
from pathlib import Path
p=Path('/home/b/cemer/artifacts/go-models');names=[('necker-kernel-validation2','authored-adaptation'),('necker-kernel-validation3','authored-adaptation'),('necker-kernel-ge-validation1','authored-high-noise')]
def flat(v):return sum((flat(x) for x in v),[]) if isinstance(v,list) else [v]
def bits(x):return struct.pack('f',x)
for directory,name in names:
 g=json.load(open(p/'necker-reference/traces-all'/f'{name}.json'))['Rows'];c={x['name']:x['values'] for x in json.load(open(p/directory/name/'cycles.json'))['result']['columns']};r={}
 for a,b in [('Act','act'),('Ge','net'),('Gi','gc_i'),('Vm','v_m_eq'),('KFast','gc_kna_f'),('KMed','gc_kna_m'),('KSlow','gc_kna_s')]:
  first=None
  for i,row in enumerate(g):
   for u,(x,y) in enumerate(zip(row[a],flat(c[b][i]))):
    if bits(x)!=bits(y):first={'trial':row['Trial'],'cycle':row['Cycle'],'unit':u,'go':x,'cpp':y};break
   if first:break
  r[a]=first
 (p/directory/'earliest-mismatch.json').write_text(json.dumps(r,indent=2)+'\n');print(directory,json.dumps(r),flush=True);del g,c;gc.collect()
