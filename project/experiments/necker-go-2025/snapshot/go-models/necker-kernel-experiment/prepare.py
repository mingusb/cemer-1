import json,shlex,subprocess,hashlib
from pathlib import Path
root=Path('/home/b/cemer');out=root/'artifacts/go-models/necker-kernel-experiment';src=root/'project/src/emergent/leabra/LeabraUnitSpec_mbrs.h';s=src.read_text();s='#include "go_fast_exp.h"\n'+s
for suffix in ['', '_arg']:
 old='return sig_mult_eff'+suffix+' / (1.0f + expf(-(x * sig_gain_nvar)));'
 new='const float exponent=-(x * sig_gain_nvar);\n      if(exponent > 50.0f) return 0.0f;\n      return sig_mult_eff'+suffix+' / (1.0f + GoNxx1FastExp(exponent));'
 assert s.count(old)==1,(suffix,s.count(old));s=s.replace(old,new)
(out/'include/LeabraUnitSpec_mbrs').write_text(s)
(out/'original-header.sha256').write_text(hashlib.sha256(src.read_bytes()).hexdigest()+'\n')
c=next(x for x in json.loads((root/'project/build/compile_commands.json').read_text()) if x['file'].endswith('LeabraUnitSpec_cpp.cpp'));command=shlex.split(c['command']);oi=command.index('-o');command=command[:oi]+command[oi+2:];ci=command.index('-c');command=command[:ci]+command[ci+2:];command[1:1]=['-I'+str(out/'include')];command += ['-fuse-ld=lld','/home/b/toolchains/Qt/lib/libQt6Core.so','-Wl,-rpath,/home/b/toolchains/Qt/lib','-fsanitize=undefined','-fno-sanitize-recover=all',str(out/'oracle.cpp'),'-o',str(out/'oracle')]
(out/'oracle-compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
with (out/'oracle-compile2.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,cwd=c['directory'])
