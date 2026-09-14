"""Compile/link an isolated exact-Go activation kernel; no shared outputs touched."""
import json,shlex,subprocess,hashlib,os
from pathlib import Path
root=Path('/home/b/cemer');out=root/'artifacts/go-models/necker-go-numerics-experiment';build=root/'build-modern-final';source=root/'project';private=out/'prefix';private.mkdir(exist_ok=True);(private/'lib').mkdir(exist_ok=True)
frozen=root/'install-legacy-checkpoint'
for path in frozen.iterdir():
 if path.name=='lib':continue
 dest=private/path.name
 if not dest.exists():dest.symlink_to(path,target_is_directory=path.is_dir())
for path in (frozen/'lib').iterdir():
 if path.name.startswith('libemergentlib.so'):continue
 dest=private/'lib'/path.name
 if not dest.exists():dest.symlink_to(path,target_is_directory=path.is_dir())
c=next(x for x in json.loads((source/'build/compile_commands.json').read_text()) if x['file'].endswith('LeabraUnitSpec_cpp.cpp'));command=shlex.split(c['command']);command[1:1]=['-I'+str(out/'include'),'-I'+str(source/'src/emergent/leabra')];command[command.index('-c')+1]=str(out/'LeabraUnitSpec_cpp.cpp');command[command.index('-o')+1]=str(out/'LeabraUnitSpec_cpp.cpp.o');(out/'private-compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
with (out/'private-compile.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,cwd=c['directory'])
line=next(x for x in reversed((root/'artifacts/go-models/necker-reference/native-link-commands.txt').read_text().splitlines()) if '-shared' in x and 'libemergentlib.so' in x);parts=shlex.split(line);assert parts[:2]==[':','&&'] and parts[-2:]==['&&',':'];parts=parts[2:-2]
for i,arg in enumerate(parts):
 if arg.endswith('LeabraUnitSpec_cpp.cpp.o'):parts[i]=str(out/'LeabraUnitSpec_cpp.cpp.o')
 elif arg.startswith('--dependency-file='):parts[i]='--dependency-file='+str(out/'private-link.d')
parts[parts.index('-o')+1]=str(private/'lib/libemergentlib.so.8.6.1')
(out/'private-link-command.json').write_text(json.dumps(parts,indent=2)+'\n')
with (out/'private-link.log').open('w') as log:subprocess.run(parts,stdout=log,stderr=subprocess.STDOUT,check=True,cwd=build)
for name in ['libemergentlib.so','libemergentlib.so.8']:
 dest=private/'lib'/name
 if not dest.exists():dest.symlink_to('libemergentlib.so.8.6.1')
(out/'private-build.json').write_text(json.dumps({'status':'BUILT_ISOLATED_EXPERIMENT','frozen_prefix':str(frozen),'private_prefix':str(private),'replacement_objects':['LeabraUnitSpec_cpp.cpp.o'],'changes':['Pinned Go FastExp quartic spline and exponent>50 cutoff in both NoisyXX1 paths; no ABI or field changes. Also allow negative integrated Ge exactly as pinned Go GFromRaw and sum current E+L+I+K in pinned Go order.'],'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [out/'LeabraUnitSpec_cpp.cpp.o',private/'lib/libemergentlib.so.8.6.1'] }},indent=2)+'\n')
print('PRIVATE_PREFIX',private,flush=True)
