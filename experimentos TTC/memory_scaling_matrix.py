import argparse, ctypes, datetime as dt, hashlib, importlib, importlib.util, json, os, pathlib, platform, subprocess, sys, tarfile, tempfile, time, sqlite3, shutil
CHUNK=1024*1024
class PMC(ctypes.Structure):
 _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t),('PrivateUsage',ctypes.c_size_t)]
def counters(h):
 p=PMC();p.cb=ctypes.sizeof(p); ps=ctypes.WinDLL('psapi',use_last_error=True);ps.GetProcessMemoryInfo.argtypes=(ctypes.c_void_p,ctypes.POINTER(PMC),ctypes.c_ulong);ps.GetProcessMemoryInfo.restype=ctypes.c_int
 if not ps.GetProcessMemoryInfo(h,ctypes.byref(p),p.cb):raise ctypes.WinError(ctypes.get_last_error())
 return {'ws':int(p.WorkingSetSize),'peak_ws':int(p.PeakWorkingSetSize),'private':int(p.PrivateUsage),'peak_commit':int(p.PeakPagefileUsage)}
def hashfile(p):
 h=hashlib.sha256(); n=0
 with open(p,'rb') as f:
  while True:
   b=f.read(CHUNK)
   if not b:break
   n+=len(b);h.update(b)
 return n,h.hexdigest()
def write_helper(p):
 p.write_text('''import importlib,importlib.util,pathlib,sys,os,builtins,typing\nbuiltins.Optional=typing.Optional\nsys.dont_write_bytecode=True\nos.environ["PYTHONDONTWRITEBYTECODE"]="1"\nb=pathlib.Path(sys.argv[1]);spec=importlib.util.spec_from_file_location("babel_probe",b/"__init__.py",submodule_search_locations=[str(b)]);m=importlib.util.module_from_spec(spec);sys.modules["babel_probe"]=m;spec.loader.exec_module(m);cli=importlib.import_module("babel_probe.cli");sys.argv=["babel",*sys.argv[2:]];cli.main()\n''',encoding='utf-8')
def measured(cmd,env,log):
 flags=getattr(subprocess,'CREATE_NO_WINDOW',0); start=time.perf_counter()
 with open(log,'w',encoding='utf-8',errors='replace') as f:
  p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,creationflags=flags)
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=(ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong);k.OpenProcess.restype=ctypes.c_void_p;k.CloseHandle.argtypes=(ctypes.c_void_p,);k.CloseHandle.restype=ctypes.c_int
  h=k.OpenProcess(0x0400|0x1000,False,p.pid)
  if not h: p.kill();raise ctypes.WinError(ctypes.get_last_error())
  ws=commit=0
  while p.poll() is None:
   try:
    c=counters(h);ws=max(ws,c['ws'],c['peak_ws']);commit=max(commit,c['private'],c['peak_commit'])
   except OSError:pass
   time.sleep(.05)
  code=p.wait();elapsed=time.perf_counter()-start
  try:
   c=counters(h);ws=max(ws,c['peak_ws']);commit=max(commit,c['peak_commit'])
  except OSError:pass
  k.CloseHandle(h)
 return code,ws,commit,elapsed,pathlib.Path(log).read_text(encoding='utf-8',errors='replace')
def main():
 if os.name!='nt':raise SystemExit('Windows required')
 ap=argparse.ArgumentParser();ap.add_argument('--babel-dir',required=True);ap.add_argument('--experiment-dir',required=True);a=ap.parse_args();bdir=pathlib.Path(a.babel_dir).resolve();edir=pathlib.Path(a.experiment_dir).resolve();work=edir/'_work';work.mkdir(parents=True,exist_ok=True)
 outj=edir/'memory_scaling_matrix_result.json';outr=edir/'memory_scaling_matrix_report.md'
 if outj.exists() or outr.exists():raise SystemExit('Artifacts exist; refusing overwrite')
 now=dt.datetime.now().astimezone().isoformat(timespec='seconds'); helper=work/'invoke_cli_memory_matrix.py';write_helper(helper);env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONIOENCODING']='utf-8'; py=sys.executable
 sources=sorted(bdir.glob('*.py'));source_hashes=[{'path':str(p),'sha256':hashfile(p)[1]} for p in sources]
 records=[]
 with tempfile.TemporaryDirectory(prefix='babel_memory_matrix_',dir=work) as t:
  root=pathlib.Path(t)
  for n in (100_000_000,300_000_000,1_000_000_000):
   d=root/f'random_{n}';d.mkdir();src=d/'input.bin';db=d/'babel.sqlite';dest=d/'out.bin';log=d/'cli.log';h=hashlib.sha256();remaining=n
   with src.open('wb') as f:
    while remaining:
     block=os.urandom(min(CHUNK,remaining));f.write(block);h.update(block);remaining-=len(block)
   srcsha=h.hexdigest(); env['BABEL_PROBE_BASELINE']=str(d/'base.json')
   init=subprocess.run([py,str(helper),str(bdir),'--package',str(db),'import',str(d/'nonexistent.babel')],capture_output=True,env=env,text=True,encoding='utf-8',errors='replace')
   # Initialize using package.create directly in a short helper mode, through the actual package API.
   init_code='''import importlib.util,pathlib,sys,builtins,typing\nbuiltins.Optional=typing.Optional\nb=pathlib.Path(sys.argv[1]);s=importlib.util.spec_from_file_location("babel_probe",b/"__init__.py",submodule_search_locations=[str(b)]);m=importlib.util.module_from_spec(s);sys.modules["babel_probe"]=m;s.loader.exec_module(m);from babel_probe.package import BabelPackage;BabelPackage(sys.argv[2]).create()'''
   init=subprocess.run([py,'-c',init_code,str(bdir),str(db)],capture_output=True,env=env,text=True,encoding='utf-8',errors='replace')
   if init.returncode:raise RuntimeError('package init failed: '+init.stderr)
   code,ws,commit,elapsed,logtxt=measured([py,str(helper),str(bdir),'--package',str(db),'add',str(src),'--path',src.name],env,log)
   entry={'case':f'random_{n}','operation':'add','input_bytes':n,'input_sha256':srcsha,'exit_code':code,'peak_working_set_bytes':ws,'peak_commit_bytes':commit,'duration_seconds':round(elapsed,3),'cli_output':logtxt.strip(),'integrity_verified':False,'status':'FAILED' if code else 'ADDED'}
   if code==0:
    dbget=d/'babel.sqlite';code2,ws2,c2,t2,log2=measured([py,str(helper),str(bdir),'--package',str(dbget),'get',src.name,'--output',str(dest)],env,d/'get.log')
    # CLI get expects logical path; source.name used as alias path above.
    gotn,gotsha=hashfile(dest) if dest.exists() else (None,None);ok=gotn==n and gotsha==srcsha
    records.append(entry);records.append({'case':f'random_{n}','operation':'get','input_bytes':n,'input_sha256':srcsha,'exit_code':code2,'peak_working_set_bytes':ws2,'peak_commit_bytes':c2,'duration_seconds':round(t2,3),'output_bytes':gotn,'output_sha256':gotsha,'integrity_verified':ok,'cli_output':log2.strip(),'status':'PASS' if code2==0 and ok else 'FAIL'})
   else:
    entry['failure_stage']='actual add CLI; see captured output';entry['get_status']='BLOCKED: add did not create retrievable item';records.append(entry)
   print(f'{n} add: exit={code}, WS={ws:,}, commit={commit:,}, {elapsed:.1f}s',flush=True)
  # Deterministic tarball of actual Python implementation files (real code, not synthetic).
  d=root/'real_code';d.mkdir();tarpath=d/'babel_sources.tar';
  with tarfile.open(tarpath,'w') as tf:
   for p in sources:
    info=tf.gettarinfo(str(p),arcname=p.name);info.mtime=0
    with p.open('rb') as f:tf.addfile(info,f)
  codebytes,codesha=hashfile(tarpath);db=d/'babel.sqlite';init=subprocess.run([py,'-c',init_code,str(bdir),str(db)],capture_output=True,env=env,text=True,encoding='utf-8',errors='replace')
  if init.returncode:raise RuntimeError('package init failed for code case: '+init.stderr)
  env['BABEL_PROBE_BASELINE']=str(d/'base.json')
  c,ws,cm,t,log=measured([py,str(helper),str(bdir),'--package',str(db),'add',str(tarpath),'--path','babel_sources.tar'],env,d/'add.log')
  records.append({'case':'real_babel_python_sources_tar','operation':'add','input_bytes':codebytes,'input_sha256':codesha,'exit_code':c,'peak_working_set_bytes':ws,'peak_commit_bytes':cm,'duration_seconds':round(t,3),'cli_output':log.strip(),'status':'PASS' if c==0 else 'FAIL'})
  if c==0:
   dest=d/'recovered.tar';c2,w2,cm2,t2,l2=measured([py,str(helper),str(bdir),'--package',str(db),'get','babel_sources.tar','--output',str(dest)],env,d/'get.log');rn,rh=hashfile(dest) if dest.exists() else (None,None);records.append({'case':'real_babel_python_sources_tar','operation':'get','input_bytes':codebytes,'input_sha256':codesha,'exit_code':c2,'peak_working_set_bytes':w2,'peak_commit_bytes':cm2,'duration_seconds':round(t2,3),'output_bytes':rn,'output_sha256':rh,'integrity_verified':rn==codebytes and rh==codesha,'cli_output':l2.strip(),'status':'PASS' if c2==0 and rn==codebytes and rh==codesha else 'FAIL'})
 result={'timestamp_local':now,'machine':platform.platform(),'python':sys.version,'python_executable':py,'babel_dir':str(bdir),'babel_python_source_sha256':source_hashes,'method':'Actual current CLI add/get in isolated child processes; Windows GetProcessMemoryInfo sampled every 50 ms; inputs generated before measurement in 1 MiB blocks; temporary database and inputs deleted after test. Random bytes from os.urandom; actual Python sources bundled as deterministic tar for compressible-code case.','criterion':'For 1 GB compared to 100 MB: peak WS and commit growth <= 50,000,000 bytes. Integrity requires exact output byte count and SHA-256.','records':records}
 outj.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
 lines=['# Matriz de memória da Babel — add/get','',f'Data: {now}',f'Máquina: {platform.platform()}',f'Python: {sys.version.split()[0]} (`{py}`)','',f'Babel testada: `{bdir}`. SHA-256 dos arquivos Python atuais registrados no JSON: `{outj.name}`. Nenhum arquivo da Babel foi editado.','', '## Método','', 'CLI atual real em subprocesso isolado para add e get; pico via Windows GetProcessMemoryInfo amostrado a cada 50 ms (inclui high-water counters); fonte aleatória preparada antes da medição com `os.urandom` em blocos de 1 MiB; dados temporários limpos ao final. Caso de código real é tar determinístico dos arquivos Python da implementação atual.','', 'Critério relativo: pico de 1 GB deve ser no máximo pico de 100 MB + 50.000.000 bytes, tanto WS quanto commit. A integridade do get exige tamanho e SHA-256 iguais.','', '## Resultados','', '| Caso | Operação | Entrada (bytes) | Pico WS (bytes) | Pico commit (bytes) | Tempo (s) | Exit | Integridade/status |','|---|---:|---:|---:|---:|---:|---:|---|']
 for r in records:lines.append(f"| {r['case']} | {r['operation']} | {r.get('input_bytes','')} | {r.get('peak_working_set_bytes','')} | {r.get('peak_commit_bytes','')} | {r.get('duration_seconds','')} | {r.get('exit_code','')} | {r.get('status','')}{'; get '+('verificado' if r.get('integrity_verified') else 'não verificado') if r['operation']=='get' else ''} |")
 lines+=['','## Comando de reprodução','','```powershell',f"& '{py}' '{edir / 'memory_scaling_matrix.py'}' --babel-dir '{bdir}' --experiment-dir '{edir}'",'```','','## Evidência detalhada','',f'Os logs do CLI, tamanhos, SHA-256 de entrada/saída, erros e medições por execução estão em `{outj.name}`.']
 outr.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({'report':str(outr),'raw':str(outj),'records':records},ensure_ascii=False,indent=2))
if __name__=='__main__':main()



