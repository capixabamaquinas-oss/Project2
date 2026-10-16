import csv,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent; fix=root/'fixtures'/'x5_cases'; prefix=b'B1:v1:'; limit=4096
worker=root/'03_worker_x5.py'; package=root/'source-copy'; rawlog=root/'x5_boundary_retry_raw.txt'; rawlog.write_text('',encoding='utf-8'); rows=[]
for n in (limit-1,limit,limit+1):
 data=prefix+b'f'*(n-len(prefix)); path=fix/f'lowercase_limit_{n}.txt'; path.write_bytes(data)
 modes=('direct','preflight')
 for mode in modes:
  argv=[sys.executable,'-X','utf8','-I',str(worker),'--package-root',str(package),'--input',str(path),'--mode',mode,'--limit',str(limit)]
  cp=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace')
  with rawlog.open('a',encoding='utf-8') as f:
   f.write('ARGV='+json.dumps(argv,ensure_ascii=True)+'\nRETURN_CODE='+str(cp.returncode)+'\nSTDOUT_BEGIN\n'+cp.stdout+'STDOUT_END\nSTDERR_BEGIN\n'+cp.stderr+'STDERR_END\n')
  if cp.returncode!=0: raise SystemExit('worker failed: '+cp.stderr[-300:])
  result=json.loads(cp.stdout.strip().splitlines()[-1]); result['case']='lowercase_limit_'+str(n); rows.append(result); print('X5_BOUNDARY='+json.dumps(result,sort_keys=True))
with (root/'x5_boundary_verified.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
by={(r['case'],r['mode']):r for r in rows}
assert by[('lowercase_limit_4096','preflight')]['outcome']=='accepted'
assert by[('lowercase_limit_4097','preflight')]['parser_calls']==0
assert by[('lowercase_limit_4097','preflight')]['format_decode_calls']==0
assert by[('lowercase_limit_4097','direct')]['parser_calls']==1
assert by[('lowercase_limit_4097','direct')]['format_decode_calls']==1
print('X5_BOUNDARY_ASSERT=PASS max_is_accepted_plus1_is_preflight_rejected_direct_package_has_no_limit')
